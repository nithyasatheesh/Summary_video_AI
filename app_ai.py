import streamlit as st
import tempfile
import json
import asyncio

from openai import OpenAI
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

st.set_page_config(page_title="AI Video Generator", layout="centered")
st.title("🎬 Transcript → Video Generator")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


# ---------------------------
# 🎨 SLIDE IMAGE (UPDATED)
# ---------------------------
def wrap_text(text, font, max_width, draw):
    lines = []
    words = text.split()
    current = ""

    for word in words:
        test = current + " " + word if current else word
        w, _ = draw.textsize(test, font=font)

        if w <= max_width:
            current = test
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def create_slide(title, points):
    img = Image.new("RGB", (1280, 720), "white")  # ✅ white bg
    draw = ImageDraw.Draw(img)

    # ✅ Load fonts
    try:
        title_font = ImageFont.truetype("fonts/DejaVuSans-Bold.ttf", 60)
        text_font = ImageFont.truetype("fonts/DejaVuSans.ttf", 40)
    except:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # ✅ Centered title
    draw.text((640, 70), title, fill="black", font=title_font, anchor="mm")

    # ✅ Bullet points with wrapping
    y = 180
    max_width = 1000

    for p in points:
        lines = wrap_text(p, text_font, max_width, draw)

        for line in lines:
            draw.text((100, y), f"• {line}", fill="black", font=text_font)
            y += 55

        y += 10  # spacing between bullets

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path


# ---------------------------
# 🔊 AUDIO
# ---------------------------
async def tts_async(text, path):
    communicate = edge_tts.Communicate(text, voice="en-US-AriaNeural")
    await communicate.save(path)


def generate_audio(text):
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    try:
        asyncio.run(tts_async(text, path))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(tts_async(text, path))
    return path


# ---------------------------
# 🎥 VIDEO
# ---------------------------
def generate_video(slides):
    clips = []

    for slide in slides:
        try:
            img = create_slide(slide["title"], slide["points"])
            audio = generate_audio(slide["explanation"])

            audio_clip = AudioFileClip(audio)

            # ✅ fixed duration method
            clip = ImageClip(img, duration=audio_clip.duration)
            clip = clip.set_audio(audio_clip)

            clips.append(clip)

        except Exception as e:
            print("Slide error:", e)

    if not clips:
        return None

    final = concatenate_videoclips(clips)

    output = "video.mp4"
    final.write_videofile(
        output,
        fps=12,
        preset="ultrafast",
        codec="libx264",
        audio_codec="aac"
    )

    return output
