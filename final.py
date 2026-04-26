import streamlit as st
import tempfile
import asyncio

import edge_tts
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Video Generator")
st.title("🎬 Stable AI Video Generator")

# ---------------------------
# 🧠 STRUCTURED AI CALL
# ---------------------------
def generate_all(text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": f"""
Create explanation slides.

RULES:
- 15 slides
- 2 points per slide
- short simple sentences

Return JSON ONLY.
TEXT:
{text}
"""
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "slides_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "slides": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "points": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "explanation": {"type": "string"}
                                },
                                "required": ["title", "points", "explanation"]
                            }
                        }
                    },
                    "required": ["slides"]
                }
            }
        }
    )

    return response.choices[0].message.parsed

# ---------------------------
# 🎨 SLIDE DESIGN
# ---------------------------
def create_slide(title, points):
    img = Image.new("RGB", (1280, 720), "#f8fafc")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 70)
        point_font = ImageFont.truetype("DejaVuSans.ttf", 48)
    except:
        title_font = ImageFont.load_default()
        point_font = ImageFont.load_default()

    draw.text((100, 60), title, fill="#111", font=title_font)

    y = 220
    for p in points:
        draw.text((120, y), p, fill="#222", font=point_font)
        y += 70

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# 🔊 TTS
# ---------------------------
async def tts_async(text, path):
    communicate = edge_tts.Communicate(
        text=text[:200],
        voice="en-US-JennyNeural",
        rate="-5%"
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
# 🎬 CLIP
# ---------------------------
def create_clip(img_path, audio_path):
    audio = AudioFileClip(audio_path)
    duration = max(audio.duration, 8)

    clip = ImageClip(img_path).set_duration(duration)
    clip = clip.set_audio(audio)

    return clip

# ---------------------------
# 🎥 VIDEO
# ---------------------------
def generate_video(slides):
    clips = []

    for i, slide in enumerate(slides):
        st.write(f"Slide {i+1}/{len(slides)}")

        img = create_slide(
            slide.get("title", "Untitled"),
            slide.get("points", [])
        )

        audio = generate_audio(slide.get("explanation", ""))

        clips.append(create_clip(img, audio))

    final = concatenate_videoclips(clips)

    output = "final_video.mp4"
    final.write_videofile(output, fps=24)

    return output

# ---------------------------
# UI
# ---------------------------
files = st.file_uploader("Upload transcript", type=["txt"], accept_multiple_files=True)

if st.button("Generate Video"):

    if not files:
        st.warning("Upload files first")
        st.stop()

    texts = [f.read().decode("utf-8") for f in files]
    merged = "\n\n".join(texts)

    data = generate_all(merged)

    st.subheader("Summary")
    st.write(data.get("summary", ""))

    video = generate_video(data.get("slides", []))

    st.video(video)

