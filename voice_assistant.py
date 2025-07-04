import os
import re
import io
import streamlit as st
import google.generativeai as genai
from gtts import gTTS
from tempfile import NamedTemporaryFile
import speech_recognition as sr


# ======= CONFIGURE GEMINI =======
API_KEY = "AIzaSyBb5rqszdrMesMt86OJ_FhGUpn92Tz2dak"  # Replace with your Gemini API key
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
        # Clean text by removing problematic characters, but preserve meaningful content
        clean_text = re.sub(r'[!@#$%^&*()_+=\[\]{}<>\\|/:;\"\'~]', '', text)
        if not clean_text.strip():
            st.error("No valid text to convert to speech. Please try again.")
            return

        # Verify language support for gTTS
        supported_gtts_langs = ['en', 'hi', 'ta', 'fr', 'es', 'de', 'ja', 'zh-cn', 'ar']
        if lang not in supported_gtts_langs:
            st.warning(f"Language '{lang}' not supported by gTTS. Falling back to English.")
            lang = "en"

        # Generate and play speech
        tts = gTTS(text=clean_text, lang=lang)
        with NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            st.audio(fp.name, format="audio/mp3")
            time.sleep(1)  # Ensure file is closed before deletion
            os.unlink(fp.name)  # Clean up temporary file
    except Exception as e:
        st.error(f"Text-to-speech error: {e}")

# ======= GEMINI: SUGGEST RECIPE NAMES =======
def suggest_recipe_names(ingredients):
    prompt = f"Suggest 3 recipe names using these ingredients: {ingredients}. Only return names, comma separated."
    model = genai.GenerativeModel("models/gemini-1.5-flash")
    try:
        response = model.generate_content(prompt)
        if response.text.strip():
            return [name.strip() for name in response.text.strip().split(",")]
        else:
            st.error("No recipe suggestions received from Gemini API.")
            return []
    except Exception as e:
        st.error(f"Suggestion Error: {e}")
        return []

# ======= GEMINI: FETCH FULL RECIPE =======
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
        if response.text.strip():
            return response.text.strip()
        else:
            st.error(f"No recipe details received for '{recipe_name}'.")
            return ""
    except Exception as e:
        st.error(f"Fetch Error: {e}")
        return ""

# ======= GEMINI: TRANSLATE =======
def translate_recipe(text, language):
    if not text.strip():
        st.error("No recipe text to translate.")
        return text
    prompt = f"Translate this recipe into {language} language:\n\n{text}"
    model = genai.GenerativeModel("models/gemini-1.5-flash")
    try:
        response = model.generate_content(prompt)
        if response.text.strip():
            return response.text.strip()
        else:
            st.warning(f"Translation to {language} failed. Showing English result.")
            return text
    except Exception as e:
        st.warning(f"Translation failed: {e}. Showing English result.")
        return text

# ======= SPEECH RECOGNITION =======
def transcribe_speech():
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            st.info("Listening... Speak clearly into the microphone.")
            r.adjust_for_ambient_noise(source, duration=1)
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
                st.info("Processing audio...")
                try:
                    text = r.recognize_google(audio)
                    return text
                except sr.UnknownValueError:
                    return "Could not understand the audio. Please speak clearly."
                except sr.RequestError as e:
                    return f"Speech recognition service error: {e}. Check your internet connection."
            except sr.WaitTimeoutError:
                return "No speech detected within 5 seconds."
    except Exception as e:
        return f"Microphone initialization failed: {e}. Ensure a microphone is connected and accessible."

# ======= CHECK PORT =======
def check_port(port=8501):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

# ======= STREAMLIT INTERFACE =======
st.set_page_config(page_title="AI Cooking Assistant", layout="centered")
st.title("👩‍🍳 AI Voice Cooking Assistant")

st.markdown("""
Welcome to the Gemini-powered Cooking Assistant! 🎙  
- Speak or type your ingredients or recipe name  
- Get full OK full recipes with ingredients, time, and steps  
- Multilingual support 🌐
""")

# Warn if port is in use
if not check_port(8501):
    st.warning("Port 8501 is in use. Run with a different port: streamlit run voice_assistant.py --server.port 8502")

# ======= LANGUAGE & MODE SELECTION =======
lang_input = st.selectbox("Choose output language:", list(SUPPORTED_LANGUAGES.keys()), index=0)
lang_code = SUPPORTED_LANGUAGES[lang_input.lower()]
mode = st.radio("Input Type", ["Ingredients", "Recipe Name"], horizontal=True)

# ======= SESSION STATE FOR RECORDING =======
if 'recording' not in st.session_state:
    st.session_state.recording = False
if "manual_input_text" not in st.session_state:
    st.session_state.manual_input_text = ""

# ======= AUDIO INPUT AND TRANSCRIPTION =======
st.markdown("🎤 Mic Input (transcribes into manual text box)")
col1, col2 = st.columns(2)
with col1:
    if st.button("Start Recording", disabled=st.session_state.recording):
        st.session_state.recording = True
        with st.spinner("Recording..."):
            time.sleep(1)  # Ensure microphone initializes
            result = transcribe_speech()
            if result and not result.startswith(("Could not", "Speech recognition", "No speech", "Microphone")):
                st.session_state.manual_input_text = result
                st.success(f"✅ Transcribed: {result}")
            else:
                st.error(result)
            st.session_state.recording = False

with col2:
    if st.button("Stop Recording", disabled=not st.session_state.recording):
        st.session_state.recording = False
        st.info("Recording stopped.")

# ======= MANUAL INPUT BOX =======
manual_input = st.text_area(
    "📝 Type or speak ingredients/recipe name",
    value=st.session_state.manual_input_text,
    key="manual_input_box"
)

# ======= PROCESS USER INPUT =======
user_input = manual_input.strip()

if user_input:
    if mode == "Ingredients":
        suggestions = suggest_recipe_names(user_input)
        if suggestions:
            selected = st.selectbox("Choose a suggested recipe:", suggestions)
            if selected and st.button("🔍 Show Recipe"):
                recipe = fetch_recipe_details(selected)
                if recipe:  # Check if recipe is not empty
                    # st.write(f"DEBUG: Recipe content: {recipe}")  # Uncomment for debugging
                    if lang_code != "en":
                        recipe = translate_recipe(recipe, lang_input)
                    if recipe:  # Check again after translation
                        st.markdown("## 🍽 Recipe")
                        st.markdown(recipe)
                        speak(recipe, lang=lang_code)
                    else:
                        st.error("No translated recipe available to display or speak.")
                else:
                    st.error("No recipe details available to display or speak.")
    else:
        if st.button("🔍 Show Recipe"):
            recipe = fetch_recipe_details(user_input)
            if recipe:  # Check if recipe is not empty
                # st.write(f"DEBUG: Recipe content: {recipe}")  # Uncomment for debugging
                if lang_code != "en":
                    recipe = translate_recipe(recipe, lang_input)
                if recipe:  # Check again after translation
                    st.markdown("## 🍽 Recipe")
                    st.markdown(recipe)
                    speak(recipe, lang=lang_code)
                else:
                    st.error("No translated recipe available to display or speak.")
            else:
                st.error("No recipe details available to display or speak.")

# ======= TROUBLESHOOTING =======
st.markdown("---")
st.markdown("""
### Troubleshooting:
- Microphone issues: Ensure a microphone is connected, enabled in system settings, and permissions are granted. Install pyaudio: pip install pyaudio.
- No transcription: Speak clearly and ensure a stable internet connection (Google Speech Recognition requires internet).
- Text-to-speech issues: Ensure the selected language is supported (English, Hindi, Tamil, French, Spanish, German, Japanese, Chinese, Arabic). Check internet connection for gTTS.
- API issues: Verify your Gemini API key and ensure access to the 'gemini-1.5-flash' model.
- Port conflict: If the app fails to load, try a different port: streamlit run voice_assistant.py --server.port 8502.
- Dependencies: Install requirements: pip install streamlit speechrecognition pyaudio google-generativeai gtts.
""")
st.caption("Made with ❤ using Gemini + Streamlit + SpeechRecognition")
