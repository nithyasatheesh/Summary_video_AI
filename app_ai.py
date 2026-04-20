import streamlit as st
import ollama
from gtts import gTTS
import tempfile

from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
from docx import Document

st.title("🎬 Summary Video Agent (TXT + DOCX Supported)")

# ---------------------------
# 📄 READ DOCX
# ---------------------------
def read_docx(file):
    doc = Document(file)
    text = []
    for para in doc.paragraphs:
        if para.text.strip():
            text.append(para.text)
    return "\n".join(text)


# ---------------------------
# 🧠 AI FUNCTIONS
# ---------------------------
def generate_summary(text):
    return ollama.chat(
        model='llama3',
        messages=[{
            'role': 'user',
            'content': f"""
Summarize ALL content clearly.

- Use all information
- Simple English
- Keep key points

{text}
"""
        }]
    )['message']['content']


def generate_slides(summary):
    return ollama.chat(
        model='llama3',
        messages=[{
            'role': 'user',
            'content': f"""
Create slides in EXACT format:

### Title: Topic
Point one
Point two

Rules:
- No symbols
- No numbering
- Simple language
- Create 4 slides

{summary}
"""
        }]
    )['message']['content']


def parse_slides(text):
    raw = text.split("### Title:")
    slides = []

    for block in raw:
        if not block.strip():
            continue

        lines = block.strip().split("\n")
        title = lines[0]
        content = "\n".join(lines[1:])

        slides.append((title, content))

    return slides


def clean_text(text):
    return text.replace('"', '').replace("'", '').replace("*", '').replace("`", '')


# ---------------------------
# 🎨 SLIDE CREATION
# ---------------------------
def create_slide_image(title, content):
    img = Image.new("RGB", (1280, 720), "white")
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("arial.ttf", 60)
        font_content = ImageFont.truetype("arial.ttf", 40)
    except:
        font_title = ImageFont.load_default()
        font_content = ImageFont.load_default()

    draw.text((100, 50), title, fill="black", font=font_title)

    y = 180
    for line in content.split("\n"):
        draw.text((120, y), line.strip(), fill="black", font=font_content)
        y += 70

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path


# ---------------------------
# 🎬 VIDEO GENERATION
# ---------------------------
def generate_video(slides_text):
    slides = parse_slides(slides_text)
    clips = []

    for title, content in slides:

        explanation = ollama.chat(
            model='llama3',
            messages=[{
                'role': 'user',
                'content': f"""
Explain clearly in simple English.

Topic:
{title}
{content}
"""
            }]
        )['message']['content']

        explanation = clean_text(explanation)

        # Audio
        tts = gTTS(explanation)
        audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        tts.save(audio_file)

        audio = AudioFileClip(audio_file)

        # Slide
        img = create_slide_image(title, content)

        clip = ImageClip(img).with_duration(audio.duration)
        clip = clip.with_audio(audio)

        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")

    video_path = "final_video.mp4"
    video.write_videofile(video_path, fps=12)

    return video_path


# ---------------------------
# 📥 UI
# ---------------------------
uploaded_files = st.file_uploader(
    "Upload TXT or DOCX files",
    type=["txt", "docx"],
    accept_multiple_files=True
)

if st.button("Generate Video"):

    if not uploaded_files:
        st.warning("Upload files first")
    else:
        with st.spinner("Processing..."):

            texts = []

            for f in uploaded_files:

                if f.name.endswith(".txt"):
                    texts.append(f.read().decode("utf-8"))

                elif f.name.endswith(".docx"):
                    texts.append(read_docx(f))

            full_text = "\n\n---\n\n".join(texts)

            summary = generate_summary(full_text)
            slides = generate_slides(summary)

            st.subheader("Summary")
            st.write(summary)

            video_path = generate_video(slides)

            st.success("Video generated!")
            st.video(video_path)
