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
st.title("🎬 Stable AI Video Generator")

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

        # try parsing
        data = json.loads(raw)

        if not data.get("slides"):
            raise ValueError("No slides")

        return data

    except:
        # 🔥 fallback (prevents empty video)
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
# SLIDE DESIGN
# ---------------------------
def create_slide(title, points):
    img = Image.new("RGB", (854, 480), "#f8fafc")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
        point_font = ImageFont.truetype("DejaVuSans.ttf", 28)
    except:
        title_font = ImageFont.load_default()
        point_font = ImageFont.load_default()

    draw.text((40, 30), str(title), fill="#111", font=title_font)

    y = 120
    for p in points:
        draw.text((60, y), str(p), fill="#222", font=point_font)
        y += 40

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# VIDEO (FIXED)
# ---------------------------
def generate_video(slides):
    if not slides:
        st.error("❌ No slides → cannot create video")
        return None

    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name

    try:
        writer = imageio.get_writer(video_path, fps=1)

        frame_count = 0

        for i, slide in enumerate(slides):
            st.write(f"Processing slide {i+1}/{len(slides)}")

            img = create_slide(
                slide.get("title", "Untitled"),
                slide.get("points", ["No content"])
            )

            frame = imageio.imread(img)

            # 🔥 force 2 seconds per slide
            for _ in range(2):
                writer.append_data(frame)
                frame_count += 1

        writer.close()

        # 🔥 prevent empty video
        if frame_count == 0:
            st.error("❌ Video is empty (no frames written)")
            return None

        return video_path

    except Exception as e:
        st.error(f"Video error: {e}")
        return None

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

        st.write("Slides count:", len(slides))  # debug

        video = generate_video(slides)

        if video:
            st.success("✅ Video generated!")
            st.video(video)
        else:
            st.error("❌ Failed to generate video")

