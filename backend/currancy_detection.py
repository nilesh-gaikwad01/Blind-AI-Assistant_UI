import cv2
from ultralytics import YOLO

MODEL_PATH = "best.pt"

model = YOLO(MODEL_PATH)

NOTE_VALUES = {
    "10":10,
    "20":20,
    "50":50,
    "100":100,
    "200":200,
    "500":500
}

def detect_currency(frame):

    results = model(frame, conf=0.5)

    total_amount = 0

    for r in results:

        boxes = r.boxes
        names = model.names

        for box in boxes:

            cls_id = int(box.cls[0])
            label = names[cls_id]

            if label in NOTE_VALUES:

                total_amount += NOTE_VALUES[label]

                x1,y1,x2,y2 = map(int, box.xyxy[0])

                cv2.rectangle(frame,(x1,y1),(x2,y2),(0,0,255),2)

                cv2.putText(frame,
                            label,
                            (x1,y1-10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (0,0,255),
                            2)

    return total_amount, frame