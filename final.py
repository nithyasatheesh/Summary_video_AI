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

st.title("🎬 AI Video Generator (Final Version)")

# ---------------------------
# AI CONTENT (MORE DETAILS)
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

FORMAT:
{{
 "summary":"...",
 "slides":[
  {{"title":"...","text":"..."}}
 ]
}}

RULES:
- 18–20 slides
- each slide = short explanation (8–12 words)
- clear educational tone

TEXT:
{text}
"""
            }]
        )

        raw = res.choices[0].message.content
        clean = raw[raw.find("{"):raw.rfind("}")+1]
        return json.loads(clean)

    except:
        return {
            "summary":"Error occurred",
            "slides":[{"title":"Retry","text":"Try again later"}]
        }

# ---------------------------
# SLIDE DESIGN (BIG LEFT)
# ---------------------------
def create_slide(title, text):
    img = Image.new("RGB", (1280, 720), "white")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 100)
        text_font = ImageFont.truetype("DejaVuSans.ttf", 90)
    except:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # Title
    draw.text((80, 80), title, fill="black", font=title_font)

    # Divider
    draw.line((80, 200, 1200, 200), fill="#888", width=4)

    # Wrap text manually
    words = text.split()
    lines, line = [], ""

    for w in words:
        test = line + w + " "
        if draw.textbbox((0,0), test, font=text_font)[2] < 1000:
            line = test
        else:
            lines.append(line)
            line = w + " "
    lines.append(line)

    y = 260
    for ln in lines:
        draw.text((80, y), ln.strip(), fill="black", font=text_font)
        y += 110

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# VIDEO
# ---------------------------
def create_video(slides):
    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=1)

    total_duration = 300  # 5 minutes
    per_slide = max(10, total_duration // len(slides))

    for slide in slides:
        img = create_slide(slide["title"], slide["text"])
        frame = imageio.imread(img)

        for _ in range(per_slide):
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
# MERGE AUDIO + VIDEO
# ---------------------------
def merge(video, audio):
    output = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name

    cmd = [
        FFMPEG,
        "-y",
        "-i", video,
        "-i", audio,
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

    if st.button("Generate Final Video"):

        data = generate_content(text)

        st.subheader("📄 Summary")
        st.write(data.get("summary", ""))

        slides = data.get("slides", [])

        video = create_video(slides)
        audio = create_audio(slides)
        final = merge(video, audio)

        st.success("✅ Video Ready!")
        st.video(final)

