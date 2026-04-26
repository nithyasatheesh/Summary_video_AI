import streamlit as st
import tempfile
import json
import imageio.v2 as imageio
import asyncio
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI
import edge_tts

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("🎬 AI Video Generator (Final Fixed)")

# ---------------------------
# AI (STRICT SHORT TEXT)
# ---------------------------
def generate_content(text):
    text = text[:1500]

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""
Return JSON only.

RULES:
- 18 slides
- EACH slide = MAX 3 WORDS
- very simple words

FORMAT:
{{"slides":[{{"title":"...","text":"..."}}]}}

TEXT:
{text}
"""
            }]
        )

        raw = res.choices[0].message.content
        clean = raw[raw.find("{"):raw.rfind("}")+1]
        return json.loads(clean)

    except:
        return {"slides":[{"title":"Retry","text":"Try again"}]}

# ---------------------------
# SLIDE (HUGE TEXT FIX)
# ---------------------------
def create_slide(title, text):
    img = Image.new("RGB", (1280, 720), "black")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 140)
        text_font = ImageFont.truetype("DejaVuSans.ttf", 180)
    except:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # center title
    tb = draw.textbbox((0,0), title, font=title_font)
    draw.text(((1280-tb[2])//2, 80), title, fill="yellow", font=title_font)

    # center text
    bb = draw.textbbox((0,0), text, font=text_font)
    draw.text(((1280-bb[2])//2, 320), text, fill="white", font=text_font)

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# VIDEO (FORCE 4 MIN)
# ---------------------------
def create_video(slides):
    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=1)

    total_target = 240  # 4 minutes
    per_slide = total_target // len(slides)

    for slide in slides:
        img = create_slide(slide["title"], slide["text"])
        frame = imageio.imread(img)

        for _ in range(per_slide):
            writer.append_data(frame)

    writer.close()
    return video_path

# ---------------------------
# AUDIO (FIXED PLAYBACK)
# ---------------------------
async def tts_async(text, path):
    communicate = edge_tts.Communicate(
        text=text,
        voice="en-US-JennyNeural",
        rate="-10%"
    )
    await communicate.save(path)

def create_audio(slides):
    script = ". ".join([s["text"] for s in slides])

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(tts_async(script, path))
    loop.close()

    return path

# ---------------------------
# UI
# ---------------------------
file = st.file_uploader("Upload transcript", type=["txt"])

if file:
    text = file.read().decode("utf-8")

    if st.button("Generate"):

        data = generate_content(text)
        slides = data.get("slides", [])

        video = create_video(slides)
        audio = create_audio(slides)

        st.success("✅ Generated!")

        st.video(video)

        st.warning("🔊 Click below to play audio (browser blocks autoplay)")
        st.audio(audio)

