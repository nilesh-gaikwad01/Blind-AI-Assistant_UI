import speech_recognition as sr
import requests

recognizer = sr.Recognizer()

print("Voice command system started")

while True:

    try:
        with sr.Microphone() as source:

            print("Listening...")

            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, phrase_time_limit=4)

        print("Processing voice...")

        command = recognizer.recognize_google(audio).lower()

        print("You said:", command)

        # -------- NAVIGATION --------
        if "navigation" in command:
            requests.post("http://127.0.0.1:5000/set_mode/navigation")

        # -------- CURRENCY --------
        elif "currency" in command:
            requests.post("http://127.0.0.1:5000/set_mode/currency")

        # -------- READ TEXT --------
        elif "read" in command:
            requests.post("http://127.0.0.1:5000/set_mode/read")

        # -------- WHATSAPP --------
        elif "whatsapp" in command or "send message" in command:
            requests.post("http://127.0.0.1:5000/whatsapp")
            print("WhatsApp message triggered")

        else:
            print("Command not recognized")

    except sr.UnknownValueError:
        print("Voice not clear")

    except Exception as e:
        print("Error:", e)