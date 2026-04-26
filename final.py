import streamlit as st
import tempfile
import json
import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Video Generator")
st.title("🎬 AI Slide Video Generator (Cloud Stable)")

# ---------------------------
# AI (SAFE JSON)
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
        data = json.loads(raw)
        return data

    except:
        return {"summary": "", "slides": []}

# ---------------------------
# SLIDE DESIGN (BIG TEXT)
# ---------------------------
def create_slide(title, points):
    img = Image.new("RGB", (1280, 720), "#f8fafc")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 70)
        point_font = ImageFont.truetype("DejaVuSans.ttf", 50)
    except:
        title_font = ImageFont.load_default()
        point_font = ImageFont.load_default()

    # Title
    draw.text((100, 80), title, fill="#111", font=title_font)

    y = 250
    for p in points:
        draw.text((120, y), p, fill="#222", font=point_font)
        y += 80

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# VIDEO (LIGHTWEIGHT)
# ---------------------------
def generate_video(slides):
    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=1)

    for i, slide in enumerate(slides):
        st.write(f"Slide {i+1}/{len(slides)}")

        img = create_slide(
            slide.get("title", "Untitled"),
            slide.get("points", [])
        )

        frame = imageio.imread(img)

        for _ in range(4):  # 4 sec per slide
            writer.append_data(frame)

    writer.close()
    return video_path

# ---------------------------
# UI
# ---------------------------
file = st.file_uploader("Upload transcript", type=["txt"])

if file:
    text = file.read().decode("utf-8")

    if st.button("Generate Video"):

        data = generate_all(text)

        st.subheader("Summary")
        st.write(data.get("summary", ""))

        video = generate_video(data.get("slides", []))

        st.success("✅ Video Ready!")
        st.video(video)

