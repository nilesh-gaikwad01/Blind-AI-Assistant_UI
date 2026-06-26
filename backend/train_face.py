import cv2
import os
import numpy as np

# dataset folder name
dataset_path = "family_faces"

faces = []
labels = []
label_map = {}

label_id = 0

for person in os.listdir(dataset_path):

    person_path = os.path.join(dataset_path, person)

    label_map[label_id] = person

    for img_name in os.listdir(person_path):

        img_path = os.path.join(person_path, img_name)

        img = cv2.imread(img_path)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        faces.append(gray)
        labels.append(label_id)

    label_id += 1


recognizer = cv2.face.LBPHFaceRecognizer_create()

recognizer.train(faces, np.array(labels))

recognizer.save("face_model.yml")

print("Training completed successfully")