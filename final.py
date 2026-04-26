import streamlit as st
import tempfile
import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Video Generator")
st.title("🎬 Transcript → Video Generator (Stable)")

# ---------------------------
# TEXT → SLIDES
# ---------------------------
def generate_slides(text):
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    slides = []

    for i, para in enumerate(paragraphs[:8]):
        sentences = [s.strip() for s in para.split(".") if s.strip()]

        slides.append({
            "title": f"Slide {i+1}",
            "points": sentences[:3] if sentences else ["No content"]
        })

    if not slides:
        slides = [{"title": "No Content", "points": ["Empty input"]}]

    return slides

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
# CREATE SLIDE IMAGE
# ---------------------------
def create_slide(title, points):
    img = Image.new("RGB", (1280, 720), "white")
    draw = ImageDraw.Draw(img)

    title_font, point_font = get_fonts()

    draw.text((80, 50), str(title), fill="black", font=title_font)

    y = 180
    for p in points:
        for line in wrap_text(str(p), point_font, 1000):
            draw.text((100, y), "• " + line, fill="black", font=point_font)
            y += 45
        y += 15

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# VIDEO GENERATION
# ---------------------------
def generate_video(slides):
    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name

    try:
        writer = imageio.get_writer(video_path, fps=1)

        for i, slide in enumerate(slides):
            st.write(f"Processing slide {i+1}/{len(slides)}")

            img_path = create_slide(
                slide.get("title", "Untitled"),
                slide.get("points", ["No content"])
            )

            image = imageio.imread(img_path)

            # repeat frame (~3 sec per slide)
            for _ in range(3):
                writer.append_data(image)

        writer.close()
        return video_path

    except Exception as e:
        st.error(f"Video generation failed: {e}")
        return None

# ---------------------------
# UI
# ---------------------------
uploaded = st.file_uploader("Upload .txt file", type=["txt"])

if uploaded:
    try:
        text = uploaded.read().decode("utf-8")
    except:
        st.error("❌ File reading failed")
        st.stop()

    if st.button("Generate Video"):
        slides = generate_slides(text)

        video = generate_video(slides)

        if video:
            st.success("✅ Video generated!")
            st.video(video)
        else:
            st.error("❌ Failed to generate video")

