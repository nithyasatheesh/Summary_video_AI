import streamlit as st
import tempfile
import json
import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="YouTube Video Generator")
st.title("🎬 3–5 Min AI Video Generator")

# ---------------------------
# AI CONTENT (LESS TEXT = BIG FONT)
# ---------------------------
def generate_content(text):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""
Create YouTube-style slides.

RULES:
- 15–18 slides
- Each slide = 1 short sentence
- Max 6 words per sentence
- Very simple words
- Include intro + recap

Return JSON:
{{
 "summary": "...",
 "slides":[
  {{"title":"...","text":"..."}}
 ]
}}

TEXT:
{text}
"""
            }]
        )

        return json.loads(res.choices[0].message.content)

    except:
        return {
            "summary": "Error generating content",
            "slides": [{"title": "Error", "text": "Try again"}]
        }

# ---------------------------
# BIG VISUAL SLIDE
# ---------------------------
def create_slide(title, text):
    img = Image.new("RGB", (1280, 720), "#0f172a")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 95)
        text_font = ImageFont.truetype("DejaVuSans.ttf", 80)
    except:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # TITLE (TOP CENTER)
    bbox = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((1280 - bbox[2]) / 2, 80), title, fill="#f8fafc", font=title_font)

    # MAIN TEXT (CENTER BIG)
    words = text.split()
    lines, line = [], ""

    for w in words:
        test = line + w + " "
        if text_font.getbbox(test)[2] < 1000:
            line = test
        else:
            lines.append(line)
            line = w + " "
    lines.append(line)

    y = 300
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=text_font)
        draw.text(((1280 - bbox[2]) / 2, y), line.strip(), fill="#38bdf8", font=text_font)
        y += 100

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# VIDEO (FORCED 3–5 MIN)
# ---------------------------
def generate_video(slides):
    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=1)

    total_slides = len(slides)

    # 🔥 target 3–5 minutes → 180–300 sec
    target_duration = 240  # 4 minutes

    duration_per_slide = max(10, target_duration // total_slides)

    for i, slide in enumerate(slides):
        st.write(f"Slide {i+1}/{total_slides}")

        img = create_slide(slide["title"], slide["text"])
        frame = imageio.imread(img)

        for _ in range(duration_per_slide):
            writer.append_data(frame)

    writer.close()
    return video_path

# ---------------------------
# UI
# ---------------------------
file = st.file_uploader("Upload transcript (.txt)", type=["txt"])

if file:
    text = file.read().decode("utf-8")

    if st.button("Generate Video"):

        with st.spinner("🎬 Generating 3–5 min video..."):

            data = generate_content(text)

            st.subheader("📄 Summary")
            st.write(data.get("summary", ""))

            slides = data.get("slides", [])

            video = generate_video(slides)

            st.success("✅ Video Ready!")
            st.video(video)

