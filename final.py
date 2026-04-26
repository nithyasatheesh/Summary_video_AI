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

st.set_page_config(page_title="AI Video Generator", layout="centered")
st.title("🎬 AI Transcript → 3–5 Min Video Generator")

# ---------------------------
# AI
# ---------------------------
def call_ai(prompt):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content

def clean_json(text):
    return text[text.find("{"):text.rfind("}")+1]

def generate_all(text):
    raw = call_ai(f"""
Create a YouTube-style explanation.

STRICT:
- 15 to 20 slides
- Each slide = max 2 points
- Each point max 8 words
- Explanation = 2 short spoken sentences
- Keep language VERY simple

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
    return json.loads(clean_json(raw))

# ---------------------------
# SLIDE DESIGN (BIG + CLEAN)
# ---------------------------
def create_slide(title, points):
    img = Image.new("RGB", (1280, 720), "#f8fafc")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 70)
        point_font = ImageFont.truetype("DejaVuSans.ttf", 48)
    except:
        title_font = ImageFont.load_default()
        point_font = ImageFont.load_default()

    # Center title
    bbox = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((1280 - bbox[2]) / 2, 60), title, fill="#111", font=title_font)

    draw.line((150, 160, 1130, 160), fill="#ccc", width=4)

    y = 220

    for p in points:
        words = p.split()
        lines, line = [], ""

        for word in words:
            test = line + word + " "
            if point_font.getbbox(test)[2] < 900:
                line = test
            else:
                lines.append(line)
                line = word + " "
        lines.append(line)

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=point_font)
            draw.text(((1280 - bbox[2]) / 2, y), line.strip(), fill="#222", font=point_font)
            y += 65

        y += 20

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# TTS (NATURAL)
# ---------------------------
async def tts_async(text, path):
    communicate = edge_tts.Communicate(
        text=text[:250],
        voice="en-US-JennyNeural",
        rate="-5%",
        pitch="+2Hz"
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
# CLIP
# ---------------------------
def create_clip(img_path, audio_path):
    audio = AudioFileClip(audio_path)

    # Ensure minimum duration
    duration = max(audio.duration, 10)

    clip = ImageClip(img_path).set_duration(duration)
    clip = clip.resize(lambda t: 1 + 0.015 * t)  # zoom
    clip = clip.set_audio(audio)

    return clip

# ---------------------------
# VIDEO
# ---------------------------
def generate_video(slides):
    clips = []

    for i, slide in enumerate(slides):
        st.write(f"Slide {i+1}/{len(slides)}")

        img = create_slide(
            slide.get("title", "Untitled"),
            slide.get("points", [])
        )

        audio = generate_audio(slide.get("explanation", ""))

        clips.append(create_clip(img, audio))

    final = concatenate_videoclips(clips, method="compose")

    output = "final_video.mp4"
    final.write_videofile(
        output,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        bitrate="3000k"
    )

    return output

# ---------------------------
# UI
# ---------------------------
files = st.file_uploader(
    "Upload transcript",
    type=["txt"],
    accept_multiple_files=True
)

if st.button("Generate Video"):

    if not files:
        st.warning("Upload files first")
        st.stop()

    with st.spinner("🎬 Generating 3–5 min video..."):

        texts = [f.read().decode("utf-8") for f in files]
        merged = "\n\n".join(texts)

        data = generate_all(merged)

        st.subheader("Summary")
        st.write(data.get("summary", ""))

        video = generate_video(data.get("slides", []))

        st.success("✅ Video Ready!")
        st.video(video)

