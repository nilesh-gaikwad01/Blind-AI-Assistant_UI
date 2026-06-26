from roboflow import Roboflow

rf = Roboflow(api_key="pNfxd9d4jr7Uk9uINAxs")

project = rf.workspace("omkar-patkar-fes59").project("indian-currency-notes")
dataset = project.version(2).download("yolov8")

print("Dataset downloaded to:", dataset.location)