import streamlit as st
import tempfile
import json
import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("🎬 AI Video Generator (FINAL CLEAN VERSION)")

# ---------------------------
# AI CONTENT (MORE SLIDES, SIMPLE TEXT)
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
- 25–30 slides
- each slide ONE sentence
- max 6–7 words
- no bullets
- simple explanation
- cover topic fully

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
            "summary":"Error generating summary",
            "slides":[{"title":"Retry","text":"Try again"}]
        }

# ---------------------------
# SLIDE (BIG TEXT LEFT)
# ---------------------------
def create_slide(title, text):
    img = Image.new("RGB", (1280, 720), "white")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 90)
        text_font = ImageFont.truetype("DejaVuSans.ttf", 120)
    except:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # Title
    draw.text((80, 80), title, fill="black", font=title_font)

    # Divider
    draw.line((80, 180, 1200, 180), fill="#ccc", width=3)

    # Wrap text
    words = text.split()
    lines, line = [], ""

    for w in words:
        test = line + w + " "
        if draw.textbbox((0,0), test, font=text_font)[2] < 1100:
            line = test
        else:
            lines.append(line)
            line = w + " "
    lines.append(line)

    y = 260
    for ln in lines:
        draw.text((80, y), ln.strip(), fill="black", font=text_font)
        y += 130

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# VIDEO (FORCE 4–5 MIN)
# ---------------------------
def create_video(slides):
    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=1)

    target_duration = 300  # 5 minutes

    n = len(slides)
    per_slide = max(10, target_duration // n)

    for i, slide in enumerate(slides):
        st.write(f"Slide {i+1}/{n}")

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

    if st.button("Generate Video"):

        data = generate_content(text)

        # Summary
        st.subheader("📄 Summary")
        st.write(data.get("summary", ""))

        slides = data.get("slides", [])

        video = create_video(slides)

        st.success("✅ Video Ready!")
        st.video(video)

