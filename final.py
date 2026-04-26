import streamlit as st
import tempfile
import json
import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

# ---------------------------
# INIT
# ---------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Video Generator")
st.title("🎬 AI Video Generator (Clean + Big Text)")

# ---------------------------
# AI (SAFE)
# ---------------------------
def generate_all(text):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""
Create slides.

RULES:
- 6 slides
- 2 short points per slide
- very simple language

Return JSON:
{{
 "summary": "...",
 "slides":[
  {{"title":"...","points":["...","..."]}}
 ]
}}

TEXT:
{text}
"""
            }]
        )

        raw = res.choices[0].message.content
        data = json.loads(raw)

        if not data.get("slides"):
            raise ValueError("No slides")

        return data

    except:
        return {
            "summary": "Fallback summary",
            "slides": [
                {
                    "title": "Sample Slide",
                    "points": ["Content failed", "Please try again"]
                }
            ]
        }

# ---------------------------
# SLIDE DESIGN (BIG + CLEAN)
# ---------------------------
def create_slide(title, points):
    img = Image.new("RGB", (1280, 720), "#f8fafc")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 90)
        point_font = ImageFont.truetype("DejaVuSans.ttf", 60)
    except:
        title_font = ImageFont.load_default()
        point_font = ImageFont.load_default()

    # Center title
    bbox = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((1280 - bbox[2]) / 2, 80), title, fill="#111", font=title_font)

    # Divider
    draw.line((150, 200, 1130, 200), fill="#ccc", width=4)

    y = 260

    for p in points:
        words = p.split()
        lines = []
        line = ""

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
            y += 80

        y += 30

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# VIDEO GENERATION (FIXED)
# ---------------------------
def generate_video(slides):
    if not slides:
        st.error("No slides found")
        return None

    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=1)

    frame_count = 0

    for i, slide in enumerate(slides):
        st.write(f"Slide {i+1}/{len(slides)}")

        img = create_slide(
            slide.get("title", "Untitled"),
            slide.get("points", ["No content"])
        )

        frame = imageio.imread(img)

        # Force duration (2 sec per slide)
        for _ in range(2):
            writer.append_data(frame)
            frame_count += 1

    writer.close()

    if frame_count == 0:
        st.error("Video empty")
        return None

    return video_path

# ---------------------------
# UI
# ---------------------------
file = st.file_uploader("Upload transcript (.txt)", type=["txt"])

if file:
    text = file.read().decode("utf-8")

    if st.button("Generate Video"):

        data = generate_all(text)

        st.subheader("Summary")
        st.write(data.get("summary", ""))

        slides = data.get("slides", [])
        st.write("Slides:", len(slides))

        video = generate_video(slides)

        if video:
            st.success("✅ Video Ready!")
            st.video(video)
        else:
            st.error("❌ Failed to generate video")
