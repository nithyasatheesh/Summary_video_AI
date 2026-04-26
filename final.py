import streamlit as st
import tempfile
import json
import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("🎬 AI Video Generator (Balanced Version)")

# ---------------------------
# AI CONTENT (LESS SLIDES, BETTER CONTENT)
# ---------------------------
def generate_content(text):
    text = text[:2000]

    prompt = f"""
Create a clear explanation.

Return JSON:
{{
 "summary": "...",
 "slides":[
  {{
    "title": "...",
    "content": "2–3 sentences explanation"
  }}
 ]
}}

RULES:
- 8 to 10 slides ONLY
- each slide = clear explanation
- simple language
- meaningful content

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
            "summary":"Error generating content",
            "slides":[{"title":"Retry","content":"Try again"}]
        }

# ---------------------------
# SAFE FONT
# ---------------------------
def get_font(size, bold=False):
    try:
        return ImageFont.truetype(
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size
        )
    except:
        return ImageFont.load_default()

# ---------------------------
# TEXT WRAP
# ---------------------------
def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, line = [], ""

    for w in words:
        test = line + w + " "
        if draw.textbbox((0,0), test, font=font)[2] < max_width:
            line = test
        else:
            lines.append(line)
            line = w + " "
    lines.append(line)
    return lines

# ---------------------------
# SLIDE DESIGN (BIG + CLEAN)
# ---------------------------
def create_slide(title, content):
    img = Image.new("RGB", (1280, 720), "white")
    draw = ImageDraw.Draw(img)

    title_font = get_font(80, bold=True)
    text_font = get_font(65)

    # Title
    draw.text((80, 60), title, fill="black", font=title_font)

    # Divider
    draw.line((80, 150, 1200, 150), fill="#aaa", width=3)

    # Content
    lines = wrap_text(draw, content, text_font, 1000)

    y = 200
    for line in lines:
        draw.text((80, y), line.strip(), fill="black", font=text_font)
        y += 80

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# VIDEO (FORCE 3–5 MIN)
# ---------------------------
def create_video(slides):
    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=1)

    target_duration = 240  # 4 minutes

    per_slide = max(20, target_duration // len(slides))

    for i, slide in enumerate(slides):
        st.write(f"Slide {i+1}/{len(slides)}")

        img = create_slide(slide["title"], slide["content"])
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

    if st.button("Generate Video"):

        data = generate_content(text)

        st.subheader("📄 Summary")
        st.write(data.get("summary", ""))

        slides = data.get("slides", [])

        video = create_video(slides)

        st.success("✅ Video Ready!")
        st.video(video)

