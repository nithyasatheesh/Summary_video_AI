import streamlit as st
import tempfile
import json
import imageio.v2 as imageio
import subprocess
import asyncio
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI
import edge_tts

# ---------------------------
# INIT
# ---------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Video Generator")
st.title("🎬 AI Video Generator (With Audio)")

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
- 12 slides
- each slide max 5 words

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
        data = json.loads(raw[start:end])

        return data

    except:
        return {
            "slides": [
                {"title": "Error", "text": "Try again"}
            ]
        }

# ---------------------------
# SLIDE (BIG TEXT)
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
# AUDIO (ALL SLIDES COMBINED)
# ---------------------------
async def generate_audio(text, path):
    communicate = edge_tts.Communicate(
        text=text,
        voice="en-US-JennyNeural",
        rate="-5%"
    )
    await communicate.save(path)

def create_full_audio(slides):
    script = ". ".join([s["text"] for s in slides])

    audio_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(generate_audio(script, audio_path))
    loop.close()

    return audio_path

# ---------------------------
# VIDEO (NO AUDIO)
# ---------------------------
def create_video(slides):
    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=1)

    duration_per_slide = 10

    for slide in slides:
        img = create_slide(slide["title"], slide["text"])
        frame = imageio.imread(img)

        for _ in range(duration_per_slide):
            writer.append_data(frame)

    writer.close()
    return video_path

# ---------------------------
# MERGE AUDIO + VIDEO (FFMPEG)
# ---------------------------
def merge_audio_video(video_path, audio_path):
    output = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name

    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        output
    ]

    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return output

# ---------------------------
# UI
# ---------------------------
file = st.file_uploader("Upload transcript", type=["txt"])

if file:
    text = file.read().decode("utf-8")

    if st.button("Generate Video"):

        with st.spinner("Generating video with audio..."):

            data = generate_content(text)
            slides = data.get("slides", [])

            video_path = create_video(slides)
            audio_path = create_full_audio(slides)

            final_video = merge_audio_video(video_path, audio_path)

            st.success("✅ Video Ready!")
            st.video(final_video)

