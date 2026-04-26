import streamlit as st
import tempfile
import json
import imageio.v2 as imageio
import asyncio
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI
import edge_tts

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Video Generator")
st.title("🎬 Video Generator (Stable + Audio)")

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

RULES:
- 10 slides
- max 5 words per slide

FORMAT:
{{"slides":[{{"title":"...","text":"..."}}]}}

TEXT:
{text}
"""
            }]
        )

        raw = res.choices[0].message.content
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])

    except:
        return {"slides":[{"title":"Error","text":"Retry"}]}

# ---------------------------
# SLIDE
# ---------------------------
def create_slide(title, text):
    img = Image.new("RGB", (1280, 720), "black")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 110)
        text_font = ImageFont.truetype("DejaVuSans.ttf", 130)
    except:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    draw.text((80, 60), title, fill="yellow", font=title_font)
    draw.text((80, 300), text, fill="white", font=text_font)

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# VIDEO
# ---------------------------
def create_video(slides):
    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=1)

    for slide in slides:
        img = create_slide(slide["title"], slide["text"])
        frame = imageio.imread(img)

        for _ in range(10):  # duration
            writer.append_data(frame)

    writer.close()
    return video_path

# ---------------------------
# AUDIO
# ---------------------------
async def tts_async(text, path):
    communicate = edge_tts.Communicate(text=text, voice="en-US-JennyNeural")
    await communicate.save(path)

def create_audio(slides):
    script = ". ".join([s["text"] for s in slides])

    audio_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(tts_async(script, audio_path))
    loop.close()

    return audio_path

# ---------------------------
# UI
# ---------------------------
file = st.file_uploader("Upload transcript", type=["txt"])

if file:
    text = file.read().decode("utf-8")

    if st.button("Generate"):

        with st.spinner("Processing..."):

            data = generate_content(text)
            slides = data.get("slides", [])

            video = create_video(slides)
            audio = create_audio(slides)

            st.success("✅ Done!")

            st.video(video)

            st.subheader("🔊 Audio Narration")
            st.audio(audio)

