import cv2
import torch
import pyttsx3
import time
import threading

# ================= VOICE =================
last_speak = ""
last_time = 0

def speak(text):
    def run():
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 160)
            engine.say(text)
            engine.runAndWait()
        except:
            pass
    threading.Thread(target=run).start()

# ================= LOAD MODEL =================
print("Loading YOLO...")
model = torch.hub.load('ultralytics/yolov5', 'yolov5n', pretrained=True)

# ================= MAIN FUNCTION =================
def process_frame(frame):
    global last_speak, last_time

    message = None
    h, w, _ = frame.shape

    results = model(frame, size=160)
    detections = results.pandas().xyxy[0]

    # ================= OBJECT LOOP =================
    for _, row in detections.iterrows():
        label = row['name']
        x1, y1, x2, y2 = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])

        # DRAW
        cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)
        cv2.putText(frame, label, (x1,y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

        # ================= DISTANCE =================
        width = x2 - x1
        if width > 220:
            distance = "very close"
        elif width > 150:
            distance = "2 meter"
        elif width > 80:
            distance = "4 meter"
        else:
            distance = "far"

        # ================= POSITION =================
        center_x = (x1 + x2) // 2
        if center_x < w // 3:
            position = "left"
        elif center_x > 2*w // 3:
            position = "right"
        else:
            position = "center"

        # ================= PRIORITY SYSTEM =================

        # 💰 CURRENCY (SIMULATED)
        if label in ["book", "cell phone"]:
            message = f"Currency detected {distance}"

        # 👤 PERSON
        elif label == "person":
            message = f"Person {position} {distance}"

        # 🚧 OBSTACLE
        elif label in ["chair", "table", "car"]:
            message = f"{label} {position} {distance}"

    # ================= NAVIGATION =================
    if message is None:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        left = gray[:, :w//2].mean()
        right = gray[:, w//2:].mean()

        if left < right:
            message = "Move left"
        else:
            message = "Move right"

    # ================= VOICE CONTROL =================
    if message and message != last_speak and time.time() - last_time > 2:
        speak(message)
        last_speak = message
        last_time = time.time()

    return frame