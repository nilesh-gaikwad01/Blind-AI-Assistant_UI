# Blind AI Assistant Backend

## Features

* Object Detection
* Face Recognition
* Indoor Navigation
* Currency Recognition
* OCR Text Reading
* SOS Feature

## Installation

```bash
python -m venv venv

venv\Scripts\activate

pip install -r requirements.txt
```

## Run

```bash
python app.py
```

## API

POST

```text
http://localhost:5000/detect
```

Form-data:

```text
image : image.jpg
lang  : en-US
```
