import mediapipe as mp
import cv2
import numpy as np
import math

FRAME_W, FRAME_H = 1280, 720
ALPHA = 0.72
KNOB_RADIUS = 45

# EQ knob definitions
eq_knobs = [
    {"label": "HIGH", "center": (120, 200), "value": 70, "color": (0, 230, 255),
     "dragging": False, "drag_start_y": 0, "drag_start_val": 0},
    {"label": "MID",  "center": (120, 340), "value": 60, "color": (0, 255, 160),
     "dragging": False, "drag_start_y": 0, "drag_start_val": 0},
    {"label": "LOW",  "center": (120, 480), "value": 50, "color": (80, 80, 255),
     "dragging": False, "drag_start_y": 0, "drag_start_val": 0},
]

BPM_SLIDER = {
    "bpm": 130.0,
    "min_bpm": 60,
    "max_bpm": 200,
    "x1": 40, "x2": 340,
    "y": 610,
    "dragging": False,
}

#drawing functions

def draw_knob(overlay, knob):
    cx, cy = knob["center"]
    val = knob["value"]
    color = knob["color"]
    r = KNOB_RADIUS

    cv2.circle(overlay, (cx, cy), r + 6, tuple(c // 4 for c in color), 3)
    cv2.circle(overlay, (cx, cy), r, (30, 30, 30), -1)

    for ang in range(-225, 45, 3):
        rad = math.radians(ang)
        px = int(cx + (r - 8) * math.cos(rad))
        py = int(cy + (r - 8) * math.sin(rad))
        cv2.circle(overlay, (px, py), 2, (60, 60, 60), -1)

    active_end = -225 + int(270 * val / 100)
    steps = list(range(-225, active_end, 3))
    total = max(len(steps), 1)
    for i, ang in enumerate(steps):
        rad = math.radians(ang)
        px = int(cx + (r - 8) * math.cos(rad))
        py = int(cy + (r - 8) * math.sin(rad))
        brightness = 0.4 + 0.6 * i / total
        c = tuple(int(ch * brightness) for ch in color)
        cv2.circle(overlay, (px, py), 2, c, -1)

    needle_rad = math.radians(-225 + int(270 * val / 100))
    nx = int(cx + (r - 14) * math.cos(needle_rad))
    ny = int(cy + (r - 14) * math.sin(needle_rad))
    cv2.line(overlay, (cx, cy), (nx, ny), color, 2)
    cv2.circle(overlay, (cx, cy), 5, color, -1)

    val_text = str(int(val))
    (tw, th), _ = cv2.getTextSize(val_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
    cv2.putText(overlay, val_text, (cx - tw // 2, cy + th // 2 + 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1, cv2.LINE_AA)

    (lw, _), _ = cv2.getTextSize(knob["label"], cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    cv2.putText(overlay, knob["label"], (cx - lw // 2, cy + r + 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

    if knob["dragging"]:
        cv2.circle(overlay, (cx, cy), r + 2, color, 2)


def draw_bpm_slider(overlay, slider):
    x1, x2, y = slider["x1"], slider["x2"], slider["y"]
    bpm = slider["bpm"]
    color = (0, 210, 255)

    cv2.rectangle(overlay, (x1, y - 5), (x2, y + 5), (40, 40, 40), -1)
    cv2.rectangle(overlay, (x1, y - 5), (x2, y + 5), (80, 80, 80), 1)

    ratio = (bpm - slider["min_bpm"]) / (slider["max_bpm"] - slider["min_bpm"])
    fill_x = int(x1 + ratio * (x2 - x1))
    cv2.rectangle(overlay, (x1, y - 5), (fill_x, y + 5), color, -1)

    cv2.circle(overlay, (fill_x, y), 14, (20, 20, 20), -1)
    cv2.circle(overlay, (fill_x, y), 14, color, 2)
    cv2.circle(overlay, (fill_x, y), 5, color, -1)

    bpm_text = f"{bpm:.1f} BPM"
    (tw, th), _ = cv2.getTextSize(bpm_text, cv2.FONT_HERSHEY_DUPLEX, 0.8, 1)
    cv2.putText(overlay, bpm_text, (x1 + (x2 - x1) // 2 - tw // 2, y - 24),
                cv2.FONT_HERSHEY_DUPLEX, 0.8, color, 1, cv2.LINE_AA)

    cv2.putText(overlay, str(slider["min_bpm"]), (x1, y + 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1, cv2.LINE_AA)
    cv2.putText(overlay, str(slider["max_bpm"]), (x2 - 22, y + 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1, cv2.LINE_AA)


def draw_ui(frame):
    overlay = frame.copy()

    cv2.rectangle(overlay, (20, 140), (220, 550), (10, 10, 20), -1)
    cv2.rectangle(overlay, (20, 140), (220, 550), (50, 50, 80), 1)
    cv2.putText(overlay, "EQ", (100, 168), cv2.FONT_HERSHEY_DUPLEX,
                0.75, (180, 180, 180), 1, cv2.LINE_AA)

    for knob in eq_knobs:
        draw_knob(overlay, knob)

    cv2.rectangle(overlay, (20, 570), (370, 645), (10, 10, 20), -1)
    cv2.rectangle(overlay, (20, 570), (370, 645), (50, 50, 80), 1)

    draw_bpm_slider(overlay, BPM_SLIDER)

    cv2.addWeighted(overlay, ALPHA, frame, 1 - ALPHA, 0, frame)


#mouse functions

def on_mouse(event, mx, my, flags, param):
    slider = BPM_SLIDER

    if event == cv2.EVENT_LBUTTONDOWN:
        # BPM thumb
        ratio = (slider["bpm"] - slider["min_bpm"]) / (slider["max_bpm"] - slider["min_bpm"])
        thumb_x = int(slider["x1"] + ratio * (slider["x2"] - slider["x1"]))
        if abs(mx - thumb_x) <= 24 and abs(my - slider["y"]) <= 24:
            slider["dragging"] = True
            return

        # BPM track click (jump)
        if slider["x1"] <= mx <= slider["x2"] and abs(my - slider["y"]) <= 20:
            slider["dragging"] = True
            r = (mx - slider["x1"]) / (slider["x2"] - slider["x1"])
            slider["bpm"] = slider["min_bpm"] + max(0.0, min(1.0, r)) * (slider["max_bpm"] - slider["min_bpm"])
            return

        # Knobs
        for knob in eq_knobs:
            cx, cy = knob["center"]
            if math.hypot(mx - cx, my - cy) <= KNOB_RADIUS + 10:
                knob["dragging"] = True
                knob["drag_start_y"] = my
                knob["drag_start_val"] = knob["value"]
                return

    elif event == cv2.EVENT_MOUSEMOVE:
        if slider["dragging"]:
            r = (mx - slider["x1"]) / (slider["x2"] - slider["x1"])
            slider["bpm"] = slider["min_bpm"] + max(0.0, min(1.0, r)) * (slider["max_bpm"] - slider["min_bpm"])

        for knob in eq_knobs:
            if knob["dragging"]:
                dy = knob["drag_start_y"] - my
                knob["value"] = max(0.0, min(100.0, knob["drag_start_val"] + dy * 0.6))

    elif event == cv2.EVENT_LBUTTONUP:
        slider["dragging"] = False
        for knob in eq_knobs:
            knob["dragging"] = False


#main
def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Camera resolution: {actual_w}x{actual_h}")

    mp_drawing = mp.solutions.drawing_utils
    mp_hands = mp.solutions.hands
    hands_detector = mp_hands.Hands(
        max_num_hands=2,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.5,
    )

    win_name = "DJ CV Overlay"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, actual_w, actual_h)
    cv2.setMouseCallback(win_name, on_mouse)

    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to read from camera.")
            break

        frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        result = hands_detector.process(rgb)
        rgb.flags.writeable = True

        if result.multi_hand_landmarks:
            for hand_lm in result.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    frame,
                    hand_lm,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 255, 160), thickness=2, circle_radius=4),
                    mp_drawing.DrawingSpec(color=(0, 180, 100), thickness=2),
                )

        # Draw UI after hand landmarks so UI is always on top
        draw_ui(frame)

        cv2.imshow(win_name, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key in (ord('+'), ord('=')):
            BPM_SLIDER["bpm"] = min(BPM_SLIDER["max_bpm"], BPM_SLIDER["bpm"] + 1)
        elif key == ord('-'):
            BPM_SLIDER["bpm"] = max(BPM_SLIDER["min_bpm"], BPM_SLIDER["bpm"] - 1)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()