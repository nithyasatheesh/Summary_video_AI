import streamlit as st
import tempfile
import json
import asyncio

from openai import OpenAI
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

st.set_page_config(page_title="AI Video Generator", layout="centered")
st.title("🎬 Transcript → Video Generator")

# Debug API key
st.write("🔑 API KEY LOADED:", "OPENAI_API_KEY" in st.secrets)

client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY"))

# ---------------------------
# 🧠 AI CALL
# ---------------------------
def call_ai(prompt):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return res.choices[0].message.content
    except Exception as e:
        st.error(f"❌ OpenAI Error: {e}")
        return None

# ---------------------------
# ✂️ SPLIT TEXT
# ---------------------------
def split_text(text, size=6000):
    return [text[i:i+size] for i in range(0, len(text), size)]

# ---------------------------
# 🧠 CHUNK SUMMARY
# ---------------------------
def summarize_chunks(text):
    chunks = split_text(text)[:5]
    summaries = []

    for i, chunk in enumerate(chunks):
        st.write(f"🔄 Processing chunk {i+1}/{len(chunks)}")
        s = call_ai(f"Extract key concepts only:\n{chunk}")
        if s:
            summaries.append(s)

    return "\n".join(summaries)

# ---------------------------
# 🧠 FINAL CONTENT
# ---------------------------
def generate_all(text):
    raw = call_ai(f"""
Create a 5-minute video script.

Return JSON:
{{
  "summary": "...",
  "slides": [
    {{
      "title": "...",
      "points": ["..."],
      "explanation": "..."
    }}
  ]
}}

TEXT:
{text}
""")

    if not raw:
        return None

    st.write("🧾 RAW AI OUTPUT:", raw)

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception as e:
        st.error(f"❌ JSON Parse Error: {e}")
        return None

# ---------------------------
# 🎨 TEXT WRAP (FIXED)
# ---------------------------
def wrap_text(text, font, max_width, draw):
    lines = []
    words = text.split()
    current = ""

    for word in words:
        test = current + " " + word if current else word

        # ✅ FIX: use textbbox instead of textsize
        bbox = draw.textbbox((0, 0), test, font=font)
        w = bbox[2] - bbox[0]

        if w <= max_width:
            current = test
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines

# ---------------------------
# 🎨 SLIDE IMAGE
# ---------------------------
def create_slide(title, points):
    img = Image.new("RGB", (1280, 720), "white")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("fonts/DejaVuSans-Bold.ttf", 60)
        text_font = ImageFont.truetype("fonts/DejaVuSans.ttf", 40)
    except Exception as e:
        st.warning(f"Font load failed: {e}")
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    draw.text((640, 70), title, fill="black", font=title_font, anchor="mm")

    y = 180
    for p in points:
        lines = wrap_text(p, text_font, 1000, draw)

        for line in lines:
            draw.text((100, y), f"• {line}", fill="black", font=text_font)
            y += 55
        y += 10

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# 🔊 AUDIO
# ---------------------------
async def tts_async(text, path):
    communicate = edge_tts.Communicate(text, voice="en-US-AriaNeural")
    await communicate.save(path)

def generate_audio(text):
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    try:
        asyncio.run(tts_async(text, path))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(tts_async(text, path))
    return path

# ---------------------------
# 🎥 VIDEO
# ---------------------------
def generate_video(slides):
    clips = []

    for i, slide in enumerate(slides):
        try:
            st.write(f"🎞️ Creating slide {i+1}")

            img = create_slide(slide["title"], slide["points"])
            audio = generate_audio(slide["explanation"])

            audio_clip = AudioFileClip(audio)
            clip = ImageClip(img, duration=audio_clip.duration)
            clip = clip.set_audio(audio_clip)

            clips.append(clip)

        except Exception as e:
            st.error(f"❌ Slide error: {e}")

    if not clips:
        return None

    final = concatenate_videoclips(clips)

    output = "video.mp4"
    st.write("⏳ Rendering video...")

    try:
        final.write_videofile(
            output,
            fps=12,
            preset="ultrafast",
            codec="libx264",
            audio_codec="aac"
        )
        return output
    except Exception as e:
        st.error(f"❌ Video render error: {e}")
        return None

# ---------------------------
# 📥 UI
# ---------------------------
files = st.file_uploader(
    "Upload transcripts",
    type=["txt"],
    accept_multiple_files=True
)

if st.button("Generate Video"):

    st.write("🚀 Button clicked")

    if not files:
        st.warning("Upload files")
        st.stop()

    texts = [f.read().decode("utf-8") for f in files]
    merged = "\n\n".join(texts)

    st.write("📄 Input length:", len(merged))

    st.write("⚡ Step 1: Summarizing...")
    chunk_summary = summarize_chunks(merged)

    st.write("🧠 Step 2: Generating slides...")
    data = generate_all(chunk_summary)

    if not data:
        st.error("AI failed")
        st.stop()

    st.write("📊 Slides generated:", len(data.get("slides", [])))

    st.subheader("📄 Summary")
    st.write(data["summary"])

    st.write("🎬 Step 3: Generating video...")
    video = generate_video(data["slides"])

    if video:
        st.success("✅ Video Ready!")
        st.video(video)
    else:
        st.error("❌ Video failed")
