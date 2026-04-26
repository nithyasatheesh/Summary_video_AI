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

st.title("🎬 AI Video Generator (Stable Audio Version)")

# ---------------------------
# AI CONTENT
# ---------------------------
def generate_content(text):
    text = text[:2000]

    prompt = f"""
Return JSON:

{{
 "summary": "...",
 "slides":[
  {{"title":"...","points":["...","..."]}}
 ]
}}

RULES:
- 20 slides
- each point 6–8 words
- clear explanation

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
# SLIDE DESIGN
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

    draw.text((80, 60), title, fill="black", font=title_font)

    y = 180
    for p in points:
        draw.text((80, y), "• " + p, fill="black", font=point_font)
        y += 100

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
    script = ". ".join(
        [" ".join(s["points"]) for s in slides]
    )

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(tts_async(script, path))
    loop.close()

    return path, script

# ---------------------------
# VIDEO (ESTIMATE DURATION)
# ---------------------------
def create_video(slides, script):
    # estimate speech duration (~150 words/min)
    words = len(script.split())
    total_seconds = max(120, int(words / 2.5))  # ~150 wpm

    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=1)

    per_slide = max(5, total_seconds // len(slides))

    for slide in slides:
        img = create_slide(slide["title"], slide["points"])
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
        st.warning("⚠️ Merge failed → showing separately")
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

        audio, script = create_audio(slides)
        video = create_video(slides, script)

        final = merge(video, audio)

        st.success("✅ Done!")

        if final:
            st.video(final)
        else:
            st.video(video)

