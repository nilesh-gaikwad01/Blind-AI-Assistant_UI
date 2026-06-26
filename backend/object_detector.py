import streamlit as st
import threading
import cv2
import pyttsx3
import speech_recognition as sr
import time
import queue
from ultralytics import YOLO

# ================= VOICE SYSTEM =================
voice_queue = queue.Queue()
voice_lock = threading.Lock()

def voice_worker():
    engine = pyttsx3.init('sapi5')
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 1)

    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[0].id)

    while True:
        text = voice_queue.get()
        if text is None:
            break

        try:
            with voice_lock:
                print("🔊:", text)
                engine.stop()
                engine.say(text)
                engine.runAndWait()
        except Exception as e:
            print("Voice error:", e)

threading.Thread(target=voice_worker, daemon=True).start()

def speak(text):
    voice_queue.put(text)

# ================= VOICE INPUT =================
def listen():
    r = sr.Recognizer()
    r.energy_threshold = 300

    # ✅ FIXED MIC INDEX
    with sr.Microphone(device_index=16) as source:
        print("🎤 Listening...")
        speak("Speak now")

        r.adjust_for_ambient_noise(source, duration=1)

        try:
            audio = r.listen(source, timeout=10, phrase_time_limit=5)
        except sr.WaitTimeoutError:
            print("❌ No voice detected")
            speak("No voice detected")
            return ""

    try:
        command = r.recognize_google(audio)
        print("✅ You said:", command)
        speak(f"You said {command}")
        return command.lower()

    except sr.UnknownValueError:
        print("❌ Could not understand")
        speak("Could not understand")
        return ""

    except sr.RequestError:
        print("❌ Internet error")
        speak("Internet error")
        return ""

# ================= LOAD MODEL =================
model = YOLO("yolov8n.pt")

# ================= GLOBAL =================
running = False
listening_active = False

# ================= OBJECT DETECTION =================
def run_object_detection():
    global running

    cap = cv2.VideoCapture(0)
    speak("Object detection started")

    prev_object = ""

    while running:
        ret, frame = cap.read()
        if not ret:
            speak("Camera error")
            break

        results = model(frame)
        detected_objects = []

        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                label = model.names[cls]
                detected_objects.append(label)

        if detected_objects:
            obj = detected_objects[0]

            if obj != prev_object:
                speak(f"{obj} detected")
                prev_object = obj

        time.sleep(2)

    cap.release()
    speak("Object detection stopped")

# ================= COMMAND HANDLER =================
def start_listening():
    global running, listening_active

    if listening_active:
        return

    listening_active = True

    speak("Say your command")

    command = listen()

    if "object detection" in command:
        running = True
        speak("Starting object detection")
        threading.Thread(target=run_object_detection, daemon=True).start()

    elif "stop" in command:
        running = False
        speak("Stopping system")

    else:
        speak("Command not recognized")

    listening_active = False

# ================= UI =================
st.title("🧭 Voice Assist System")

if st.button("Start System"):
    threading.Thread(target=start_listening, daemon=True).start()

if st.button("Stop System"):
    if running:
        running = False
        speak("Stopping system")