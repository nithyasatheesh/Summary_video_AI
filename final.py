import streamlit as st
import tempfile
import json
import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI
import edge_tts
import asyncio

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Video Generator")
st.title("🎬 AI Video Generator (Visible + Audio)")

# ---------------------------
# AI CONTENT
# ---------------------------
def generate_content(text):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""
Create slides.

RULES:
- 12 slides
- Each slide: 1 short sentence
- Max 6 words

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
            "summary": "Error",
            "slides": [{"title": "Error", "text": "Try again"}]
        }

# ---------------------------
# SLIDE DESIGN (VERY VISIBLE)
# ---------------------------
def create_slide(title, text):
    img = Image.new("RGB", (1280, 720), "black")  # strong contrast
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 100)
        text_font = ImageFont.truetype("DejaVuSans.ttf", 90)
    except:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # TITLE
    draw.text((80, 80), title, fill="yellow", font=title_font)

    # TEXT
    draw.text((80, 350), text, fill="white", font=text_font)

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# AUDIO (LIGHT)
# ---------------------------
async def tts_async(text, path):
    communicate = edge_tts.Communicate(text=text, voice="en-US-JennyNeural")
    await communicate.save(path)

def generate_audio(text):
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(tts_async(text[:200], path))
    loop.close()
    return path

# ---------------------------
# VIDEO (STABLE)
# ---------------------------
def generate_video(slides):
    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=1)

    duration_per_slide = 12  # ~12 sec each → ~3–4 min total

    for i, slide in enumerate(slides):
        st.write(f"Slide {i+1}/{len(slides)}")

        img = create_slide(slide["title"], slide["text"])
        frame = imageio.imread(img)

        for _ in range(duration_per_slide):
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

        with st.spinner("Generating..."):

            data = generate_content(text)

            st.subheader("Summary")
            st.write(data.get("summary", ""))

            slides = data.get("slides", [])

            video = generate_video(slides)

            st.success("✅ Video Ready!")
            st.video(video)

