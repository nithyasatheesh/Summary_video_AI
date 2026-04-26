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

st.set_page_config(page_title="AI Video Generator")
st.title("🎬 AI Video Generator (Final Version)")

# ---------------------------
# AI CONTENT (BALANCED)
# ---------------------------
def generate_content(text):
    text = text[:2000]

    prompt = f"""
Return JSON:

{{
 "summary": "...",
 "slides":[
  {{"text":"..."}}
 ]
}}

RULES:
- 10 slides
- each slide 1 clear sentence
- 8–12 words
- meaningful explanation
- simple language

TEXT:
{text}
"""

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        raw = res.choices[0].message.content
        clean = raw[raw.find("{"):raw.rfind("}")+1]
        return json.loads(clean)

    except:
        return {
            "summary": "Error generating content",
            "slides": [{"text": "Please try again"}]
        }

# ---------------------------
# SAFE FONT
# ---------------------------
def load_font(size):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except:
        return ImageFont.load_default()

# ---------------------------
# AUTO FONT SCALE (FIXED)
# ---------------------------
def get_best_font(draw, text):
    for size in range(160, 40, -4):
        font = load_font(size)
        bbox = draw.textbbox((0,0), text, font=font)

        if bbox[2] < 1000 and bbox[3] < 500:
            return font

    return load_font(50)

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
# SLIDE (LEFT + BIG)
# ---------------------------
def create_slide(text):
    img = Image.new("RGB", (1280, 720), "white")
    draw = ImageDraw.Draw(img)

    font = get_best_font(draw, text)
    lines = wrap_text(draw, text, font, 1000)

    y = 180

    for line in lines:
        draw.text((80, y), line.strip(), fill="black", font=font)
        y += font.size + 25

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
# VIDEO (3–5 MIN)
# ---------------------------
def create_video(slides):
    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=1)

    total_duration = 240  # ~4 minutes
    per_slide = max(12, total_duration // len(slides))

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
                st.warning("⚠️ Audio merge failed → using separate audio")
                st.video(video)
                st.audio(audio)

