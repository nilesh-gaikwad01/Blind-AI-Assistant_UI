import cv2
import torch
import pyttsx3
import numpy as np
from ultralytics import YOLO
import subprocess
import sys

# -------------------------------
# Fix dependency (timm)
# -------------------------------
try:
    import timm
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "timm"])
    import timm

# -------------------------------
# Load Models
# -------------------------------
yolo_model = YOLO("yolov8n.pt")

midas = torch.hub.load("intel-isl/MiDaS", "MiDaS_small", trust_repo=True)
midas.eval()

transform = torch.hub.load("intel-isl/MiDaS", "transforms", trust_repo=True).small_transform

# Voice
engine = pyttsx3.init()
engine.setProperty('rate', 150)

# -------------------------------
# Functions
# -------------------------------
def speak(text):
    engine.say(text)
    engine.runAndWait()

def get_depth_map(frame):
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    input_batch = transform(img)

    with torch.no_grad():
        prediction = midas(input_batch)
        prediction = torch.nn.functional.interpolate(
            prediction.unsqueeze(1),
            size=img.shape[:2],
            mode="bicubic",
            align_corners=False
        ).squeeze()

    return prediction.cpu().numpy()

def estimate_distance(depth_map, bbox):
    x1, y1, x2, y2 = bbox
    cx, cy = int((x1+x2)/2), int((y1+y2)/2)

    depth = depth_map[cy, cx]
    if depth <= 0:
        return 10

    return round(1 / depth, 2)

# 🔥 NEW SMART NAVIGATION
def decide_direction(x_center, frame_width, distance):
    center_margin = frame_width * 0.2

    if distance < 1.5:
        # Obstacle in center
        if abs(x_center - frame_width/2) < center_margin:
            return "Stop"
        # Obstacle on left
        elif x_center < frame_width/2:
            return "Turn Right"
        # Obstacle on right
        else:
            return "Turn Left"
    
    return "Move Forward"

# -------------------------------
# Main
# -------------------------------
cap = cv2.VideoCapture(0)

last_message = ""
frame_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("Camera not working")
        break

    h, w = frame.shape[:2]

    # Optimize depth (every 5 frames)
    if frame_count % 5 == 0:
        depth_map = get_depth_map(frame)

    results = yolo_model(frame)[0]

    closest_obj = None
    min_distance = float('inf')

    # 🔥 Find closest object
    for box in results.boxes:
        conf = float(box.conf[0])
        if conf < 0.5:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        distance = estimate_distance(depth_map, (x1, y1, x2, y2))

        if distance < min_distance:
            min_distance = distance
            closest_obj = (box, distance)

    if closest_obj:
        box, distance = closest_obj
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cls = int(box.cls[0])
        label = yolo_model.names[cls]

        x_center = (x1 + x2) / 2

        direction = decide_direction(x_center, w, distance)

        # 🔥 Clean voice messages
        if direction == "Stop":
            message = "Obstacle ahead, Stop"
        elif direction == "Turn Left":
            message = f"{label} detected, Turn Left"
        elif direction == "Turn Right":
            message = f"{label} detected, Turn Right"
        else:
            message = "Path clear, Move Forward"

        if message != last_message:
            print(message)
            speak(message)
            last_message = message

        # Draw
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)
        cv2.putText(frame, message, (x1, y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

    else:
        message = "Path clear, Move Forward"
        if message != last_message:
            print(message)
            speak(message)
            last_message = message

    cv2.imshow("Smart Navigation", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

    frame_count += 1

cap.release()
cv2.destroyAllWindows()