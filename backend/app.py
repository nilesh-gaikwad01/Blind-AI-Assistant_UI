import cv2
import pyttsx3
import time
import threading
import pytesseract
from flask import Flask, render_template, jsonify, request
from ultralytics import YOLO
from whatsapp import send_sos
import base64
import numpy as np

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

app = Flask(__name__)
print("Smart Blind Assistant Starting...")


# =======================================================
# SPEECH — laptop standby
# =======================================================
def speak(text):
    def run():
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 170)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            print(f"Speech error: {e}")
    threading.Thread(target=run, daemon=True).start()


# =======================================================
# STATE
# =======================================================
mode         = "navigation"
latest_frame = None
last_result  = ""


# =======================================================
# MODELS
# =======================================================
print("Loading models...")
navigation_model = YOLO("yolov8n.pt")
currency_model   = YOLO("best.pt")
print("Models loaded successfully.")


# =======================================================
# TIMING
# =======================================================
last_speak_time     = 0
last_detection_time = 0
last_ocr_time       = 0
detect_interval     = 2
ocr_interval        = 3


# =======================================================
# OCR
# =======================================================
def run_ocr(frame):
    global last_result
    try:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray).strip()
        result = text[:200] if text else "no text found, show text to camera"
        last_result = result
        speak(result)
    except Exception as e:
        print(f"OCR error: {e}")
        last_result = "text reading error"


# =======================================================
# BACKGROUND LOOP
# =======================================================
def background_loop():
    global mode, last_speak_time, last_detection_time
    global last_ocr_time, latest_frame, last_result

    while True:
        if latest_frame is None:
            time.sleep(0.05)
            continue

        frame        = latest_frame.copy()
        current_time = time.time()
        message      = ""

        if mode == "navigation":
            if current_time - last_detection_time > detect_interval:
                try:
                    results    = navigation_model(frame, verbose=False)
                    detections = []
                    for r in results:
                        for box in r.boxes:
                            cls      = int(box.cls[0])
                            label    = navigation_model.names[cls]
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            width    = x2 - x1
                            if width > 0:
                                distance = round(500 / width, 1)
                                if distance < 1:
                                    detections.append(f"{label} very close, stop")
                                else:
                                    detections.append(f"{label} {distance} meter ahead")
                    message = detections[0] if detections else "path clear, move forward"
                except Exception as e:
                    print(f"Navigation error: {e}")
                    message = "detection error"
                last_detection_time = current_time

        elif mode == "currency":
            if current_time - last_detection_time > detect_interval:
                try:
                    results       = currency_model(frame, verbose=False)
                    detected_note = None
                    for r in results:
                        for box in r.boxes:
                            cls           = int(box.cls[0])
                            detected_note = currency_model.names[cls]
                    message = (
                        detected_note.replace("_", " ")
                        if detected_note
                        else "no currency detected"
                    )
                except Exception as e:
                    print(f"Currency error: {e}")
                    message = "detection error"
                last_detection_time = current_time

        elif mode == "read":
            if current_time - last_ocr_time > ocr_interval:
                threading.Thread(
                    target=run_ocr,
                    args=(frame.copy(),),
                    daemon=True,
                ).start()
                last_ocr_time = current_time
            message = last_result

        if message:
            last_result = message
            if current_time - last_speak_time > 3:
                speak(message)
                last_speak_time = current_time


# =======================================================
# ROUTES
# =======================================================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload_frame', methods=['POST'])
def upload_frame():
    global latest_frame
    try:
        data    = request.json['image']
        encoded = data.split(',')[1]
        nparr   = np.frombuffer(base64.b64decode(encoded), np.uint8)
        frame   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"message": "", "status": "error"})

        latest_frame = frame
        return jsonify({"message": last_result, "status": "ok"})

    except Exception as e:
        print(f"Frame error: {e}")
        return jsonify({"message": "", "status": "error"})


@app.route('/set_mode/<new_mode>', methods=['POST'])
def set_mode(new_mode):
    global mode, last_result
    mode        = new_mode
    last_result = ""
    print(f"MODE: {mode}")

    labels = {
        "navigation": "navigation mode activated",
        "currency":   "currency detection started",
        "read":       "text reading started",
        "family":     "calling family member",
    }
    msg = labels.get(new_mode, f"{new_mode} mode activated")
    speak(msg)
    return jsonify({"status": "ok", "message": msg})


@app.route('/whatsapp', methods=['POST'])
def whatsapp_route():
    """
    Receives GPS from Flutter, fires send_sos() which runs automation
    in a background thread and returns IMMEDIATELY — no timeout.
    """
    try:
        data = request.json or {}
        lat  = data.get('lat', None)
        lng  = data.get('lng', None)
    except Exception:
        lat, lng = None, None

    speak("Sending emergency WhatsApp message")

    # Non-blocking — automation runs in background thread inside send_sos()
    send_sos(lat=lat, lng=lng)

    # Return immediately so Flutter gets success, not a timeout
    return jsonify({"status": "ok", "message": "Emergency alert sending"})


# =======================================================
# RUN
# =======================================================
if __name__ == "__main__":
    threading.Thread(target=background_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False)