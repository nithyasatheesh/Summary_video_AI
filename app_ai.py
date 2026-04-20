import streamlit as st
import tempfile
import json
import asyncio

from openai import OpenAI
import edge_tts
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="AI Video Generator", layout="centered")
st.title("🎬 AI Transcript → Video Generator (Cloud Ready)")

# ---------------------------
# 🔑 OPENAI CLIENT
# ---------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ---------------------------
# 🧠 CALL OPENAI
# ---------------------------
def call_ai(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content

# ---------------------------
# 🧹 CLEAN JSON
# ---------------------------
def clean_json(text):
    start = text.find("{")
    end = text.rfind("}") + 1
    return text[start:end]

# ---------------------------
# 🧠 SINGLE AI CALL
# ---------------------------
def generate_all(text):
    raw = call_ai(f"""
You are a teaching assistant.

Task:
1. Create a COMPLETE summary (cover ALL concepts)
2. Create slides

STRICT RULES:
- Do NOT skip important ideas
- Use simple English
- Minimum summary length: 150 words

Slides:
- 4 to 5 slides
- Max 4 points each
- Add short explanation per slide

RETURN ONLY VALID JSON

Format:
{{
  "summary": "...",
  "slides": [
    {{
      "title": "...",
      "points": ["...", "..."],
      "explanation": "..."
    }}
  ]
}}

TEXT:
{text}
""")

    try:
        raw = clean_json(raw)
        return json.loads(raw)
    except:
        return None

# ---------------------------
# 🎨 SLIDE IMAGE
# ---------------------------
def create_slide(title, points):
    img = Image.new("RGB", (1280, 720), "#f5f5f5")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    draw.text((50, 40), title, fill="black", font=font)
    draw.line((50, 100, 1200, 100), fill="black", width=2)

    y = 150
    for p in points:
        draw.text((80, y), f"• {p}", fill="black", font=font)
        y += 50

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# 🔊 EDGE TTS
# ---------------------------
async def tts_async(text, path):
    communicate = edge_tts.Communicate(
        text=text,
        voice="en-US-AriaNeural"
    )
    await communicate.save(path)

def generate_audio(text):
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    asyncio.run(tts_async(text, path))
    return path

# ---------------------------
# 🎬 CREATE CLIP
# ---------------------------
def create_clip(img_path, audio_path):
    audio = AudioFileClip(audio_path)
    clip = ImageClip(img_path).with_duration(audio.duration)
    clip = clip.with_audio(audio)
    return clip

# ---------------------------
# 🎥 GENERATE VIDEO
# ---------------------------
def generate_video(slides):
    clips = []

    for slide in slides:
        img = create_slide(slide["title"], slide["points"])
        audio = generate_audio(slide["explanation"])

        clip = create_clip(img, audio)
        clips.append(clip)

    final = concatenate_videoclips(clips, method="compose")

    output = "final_video.mp4"
    final.write_videofile(output, fps=12, preset="ultrafast")

    return output

# ---------------------------
# 📥 UI
# ---------------------------
files = st.file_uploader(
    "Upload transcript files",
    type=["txt"],
    accept_multiple_files=True
)

if st.button("Generate Video"):

    if not files:
        st.warning("Upload files first")
        st.stop()

    with st.spinner("Processing..."):

        texts = [f.read().decode("utf-8") for f in files]
        merged = "\n\n".join(texts)

        data = generate_all(merged)

        if not data:
            st.error("AI failed. Try again.")
            st.stop()

        st.subheader("📄 Summary")
        st.write(data["summary"])

        video = generate_video(data["slides"])

        st.success("✅ Video Ready!")
        st.video(video)
