import speech_recognition as sr
import requests
import time

print("Voice command system started")

recognizer = sr.Recognizer()
recognizer.energy_threshold = 300
recognizer.dynamic_energy_threshold = True

mic = sr.Microphone()

def send_command(command):

    try:

        if "navigation" in command:
            requests.post("http://127.0.0.1:5000/set_mode/navigation")
            print("Navigation mode activated")

        elif "currency" in command:
            requests.post("http://127.0.0.1:5000/set_mode/currency")
            print("Currency detection activated")

        elif "sos" in command:
            requests.post("http://127.0.0.1:5000/sos")
            print("SOS triggered")

        elif "stop navigation" in command:
            requests.post("http://127.0.0.1:5000/set_mode/stop")
            print("Navigation stopped")

        else:
            print("Command not recognized")

    except Exception as e:
        print("Server connection error:", e)


while True:

    try:

        with mic as source:

            print("\nListening for command...")
            recognizer.adjust_for_ambient_noise(source, duration=1)

            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)

        print("Processing voice...")

        command = recognizer.recognize_google(audio).lower()

        print("You said:", command)

        send_command(command)

        time.sleep(1)

    except sr.UnknownValueError:
        print("Voice not clear")

    except sr.WaitTimeoutError:
        print("No speech detected")

    except sr.RequestError:
        print("Internet connection problem")

    except Exception as e:
        print("Error:", e)