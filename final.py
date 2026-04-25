import streamlit as st
import ollama
import tempfile
import json
import asyncio

import edge_tts
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Fast AI Video Generator", layout="centered")
st.title("⚡ Fast AI Transcript → Video Generator")

# ---------------------------
# 🧠 OLLAMA CALL
# ---------------------------
def call_ollama(prompt):
    res = ollama.chat(
        model="llama3",
        messages=[{"role": "user", "content": prompt}]
    )
    return res["message"]["content"]

# ---------------------------
# 🧹 CLEAN JSON
# ---------------------------
def clean_json(text):
    start = text.find("{")
    end = text.rfind("}") + 1
    return text[start:end]

# ---------------------------
# 🧠 AI GENERATION
# ---------------------------
def generate_all(text):
    raw = call_ollama(f"""
Create summary + slides.

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
    raw = clean_json(raw)
    return json.loads(raw)

# ---------------------------
# 🎨 CREATE SLIDE (FAST)
# ---------------------------
def create_slide(title, points):
    # ⚡ Lower resolution = faster
    img = Image.new("RGB", (854, 480), "white")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("arial.ttf", 40)
        point_font = ImageFont.truetype("arial.ttf", 25)
    except:
        title_font = ImageFont.load_default()
        point_font = ImageFont.load_default()

    # Title
    draw.text((40, 20), title, fill="black", font=title_font)

    y = 100
    for p in points:
        draw.text((60, y), f"• {p}", fill="black", font=point_font)
        y += 40

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# 🔊 FAST TTS (SHORT)
# ---------------------------
async def tts_async(text, path):
    communicate = edge_tts.Communicate(
        text=text,
        voice="en-US-AriaNeural"
    )
    await communicate.save(path)

def generate_audio(text):
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name

    # ⚡ limit audio length
    short_text = text[:120]

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
# 🎥 FAST VIDEO GENERATION
# ---------------------------
def generate_video(slides):
    clips = []

    for slide in slides:
        img = create_slide(slide["title"], slide["points"])
        audio = generate_audio(slide["explanation"])

        clip = create_clip(img, audio)
        clips.append(clip)

    final = concatenate_videoclips(clips, method="compose")

    output = "final_video.mp4"

    # ⚡ ULTRA FAST render
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
    "Upload transcript files",
    type=["txt"],
    accept_multiple_files=True
)

if st.button("Generate Video"):

    if not files:
        st.warning("Upload files first")
        st.stop()

    with st.spinner("⚡ Processing fast..."):

        texts = [f.read().decode("utf-8") for f in files]
        merged = "\n\n".join(texts)

        data = generate_all(merged)

        summary = data["summary"]
        slides = data["slides"]

        st.subheader("📄 Summary")
        st.write(summary)

        video = generate_video(slides)

        st.success("✅ Video Ready (Fast Mode)!")
        st.video(video)

