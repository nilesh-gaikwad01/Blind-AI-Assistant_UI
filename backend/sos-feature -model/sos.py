import pyttsx3
import time

engine = pyttsx3.init()
engine.setProperty('rate', 150)

def speak(text):
    engine.say(text)
    engine.runAndWait()

def get_location():
    # 👉 Demo location (prototype)
    return "Latitude: 18.5204, Longitude: 73.8567 (Pune)"

def send_alert():
    print("[SOS] Sending alert message...")
    time.sleep(1)
    print("[SOS] Message sent successfully!")

def send_location():
    location = get_location()
    print(f"[SOS] Sending location: {location}")
    time.sleep(1)
    print("[SOS] Location shared!")

def start_sos():
    print("\n🚨 [INFO] SOS Activated!")

    # 👉 Voice alert
    speak("Emergency SOS activated")

    time.sleep(1)

    # 👉 Message send
    send_alert()

    time.sleep(1)

    # 👉 Location send
    send_location()

    time.sleep(1)

    # 👉 Final voice
    speak("Your location has been shared. Help is on the way")

    print("✅ [INFO] SOS Process Completed\n")