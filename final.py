import streamlit as st
from openai import OpenAI
import tempfile
import json
import asyncio
import base64

import edge_tts
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont

# ---------------------------
# 🔑 OPENAI CLIENT
# ---------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Video Generator", layout="centered")
st.title("🎬 AI Transcript → Video Generator (3–5 min)")

# ---------------------------
# 🧠 OPENAI CALL
# ---------------------------
def call_openai(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
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
Create a detailed educational video script.

STRICT RULES:
- Total video duration: 3 to 5 minutes
- Create 8 to 12 slides
- Each explanation: 40–80 words
- Keep bullet points short (max 4 per slide)

Return JSON only:
{{
  "summary": "...",
  "slides": [
    {{
      "title": "...",
      "points": ["...", "..."],
      "explanation": "...",
      "image_prompt": "describe an image"
    }}
  ]
}}

TEXT:
{text}
""")
    raw = clean_json(raw)
    return json.loads(raw)

# ---------------------------
# 🖼️ GENERATE IMAGE
# ---------------------------
def generate_image(prompt):
    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="512x512"
    )

    image_base64 = response.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    with open(path, "wb") as f:
        f.write(image_bytes)

    return path

# ---------------------------
# 🎨 CREATE SLIDE
# ---------------------------
def create_slide(title, points, image_path=None):
    img = Image.new("RGB", (1280, 720), "white")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("arial.ttf", 70)
        point_font = ImageFont.truetype("arial.ttf", 45)
    except:
        title_font = ImageFont.load_default()
        point_font = ImageFont.load_default()

    # Title
    draw.text((60, 40), title, fill="black", font=title_font)

    y = 180
    for p in points[:4]:
        draw.text((80, y), f"• {p}", fill="black", font=point_font)
        y += 80

    # Add image
    if image_path:
        try:
            slide_img = Image.open(image_path).resize((400, 300))
            img.paste(slide_img, (820, 200))
        except:
            pass

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# 🔊 TEXT TO SPEECH
# ---------------------------
async def tts_async(text, path):
    communicate = edge_tts.Communicate(
        text=text,
        voice="en-US-AriaNeural"
    )
    await communicate.save(path)

def generate_audio(text):
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    asyncio.run(tts_async(text, path))
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

    for slide in slides:
        img_ai = generate_image(slide["image_prompt"])

        img = create_slide(
            slide["title"],
            slide["points"],
            img_ai
        )

        audio = generate_audio(slide["explanation"])
        clip = create_clip(img, audio)

        clips.append(clip)

    final = concatenate_videoclips(clips, method="compose")

    output = "final_video.mp4"

    final.write_videofile(
        output,
        fps=24,
        preset="medium"
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

    with st.spinner("⏳ Generating 3–5 min video..."):

        texts = [f.read().decode("utf-8") for f in files]
        merged = "\n\n".join(texts)

        data = generate_all(merged)

        st.subheader("📄 Summary")
        st.write(data["summary"])

        video = generate_video(data["slides"])

        st.success("✅ Video Ready!")
        st.video(video)
