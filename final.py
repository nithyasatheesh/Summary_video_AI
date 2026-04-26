import streamlit as st
import tempfile
import json
import imageio.v2 as imageio
import imageio_ffmpeg
import subprocess
import asyncio
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI
import edge_tts

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

st.title("🎬 Clean Video Generator (Final Fix)")

# ---------------------------
# AI CONTENT (SHORT TEXT)
# ---------------------------
def generate_content(text):
    text = text[:2000]

    prompt = f"""
Return JSON:

{{
 "summary": "...",
 "slides":[{{"text":"..."}}]
}}

RULES:
- 30–40 slides
- each slide max 4 words
- very simple phrases

TEXT:
{text}
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )

    raw = res.choices[0].message.content
    clean = raw[raw.find("{"):raw.rfind("}")+1]

    return json.loads(clean)

# ---------------------------
# AUTO FONT SCALE
# ---------------------------
def get_big_font(draw, text, max_width, max_height):
    size = 200
    while size > 40:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", size)
        bbox = draw.textbbox((0,0), text, font=font)

        if bbox[2] < max_width and bbox[3] < max_height:
            return font
        size -= 5

    return ImageFont.load_default()

# ---------------------------
# SLIDE (FULL SCREEN TEXT)
# ---------------------------
def create_slide(text):
    img = Image.new("RGB", (1280, 720), "white")
    draw = ImageDraw.Draw(img)

    font = get_big_font(draw, text, 1100, 500)

    bbox = draw.textbbox((0,0), text, font=font)

    x = (1280 - bbox[2]) // 2
    y = (720 - bbox[3]) // 2

    draw.text((x, y), text, fill="black", font=font)

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# AUDIO
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
# VIDEO
# ---------------------------
def create_video(slides):
    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=1)

    total_duration = 300  # 5 min
    per_slide = total_duration // len(slides)

    for slide in slides:
        img = create_slide(slide["text"])
        frame = imageio.imread(img)

        for _ in range(per_slide):
            writer.append_data(frame)

    writer.close()
    return video_path

# ---------------------------
# MERGE AUDIO + VIDEO
# ---------------------------
def merge(video, audio):
    output = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name

    try:
        subprocess.run([
            FFMPEG,
            "-y",
            "-i", video,
            "-i", audio,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output
        ], check=True)

        return output

    except:
        st.warning("⚠️ Audio merge failed → playing separately")
        return None

# ---------------------------
# UI
# ---------------------------
file = st.file_uploader("Upload transcript", type=["txt"])

if file:
    text = file.read().decode("utf-8")

    if st.button("Generate Video"):

        data = generate_content(text)

        st.subheader("📄 Summary")
        st.write(data["summary"])

        slides = data["slides"]

        audio = create_audio(slides)
        video = create_video(slides)

        final = merge(video, audio)

        st.success("✅ Done!")

        if final:
            st.video(final)
        else:
            st.video(video)
            st.audio(audio)

