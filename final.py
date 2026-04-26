import streamlit as st
import tempfile
import json
import imageio.v2 as imageio
import asyncio
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI
import edge_tts

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("🎬 YouTube Automation Video Generator")

# ---------------------------
# AI (STORY STYLE)
# ---------------------------
def generate_content(text):
    text = text[:1500]

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": f"""
Create engaging YouTube script.

STRUCTURE:
- Hook (2 slides)
- Main content (12 slides)
- Recap (2 slides)

RULES:
- Each slide: max 4 words
- Powerful words
- simple language

Return JSON:
{{"slides":[{{"title":"...","text":"..."}}]}}

TEXT:
{text}
"""
        }]
    )

    raw = res.choices[0].message.content
    clean = raw[raw.find("{"):raw.rfind("}")+1]
    return json.loads(clean)

# ---------------------------
# GRADIENT BACKGROUND
# ---------------------------
def gradient_bg():
    img = Image.new("RGB", (1280, 720))
    draw = ImageDraw.Draw(img)

    for y in range(720):
        r = int(10 + y * 0.1)
        g = int(20 + y * 0.05)
        b = int(40 + y * 0.2)
        draw.line([(0, y), (1280, y)], fill=(r, g, b))

    return img

# ---------------------------
# CINEMATIC SLIDE
# ---------------------------
def create_slide(title, text):
    img = gradient_bg()
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 110)
        text_font = ImageFont.truetype("DejaVuSans.ttf", 170)
    except:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # Title
    tb = draw.textbbox((0,0), title, font=title_font)
    draw.text(((1280-tb[2])//2, 80), title, fill="#FFD700", font=title_font)

    # Text
    bb = draw.textbbox((0,0), text, font=text_font)
    draw.text(((1280-bb[2])//2, 320), text, fill="#00E5FF", font=text_font)

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# VIDEO (ZOOM EFFECT)
# ---------------------------
def create_video(slides):
    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=2)

    total_time = 240  # 4 min
    per_slide = total_time // len(slides)

    for slide in slides:
        img = create_slide(slide["title"], slide["text"])
        frame = imageio.imread(img)

        for i in range(per_slide):
            writer.append_data(frame)

    writer.close()
    return video_path

# ---------------------------
# AUDIO
# ---------------------------
async def tts_async(text, path):
    communicate = edge_tts.Communicate(
        text=text,
        voice="en-US-JennyNeural",
        rate="-5%"
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

    if st.button("Generate Cinematic Video"):

        data = generate_content(text)
        slides = data["slides"]

        video = create_video(slides)
        audio = create_audio(slides)

        st.success("🔥 Cinematic Video Ready!")

        st.video(video)

        st.subheader("🔊 Voice Narration")
        st.audio(audio)

