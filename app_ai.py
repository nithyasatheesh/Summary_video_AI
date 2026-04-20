import streamlit as st
from openai import OpenAI
from gtts import gTTS
import tempfile

# 🔐 Read API key from Streamlit Secrets
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="AI Coding Mentor", layout="centered")

st.title("💻 Smart Coding Mentor AI 🚀")
st.write("Ask coding, concept, or debugging questions (Java, React, Python, etc.)")

# ---------------------------
# 🎙️ Audio function
# ---------------------------
def generate_audio(text):
    clean_text = (
        text.replace("`", "")
        .replace("*", "")
        .replace("#", "")
    )
    tts = gTTS(clean_text)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(temp_file.name)
    return temp_file.name


# ---------------------------
# 🧠 System Prompt
# ---------------------------
SYSTEM_PROMPT = """
You are an AI coding mentor.

You can answer:
- Programming questions (Java, React, Python, etc.)
- Conceptual questions
- Debugging problems
- Real-world scenarios

Guidelines:
- Use simple English
- Be clear and structured
- If coding → give code + explanation
- If concept → explain with examples
- If debugging → explain error + fix
- Keep it beginner friendly
"""

# ---------------------------
# 💬 Multi-line input
# ---------------------------
user_input = st.text_area(
    "Ask your question:",
    height=180,
    placeholder="""Example:

Explain why this React code is not updating:

const [count, setCount] = useState(0);

setCount(count + 1);
setCount(count + 1);
"""
)

# ---------------------------
# 🚀 Generate Answer
# ---------------------------
if st.button("Generate Answer"):

    if user_input.strip() == "":
        st.warning("Please enter a question")
    else:
        with st.spinner("Thinking... 🤖"):

            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_input}
                    ]
                )

                answer = response.choices[0].message.content

                # 📘 Output
                st.subheader("📘 Explanation")
                st.write(answer)

                # 🎙️ Audio
                audio_file = generate_audio(answer)
                st.audio(audio_file)

            except Exception as e:
                st.error(f"Error: {e}")
