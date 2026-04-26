import streamlit as st
import tempfile
import asyncio
import os
import imageio
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont
import edge_tts

# ---------------------------
# Setup ffmpeg
# ---------------------------
os.environ["IMAGEIO_FFMPEG_EXE"] = imageio_ffmpeg.get_ffmpeg_exe()

st.set_page_config(page_title="Free Video Generator")
st.title("🎬 Transcript → Video Generator (Free Version)")

# ---------------------------
# Simple Text Processing (No AI)
# ---------------------------
def generate_slides(text):
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    slides = []

    for i, para in enumerate(paragraphs[:8]):
        sentences = [s.strip() for s in para.split(".") if s.strip()]
        slides.append({
            "title": f"Slide {i+1}",
            "points": sentences[:3],
            "explanation": para[:200]
        })

    if not slides:
        slides = [{"title": "No Content", "points": ["Empty input"], "explanation": ""}]

    return slides

# ---------------------------
# Fonts
# ---------------------------
def get_fonts():
    try:
        return (
            ImageFont.truetype("DejaVuSans-Bold.ttf", 60),
            ImageFont.truetype("DejaVuSans.ttf", 36)
        )
    except:
        return (ImageFont.load_default(), ImageFont.load_default())

# ---------------------------
# Text wrap
# ---------------------------
def wrap_text(text, font, max_width):
    words = text.split()
    lines, line = [], ""

    for word in words:
        test = line + word + " "
        if font.getbbox(test)[2] <= max_width:
            line = test
        else:
            lines.append(line)
            line = word + " "

    lines.append(line)
    return lines

# ---------------------------
# Create Slide Image
# ---------------------------
def create_slide(title, points):
    img = Image.new("RGB", (1280, 720), "white")
    draw = ImageDraw.Draw(img)
    title_font, point_font = get_fonts()

    draw.text((80, 50), title, fill="black", font=title_font)
    y = 180

    for p in points:
        for line in wrap_text(p, point_font, 1000):
            draw.text((100, y), "• " + line, fill="black", font=point_font)
            y += 45
        y += 15

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# TTS
# ---------------------------
async def tts_async(text, path):
    communicate = edge_tts.Communicate(text=text[:300], voice="en-US-JennyNeural")
    await communicate.save(path)

def generate_audio(text):
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(tts_async(text, path))
    loop.close()
    return path

# ---------------------------
# Create Video (ImageIO)
# ---------------------------
def generate_video(slides):
    video_path = "output.mp4"
    writer = imageio.get_writer(video_path, fps=1)

    for i, slide in enumerate(slides):
        st.write(f"Processing slide {i+1}/{len(slides)}")

        img_path = create_slide(slide["title"], slide["points"])
        image = imageio.imread(img_path)

        # repeat frame ~3 seconds
        for _ in range(3):
            writer.append_data(image)

    writer.close()
    return video_path

# ---------------------------
# UI
# ---------------------------
uploaded = st.file_uploader("Upload .txt file", type=["txt"])

if uploaded:
    text = uploaded.read().decode("utf-8")

    if st.button("Generate Video"):
        slides = generate_slides(text)
        video = generate_video(slides)

        st.success("✅ Video generated!")
        st.video(video)

