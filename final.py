import streamlit as st
import tempfile
import asyncio
import os
import imageio
import imageio_ffmpeg

from PIL import Image, ImageDraw, ImageFont
import edge_tts

# ---------------------------
# FFMPEG SETUP
# ---------------------------
os.environ["IMAGEIO_FFMPEG_EXE"] = imageio_ffmpeg.get_ffmpeg_exe()

st.set_page_config(page_title="Free AI Video Generator")
st.title("🎬 Free Transcript → Video Generator")

# ---------------------------
# SIMPLE FREE "AI"
# ---------------------------
def generate_all(text):
    paragraphs = text.split("\n\n")

    slides = []
    for i, para in enumerate(paragraphs[:10]):
        sentences = [s.strip() for s in para.split(".") if s.strip()]

        slides.append({
            "title": f"Topic {i+1}",
            "points": sentences[:3],
            "explanation": para[:200]
        })

    return {"summary": text[:300], "slides": slides}

# ---------------------------
# FONTS
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
# TEXT WRAP
# ---------------------------
def wrap_text(text, font, max_width):
    words = text.split()
    lines, line = [], ""

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
# SLIDE IMAGE
# ---------------------------
def create_slide(title, points):
    img = Image.new("RGB", (1280, 720), "#f9fafb")
    draw = ImageDraw.Draw(img)

    title_font, point_font = get_fonts()

    draw.text((80, 60), title, fill="#111", font=title_font)
    draw.line((80, 140, 1200, 140), fill="#ccc", width=3)

    y = 180
    for p in points:
        lines = wrap_text(p, point_font, 1000)
        for i, line in enumerate(lines):
            prefix = "• " if i == 0 else "  "
            draw.text((100, y), prefix + line, fill="#333", font=point_font)
            y += 45
        y += 15

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# TTS
# ---------------------------
async def tts_async(text, path):
    communicate = edge_tts.Communicate(
        text=text[:500],
        voice="en-US-JennyNeural"
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
# VIDEO (NO MOVIEPY)
# ---------------------------
def generate_video(slides):
    video_path = "final_video.mp4"
    writer = imageio.get_writer(video_path, fps=1)

    for i, slide in enumerate(slides):
        st.write(f"Slide {i+1}/{len(slides)}")

        img_path = create_slide(
            slide.get("title", "Untitled"),
            slide.get("points", [])
        )

        image = imageio.imread(img_path)

        # repeat frame for duration (~3 sec)
        for _ in range(3):
            writer.append_data(image)

    writer.close()
    return video_path

# ---------------------------
# UI
# ---------------------------
files = st.file_uploader("Upload transcript", type=["txt"], accept_multiple_files=True)

if st.button("Generate Video"):

    if not files:
        st.warning("Upload files first")
        st.stop()

    texts = [f.read().decode("utf-8") for f in files]
    merged = "\n\n".join(texts)

    data = generate_all(merged)

    st.subheader("Summary")
    st.write(data["summary"])

    video = generate_video(data["slides"])

    st.success("Done!")
    st.video(video)

