import streamlit as st
import tempfile
import json
import asyncio

import edge_tts
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

# ---------------------------
# INIT
# ---------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="Fast AI Video Generator", layout="centered")
st.title("⚡ AI Transcript → Video Generator")

# ---------------------------
# 🤖 OPENAI CALL
# ---------------------------
def call_ai(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content

# ---------------------------
# 🧹 CLEAN JSON
# ---------------------------
def clean_json(text):
    start = text.find("{")
    end = text.rfind("}") + 1
    return text[start:end]

# ---------------------------
# 🧠 GENERATE CONTENT
# ---------------------------
def generate_all(text):
    raw = call_ai(f"""
Create summary + slides.

STRICT:
- 10 slides
- Max 3 bullet points per slide
- Simple language

Return JSON only:
{{
  "summary": "...",
  "slides": [
    {{
      "title": "...",
      "points": ["...", "..."],
      "explanation": "..."
    }}
  ]
}}

TEXT:
{text}
""")

    try:
        return json.loads(clean_json(raw))
    except:
        st.error("AI JSON failed")
        st.text(raw)
        st.stop()

# ---------------------------
# 🎨 CREATE SLIDE
# ---------------------------
def create_slide(title, points):
    img = Image.new("RGB", (854, 480), "white")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
        point_font = ImageFont.truetype("DejaVuSans.ttf", 25)
    except:
        title_font = ImageFont.load_default()
        point_font = ImageFont.load_default()

    draw.text((40, 20), title, fill="black", font=title_font)

    y = 100
    for p in points:
        draw.text((60, y), f"• {p}", fill="black", font=point_font)
        y += 40

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# 🔊 TTS
# ---------------------------
async def tts_async(text, path):
    communicate = edge_tts.Communicate(
        text=text[:150],
        voice="en-US-AriaNeural"
    )
    await communicate.save(path)

def generate_audio(text):
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(tts_async(text, path))
    loop.close()

    return path

# ---------------------------
# 🎬 CLIP
# ---------------------------
def create_clip(img_path, audio_path):
    audio = AudioFileClip(audio_path)
    duration = max(audio.duration, 5)

    clip = ImageClip(img_path).set_duration(duration)
    clip = clip.set_audio(audio)

    return clip

# ---------------------------
# 🎥 VIDEO
# ---------------------------
def generate_video(slides):
    clips = []

    for i, slide in enumerate(slides):
        st.write(f"Slide {i+1}/{len(slides)}")

        title = slide.get("title", "Untitled")
        points = slide.get("points", [])
        explanation = slide.get("explanation", "")

        img = create_slide(title, points)
        audio = generate_audio(explanation)

        clips.append(create_clip(img, audio))

    final = concatenate_videoclips(clips, method="compose")

    output = "final_video.mp4"
    final.write_videofile(
        output,
        fps=12,
        preset="ultrafast",
        threads=2
    )

    return output

# ---------------------------
# UI
# ---------------------------
files = st.file_uploader(
    "Upload transcript files",
    type=["txt"],
    accept_multiple_files=True
)

if st.button("Generate Video"):

    if not files:
        st.warning("Upload files first")
        st.stop()

    with st.spinner("⚡ Generating..."):

        texts = [f.read().decode("utf-8") for f in files]
        merged = "\n\n".join(texts)

        data = generate_all(merged)

        st.subheader("📄 Summary")
        st.write(data.get("summary", ""))

        video = generate_video(data.get("slides", []))

        st.success("✅ Video Ready!")
        st.video(video)

