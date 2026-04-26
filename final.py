import streamlit as st
import tempfile
import json
import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("🎬 AI Video Generator (Left Layout + Summary)")

# ---------------------------
# AI CONTENT
# ---------------------------
def generate_content(text):
    text = text[:2000]

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""
Return JSON only.

FORMAT:
{{
 "summary": "...",
 "slides":[
  {{"title":"...","text":"..."}}
 ]
}}

RULES:
- 15 slides
- each slide max 6 words
- simple explanation

TEXT:
{text}
"""
            }]
        )

        raw = res.choices[0].message.content
        clean = raw[raw.find("{"):raw.rfind("}")+1]
        return json.loads(clean)

    except:
        return {
            "summary": "Error generating summary",
            "slides":[{"title":"Retry","text":"Try again"}]
        }

# ---------------------------
# LEFT-ALIGNED SLIDE
# ---------------------------
def create_slide(title, text):
    img = Image.new("RGB", (1280, 720), "white")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 90)
        text_font = ImageFont.truetype("DejaVuSans.ttf", 110)
    except:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # Title (LEFT)
    draw.text((80, 80), title, fill="black", font=title_font)

    # Divider
    draw.line((80, 200, 1200, 200), fill="#ccc", width=4)

    # Text (LEFT BIG)
    draw.text((80, 300), text, fill="black", font=text_font)

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# VIDEO GENERATION (3–5 MIN)
# ---------------------------
def create_video(slides):
    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=1)

    total_duration = 240  # 4 minutes
    per_slide = max(10, total_duration // len(slides))

    for i, slide in enumerate(slides):
        st.write(f"Slide {i+1}/{len(slides)}")

        img = create_slide(slide["title"], slide["text"])
        frame = imageio.imread(img)

        for _ in range(per_slide):
            writer.append_data(frame)

    writer.close()
    return video_path

# ---------------------------
# UI
# ---------------------------
file = st.file_uploader("Upload transcript (.txt)", type=["txt"])

if file:
    text = file.read().decode("utf-8")

    if st.button("Generate Summary + Video"):

        data = generate_content(text)

        # ---------------------------
        # SHOW SUMMARY FIRST
        # ---------------------------
        st.subheader("📄 Summary")
        st.write(data.get("summary", ""))

        slides = data.get("slides", [])

        # ---------------------------
        # GENERATE VIDEO
        # ---------------------------
        video = create_video(slides)

        st.success("✅ Video Ready!")
        st.video(video)

