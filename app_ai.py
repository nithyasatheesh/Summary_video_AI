import streamlit as st
import tempfile
import json
import asyncio

from openai import OpenAI
import edge_tts
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="AI Video Generator", layout="centered")
st.title("🎬 AI Transcript → Video Generator")

# ---------------------------
# 🔑 OPENAI CLIENT
# ---------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ---------------------------
# 🧠 CALL AI
# ---------------------------
def call_ai(prompt):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return res.choices[0].message.content

# ---------------------------
# 🧹 CLEAN JSON
# ---------------------------
def clean_json(text):
    start = text.find("{")
    end = text.rfind("}") + 1
    return text[start:end]

# ---------------------------
# 🧠 GENERATE CONTENT
# ---------------------------
def generate_all(text):
    raw = call_ai(f"""
You are a teaching assistant.

Task:
1. Create COMPLETE summary (cover ALL concepts)
2. Create slides

Rules:
- Simple English
- Minimum 150 words summary

Slides:
- 3 slides only (faster)
- Max 4 points each
- Add short explanation

Return ONLY JSON:

{{
  "summary": "...",
  "slides": [
    {{
      "title": "...",
      "points": ["..."],
      "explanation": "..."
    }}
  ]
}}

TEXT:
{text}
""")

    try:
        return json.loads(clean_json(raw))
    except:
        return None

# ---------------------------
# 🎨 SLIDE IMAGE
# ---------------------------
def create_slide(title, points):
    img = Image.new("RGB", (1280, 720), "#222")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    draw.text((50, 40), title, fill="white", font=font)

    y = 150
    for p in points:
        draw.text((80, y), f"• {p}", fill="white", font=font)
        y += 50

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# 🔊 TTS (SAFE)
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
            clip = ImageClip(img).with_duration(audio_clip.duration)
            clip = clip.with_audio(audio_clip)

            clips.append(clip)

        except:
            continue

    if not clips:
        return None

    final = concatenate_videoclips(clips, method="compose")

    output = "video.mp4"
    final.write_videofile(output, fps=12, preset="ultrafast")

    return output

# ---------------------------
# 📥 UI
# ---------------------------
files = st.file_uploader("Upload transcripts", type=["txt"], accept_multiple_files=True)

if st.button("Generate Video"):

    if not files:
        st.warning("Upload files")
        st.stop()

    texts = [f.read().decode("utf-8") for f in files]
    merged = "\n\n".join(texts)

    data = generate_all(merged)

    if not data:
        st.error("AI failed")
        st.stop()

    st.subheader("Summary")
    st.write(data["summary"])

    video = generate_video(data["slides"])

    if video:
        st.video(video)
    else:
        st.error("Video failed")
