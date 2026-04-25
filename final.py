import streamlit as st
import tempfile
import json
import asyncio

import edge_tts
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Video Generator", layout="centered")
st.title("🎬 AI Transcript → 3-5 Min Video Generator")

# ---------------------------
# AI
# ---------------------------
def call_ai(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content

def clean_json(text):
    return text[text.find("{"):text.rfind("}")+1]

def generate_all(text):
    raw = call_ai(f"""
Create a COMPLETE explanation.

STRICT:
- 12 to 18 slides
- Max 4 bullet points per slide
- Explanation: 2–3 sentences

Return JSON only.

TEXT:
{text}
""")
    return json.loads(clean_json(raw))

# ---------------------------
# TEXT WRAP (BETTER)
# ---------------------------
def wrap_text(text, font, max_width):
    words = text.split()
    lines = []
    line = ""

    for word in words:
        test = line + word + " "
        if font.getbbox(test)[2] <= max_width:
            line = test
        else:
            lines.append(line.strip())
            line = word + " "

    lines.append(line.strip())
    return lines

# ---------------------------
# SLIDE DESIGN (UPGRADED)
# ---------------------------
def create_slide(title, points):
    img = Image.new("RGB", (854, 480), "white")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("arial.ttf", 65)   # 🔥 bigger
        point_font = ImageFont.truetype("arial.ttf", 40)   # 🔥 bigger
    except:
        title_font = ImageFont.load_default()
        point_font = ImageFont.load_default()

    # Center Title
    bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = bbox[2]
    draw.text(((854 - title_w) / 2, 30), title, fill="black", font=title_font)

    # Divider
    draw.line((80, 120, 770, 120), fill="#444", width=3)

    y = 160

    for p in points:
        # Bullet circle
        bullet_x = 90
        draw.ellipse((bullet_x, y+12, bullet_x+14, y+26), fill="#222")

        # Wrapped text
        lines = wrap_text(p, point_font, 600)

        for line in lines:
            draw.text((120, y), line, fill="#111", font=point_font)
            y += 48  # 🔥 better spacing

        y += 15  # space between bullets

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# TTS (UNCHANGED VOICE)
# ---------------------------
async def tts_async(text, path):
    communicate = edge_tts.Communicate(
        text=text[:400],
        voice="en-US-AriaNeural",
        rate="-10%"
    )
    await communicate.save(path)

def generate_audio(text):
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    asyncio.run(tts_async(text, path))
    return path

# ---------------------------
# VIDEO
# ---------------------------
def create_clip(img_path, audio_path):
    audio = AudioFileClip(audio_path)
    duration = max(audio.duration, 10)

    clip = ImageClip(img_path).with_duration(duration)
    clip = clip.with_audio(audio)
    return clip

def generate_video(slides):
    clips = []

    for slide in slides:
        img = create_slide(slide["title"], slide["points"])
        audio = generate_audio(slide["explanation"])

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

    with st.spinner("🎬 Generating video..."):

        texts = [f.read().decode("utf-8") for f in files]
        merged = "\n\n".join(texts)

        data = generate_all(merged)

        st.subheader("📄 Summary")
        st.write(data["summary"])
        video = generate_video(data["slides"])

        st.success("✅ Video Ready!")
        st.video(video)

