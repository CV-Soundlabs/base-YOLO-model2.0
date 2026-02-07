from ultralytics import YOLO

def main():
    model = YOLO("yolov8n.pt")
    model.predict(source=0, show=True)

if __name__ == "__main__":
    main()
