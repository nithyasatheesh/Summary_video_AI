```python
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
st.title("🎬 AI Transcript → HD Video Generator")

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

STRICT RULES:
- 12–15 slides
- Each slide: MAX 3 bullet points
- Each bullet: MAX 10 words
- Use SIMPLE, CLEAR language
- Explanation: 2 short sentences (spoken style)

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
# FONTS
# ---------------------------
def get_fonts():
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 72)
        point_font = ImageFont.truetype("DejaVuSans.ttf", 42)
    except:
        title_font = ImageFont.load_default()
        point_font = ImageFont.load_default()
    return title_font, point_font

# ---------------------------
# TEXT WRAP
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
# SLIDE DESIGN (HD)
# ---------------------------
def create_slide(title, points):
    img = Image.new("RGB", (1280, 720), "#f9fafb")
    draw = ImageDraw.Draw(img)

    title_font, point_font = get_fonts()

    # Title
    draw.text((100, 60), title, fill="#111", font=title_font)

    # Divider
    draw.line((100, 150, 1180, 150), fill="#ddd", width=4)

    y = 200

    for p in points:
        lines = wrap_text(p, point_font, 1000)

        for i, line in enumerate(lines):
            prefix = "• " if i == 0 else "  "
            draw.text((120, y), prefix + line, fill="#333", font=point_font)
            y += 55

        y += 20

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path, quality=95)
    return path

# ---------------------------
# TTS
# ---------------------------
async def tts_async(text, path):
    communicate = edge_tts.Communicate(
        text=text[:500],
        voice="en-US-JennyNeural",
        rate="-5%",
        pitch="+2Hz"
    )
    await communicate.save(path)

def generate_audio(text):
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    asyncio.run(tts_async(text, path))
    return path

# ---------------------------
# VIDEO CLIP (Zoom Effect)
# ---------------------------
def create_clip(img_path, audio_path):
    audio = AudioFileClip(audio_path)
    duration = max(audio.duration, 10)

    clip = (
        ImageClip(img_path)
        .with_duration(duration)
        .resize(lambda t: 1 + 0.02 * t)  # subtle zoom
        .with_audio(audio)
    )
    return clip

# ---------------------------
# VIDEO GENERATION
# ---------------------------
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
        fps=24,
        codec="libx264",
        audio_codec="aac",
        bitrate="3000k",
        preset="medium"
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
```
