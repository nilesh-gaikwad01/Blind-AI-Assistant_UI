import cv2
import smtplib
import pyttsx3
import time
import threading
from flask import Flask, render_template, Response, jsonify
from ultralytics import YOLO
from currancy_detection import detect_currency

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

# ---------------- YOLO MODEL ----------------
model = YOLO("yolov8n.pt")

# ---------------- CAMERA ----------------
camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not camera.isOpened():
    camera = cv2.VideoCapture(1, cv2.CAP_DSHOW)

# ---------------- EMAIL CONFIG ----------------
sender_email = "ankitadongare045@gmail.com"
app_password = "pblhbcjgfcwokkxl"
receiver_email = "ankitadongare045@gmail.com"

last_speak_time = 0


# ---------------- DISTANCE ----------------
def estimate_distance(width):

    if width == 0:
        return 0

    return round(4500 / width, 2)


# ---------------- NAVIGATION ----------------
def navigation(center, frame_width):

    if center < frame_width * 0.3:
        return "move right"

    elif center > frame_width * 0.7:
        return "move left"

    else:
        return "stop"


# ---------------- FRAME LOOP ----------------
def generate_frames():

    global last_speak_time, mode

    while True:

        success, frame = camera.read()

        if not success:
            continue

        frame = cv2.flip(frame,1)

        message = ""
        h, w, _ = frame.shape


        # ---------------- NAVIGATION MODE ----------------
        if mode == "navigation":

            results = model(frame)

            closest_label = None
            closest_distance = 999
            closest_direction = ""

            for r in results:
                for box in r.boxes:

                    conf = float(box.conf[0])
                    if conf < 0.5:
                        continue

                    cls = int(box.cls[0])
                    label = model.names[cls]

                    x1,y1,x2,y2 = map(int,box.xyxy[0])

                    width = x2-x1
                    distance = estimate_distance(width)

                    center = (x1+x2)/2
                    direction = navigation(center,w)

                    cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)

                    cv2.putText(frame,
                                f"{label} {distance}m",
                                (x1,y1-10),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.6,
                                (0,255,0),
                                2)

                    if distance < closest_distance:

                        closest_distance = distance
                        closest_label = label
                        closest_direction = direction


            if closest_label:

                message = f"{closest_label} {closest_distance} meters ahead {closest_direction}"

            else:

                message = "path clear move forward"


        # ---------------- CURRENCY MODE ----------------
        elif mode == "currency":

            total_amount, frame = detect_currency(frame)

            if total_amount > 0:

                message = f"{total_amount} rupees detected"

            else:

                message = "show currency to camera"


        # ---------------- SPEAK ----------------
        current_time = time.time()

        if current_time - last_speak_time > 1:

            speak(message)

            last_speak_time = current_time


        # ---------------- STREAM ----------------
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


# ---------------- MODE CHANGE ----------------
@app.route('/set_mode/<new_mode>', methods=['POST'])
def set_mode(new_mode):

    global mode
    mode = new_mode

    print("Mode changed to:", mode)

    return jsonify({"status":"ok"})


# ---------------- SOS ROUTE ----------------
@app.route('/sos', methods=['POST'])
def sos():

    global mode
    mode = "sos"

    # Inform the user first
    speak("SOS message will be sent")

    message = """Subject: SOS Alert

Emergency! Blind assistant user needs help immediately.
"""

    try:

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()

        server.login(sender_email, app_password)

        server.sendmail(sender_email, receiver_email, message)

        server.quit()

        # Confirmation voice
        speak("SOS message sent successfully")

        mode = "navigation"

        return jsonify({"status":"SOS Sent"})

    except Exception as e:

        print("SOS Error:", e)

        speak("Failed to send SOS message")

        mode = "navigation"

        return jsonify({"status":"Error"})


# ---------------- RUN ----------------
if __name__ == "__main__":

    app.run(debug=False)