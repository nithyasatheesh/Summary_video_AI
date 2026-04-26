import streamlit as st
import tempfile
import json
import asyncio
import os

# ---------------------------
# SAFE MOVIEPY IMPORT
# ---------------------------
MOVIEPY_AVAILABLE = True
try:
    import imageio_ffmpeg
    os.environ["IMAGEIO_FFMPEG_EXE"] = imageio_ffmpeg.get_ffmpeg_exe()
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
except Exception as e:
    MOVIEPY_AVAILABLE = False
    MOVIEPY_ERROR = str(e)

import edge_tts
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Video Generator", layout="centered")
st.title("🎬 AI Transcript → HD Video Generator")

# ---------------------------
# STOP IF MOVIEPY MISSING
# ---------------------------
if not MOVIEPY_AVAILABLE:
    st.error("❌ MoviePy not installed")
    st.code(MOVIEPY_ERROR)
    st.stop()

# ---------------------------
# AI
# ---------------------------
def call_ai(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"AI call failed: {e}")
        return "{}"

def clean_json(text):
    if not text:
        return "{}"
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return "{}"
    return text[start:end+1]

def generate_all(text):
    raw = call_ai(f"""
Create explanation slides.

STRICT:
- 10-12 slides
- Each slide MUST include title, points, explanation
- points = list of short bullets

Return JSON only.

TEXT:
{text}
""")

    try:
        return json.loads(clean_json(raw))
    except:
        st.warning("⚠️ AI JSON invalid, using fallback")
        return {"summary": "", "slides": []}

# ---------------------------
# VALIDATION (STRONG)
# ---------------------------
def validate_data(data):
    if not isinstance(data, dict):
        return {"summary": "", "slides": []}

    slides = data.get("slides", [])

    if not isinstance(slides, list):
        slides = []

    clean_slides = []

    for s in slides:
        if not isinstance(s, dict):
            continue

        title = str(s.get("title", "Untitled"))
        points = s.get("points", ["No content"])
        explanation = str(s.get("explanation", ""))

        if not isinstance(points, list):
            points = [str(points)]

        clean_slides.append({
            "title": title,
            "points": points,
            "explanation": explanation
        })

    if len(clean_slides) == 0:
        clean_slides = [{
            "title": "No Data",
            "points": ["AI failed to generate slides"],
            "explanation": "Please try again"
        }]

    return {
        "summary": data.get("summary", ""),
        "slides": clean_slides
    }

# ---------------------------
# FONTS
# ---------------------------
def get_fonts():
    try:
        return (
            ImageFont.truetype("DejaVuSans-Bold.ttf", 72),
            ImageFont.truetype("DejaVuSans.ttf", 42)
        )
    except:
        return (ImageFont.load_default(), ImageFont.load_default())

# ---------------------------
# TEXT WRAP
# ---------------------------
def wrap_text(text, font, max_width):
    words = str(text).split()
    lines, line = [], ""

    for word in words:
        test = line + word + " "
        if font.getbbox(test)[2] <= max_width:
            line = test
        else:
            lines.append(line.strip())
            line = word + " "

    lines.append(line.strip())
    return lines

# ---------------------------
# SLIDE
# ---------------------------
def create_slide(title, points):
    img = Image.new("RGB", (1280, 720), "#f9fafb")
    draw = ImageDraw.Draw(img)
    title_font, point_font = get_fonts()

    draw.text((100, 60), str(title), fill="#111", font=title_font)
    draw.line((100, 150, 1180, 150), fill="#ddd", width=4)

    y = 200
    for p in points:
        lines = wrap_text(p, point_font, 1000)
        for i, line in enumerate(lines):
            prefix = "• " if i == 0 else "  "
            draw.text((120, y), prefix + line, fill="#333", font=point_font)
            y += 55
        y += 20

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# TTS
# ---------------------------
async def tts_async(text, path):
    communicate = edge_tts.Communicate(
        text=str(text)[:500],
        voice="en-US-JennyNeural"
    )
    await communicate.save(path)

def generate_audio(text):
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(tts_async(text, path))
    loop.close()

    return path

# ---------------------------
# VIDEO
# ---------------------------
def create_clip(img_path, audio_path):
    audio = AudioFileClip(audio_path)
    duration = max(audio.duration, 8)

    clip = ImageClip(img_path).set_duration(duration)
    clip = clip.set_audio(audio)

    return clip

def generate_video(slides):
    clips = []

    for i, slide in enumerate(slides):
        st.write(f"Slide {i+1}/{len(slides)}")

        title = slide.get("title", "Untitled")
        points = slide.get("points", ["No content"])
        explanation = slide.get("explanation", "")

        img = create_slide(title, points)
        audio = generate_audio(explanation)

        clips.append(create_clip(img, audio))

    if not clips:
        raise Exception("No clips generated")

    final = concatenate_videoclips(clips, method="compose")

    output = "final_video.mp4"
    final.write_videofile(output, fps=24)

    return output

# ---------------------------
# UI
# ---------------------------
files = st.file_uploader(
    "Upload transcript",
    type=["txt"],
    accept_multiple_files=True
)

if st.button("Generate Video"):

    if not files:
        st.warning("Upload files first")
        st.stop()

    texts = [f.read().decode("utf-8") for f in files]
    merged = "\n\n".join(texts)

    data = generate_all(merged)
    data = validate_data(data)

    st.write("DEBUG:", data)

    try:
        video = generate_video(data["slides"])
        st.video(video)
    except Exception as e:
        st.error(f"Video failed: {e}")

