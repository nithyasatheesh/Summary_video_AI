import streamlit as st
import tempfile
import json
import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("🎬 Clean YouTube Style Video Generator")

# ---------------------------
# AI CONTENT (SHORT + CLEAR)
# ---------------------------
def generate_content(text):
    text = text[:2000]

    prompt = f"""
Return JSON:

{{
 "summary": "...",
 "slides":[
  {{"title":"...","text":"..."}}
 ]
}}

RULES:
- 30–40 slides
- EACH slide = 1 idea
- MAX 4 words per slide
- simple language
- no explanation sentences
- no bullets

TEXT:
{text}
"""

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}]
        )

        raw = res.choices[0].message.content
        clean = raw[raw.find("{"):raw.rfind("}")+1]

        return json.loads(clean)

    except:
        return {
            "summary":"Error",
            "slides":[{"title":"Retry","text":"Try again"}]
        }

# ---------------------------
# SLIDE (VERY CLEAN STYLE)
# ---------------------------
def create_slide(title, text):
    img = Image.new("RGB", (1280, 720), "white")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 110)
        text_font = ImageFont.truetype("DejaVuSans.ttf", 170)
    except:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # Title
    draw.text((80, 80), title, fill="#333", font=title_font)

    # Big main text
    draw.text((80, 300), text, fill="#000", font=text_font)

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# VIDEO (SLOW + CLEAR)
# ---------------------------
def create_video(slides):
    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=1)

    total_duration = 300  # 5 minutes
    per_slide = total_duration // len(slides)

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
file = st.file_uploader("Upload transcript", type=["txt"])

if file:
    text = file.read().decode("utf-8")

    if st.button("Generate Clean Video"):

        data = generate_content(text)

        st.subheader("📄 Summary")
        st.write(data.get("summary", ""))

        slides = data.get("slides", [])

        video = create_video(slides)

        st.success("✅ Clean Video Ready!")
        st.video(video)

