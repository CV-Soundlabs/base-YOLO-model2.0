# base-YOLO-model

Baseline YOLOv8 webcam detection setup for CV Soundlabs.

This repository provides a minimal Python environment to run YOLO on a webcam.
It is intended to serve as the base computer-vision layer before integrating
MediaPipe for hand/gesture tracking.

---

## Requirements

- Python 3.11+
- Git

---

## Setup

Clone the repository:

git clone https://github.com/CV-Soundlabs/base-YOLO-model.git
cd base-YOLO-model

Create virtual environment:

python -m venv venv

Activate:

Windows:
venv\Scripts\activate

Mac/Linux:
source venv/bin/activate

Install dependencies:

pip install -r requirements.txt

---

## Run

python run_yolo.py

Your webcam should open with YOLO detections displayed.

---

## Notes

- Model weights are downloaded automatically by Ultralytics.
- The MediaPipe team will integrate hand-tracking inside run_yolo.py.
- The venv/ and runs/ folders are git-ignored.
