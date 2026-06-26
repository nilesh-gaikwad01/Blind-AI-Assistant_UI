import cv2
import pyttsx3
import time
import threading
import pytesseract
from flask import Flask, render_template, Response, jsonify
from ultralytics import YOLO
from whatsapp import send_sos

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

app = Flask(__name__)

print("Smart Blind Assistant Starting...")

# ---------------- SPEECH ----------------
def speak(text):

    def run():
        engine = pyttsx3.init()
        engine.setProperty('rate',170)
        engine.say(text)
        engine.runAndWait()
        engine.stop()

    threading.Thread(target=run).start()


# ---------------- MODE ----------------
mode = "navigation"

# ---------------- MODELS ----------------
navigation_model = YOLO("yolov8n.pt")
currency_model = YOLO("project-1-at-2026-01-25-01-36-c7f2efad/runs/detect/train3/weights/best.pt")

# ---------------- CAMERA ----------------
camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

last_speak_time = 0
last_detection_time = 0
last_ocr_time = 0

ocr_interval = 3
detect_interval = 2


# ---------------- OCR ----------------
def run_ocr(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray).strip()

    if text != "":
        speak(text[:200])
    else:
        speak("show paragraph to camera")


# ---------------- FRAME LOOP ----------------
def generate_frames():

    global mode, last_speak_time, last_detection_time, last_ocr_time

    while True:

        success, frame = camera.read()

        if not success:
            continue

        # ✅ FIX: Removed mirror effect
        # frame = cv2.flip(frame,1)

        message = ""
        current_time = time.time()

        # -------- NAVIGATION --------
        if mode == "navigation":

            if current_time - last_detection_time > detect_interval:

                results = navigation_model(frame)

                for r in results:
                    for box in r.boxes:

                        cls = int(box.cls[0])
                        label = navigation_model.names[cls]

                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        width = x2 - x1

                        if width > 0:

                            distance = round(500 / width,1)

                            if distance < 1:
                                message = f"{label} very close stop"
                            elif distance < 2:
                                message = f"{label} {distance} meter ahead move carefully"
                            else:
                                message = f"{label} {distance} meter ahead"

                if message == "":
                    message = "path clear move forward"

                last_detection_time = current_time

        # -------- CURRENCY --------
        elif mode == "currency":

            if current_time - last_detection_time > detect_interval:

                results = currency_model(frame)

                detected_note = None

                for r in results:
                    for box in r.boxes:
                        cls = int(box.cls[0])
                        detected_note = currency_model.names[cls]

                if detected_note:
                    message = detected_note.replace("_"," ")
                else:
                    message = "show currency to camera"

                last_detection_time = current_time

        # -------- TEXT READER --------
        elif mode == "read":

            if current_time - last_ocr_time > ocr_interval:
                threading.Thread(target=run_ocr, args=(frame.copy(),)).start()
                last_ocr_time = current_time

        # -------- SPEAK --------
        if current_time - last_speak_time > 3 and message != "":
            speak(message)
            last_speak_time = current_time

        # -------- STREAM --------
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# ---------------- ROUTES ----------------
@app.route('/')
def index():
    return render_template("index.html")


@app.route('/video')
def video():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# -------- MODE SWITCH --------
@app.route('/set_mode/<new_mode>', methods=['POST'])
def set_mode(new_mode):

    global mode
    mode = new_mode

    if mode == "navigation":
        speak("navigation mode activated")

    elif mode == "currency":
        speak("currency detection started")

    elif mode == "read":
        speak("text reading started show paragraph")

    return jsonify({"status":"ok"})


# -------- WHATSAPP ROUTE --------
@app.route('/whatsapp', methods=['POST'])
def whatsapp_route():

    print("WHATSAPP ROUTE TRIGGERED")

    speak("Sending WhatsApp message")

    def run_whatsapp():
        try:
            send_sos()
            speak("WhatsApp message sent successfully")
        except:
            speak("Failed to send WhatsApp message")

    threading.Thread(target=run_whatsapp).start()

    return jsonify({"status": "done"})



# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)