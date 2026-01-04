from vosk import Model, KaldiRecognizer
import pyaudio
import pyttsx3
import json
import subprocess
import webbrowser
import datetime
import keyboard
import requests

# ---------------- OLLAMA CONFIG ----------------

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "tinyllama"

# ---------------- INIT ----------------

model = Model("model-hi")
rec = KaldiRecognizer(model, 16000)
rec.SetWords(True)

engine = pyttsx3.init()
engine.setProperty("rate", 170)

def speak(text):
    print("Aayu:", text)
    engine.say(text)
    engine.runAndWait()

audio = pyaudio.PyAudio()

def open_stream():
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=8000
    )
    stream.start_stream()
    return stream

def close_stream(stream):
    stream.stop_stream()
    stream.close()


def normalize_text(text):
    replacements = {
        "ओपेन": "open",
        "ओपन": "open",
        "नोट पैड": "notepad",
        "नोटपैड": "notepad",
        "नोट पैड": "notepad",
        "नोटपैड": "notepad",
        "कैलकुलेटर": "calculator",
        "कैल्कुलेटर": "calculator",
        "यूट्यूब": "youtube",
        "गूगल": "google",
        "व्हाट": "what",
        "इस": "is",
        "टाइम": "time",
        "समय": "time",
        "अभी": "now",
        "क्या": "what",
        "आज": "today",
        "तारीख": "date",
        "डेट": "date",

    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    return text

# ---------------- AI BRAIN ----------------

def ask_brain(user_text):
    prompt = f"""
You are a STRICT intent classifier for a WINDOWS desktop assistant named Aayu.

Rules:
- Intent MUST be one of: open_app, open_website, get_time, get_date, search, none
- Target MUST be one of: notepad, calculator, youtube, google, ""
- No mobile apps, no placeholders, no explanations
- If unsure, intent = none

Examples:
"नोटपैड खोलो" → {{ "intent": "open_app", "target": "notepad", "confidence": 0.9 }}
"ओपन यूट्यूब" → {{ "intent": "open_website", "target": "youtube", "confidence": 0.9 }}
"टाइम क्या है" → {{ "intent": "get_time", "target": "", "confidence": 0.9 }}

User: "{user_text}"
"""

    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "format": "json",
                "stream": False
            },
            timeout=30
        )

        data = r.json().get("response", {})
        return data if isinstance(data, dict) else {"intent": "none", "target": "", "confidence": 0.0}

    except Exception as e:
        print("Brain error:", e)
        return {"intent": "none", "target": "", "confidence": 0.0}

# ---------------- START ----------------

speak("Aayu ready. Press control and space to talk.")

while True:
    keyboard.wait("ctrl+space")
    speak("Listening.")

    stream = open_stream()
    rec.Reset()

    while True:
        data = stream.read(4000, exception_on_overflow=False)
        if not rec.AcceptWaveform(data):
            continue

        raw_text = json.loads(rec.Result()).get("text", "").lower().strip()
        text = normalize_text(raw_text)

        if not text:
            continue

        print("You:", raw_text)
        print("Normalized:", text)


        # -------- STOP --------
        if any(w in text for w in ["stop", "sleep", "रुक", "रुक जाओ", "बस", "बंद"]):
            speak("Okay.")
            close_stream(stream)
            break



        # ---- FAST FALLBACK FOR COMMON COMMANDS ----
        if "notepad" in text:
            speak("Opening notepad.")
            subprocess.Popen(["notepad.exe"])
            close_stream(stream)
            break

        if "calculator" in text:
            speak("Opening calculator.")
            subprocess.Popen(["calc.exe"])
            close_stream(stream)
            break

        if "youtube" in text:
            speak("Opening YouTube.")
            webbrowser.open("https://www.youtube.com")
            close_stream(stream)
            break

        # ---- FAST FALLBACK FOR TIME ----
        if "time" in text:
            now = datetime.datetime.now().strftime("%I:%M %p")
            speak(f"The time is {now}")
            close_stream(stream)
            break

        # ---- FAST FALLBACK FOR DATE ----
        if "date" in text or "today" in text:
            today = datetime.datetime.now().strftime("%A, %d %B %Y")
            speak(f"Today is {today}")
            close_stream(stream)
            break


        # -------- AI DECISION --------
        brain = ask_brain(text)
        print("Brain:", brain)

        intent = brain.get("intent")
        target = brain.get("target", "")
        confidence = brain.get("confidence", 0)

        ALLOWED_INTENTS = ["open_app", "open_website", "get_time", "get_date", "search", "none"]
        ALLOWED_TARGETS = ["notepad", "calculator", "youtube", "google", ""]

        if intent not in ALLOWED_INTENTS or target not in ALLOWED_TARGETS:
            speak("I am not sure what you meant.")
            close_stream(stream)
            break

        if confidence < 0.5:
            speak("I am not confident about that.")
            close_stream(stream)
            break

        # -------- EXECUTION --------

        if intent == "open_app":
            if target == "notepad":
                speak("Opening notepad.")
                subprocess.Popen(["notepad.exe"])
            elif target == "calculator":
                speak("Opening calculator.")
                subprocess.Popen(["calc.exe"])

        elif intent == "open_website":
            if target == "youtube":
                speak("Opening YouTube.")
                webbrowser.open("https://www.youtube.com")
            elif target == "google":
                speak("Opening Google.")
                webbrowser.open("https://www.google.com")

        elif intent == "get_time":
            now = datetime.datetime.now().strftime("%I:%M %p")
            speak(f"The time is {now}")

        elif intent == "get_date":
            today = datetime.datetime.now().strftime("%A, %d %B %Y")
            speak(f"Today is {today}")

        elif intent == "search":
            speak(f"Searching {target}")
            webbrowser.open(f"https://www.google.com/search?q={target}")

        else:
            speak("I did not understand that.")

        close_stream(stream)
        break
