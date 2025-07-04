import os
import re
import io
import time
import socket
import streamlit as st
import google.generativeai as genai
from gtts import gTTS
from tempfile import NamedTemporaryFile
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr
from pydub import AudioSegment

# ======= CONFIGURE GEMINI =======
API_KEY = "AIzaSyBb5rqszdrMesMt86OJ_FhGUpn92Tz2dak"
genai.configure(api_key=API_KEY)

# ======= SUPPORTED LANGUAGES =======
SUPPORTED_LANGUAGES = {
    "english": "en", "hindi": "hi", "telugu": "te", "tamil": "ta",
    "kannada": "kn", "french": "fr", "spanish": "es", "german": "de",
    "japanese": "ja", "chinese": "zh", "arabic": "ar"
}

# ======= TEXT TO SPEECH =======
def speak(text, lang="en"):
    try:
        clean_text = re.sub(r'[!@#$%^&*()_+=\[\]{}<>\\|/:;\"\'~]', '', text)
        if not clean_text.strip():
            st.error("No valid text to convert to speech.")
            return
        supported_gtts_langs = ['en', 'hi', 'ta', 'fr', 'es', 'de', 'ja', 'zh-cn', 'ar']
        if lang not in supported_gtts_langs:
            st.warning(f"Language '{lang}' not supported by gTTS. Falling back to English.")
            lang = "en"
        tts = gTTS(text=clean_text, lang=lang)
        with NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            st.audio(fp.name, format="audio/mp3")
            time.sleep(1)
            os.unlink(fp.name)
    except Exception as e:
        st.error(f"TTS Error: {e}")

# ======= GEMINI FUNCTIONS =======
def suggest_recipe_names(ingredients):
    prompt = f"Suggest 3 recipe names using these ingredients: {ingredients}. Only return names, comma separated."
    model = genai.GenerativeModel("models/gemini-1.5-flash")
    try:
        response = model.generate_content(prompt)
        return [name.strip() for name in response.text.strip().split(",")] if response.text else []
    except Exception as e:
        st.error(f"Suggestion Error: {e}")
        return []

def fetch_recipe_details(recipe_name):
    prompt = f"""Give me a full recipe for '{recipe_name}' including:
- Title
- Estimated cooking time
- List of ingredients
- Step-by-step cooking instructions

Separate each section with two newlines."""
    model = genai.GenerativeModel("models/gemini-1.5-flash")
    try:
        response = model.generate_content(prompt)
        return response.text.strip() if response.text else ""
    except Exception as e:
        st.error(f"Fetch Error: {e}")
        return ""

def translate_recipe(text, language):
    if not text.strip():
        return text
    prompt = f"Translate this recipe into {language}:\n\n{text}"
    model = genai.GenerativeModel("models/gemini-1.5-flash")
    try:
        response = model.generate_content(prompt)
        return response.text.strip() if response.text else text
    except Exception as e:
        st.warning(f"Translation failed: {e}. Showing original.")
        return text

# ======= TRANSCRIBE RECORDED AUDIO =======
def transcribe_audio_bytes(audio_bytes):
    recognizer = sr.Recognizer()
    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        with NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            audio.export(temp_audio.name, format="wav")
            with sr.AudioFile(temp_audio.name) as source:
                audio_data = recognizer.record(source)
                return recognizer.recognize_google(audio_data)
    except sr.UnknownValueError:
        return "Could not understand the audio. Please try again."
    except sr.RequestError as e:
        return f"Speech recognition service error: {e}."
    except Exception as e:
        return f"Audio processing error: {e}"

# ======= STREAMLIT UI =======
st.set_page_config(page_title="AI Voice Cooking Assistant", layout="centered")
st.title("👩‍🍳 AI Voice Cooking Assistant")

st.markdown("""
Welcome to the Gemini-powered Cooking Assistant! 🎙  
- Speak or type your ingredients or recipe name  
- Get full recipes with ingredients, time, and steps  
- Multilingual support 🌐
""")

lang_input = st.selectbox("Choose output language:", list(SUPPORTED_LANGUAGES.keys()))
lang_code = SUPPORTED_LANGUAGES[lang_input.lower()]
mode = st.radio("Input Type", ["Ingredients", "Recipe Name"], horizontal=True)

# ======= RECORD BUTTON =======
st.markdown("🎤 Click below to record audio input:")
audio = mic_recorder(start_prompt="Start recording", stop_prompt="Stop recording", key="recorder")

if audio and audio["bytes"]:
    transcription = transcribe_audio_bytes(audio["bytes"])
    if transcription:
        st.session_state.manual_input_text = transcription
        st.success(f"📝 Transcribed: {transcription}")

# ======= MANUAL TEXT AREA =======
manual_input = st.text_area(
    "📝 Type or speak ingredients/recipe name",
    value=st.session_state.get("manual_input_text", ""),
    key="manual_input_box"
)

# ======= MAIN LOGIC =======
user_input = manual_input.strip()

if user_input:
    if mode == "Ingredients":
        suggestions = suggest_recipe_names(user_input)
        if suggestions:
            selected = st.selectbox("Choose a suggested recipe:", suggestions)
            if selected and st.button("🔍 Show Recipe"):
                recipe = fetch_recipe_details(selected)
                if lang_code != "en":
                    recipe = translate_recipe(recipe, lang_input)
                st.markdown("## 🍽 Recipe")
                st.markdown(recipe)
                speak(recipe, lang=lang_code)
    else:
        if st.button("🔍 Show Recipe"):
            recipe = fetch_recipe_details(user_input)
            if lang_code != "en":
                recipe = translate_recipe(recipe, lang_input)
            st.markdown("## 🍽 Recipe")
            st.markdown(recipe)
            speak(recipe, lang=lang_code)

# ======= TROUBLESHOOTING =======
st.markdown("---")
st.markdown("""
### Troubleshooting:
- 🎤 Use Chrome or Firefox for microphone access.
- 📡 Make sure you're connected to the internet.
- 💬 Speak clearly and avoid background noise.
- ⚠️ Languages: Only supports en, hi, ta, fr, es, de, ja, zh-cn, ar for text-to-speech.
""")
st.caption("Made with ❤ using Gemini + Streamlit + SpeechRecognition")
