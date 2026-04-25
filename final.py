import streamlit as st
from openai import OpenAI
import tempfile
import json
import asyncio

import edge_tts
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont

# ---------------------------
# 🔑 OPENAI CLIENT
# ---------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="Clean AI Video Generator", layout="centered")
st.title("🎬 Clean AI Transcript → Video")

# ---------------------------
# 🧠 OPENAI CALL
# ---------------------------
def call_openai(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6
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
    raw = call_openai(f"""
Create clean presentation slides.

RULES:
- 6 to 7 slides
- Each slide: max 3 bullet points
- Each bullet: short and clear
- Explanation: 20–40 words (natural speech)
- Titles must be short and strong

Return JSON:
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

    raw = clean_json(raw)

    try:
        return json.loads(raw)
    except:
        return {"summary": "", "slides": []}

# ---------------------------
# 🎨 CREATE SLIDE (BIG TEXT)
# ---------------------------
def create_slide(title, points):
    img = Image.new("RGB", (1280, 720), "white")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("arial.ttf", 95)
        point_font = ImageFont.truetype("arial.ttf", 60)
    except:
        title_font = ImageFont.load_default()
        point_font = ImageFont.load_default()

    # Title centered
    draw.text((60, 60), title, fill="black", font=title_font)

    y = 260
    for p in points[:3]:
        draw.text((100, y), f"• {p}", fill="black", font=point_font)
        y += 120

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# 🔊 TTS
# ---------------------------
async def tts_async(text, path):
    communicate = edge_tts.Communicate(
        text=text,
        voice="en-US-AriaNeural"
    )
    await communicate.save(path)

def generate_audio(text):
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name

    # keep narration short but natural
    short_text = text[:180]

    asyncio.run(tts_async(short_text, path))
    return path

# ---------------------------
# 🎬 CREATE CLIP
# ---------------------------
def create_clip(img_path, audio_path):
    audio = AudioFileClip(audio_path)
    clip = ImageClip(img_path).with_duration(audio.duration)
    clip = clip.with_audio(audio)
    return clip

# ---------------------------
# 🎥 GENERATE VIDEO
# ---------------------------
def generate_video(slides):
    clips = []

    for slide in slides[:7]:
        img = create_slide(
            slide.get("title", "Slide"),
            slide.get("points", [])
        )

        audio = generate_audio(slide.get("explanation", ""))
        clip = create_clip(img, audio)

        clips.append(clip)

    if not clips:
        return None

    final = concatenate_videoclips(clips, method="compose")

    output = "final_video.mp4"

    final.write_videofile(
        output,
        fps=12,
        preset="ultrafast",
        threads=4
    )

    return output

# ---------------------------
# 📥 UI
# ---------------------------
files = st.file_uploader(
    "Upload transcript (.txt)",
    type=["txt"],
    accept_multiple_files=True
)

if st.button("Generate Video"):

    if not files:
        st.warning("Upload files first")
        st.stop()

    with st.spinner("⚡ Generating clean video..."):

        texts = [f.read().decode("utf-8") for f in files]
        merged = "\n\n".join(texts)

        data = generate_all(merged)

        st.subheader("📄 Summary")
        st.write(data.get("summary", ""))

        video = generate_video(data.get("slides", []))

        if video:
            st.success("✅ Video Ready!")
            st.video(video)
        else:
            st.error("❌ Failed to generate video")
