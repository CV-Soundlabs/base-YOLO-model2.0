import mediapipe as mp
import cv2
import math

FRAME_W, FRAME_H = 1280, 720
ALPHA = 0.72
KNOB_RADIUS = 20

# =========================
# LAYOUT
# =========================

# Main left deck container (moved to top-left, kept left of screen midpoint)
LEFT_PANEL = {
    "x1": 20, "y1": 20,
    "x2": 610, "y2": 490
}

TOP_PANEL = {
    "x1": 35, "y1": 35,
    "x2": 595, "y2": 270
}

BOTTOM_PANEL = {
    "x1": 35, "y1": 290,
    "x2": 595, "y2": 475
}

TRANSPORT_PANEL = {
    "x1": 50, "y1": 305,
    "x2": 140, "y2": 460
}

FX_PANEL = {
    "x1": 155, "y1": 305,
    "x2": 345, "y2": 460
}

BPM_PANEL = {
    "x1": 365, "y1": 305,
    "x2": 455, "y2": 460
}

VOLUME_PANEL = {
    "x1": 475, "y1": 305,
    "x2": 565, "y2": 460
}

JOG_PANEL = {
    "x1": 50, "y1": 50,
    "x2": 355, "y2": 250
}

EQ_PANEL = {
    "x1": 380, "y1": 50,
    "x2": 565, "y2": 250
}

WAVEFORM_TOP_PANEL = {
    "x1": 20, "y1": 520,
    "x2": FRAME_W - 20, "y2": 595
}

WAVEFORM_BOTTOM_PANEL = {
    "x1": 20, "y1": 605,
    "x2": FRAME_W - 20, "y2": 680
}

# =========================
# CONTROLS
# =========================

PLAY_BUTTON = {
    "cx": 95, "cy": 405,
    "r": 28,
    "label": "PLAY",
    "playing": False,
    "pressed": False,
    "color": (0, 220, 120),
}

CUE_BUTTON = {
    "cx": 95, "cy": 345,
    "r": 25,
    "label": "CUE",
    "pressed": False,
    "color": (0, 180, 255),
}

FX_PAD = {
    "x1": 175, "y1": 330,
    "x2": 325, "y2": 430,
    "rows": 2,
    "cols": 2,
    "active_pad": -1,
    "color": (255, 170, 40),
}

BPM_SLIDER = {
    "value": 130.0,
    "min_value": 60.0,
    "max_value": 200.0,
    "x": 410,
    "y1": 340,
    "y2": 435,
    "dragging": False,
    "color": (0, 210, 255),
    "label": "BPM"
}

VOLUME_SLIDER = {
    "value": 75.0,
    "min_value": 0.0,
    "max_value": 100.0,
    "x": 520,
    "y1": 340,
    "y2": 435,
    "dragging": False,
    "color": (180, 120, 255),
    "label": "VOL"
}

JOG_WHEEL = {
    "dragging": False,
    "angle": -40.0,
    "drag_start_x": 0,
    "drag_start_angle": 0.0,
}

eq_knobs = [
    {"label": "HIGH", "center": (472, 88), "value": 70, "color": (0, 230, 255),
     "dragging": False, "drag_start_y": 0, "drag_start_val": 0},
    {"label": "MID",  "center": (472, 150), "value": 60, "color": (0, 255, 160),
     "dragging": False, "drag_start_y": 0, "drag_start_val": 0},
    {"label": "LOW",  "center": (472, 212), "value": 50, "color": (80, 80, 255),
     "dragging": False, "drag_start_y": 0, "drag_start_val": 0},
]

# =========================
# HELPERS
# =========================

def draw_panel(overlay, x1, y1, x2, y2, fill=(10, 10, 20), border=(50, 50, 80), thickness=1):
    cv2.rectangle(overlay, (x1, y1), (x2, y2), fill, -1)
    cv2.rectangle(overlay, (x1, y1), (x2, y2), border, thickness)

def draw_knob(overlay, knob):
    cx, cy = knob["center"]
    val = knob["value"]
    color = knob["color"]
    r = KNOB_RADIUS

    cv2.circle(overlay, (cx, cy), r + 5, tuple(max(20, c // 4) for c in color), 2)
    cv2.circle(overlay, (cx, cy), r, (30, 30, 30), -1)

    for ang in range(-225, 45, 4):
        rad = math.radians(ang)
        px = int(cx + (r - 7) * math.cos(rad))
        py = int(cy + (r - 7) * math.sin(rad))
        cv2.circle(overlay, (px, py), 2, (60, 60, 60), -1)

    active_end = -225 + int(270 * val / 100)
    steps = list(range(-225, active_end, 4))
    total = max(len(steps), 1)

    for i, ang in enumerate(steps):
        rad = math.radians(ang)
        px = int(cx + (r - 7) * math.cos(rad))
        py = int(cy + (r - 7) * math.sin(rad))
        brightness = 0.4 + 0.6 * i / total
        c = tuple(int(ch * brightness) for ch in color)
        cv2.circle(overlay, (px, py), 2, c, -1)

    needle_rad = math.radians(-225 + int(270 * val / 100))
    nx = int(cx + (r - 13) * math.cos(needle_rad))
    ny = int(cy + (r - 13) * math.sin(needle_rad))
    cv2.line(overlay, (cx, cy), (nx, ny), color, 2)
    cv2.circle(overlay, (cx, cy), 4, color, -1)

    val_text = str(int(val))
    (tw, th), _ = cv2.getTextSize(val_text, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
    cv2.putText(overlay, val_text, (cx - tw // 2, cy + th // 2 + 1),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (220, 220, 220), 1, cv2.LINE_AA)

    # LABEL TO THE LEFT OF THE KNOB
    (lw, lh), _ = cv2.getTextSize(knob["label"], cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
    label_x = cx - r - 16 - lw
    label_y = cy + lh // 2
    cv2.putText(overlay, knob["label"], (label_x, label_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)

    if knob["dragging"]:
        cv2.circle(overlay, (cx, cy), r + 2, color, 2)

def draw_button(overlay, button):
    cx, cy, r = button["cx"], button["cy"], button["r"]
    color = button["color"]

    fill = (25, 25, 35)
    if button.get("playing", False):
        fill = tuple(min(255, int(c * 0.30) + 35) for c in color)
    if button["pressed"]:
        fill = tuple(min(255, int(c * 0.50) + 45) for c in color)

    cv2.circle(overlay, (cx, cy), r, fill, -1)
    cv2.circle(overlay, (cx, cy), r, color, 2)
    cv2.circle(overlay, (cx, cy), r + 5, tuple(max(20, c // 4) for c in color), 2)

    label = "PAUSE" if button.get("playing", False) and button["label"] == "PLAY" else button["label"]
    font_scale = 0.62 if label != "PAUSE" else 0.44
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, font_scale, 1)
    cv2.putText(overlay, label, (cx - tw // 2, cy + th // 2),
                cv2.FONT_HERSHEY_DUPLEX, font_scale, (230, 230, 230), 1, cv2.LINE_AA)

    caption = "PLAY/PAUSE" if button["label"] == "PLAY" else "CUE"
    (cw, _), _ = cv2.getTextSize(caption, cv2.FONT_HERSHEY_SIMPLEX, 0.30, 1)
    cv2.putText(overlay, caption, (cx - cw // 2, cy + r + 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.30, color, 1, cv2.LINE_AA)

def draw_vertical_slider(overlay, slider):
    x, y1, y2 = slider["x"], slider["y1"], slider["y2"]
    value = slider["value"]
    min_value = slider["min_value"]
    max_value = slider["max_value"]
    color = slider["color"]
    label = slider["label"]

    track_half_width = 5

    cv2.rectangle(overlay, (x - track_half_width, y1), (x + track_half_width, y2), (40, 40, 40), -1)
    cv2.rectangle(overlay, (x - track_half_width, y1), (x + track_half_width, y2), (80, 80, 80), 1)

    ratio = (value - min_value) / (max_value - min_value)
    fill_y = int(y2 - ratio * (y2 - y1))

    cv2.rectangle(overlay, (x - track_half_width, fill_y), (x + track_half_width, y2), color, -1)
    cv2.circle(overlay, (x, fill_y), 12, (20, 20, 20), -1)
    cv2.circle(overlay, (x, fill_y), 12, color, 2)
    cv2.circle(overlay, (x, fill_y), 4, color, -1)

    value_text = f"{int(value)}"
    (tw, th), _ = cv2.getTextSize(value_text, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
    cv2.putText(overlay, value_text, (x - tw // 2, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)

    (lw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
    cv2.putText(overlay, label, (x - lw // 2, y2 + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)

def draw_fx_pad(overlay, pad):
    x1, y1, x2, y2 = pad["x1"], pad["y1"], pad["x2"], pad["y2"]
    rows, cols = pad["rows"], pad["cols"]
    color = pad["color"]

    cv2.rectangle(overlay, (x1, y1), (x2, y2), (15, 15, 25), -1)
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (60, 60, 90), 1)

    cell_w = (x2 - x1) // cols
    cell_h = (y2 - y1) // rows

    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            cx1 = x1 + c * cell_w
            cy1 = y1 + r * cell_h
            cx2 = cx1 + cell_w
            cy2 = cy1 + cell_h

            fill = (30, 30, 40)
            if pad["active_pad"] == idx:
                fill = tuple(min(255, int(ch * 0.4) + 40) for ch in color)

            cv2.rectangle(overlay, (cx1 + 5, cy1 + 5), (cx2 - 5, cy2 - 5), fill, -1)
            cv2.rectangle(overlay, (cx1 + 5, cy1 + 5), (cx2 - 5, cy2 - 5), color, 2)

            label = f"FX {idx + 1}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
            tx = cx1 + cell_w // 2 - tw // 2
            ty = cy1 + cell_h // 2 + th // 2
            cv2.putText(overlay, label, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                        (220, 220, 220), 1, cv2.LINE_AA)

    cv2.putText(overlay, "FX PAD", (x1 + 48, y2 + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.46, (220, 220, 220), 1, cv2.LINE_AA)

def draw_jog_wheel(overlay, panel):
    x1, y1, x2, y2 = panel["x1"], panel["y1"], panel["x2"], panel["y2"]
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    r_outer = min((x2 - x1), (y2 - y1)) // 2 - 18
    r_mid = r_outer - 18
    r_inner = r_mid - 26

    # outer ring
    cv2.circle(overlay, (cx, cy), r_outer, (70, 70, 95), 2)
    cv2.circle(overlay, (cx, cy), r_outer - 6, (35, 35, 50), 2)

    # platter
    cv2.circle(overlay, (cx, cy), r_mid, (22, 22, 30), -1)
    cv2.circle(overlay, (cx, cy), r_mid, (90, 90, 120), 1)

    # inner disc
    cv2.circle(overlay, (cx, cy), r_inner, (35, 35, 45), -1)
    cv2.circle(overlay, (cx, cy), r_inner, (100, 100, 130), 1)

    # center cap
    cv2.circle(overlay, (cx, cy), 12, (60, 60, 70), -1)
    cv2.circle(overlay, (cx, cy), 12, (140, 140, 160), 1)

    # small ticks around platter
    for ang in range(0, 360, 18):
        rad = math.radians(ang)
        p1x = int(cx + (r_outer - 12) * math.cos(rad))
        p1y = int(cy + (r_outer - 12) * math.sin(rad))
        p2x = int(cx + (r_outer - 4) * math.cos(rad))
        p2y = int(cy + (r_outer - 4) * math.sin(rad))
        cv2.line(overlay, (p1x, p1y), (p2x, p2y), (120, 120, 145), 1)

    # rotating marker
    marker_ang = math.radians(JOG_WHEEL["angle"])
    mx = int(cx + (r_mid - 12) * math.cos(marker_ang))
    my = int(cy + (r_mid - 12) * math.sin(marker_ang))
    cv2.line(overlay, (cx, cy), (mx, my), (0, 210, 255), 2)

    # small marker dot
    cv2.circle(overlay, (mx, my), 4, (0, 210, 255), -1)

    if JOG_WHEEL["dragging"]:
        cv2.circle(overlay, (cx, cy), r_outer + 4, (0, 210, 255), 2)

def draw_waveform_placeholder(overlay, panel, title):
    x1, y1, x2, y2 = panel["x1"], panel["y1"], panel["x2"], panel["y2"]

    draw_panel(overlay, x1, y1, x2, y2, fill=(12, 12, 22))

    mid_y = (y1 + y2) // 2
    cv2.line(overlay, (x1 + 14, mid_y), (x2 - 14, mid_y), (60, 60, 80), 1)

    inner_w = (x2 - x1) - 28
    step = 8
    for i in range(0, inner_w, step):
        px = x1 + 14 + i
        h = 8 + int(12 * abs(math.sin(i * 0.035)))
        cv2.line(overlay, (px, mid_y - h), (px, mid_y + h), (0, 210, 255), 1)

    cv2.putText(overlay, title, (x1 + 18, y1 + 24),
                cv2.FONT_HERSHEY_DUPLEX, 0.55, (180, 180, 180), 1, cv2.LINE_AA)

# =========================
# UI DRAW
# =========================

def draw_ui(frame):
    overlay = frame.copy()

    # Outer left deck container
    draw_panel(overlay, LEFT_PANEL["x1"], LEFT_PANEL["y1"], LEFT_PANEL["x2"], LEFT_PANEL["y2"])

    # Top and bottom containers
    draw_panel(overlay, TOP_PANEL["x1"], TOP_PANEL["y1"], TOP_PANEL["x2"], TOP_PANEL["y2"])
    draw_panel(overlay, BOTTOM_PANEL["x1"], BOTTOM_PANEL["y1"], BOTTOM_PANEL["x2"], BOTTOM_PANEL["y2"])

    # Top section: jog + eq
    draw_panel(overlay, JOG_PANEL["x1"], JOG_PANEL["y1"], JOG_PANEL["x2"], JOG_PANEL["y2"], fill=(12, 12, 22))
    draw_jog_wheel(overlay, JOG_PANEL)
    cv2.putText(overlay, "JOG WHEEL", (155, 266), cv2.FONT_HERSHEY_SIMPLEX,
                0.52, (120, 120, 140), 1, cv2.LINE_AA)

    draw_panel(overlay, EQ_PANEL["x1"], EQ_PANEL["y1"], EQ_PANEL["x2"], EQ_PANEL["y2"], fill=(12, 12, 22))
    cv2.putText(overlay, "EQ", (455, 266), cv2.FONT_HERSHEY_DUPLEX,
                0.52, (180, 180, 180), 1, cv2.LINE_AA)

    for knob in eq_knobs:
        draw_knob(overlay, knob)

    # Bottom section: transport + fx + bpm + volume
    draw_panel(overlay, TRANSPORT_PANEL["x1"], TRANSPORT_PANEL["y1"], TRANSPORT_PANEL["x2"], TRANSPORT_PANEL["y2"], fill=(12, 12, 22))
    draw_button(overlay, CUE_BUTTON)
    draw_button(overlay, PLAY_BUTTON)

    draw_panel(overlay, FX_PANEL["x1"], FX_PANEL["y1"], FX_PANEL["x2"], FX_PANEL["y2"], fill=(12, 12, 22))
    draw_fx_pad(overlay, FX_PAD)

    draw_panel(overlay, BPM_PANEL["x1"], BPM_PANEL["y1"], BPM_PANEL["x2"], BPM_PANEL["y2"], fill=(12, 12, 22))
    draw_vertical_slider(overlay, BPM_SLIDER)

    draw_panel(overlay, VOLUME_PANEL["x1"], VOLUME_PANEL["y1"], VOLUME_PANEL["x2"], VOLUME_PANEL["y2"], fill=(12, 12, 22))
    draw_vertical_slider(overlay, VOLUME_SLIDER)

    draw_waveform_placeholder(overlay, WAVEFORM_TOP_PANEL, "TRACK A WAVEFORM")
    draw_waveform_placeholder(overlay, WAVEFORM_BOTTOM_PANEL, "TRACK B WAVEFORM")

    cv2.addWeighted(overlay, ALPHA, frame, 1 - ALPHA, 0, frame)

# =========================
# MOUSE
# =========================

def on_mouse(event, mx, my, flags, param):
    bpm = BPM_SLIDER
    vol = VOLUME_SLIDER
    fx = FX_PAD

    if event == cv2.EVENT_LBUTTONDOWN:
        if math.hypot(mx - PLAY_BUTTON["cx"], my - PLAY_BUTTON["cy"]) <= PLAY_BUTTON["r"]:
            PLAY_BUTTON["pressed"] = True
            PLAY_BUTTON["playing"] = not PLAY_BUTTON["playing"]
            print("PLAY/PAUSE:", "PLAYING" if PLAY_BUTTON["playing"] else "PAUSED")
            return

        if math.hypot(mx - CUE_BUTTON["cx"], my - CUE_BUTTON["cy"]) <= CUE_BUTTON["r"]:
            CUE_BUTTON["pressed"] = True
            print("CUE pressed")
            return

        if fx["x1"] <= mx <= fx["x2"] and fx["y1"] <= my <= fx["y2"]:
            cell_w = (fx["x2"] - fx["x1"]) // fx["cols"]
            cell_h = (fx["y2"] - fx["y1"]) // fx["rows"]
            col = (mx - fx["x1"]) // cell_w
            row = (my - fx["y1"]) // cell_h
            fx["active_pad"] = int(row * fx["cols"] + col)
            print(f"FX pad {fx['active_pad'] + 1} pressed")
            return

        bpm_ratio = (bpm["value"] - bpm["min_value"]) / (bpm["max_value"] - bpm["min_value"])
        bpm_thumb_y = int(bpm["y2"] - bpm_ratio * (bpm["y2"] - bpm["y1"]))
        if abs(mx - bpm["x"]) <= 24 and abs(my - bpm_thumb_y) <= 24:
            bpm["dragging"] = True
            return

        if abs(mx - bpm["x"]) <= 20 and bpm["y1"] <= my <= bpm["y2"]:
            bpm["dragging"] = True
            r = (bpm["y2"] - my) / (bpm["y2"] - bpm["y1"])
            bpm["value"] = bpm["min_value"] + max(0.0, min(1.0, r)) * (bpm["max_value"] - bpm["min_value"])
            return

        vol_ratio = (vol["value"] - vol["min_value"]) / (vol["max_value"] - vol["min_value"])
        vol_thumb_y = int(vol["y2"] - vol_ratio * (vol["y2"] - vol["y1"]))
        if abs(mx - vol["x"]) <= 24 and abs(my - vol_thumb_y) <= 24:
            vol["dragging"] = True
            return

        if abs(mx - vol["x"]) <= 20 and vol["y1"] <= my <= vol["y2"]:
            vol["dragging"] = True
            r = (vol["y2"] - my) / (vol["y2"] - vol["y1"])
            vol["value"] = vol["min_value"] + max(0.0, min(1.0, r)) * (vol["max_value"] - vol["min_value"])
            return

        for knob in eq_knobs:
            cx, cy = knob["center"]
            if math.hypot(mx - cx, my - cy) <= KNOB_RADIUS + 10:
                knob["dragging"] = True
                knob["drag_start_y"] = my
                knob["drag_start_val"] = knob["value"]
                return
        # Jog wheel drag start
        jog_cx = (JOG_PANEL["x1"] + JOG_PANEL["x2"]) // 2
        jog_cy = (JOG_PANEL["y1"] + JOG_PANEL["y2"]) // 2
        jog_r = min((JOG_PANEL["x2"] - JOG_PANEL["x1"]), (JOG_PANEL["y2"] - JOG_PANEL["y1"])) // 2 - 18

        if math.hypot(mx - jog_cx, my - jog_cy) <= jog_r:
            JOG_WHEEL["dragging"] = True
            JOG_WHEEL["drag_start_x"] = mx
            JOG_WHEEL["drag_start_angle"] = JOG_WHEEL["angle"]
            return

    elif event == cv2.EVENT_MOUSEMOVE:
        if bpm["dragging"]:
            r = (bpm["y2"] - my) / (bpm["y2"] - bpm["y1"])
            bpm["value"] = bpm["min_value"] + max(0.0, min(1.0, r)) * (bpm["max_value"] - bpm["min_value"])

        if vol["dragging"]:
            r = (vol["y2"] - my) / (vol["y2"] - vol["y1"])
            vol["value"] = vol["min_value"] + max(0.0, min(1.0, r)) * (vol["max_value"] - vol["min_value"])

        for knob in eq_knobs:
            if knob["dragging"]:
                dy = knob["drag_start_y"] - my
                knob["value"] = max(0.0, min(100.0, knob["drag_start_val"] + dy * 0.6))
        
        if JOG_WHEEL["dragging"]:
            dx = mx - JOG_WHEEL["drag_start_x"]
            JOG_WHEEL["angle"] = JOG_WHEEL["drag_start_angle"] + dx * 0.8
    elif event == cv2.EVENT_LBUTTONUP:
        bpm["dragging"] = False
        vol["dragging"] = False
        PLAY_BUTTON["pressed"] = False
        CUE_BUTTON["pressed"] = False
        FX_PAD["active_pad"] = -1
        JOG_WHEEL["dragging"] = False

        for knob in eq_knobs:
            knob["dragging"] = False
# =========================
# MAIN
# =========================

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

        draw_ui(frame)
        cv2.imshow(win_name, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()