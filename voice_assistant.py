import os
import re
import base64
import io
import streamlit as st
import google.generativeai as genai
from gtts import gTTS
from tempfile import NamedTemporaryFile
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr

# ======= CONFIGURE GEMINI =======
API_KEY = "AIzaSyBuIBRTB_Oe1Vtip702MDrMvLJhK3y4dms"  # ← Replace with your actual Gemini API key
genai.configure(api_key=API_KEY)

# ======= SUPPORTED LANGUAGES =======
SUPPORTED_LANGUAGES = {
    "english": "en", "hindi": "hi", "telugu": "te", "tamil": "ta",
    "kannada": "kn", "french": "fr", "spanish": "es", "german": "de",
    "japanese": "ja", "chinese": "zh", "arabic": "ar"
}

# ======= TEXT TO SPEECH =======
def speak(text, lang="en"):
    clean_text = re.sub(r'[!@#$%^&*()_+=\[\]{}<>\\|/:;\"\'~]', '', text)
    tts = gTTS(text=clean_text, lang=lang)
    with NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        tts.save(fp.name)
        st.audio(fp.name, format="audio/mp3")

# ======= GEMINI: SUGGEST RECIPE NAMES =======
def suggest_recipe_names(ingredients):
    prompt = f"""
Suggest 3 recipe names using these ingredients: {ingredients}.
Only return names, comma separated.
"""
    model = genai.GenerativeModel("models/gemini-1.5-flash")
    try:
        response = model.generate_content(prompt)
        return [name.strip() for name in response.text.strip().split(",")]
    except Exception as e:
        st.error(f"Suggestion Error: {e}")
        return []

# ======= GEMINI: FETCH FULL RECIPE =======
def fetch_recipe_details(recipe_name):
    prompt = f"""
Give me a full recipe for '{recipe_name}' including:
- Title
- Estimated cooking time
- List of ingredients
- Step-by-step cooking instructions

Separate each section with two newlines.
"""
    model = genai.GenerativeModel("models/gemini-1.5-flash")
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        st.error(f"Fetch Error: {e}")
        return ""

# ======= GEMINI: TRANSLATE =======
def translate_recipe(text, language):
    prompt = f"Translate this recipe into {language} language:\n\n{text}"
    model = genai.GenerativeModel("models/gemini-1.5-flash")
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        st.warning("Translation failed. Showing English result.")
        return text

# ======= STREAMLIT INTERFACE =======
st.set_page_config(page_title="AI Cooking Assistant", layout="centered")
st.title("👩‍🍳 AI Voice Cooking Assistant")

st.markdown("""
Welcome to the *Gemini-powered Cooking Assistant*! 🎙  
- Speak or type your ingredients or recipe name  
- Get full recipes with ingredients, time, and steps  
- Multilingual support 🌐
""")

# ======= LANGUAGE & MODE SELECTION =======
lang_input = st.selectbox("Choose output language:", list(SUPPORTED_LANGUAGES.keys()), index=0)
lang_code = SUPPORTED_LANGUAGES[lang_input.lower()]
mode = st.radio("Input Type", ["Ingredients", "Recipe Name"], horizontal=True)

# ======= MIC AND/OR MANUAL INPUT =======
col1, col2 = st.columns(2)
with col1:
    st.markdown("🎤 *Mic Input*")
    audio = mic_recorder(start_prompt="Click to speak", stop_prompt="Stop recording", key="mic")
with col2:
    st.markdown("📝 *Manual Input*")
    manual_input = st.text_area("Or type here if mic doesn't work", "")

user_input = ""

# ======= PROCESS AUDIO IF PRESENT =======
if audio and "data" in audio:
    try:
        audio_bytes = base64.b64decode(audio["data"].split(",")[1])
        audio_file = io.BytesIO(audio_bytes)

        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)
            user_input = recognizer.recognize_google(audio_data)
        st.success(f"🎧 Transcribed: {user_input}")

    except Exception as e:
        st.error(f"❌ Voice input failed: {e}")

# ======= FALLBACK TO MANUAL INPUT =======
if not user_input and manual_input.strip():
    user_input = manual_input.strip()
    st.info(f"✍ Using manual input: {user_input}")

# ======= HANDLE MAIN FUNCTIONALITY =======
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

    else:  # Direct recipe name mode
        if st.button("🔍 Show Recipe"):
            recipe = fetch_recipe_details(user_input)
            if lang_code != "en":
                recipe = translate_recipe(recipe, lang_input)
            st.markdown("## 🍽 Recipe")
            st.markdown(recipe)
            speak(recipe, lang=lang_code)

st.markdown("---")
st.caption("Made with ❤ using Gemini + Streamlit")