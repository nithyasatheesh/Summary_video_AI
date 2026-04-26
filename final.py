import streamlit as st
import tempfile
import json
import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="YouTube Video Generator")
st.title("🎬 Transcript → YouTube-Style Video")

# ---------------------------
# 🧠 AI GENERATION
# ---------------------------
def generate_content(text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": f"""
Create a YouTube-style explanation.

STRUCTURE:
1. Hook (1 slide)
2. Main content (8–10 slides)
3. Recap (1 slide)

RULES:
- Each slide = 1 short sentence
- Max 8 words
- Very simple language
- Engaging and clear

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

    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {
            "summary": "Could not generate summary",
            "slides": [
                {"title": "Error", "text": "Try again"}
            ]
        }

# ---------------------------
# 🎨 SLIDE DESIGN
# ---------------------------
def create_slide(title, text):
    img = Image.new("RGB", (1280, 720), "#0f172a")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 80)
        text_font = ImageFont.truetype("DejaVuSans.ttf", 70)
    except:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # Title
    bbox = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((1280 - bbox[2]) / 2, 100), title, fill="white", font=title_font)

    # Text
    bbox = draw.textbbox((0, 0), text, font=text_font)
    draw.text(((1280 - bbox[2]) / 2, 350), text, fill="#38bdf8", font=text_font)

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# 🎥 VIDEO GENERATION
# ---------------------------
def generate_video(slides):
    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=1)

    for slide in slides:
        img = create_slide(slide["title"], slide["text"])
        frame = imageio.imread(img)

        # ~10 sec per slide → 3–4 min total
        for _ in range(8):
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

        with st.spinner("Creating YouTube-style video..."):

            data = generate_content(text)

            st.subheader("📄 Summary")
            st.write(data.get("summary", ""))

            slides = data.get("slides", [])

            video = generate_video(slides)

            st.success("✅ Video Ready!")
            st.video(video)

