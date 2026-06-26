import cv2
import pytesseract
import pyttsx3
import time

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

print("Text reader started")
print("Show paragraph to camera")

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("Camera not detected")
    exit()

last_time = 0
scan_interval = 2   # seconds between scans

def speak(text):
    engine = pyttsx3.init()
    engine.setProperty('rate',170)
    engine.say(text)
    engine.runAndWait()
    engine.stop()

while True:

    ret, frame = cap.read()
    if not ret:
        continue

    frame = cv2.resize(frame, None, fx=0.7, fy=0.7)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    cv2.imshow("Text Reader", frame)

    if time.time() - last_time > scan_interval:

        text = pytesseract.image_to_string(gray).strip()

        if text != "":
            print("Detected text:")
            print(text)

            speak(text)

        last_time = time.time()

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()