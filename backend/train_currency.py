from ultralytics import YOLO

model = YOLO("yolov8n.pt")

results = model.train(
    data="indian-currency/notes-2/data.yaml",
    epochs=80,
    imgsz=640,
    batch=16,
    patience=15,
    name="currency_v2"
)