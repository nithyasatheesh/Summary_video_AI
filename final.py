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

# ---------------------------
# INIT
# ---------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

st.set_page_config(page_title="Clean Video Generator")
st.title("🎬 Clean YouTube Style Video Generator")

# ---------------------------
# SAFE FONT LOADER
# ---------------------------
def get_font(size):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except:
        return ImageFont.load_default()

# ---------------------------
# AUTO FONT SCALE
# ---------------------------
def get_big_font(draw, text):
    for size in range(220, 40, -5):
        font = get_font(size)
        bbox = draw.textbbox((0, 0), text, font=font)

        if bbox[2] < 1100 and bbox[3] < 500:
            return font

    return get_font(40)

# ---------------------------
# AI CONTENT (SHORT + MANY SLIDES)
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
- 35 slides
- each slide max 4 words
- simple phrases
- no bullets
- no long sentences

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
            "slides":[{"text":"Try again"}]
        }

# ---------------------------
# SLIDE (FULL SCREEN TEXT)
# ---------------------------
def create_slide(text):
    img = Image.new("RGB", (1280, 720), "white")
    draw = ImageDraw.Draw(img)

    font = get_big_font(draw, text)

    bbox = draw.textbbox((0, 0), text, font=font)

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
# VIDEO (FORCE 5 MIN)
# ---------------------------
def create_video(slides):
    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=1)

    total_duration = 300  # 5 minutes
    per_slide = max(5, total_duration // len(slides))

    for i, slide in enumerate(slides):
        st.write(f"Slide {i+1}/{len(slides)}")

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
        st.warning("⚠️ Audio merge failed → showing separately")
        return None

# ---------------------------
# UI
# ---------------------------
file = st.file_uploader("Upload transcript (.txt)", type=["txt"])

if file:
    text = file.read().decode("utf-8")

    if st.button("Generate Video"):

        with st.spinner("Generating..."):

            data = generate_content(text)

            st.subheader("📄 Summary")
            st.write(data.get("summary", ""))

            slides = data.get("slides", [])

            audio = create_audio(slides)
            video = create_video(slides)

            final = merge(video, audio)

            st.success("✅ Video Ready!")

            if final:
                st.video(final)
            else:
                st.video(video)
                st.audio(audio)

