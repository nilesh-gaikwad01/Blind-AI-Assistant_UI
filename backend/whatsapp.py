import webbrowser
import pyautogui
import time
import pyttsx3
import urllib.parse
import geocoder
import threading

PHONE_NUMBER = "919373980570"


def speak(text):
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 170)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception as e:
        print(f"Speech error: {e}")


def get_location_from_ip():
    try:
        g = geocoder.ip('me')
        if g.latlng:
            lat, lon = g.latlng
            return f"https://maps.google.com/?q={lat},{lon}"
        return "Location not available"
    except Exception:
        return "Location not available"


def get_location(lat=None, lng=None):
    if lat is not None and lng is not None:
        return f"https://maps.google.com/?q={lat},{lng}"
    print("No GPS from phone — using IP location as fallback")
    return get_location_from_ip()


def _run_whatsapp_automation(lat=None, lng=None):
    """
    Runs the actual WhatsApp Web automation.
    Called in a background thread so the Flask route returns immediately.
    """
    try:
        speak("Sending emergency message")
        location = get_location(lat=lat, lng=lng)

        message = (
            f"SOS ALERT! Blind assistant user needs help immediately. "
            f"Live Location: {location}"
        )

        encoded_message = urllib.parse.quote(message)
        url = f"https://web.whatsapp.com/send?phone={PHONE_NUMBER}&text={encoded_message}"

        webbrowser.open(url)

        # Wait for WhatsApp Web to fully load
        time.sleep(20)

        # Click the message input area and press Enter to send
        screen_width, screen_height = pyautogui.size()
        pyautogui.click(screen_width / 2, screen_height * 0.9)
        time.sleep(2)
        pyautogui.press("enter")

        speak("SOS message sent successfully")
        print("SOS WhatsApp message sent.")

    except Exception as e:
        print(f"WhatsApp automation error: {e}")
        speak("Failed to send SOS message")


def send_sos(lat=None, lng=None):
    """
    Starts WhatsApp automation in a background thread and returns immediately.
    This prevents Flask from timing out while waiting for the 20-second automation.
    """
    thread = threading.Thread(
        target=_run_whatsapp_automation,
        args=(lat, lng),
        daemon=True
    )
    thread.start()
    print(f"SOS triggered — automation running in background (lat={lat}, lng={lng})")