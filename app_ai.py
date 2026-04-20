import streamlit as st
import tempfile
import json
import asyncio

from openai import OpenAI
import edge_tts
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont

st.title("🎬 Long Transcript → Video Generator")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ---------------------------
# 🧠 AI CALL
# ---------------------------
def call_ai(prompt):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return res.choices[0].message.content

# ---------------------------
# ✂️ SPLIT TEXT
# ---------------------------
def split_text(text, size=3000):
    return [text[i:i+size] for i in range(0, len(text), size)]

# ---------------------------
# 🧠 STEP 1: CHUNK SUMMARIES
# ---------------------------
def summarize_chunks(text):
    chunks = split_text(text)
    summaries = []

    for chunk in chunks:
        s = call_ai(f"""
Summarize ALL important concepts.

Rules:
- Do NOT skip ideas
- Simple English

TEXT:
{chunk}
""")
        summaries.append(s)

    return "\n".join(summaries)

# ---------------------------
# 🧠 STEP 2: FINAL CONTENT
# ---------------------------
def generate_all(text):
    raw = call_ai(f"""
You are a teacher.

GOAL:
Create a 5-minute learning video script.

RULES:
- Use ALL concepts from input
- Do NOT skip anything
- 600–900 words explanation

SLIDES:
- 6–8 slides
- Each explanation: 80–120 words

RETURN JSON:

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
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except:
        return None

# ---------------------------
# 🎨 SLIDE
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
# 🔊 AUDIO
# ---------------------------
async def tts_async(text, path):
    communicate = edge_tts.Communicate(text, voice="en-US-AriaNeural")
    await communicate.save(path)

def generate_audio(text):
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    try:
        asyncio.run(tts_async(text, path))
    except:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(tts_async(text, path))
    return path

# ---------------------------
# 🎥 VIDEO
# ---------------------------
def generate_video(slides):
    clips = []

    for slide in slides:
        img = create_slide(slide["title"], slide["points"])
        audio = generate_audio(slide["explanation"])

        audio_clip = AudioFileClip(audio)
        clip = ImageClip(img).with_duration(audio_clip.duration)
        clip = clip.with_audio(audio_clip)

        clips.append(clip)

    final = concatenate_videoclips(clips)

    output = "video.mp4"
    final.write_videofile(output, fps=12, preset="ultrafast")

    return output

# ---------------------------
# UI
# ---------------------------
files = st.file_uploader("Upload transcripts", type=["txt"], accept_multiple_files=True)

if st.button("Generate Video"):

    texts = [f.read().decode("utf-8") for f in files]
    merged = "\n\n".join(texts)

    st.write("🔄 Step 1: Processing chunks...")
    chunk_summary = summarize_chunks(merged)

    st.write("🔄 Step 2: Creating final content...")
    data = generate_all(chunk_summary)

    if not data:
        st.error("Failed")
        st.stop()

    st.write(data["summary"])

    st.write("🎬 Generating video...")
    video = generate_video(data["slides"])

    st.video(video)
