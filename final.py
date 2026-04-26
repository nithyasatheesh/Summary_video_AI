import streamlit as st
import tempfile
import json
import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

# ---------------------------
# INIT
# ---------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="YouTube Video Generator")
st.title("🎬 Transcript → 3–4 Min Video (Stable)")

# ---------------------------
# 🧠 AI (STRICT + SAFE)
# ---------------------------
def generate_content(text):
    # keep input short for reliability
    text = text[:2000]

    prompt = f"""
Return ONLY valid JSON. No extra text.

FORMAT:
{{
 "summary": "string",
 "slides": [
   {{"title": "string", "text": "string"}}
 ]
}}

RULES:
- 12–16 slides
- Each slide: ONE short sentence
- Max 6 words per sentence
- Very simple language
- Include intro and recap

TEXT:
{text}
"""

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        raw = res.choices[0].message.content.strip()

        # ---- clean JSON safely
        start = raw.find("{")
        end = raw.rfind("}") + 1
        clean = raw[start:end]

        data = json.loads(clean)

        # ---- validate
        slides = data.get("slides", [])
        if not isinstance(slides, list) or len(slides) == 0:
            raise ValueError("No slides")

        # sanitize each slide
        fixed = []
        for s in slides:
            if isinstance(s, dict):
                title = str(s.get("title", "Topic")).strip()[:40]
                text = str(s.get("text", "")).strip()[:80]
                if text:
                    fixed.append({"title": title, "text": text})

        if not fixed:
            raise ValueError("Invalid slides")

        data["slides"] = fixed
        return data

    except Exception as e:
        st.warning(f"AI issue → using fallback. ({e})")

        # ---- fallback (always works)
        sentences = [s.strip() for s in text.split(".") if s.strip()][:12]
        slides = []
        for i, s in enumerate(sentences):
            slides.append({
                "title": f"Point {i+1}",
                "text": " ".join(s.split()[:6])
            })

        if not slides:
            slides = [{"title": "Info", "text": "Upload valid transcript"}]

        return {"summary": "Auto summary", "slides": slides}

# ---------------------------
# 🎨 BIG, CLEAR SLIDE
# ---------------------------
def create_slide(title, text):
    img = Image.new("RGB", (1280, 720), "#0b1220")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 100)
        text_font = ImageFont.truetype("DejaVuSans.ttf", 90)
    except:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # Title (centered)
    tb = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((1280 - tb[2]) / 2, 80), title, fill="#facc15", font=title_font)

    # Text (wrap + centered)
    words = text.split()
    lines, line = [], ""
    for w in words:
        test = line + w + " "
        if text_font.getbbox(test)[2] < 1000:
            line = test
        else:
            lines.append(line)
            line = w + " "
    lines.append(line)

    y = 300
    for ln in lines:
        bb = draw.textbbox((0, 0), ln, font=text_font)
        draw.text(((1280 - bb[2]) / 2, y), ln.strip(), fill="#e5e7eb", font=text_font)
        y += 110

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path

# ---------------------------
# 🎥 VIDEO (3–4 MIN GUARANTEED)
# ---------------------------
def generate_video(slides):
    video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    writer = imageio.get_writer(video_path, fps=1)

    n = max(1, len(slides))
    target_seconds = 240  # ~4 minutes
    per_slide = max(8, target_seconds // n)  # >= 8s each

    total_frames = 0

    for i, s in enumerate(slides):
        st.write(f"Slide {i+1}/{n}")

        img = create_slide(s["title"], s["text"])
        frame = imageio.imread(img)

        for _ in range(per_slide):
            writer.append_data(frame)
            total_frames += 1

    writer.close()

    if total_frames == 0:
        return None

    return video_path

# ---------------------------
# UI
# ---------------------------
file = st.file_uploader("Upload transcript (.txt)", type=["txt"])

if file:
    text = file.read().decode("utf-8")

    if st.button("Generate Video"):
        with st.spinner("🎬 Generating…"):
            data = generate_content(text)

            st.subheader("Summary")
            st.write(data.get("summary", ""))

            slides = data.get("slides", [])
            st.write(f"Slides: {len(slides)}")

            video = generate_video(slides)

            if video:
                st.success("✅ Video ready!")
                st.video(video)
            else:
                st.error("❌ Failed to generate video")

