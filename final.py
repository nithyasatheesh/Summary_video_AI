import streamlit as st
from openai import OpenAI
import tempfile
import json
import asyncio
import os

import edge_tts
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont

# ---------------------------
# 🔑 OPENAI CLIENT
# ---------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Video Generator", layout="centered")
st.title("🎬 AI Transcript → Clean Video")

FONT_FILE = "Roboto-Bold.ttf"

# ---------------------------
# 🔤 LOAD FONT (LOCAL ONLY)
# ---------------------------
def load_fonts():
    try:
        title_font = ImageFont.truetype(FONT_FILE, 140)  # BIG
        point_font = ImageFont.truetype(FONT_FILE, 80)
    except Exception as e:
        st.error(f"Font error: {e}")
        title_font = ImageFont.load_default()
        point_font = ImageFont.load_default()
    return title_font, point_font

# ---------------------------
# 🧠 OPENAI CALL
# ---------------------------
def call_openai(prompt):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6
    )
    return res.choices[0].message.content

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
Create presentation slides.

RULES:
- 5 slides only
- Max 2 bullet points
- Each bullet under 4 words
- Titles: 2–3 words
- Explanation max 15 words

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
    return json.loads(raw)

# ---------------------------
# 🎨 CREATE SLIDE
# ---------------------------
def create_slide(title, points):
    img = Image.new("RGB", (1280, 720), "#ffffff")
    draw = ImageDraw.Draw(img)

    title_font, point_font = load_fonts()

    # Title
    draw.text((80, 80), title, fill="black", font=title_font)

    # underline
    draw.line((80, 240, 1200, 240), fill="black", width=5)

    # bullets
    y = 320
    for p in points[:2]:
        draw.text((120, y), f"• {p}", fill="black", font=point_font)
        y += 150

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
    short_text = text[:100]  # keep fast
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

    for slide in slides[:5]:
        img = create_slide(slide["title"], slide["points"])
        audio = generate_audio(slide["explanation"])

        clip = create_clip(img, audio)
        clips.append(clip)

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

    with st.spinner("⚡ Generating video..."):

        texts = [f.read().decode("utf-8") for f in files]
        merged = "\n\n".join(texts)

        data = generate_all(merged)

        st.subheader("📄 Summary")
        st.write(data["summary"])

        video = generate_video(data["slides"])

        st.success("✅ Video Ready!")
        st.video(video)
