import streamlit as st
import tempfile
import json
import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("🎬 AI Video Generator (Final Improved)")

# ---------------------------
# AI CONTENT (BETTER STRUCTURE)
# ---------------------------
def generate_content(text):
    text = text[:2000]

    prompt = f"""
Create a clear educational explanation.

OUTPUT JSON:
{{
 "summary": "...",
 "slides":[
  {{"title":"...","points":["...","..."]}}
 ]
}}

RULES:
- 20–25 slides
- Each slide: 2 short points
- Each point: max 6–8 words
- Simple explanation
- Cover topic fully (not shallow)

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
            "slides":[
                {"title":"Retry","points":["Try again","Check input"]}
            ]
        }

# ---------------------------
# SLIDE DESIGN (BIG TEXT LEFT)
# ---------------------------
def create_slide(title, points):
    img = Image.new("RGB", (1280, 720), "white")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 85)
        point_font = ImageFont.truetype("DejaVuSans.ttf", 70)
    except:
        title_font = ImageFont.load_default()
        point_font = ImageFont.load_default()

    # Title
    draw.text((80, 60), title, fill="black", font=title_font)

    # Divider
    draw.line((80, 160, 1200, 160), fill="#aaa", width=3)

    y = 200

    # Points (large + spaced)
    for p in points:
        words = p.split()
        lines, line = [], ""

        for w in words:
            test = line + w + " "
            if draw.textbbox((0,0), test, font=point_font)[2] < 1000:
                line = test
            else:
                lines.append(line)
                line = w + " "
        lines.append(line)

        for ln in lines:
            draw.text((80, y), ln.strip(), fill="black", font=point_font)
            y += 90

        y += 30

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# VIDEO (STRICT 3–5 MIN)
# ---------------------------
def create_video(slides):
    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=1)

    target_duration = 240  # 4 minutes

    n = len(slides)
    per_slide = max(8, target_duration // n)

    for i, slide in enumerate(slides):
        st.write(f"Slide {i+1}/{n}")

        img = create_slide(
            slide["title"],
            slide["points"]
        )

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

    if st.button("Generate Video"):

        data = generate_content(text)

        # SUMMARY FIRST
        st.subheader("📄 Summary")
        st.write(data.get("summary", ""))

        slides = data.get("slides", [])

        video = create_video(slides)

        st.success("✅ Video Ready!")
        st.video(video)

