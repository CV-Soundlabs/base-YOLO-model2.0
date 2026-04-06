import mediapipe as mp
import cv2
import math
from dataclasses import dataclass
from audio_engine import create_decks

FRAME_W, FRAME_H = 1280, 720
ALPHA = 0.72
KNOB_RADIUS = 20

@dataclass
class DeckState:
    volume: float = 75.0
    eq_high: float = 50.0
    eq_mid: float = 50.0
    eq_low: float = 50.0
    jog_angle: float = 0.0
    bpm: float = 0.0

state_a = DeckState()
state_b = DeckState()

deck_a, deck_b = create_decks()  # each gets its own VLC instance (see audio_engine.py)
active_deck = deck_a

DECK_A_COLOR = (0, 210, 255)
DECK_B_COLOR = (220, 0, 255)

def active_color() -> tuple:
    return DECK_A_COLOR if active_deck is deck_a else DECK_B_COLOR

def active_label() -> str:
    return "A" if active_deck is deck_a else "B"

def _active_state() -> DeckState:
    return state_a if active_deck is deck_a else state_b

# =========================
# LAYOUT — LEFT DECK (A)
# =========================
LEFT_PANEL = {"x1": 20,  "y1": 20, "x2": 610, "y2": 490}
TOP_PANEL  = {"x1": 35,  "y1": 35, "x2": 595, "y2": 270}
BOTTOM_PANEL = {"x1": 35, "y1": 290, "x2": 595, "y2": 475}

TRANSPORT_PANEL = {"x1": 50,  "y1": 305, "x2": 140, "y2": 460}
FX_PANEL        = {"x1": 155, "y1": 305, "x2": 345, "y2": 460}
BPM_PANEL       = {"x1": 365, "y1": 305, "x2": 455, "y2": 460}
VOLUME_PANEL    = {"x1": 475, "y1": 305, "x2": 565, "y2": 460}

JOG_PANEL = {"x1": 50,  "y1": 50, "x2": 355, "y2": 250}
EQ_PANEL  = {"x1": 380, "y1": 50, "x2": 565, "y2": 250}

WAVEFORM_A = {"x1": 20, "y1": 520, "x2": FRAME_W - 20, "y2": 595, "deck": "A"}
WAVEFORM_B = {"x1": 20, "y1": 605, "x2": FRAME_W - 20, "y2": 680, "deck": "B"}

# =========================
# LAYOUT — RIGHT DECK (B)
# Mirror of left over x = 640
# =========================
# Left panel:  x1=20,  x2=610  → mirror: x1=670, x2=1260
# Top panel:   x1=35,  x2=595  → mirror: x1=685, x2=1245
# etc.  Formula: new_x = 1280 - old_x  (then swap x1/x2)

R_LEFT_PANEL    = {"x1": 670,  "y1": 20,  "x2": 1260, "y2": 490}
R_TOP_PANEL     = {"x1": 685,  "y1": 35,  "x2": 1245, "y2": 270}
R_BOTTOM_PANEL  = {"x1": 685,  "y1": 290, "x2": 1245, "y2": 475}

# Transport:   left x1=50,x2=140  → right x1=1140,x2=1230
R_TRANSPORT_PANEL = {"x1": 1140, "y1": 305, "x2": 1230, "y2": 460}
# FX:          left x1=155,x2=345 → right x1=935,x2=1125
R_FX_PANEL        = {"x1": 935,  "y1": 305, "x2": 1125, "y2": 460}
# BPM:         left x1=365,x2=455 → right x1=825,x2=915
R_BPM_PANEL       = {"x1": 825,  "y1": 305, "x2": 915,  "y2": 460}
# Volume:      left x1=475,x2=565 → right x1=715,x2=805
R_VOLUME_PANEL    = {"x1": 715,  "y1": 305, "x2": 805,  "y2": 460}

# Jog:         left x1=50,x2=355  → right x1=925,x2=1230
R_JOG_PANEL = {"x1": 925,  "y1": 50, "x2": 1230, "y2": 250}
# EQ:          left x1=380,x2=565 → right x1=715,x2=900
R_EQ_PANEL  = {"x1": 715,  "y1": 50, "x2": 900,  "y2": 250}

# =========================
# CONTROLS — LEFT DECK (A)
# =========================
PLAY_BUTTON = {
    "cx": 95, "cy": 405, "r": 28,
    "label": "PLAY", "playing": False, "pressed": False,
    "color": (0, 220, 120),
}
CUE_BUTTON = {
    "cx": 95, "cy": 345, "r": 25,
    "label": "CUE", "pressed": False,
    "color": (0, 180, 255),
}
FX_PAD = {
    "x1": 175, "y1": 330, "x2": 325, "y2": 430,
    "rows": 2, "cols": 2, "active_pad": -1,
    "color": (255, 170, 40),
}
BPM_SLIDER = {
    "value": 130.0, "min_value": 60.0, "max_value": 200.0,
    "x": 410, "y1": 340, "y2": 435,
    "dragging": False, "drag_start_y": 0, "drag_start_val": 0.0,
    "color": (0, 210, 255), "label": "BPM",
}
VOLUME_SLIDER = {
    "value": 75.0, "min_value": 0.0, "max_value": 100.0,
    "x": 520, "y1": 340, "y2": 435,
    "dragging": False, "drag_start_y": 0, "drag_start_val": 0.0,
    "color": (180, 120, 255), "label": "VOL",
}
JOG_WHEEL = {
    "dragging": False, "angle": 0.0, "prev_mouse_angle": 0.0,
}
eq_knobs = [
    {"label": "HIGH", "center": (472, 88),  "value": 50, "color": (0, 230, 255),  "dragging": False, "drag_start_y": 0, "drag_start_val": 0},
    {"label": "MID",  "center": (472, 150), "value": 50, "color": (0, 255, 160),  "dragging": False, "drag_start_y": 0, "drag_start_val": 0},
    {"label": "LOW",  "center": (472, 212), "value": 50, "color": (80, 80, 255),  "dragging": False, "drag_start_y": 0, "drag_start_val": 0},
]

# =========================
# CONTROLS — RIGHT DECK (B)
# Mirror of left controls
# =========================
# Play/Cue:    left cx=95  → right cx=1280-95=1185
R_PLAY_BUTTON = {
    "cx": 1185, "cy": 405, "r": 28,
    "label": "PLAY", "playing": False, "pressed": False,
    "color": (0, 220, 120),
}
R_CUE_BUTTON = {
    "cx": 1185, "cy": 345, "r": 25,
    "label": "CUE", "pressed": False,
    "color": (0, 180, 255),
}
# FX pad:      left x1=175,x2=325 → right x1=955,x2=1105
R_FX_PAD = {
    "x1": 955, "y1": 330, "x2": 1105, "y2": 430,
    "rows": 2, "cols": 2, "active_pad": -1,
    "color": (255, 170, 40),
}
# BPM slider:  left x=410 → right x=1280-410=870
R_BPM_SLIDER = {
    "value": 130.0, "min_value": 60.0, "max_value": 200.0,
    "x": 870, "y1": 340, "y2": 435,
    "dragging": False, "drag_start_y": 0, "drag_start_val": 0.0,
    "color": (220, 0, 255), "label": "BPM",
}
# Volume slider: left x=520 → right x=1280-520=760
R_VOLUME_SLIDER = {
    "value": 75.0, "min_value": 0.0, "max_value": 100.0,
    "x": 760, "y1": 340, "y2": 435,
    "dragging": False, "drag_start_y": 0, "drag_start_val": 0.0,
    "color": (180, 120, 255), "label": "VOL",
}
R_JOG_WHEEL = {
    "dragging": False, "angle": 0.0, "prev_mouse_angle": 0.0,
}
# EQ knobs:    left cx=472 → right cx=1280-472=808
r_eq_knobs = [
    {"label": "HIGH", "center": (808, 88),  "value": 50, "color": (0, 230, 255),  "dragging": False, "drag_start_y": 0, "drag_start_val": 0},
    {"label": "MID",  "center": (808, 150), "value": 50, "color": (0, 255, 160),  "dragging": False, "drag_start_y": 0, "drag_start_val": 0},
    {"label": "LOW",  "center": (808, 212), "value": 50, "color": (80, 80, 255),  "dragging": False, "drag_start_y": 0, "drag_start_val": 0},
]

# =========================
# HELPERS
# =========================
def _knob_to_db(v: float) -> float:
    return (v - 50.0) * 0.4

def _save_active_state():
    s = _active_state()
    s.volume    = VOLUME_SLIDER["value"]
    s.eq_high   = eq_knobs[0]["value"]
    s.eq_mid    = eq_knobs[1]["value"]
    s.eq_low    = eq_knobs[2]["value"]
    s.jog_angle = JOG_WHEEL["angle"]
    s.bpm       = BPM_SLIDER["value"]

def _restore_state(s: DeckState):
    VOLUME_SLIDER["value"]  = s.volume
    eq_knobs[0]["value"]    = s.eq_high
    eq_knobs[1]["value"]    = s.eq_mid
    eq_knobs[2]["value"]    = s.eq_low
    JOG_WHEEL["angle"]      = s.jog_angle
    BPM_SLIDER["value"]     = s.bpm

def _jog_center() -> tuple[int, int]:
    return ((JOG_PANEL["x1"] + JOG_PANEL["x2"]) // 2,
            (JOG_PANEL["y1"] + JOG_PANEL["y2"]) // 2)

def _jog_radius() -> int:
    return min(JOG_PANEL["x2"] - JOG_PANEL["x1"],
               JOG_PANEL["y2"] - JOG_PANEL["y1"]) // 2 - 18

def _r_jog_center() -> tuple[int, int]:
    return ((R_JOG_PANEL["x1"] + R_JOG_PANEL["x2"]) // 2,
            (R_JOG_PANEL["y1"] + R_JOG_PANEL["y2"]) // 2)

def _r_jog_radius() -> int:
    return min(R_JOG_PANEL["x2"] - R_JOG_PANEL["x1"],
               R_JOG_PANEL["y2"] - R_JOG_PANEL["y1"]) // 2 - 18

# =========================
# DRAW HELPERS
# =========================
def draw_panel(overlay, x1, y1, x2, y2,
               fill=(10, 10, 20), border=(50, 50, 80), thickness=1):
    cv2.rectangle(overlay, (x1, y1), (x2, y2), fill, -1)
    cv2.rectangle(overlay, (x1, y1), (x2, y2), border, thickness)

def draw_knob(overlay, knob):
    cx, cy = knob["center"]
    val, color, r = knob["value"], knob["color"], KNOB_RADIUS
    cv2.circle(overlay, (cx, cy), r+5, tuple(max(20, c//4) for c in color), 2)
    cv2.circle(overlay, (cx, cy), r, (30, 30, 30), -1)
    for ang in range(-225, 45, 4):
        rad = math.radians(ang)
        cv2.circle(overlay, (int(cx+(r-7)*math.cos(rad)), int(cy+(r-7)*math.sin(rad))), 2, (60, 60, 60), -1)
    active_end = -225 + int(270*val/100)
    steps = list(range(-225, active_end, 4))
    total = max(len(steps), 1)
    for i, ang in enumerate(steps):
        rad = math.radians(ang)
        brightness = 0.4 + 0.6*i/total
        c = tuple(int(ch*brightness) for ch in color)
        cv2.circle(overlay, (int(cx+(r-7)*math.cos(rad)), int(cy+(r-7)*math.sin(rad))), 2, c, -1)
    nr = math.radians(-225 + int(270*val/100))
    cv2.line(overlay, (cx, cy), (int(cx+(r-13)*math.cos(nr)), int(cy+(r-13)*math.sin(nr))), color, 2)
    cv2.circle(overlay, (cx, cy), 4, color, -1)
    (tw, th), _ = cv2.getTextSize(str(int(val)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
    cv2.putText(overlay, str(int(val)), (cx-tw//2, cy+th//2+1), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (220, 220, 220), 1, cv2.LINE_AA)
    (lw, lh), _ = cv2.getTextSize(knob["label"], cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
    cv2.putText(overlay, knob["label"], (cx-r-16-lw, cy+lh//2), cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)
    if knob["dragging"]:
        cv2.circle(overlay, (cx, cy), r+2, color, 2)

def draw_knob_right(overlay, knob):
    """Same as draw_knob but label is drawn to the RIGHT of the knob (mirrored)."""
    cx, cy = knob["center"]
    val, color, r = knob["value"], knob["color"], KNOB_RADIUS
    cv2.circle(overlay, (cx, cy), r+5, tuple(max(20, c//4) for c in color), 2)
    cv2.circle(overlay, (cx, cy), r, (30, 30, 30), -1)
    for ang in range(-225, 45, 4):
        rad = math.radians(ang)
        cv2.circle(overlay, (int(cx+(r-7)*math.cos(rad)), int(cy+(r-7)*math.sin(rad))), 2, (60, 60, 60), -1)
    active_end = -225 + int(270*val/100)
    steps = list(range(-225, active_end, 4))
    total = max(len(steps), 1)
    for i, ang in enumerate(steps):
        rad = math.radians(ang)
        brightness = 0.4 + 0.6*i/total
        c = tuple(int(ch*brightness) for ch in color)
        cv2.circle(overlay, (int(cx+(r-7)*math.cos(rad)), int(cy+(r-7)*math.sin(rad))), 2, c, -1)
    nr = math.radians(-225 + int(270*val/100))
    cv2.line(overlay, (cx, cy), (int(cx+(r-13)*math.cos(nr)), int(cy+(r-13)*math.sin(nr))), color, 2)
    cv2.circle(overlay, (cx, cy), 4, color, -1)
    (tw, th), _ = cv2.getTextSize(str(int(val)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
    cv2.putText(overlay, str(int(val)), (cx-tw//2, cy+th//2+1), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (220, 220, 220), 1, cv2.LINE_AA)
    # label to the RIGHT instead of left
    cv2.putText(overlay, knob["label"], (cx+r+6, cy+th//2), cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)
    if knob["dragging"]:
        cv2.circle(overlay, (cx, cy), r+2, color, 2)

def draw_button(overlay, button):
    cx, cy, r = button["cx"], button["cy"], button["r"]
    color = button["color"]
    fill = (25, 25, 35)
    if button.get("playing"):
        fill = tuple(min(255, int(c*0.30)+35) for c in color)
    if button["pressed"]:
        fill = tuple(min(255, int(c*0.50)+45) for c in color)
    cv2.circle(overlay, (cx, cy), r, fill, -1)
    cv2.circle(overlay, (cx, cy), r, color, 2)
    cv2.circle(overlay, (cx, cy), r+5, tuple(max(20, c//4) for c in color), 2)
    label = ("PAUSE" if button.get("playing") and button["label"] == "PLAY" else button["label"])
    fs = 0.44 if label == "PAUSE" else 0.62
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, fs, 1)
    cv2.putText(overlay, label, (cx-tw//2, cy+th//2), cv2.FONT_HERSHEY_DUPLEX, fs, (230, 230, 230), 1, cv2.LINE_AA)
    caption = "PLAY/PAUSE" if button["label"] == "PLAY" else "CUE"
    (cw, _), _ = cv2.getTextSize(caption, cv2.FONT_HERSHEY_SIMPLEX, 0.30, 1)
    cv2.putText(overlay, caption, (cx-cw//2, cy+r+15), cv2.FONT_HERSHEY_SIMPLEX, 0.30, color, 1, cv2.LINE_AA)

def draw_vertical_slider(overlay, slider):
    x, y1, y2 = slider["x"], slider["y1"], slider["y2"]
    value, lo, hi = slider["value"], slider["min_value"], slider["max_value"]
    color, label = slider["color"], slider["label"]
    tw = 5
    cv2.rectangle(overlay, (x-tw, y1), (x+tw, y2), (40, 40, 40), -1)
    cv2.rectangle(overlay, (x-tw, y1), (x+tw, y2), (80, 80, 80), 1)
    ratio = (value-lo) / (hi-lo)
    fill_y = int(y2 - ratio*(y2-y1))
    cv2.rectangle(overlay, (x-tw, fill_y), (x+tw, y2), color, -1)
    cv2.circle(overlay, (x, fill_y), 12, (20, 20, 20), -1)
    cv2.circle(overlay, (x, fill_y), 12, color, 2)
    cv2.circle(overlay, (x, fill_y), 4, color, -1)
    (vtw, vth), _ = cv2.getTextSize(str(int(value)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
    cv2.putText(overlay, str(int(value)), (x-vtw//2, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)
    (lw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
    cv2.putText(overlay, label, (x-lw//2, y2+18), cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)

def draw_fx_pad(overlay, pad):
    x1, y1, x2, y2 = pad["x1"], pad["y1"], pad["x2"], pad["y2"]
    rows, cols, color = pad["rows"], pad["cols"], pad["color"]
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (15, 15, 25), -1)
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (60, 60, 90), 1)
    cw_ = (x2-x1) // cols
    ch_ = (y2-y1) // rows
    for row in range(rows):
        for col in range(cols):
            idx = row*cols + col
            cx1, cy1 = x1+col*cw_, y1+row*ch_
            cx2, cy2 = cx1+cw_, cy1+ch_
            fill = ((30, 30, 40) if pad["active_pad"] != idx
                    else tuple(min(255, int(v*0.4)+40) for v in color))
            cv2.rectangle(overlay, (cx1+5, cy1+5), (cx2-5, cy2-5), fill, -1)
            cv2.rectangle(overlay, (cx1+5, cy1+5), (cx2-5, cy2-5), color, 2)
            lbl = f"FX {idx+1}"
            (tw, th), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
            cv2.putText(overlay, lbl, (cx1+cw_//2-tw//2, cy1+ch_//2+th//2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (220, 220, 220), 1, cv2.LINE_AA)
    cv2.putText(overlay, "FX PAD", (x1+48, y2+18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.46, (220, 220, 220), 1, cv2.LINE_AA)

def draw_jog_wheel(overlay, panel, jog_state, deck_color, deck_lbl):
    x1, y1, x2, y2 = panel["x1"], panel["y1"], panel["x2"], panel["y2"]
    cx, cy = (x1+x2)//2, (y1+y2)//2
    r_outer = min(x2-x1, y2-y1) // 2 - 18
    r_mid   = r_outer - 18
    r_inner = r_mid   - 26
    cv2.circle(overlay, (cx, cy), r_outer,   deck_color, 2)
    cv2.circle(overlay, (cx, cy), r_outer-6, (35, 35, 50), 2)
    cv2.circle(overlay, (cx, cy), r_mid,     (22, 22, 30), -1)
    cv2.circle(overlay, (cx, cy), r_mid,     (90, 90, 120), 1)
    cv2.circle(overlay, (cx, cy), r_inner,   (35, 35, 45), -1)
    cv2.circle(overlay, (cx, cy), r_inner,   (100, 100, 130), 1)
    cv2.circle(overlay, (cx, cy), 12,        (60, 60, 70), -1)
    cv2.circle(overlay, (cx, cy), 12,        (140, 140, 160), 1)
    for ang in range(0, 360, 18):
        rad = math.radians(ang)
        cv2.line(overlay,
                 (int(cx+(r_outer-12)*math.cos(rad)), int(cy+(r_outer-12)*math.sin(rad))),
                 (int(cx+(r_outer-4) *math.cos(rad)), int(cy+(r_outer-4) *math.sin(rad))),
                 (120, 120, 145), 1)
    mr  = math.radians(jog_state["angle"])
    mx_ = int(cx + (r_mid-12)*math.cos(mr))
    my_ = int(cy + (r_mid-12)*math.sin(mr))
    cv2.line(overlay, (cx, cy), (mx_, my_), deck_color, 2)
    cv2.circle(overlay, (mx_, my_), 4, deck_color, -1)
    if jog_state["dragging"]:
        cv2.circle(overlay, (cx, cy), r_outer+4, deck_color, 2)
    lbl = f"DECK {deck_lbl}"
    (lw, lh), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
    cv2.putText(overlay, lbl, (cx-lw//2, cy+lh//2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, deck_color, 1, cv2.LINE_AA)

def draw_waveform_bar(overlay, panel, title, is_active=False):
    x1, y1, x2, y2 = panel["x1"], panel["y1"], panel["x2"], panel["y2"]
    border_color = active_color() if is_active else (50, 50, 80)
    border_thick = 2 if is_active else 1
    draw_panel(overlay, x1, y1, x2, y2, fill=(12, 12, 22),
               border=border_color, thickness=border_thick)
    mid_y = (y1+y2)//2
    cv2.line(overlay, (x1+14, mid_y), (x2-14, mid_y), (60, 60, 80), 1)
    for i in range(0, (x2-x1)-28, 8):
        px = x1+14+i
        h  = 8 + int(12*abs(math.sin(i*0.035)))
        wv_color = active_color() if is_active else (0, 100, 130)
        cv2.line(overlay, (px, mid_y-h), (px, mid_y+h), wv_color, 1)
    cv2.putText(overlay, title, (x1+18, y1+24),
                cv2.FONT_HERSHEY_DUPLEX, 0.55, (180, 180, 180), 1, cv2.LINE_AA)

# =========================
# UI DRAW
# =========================
def draw_ui(frame):
    overlay = frame.copy()

    # ── LEFT DECK (A) ──────────────────────────────────────────
    draw_panel(overlay, LEFT_PANEL["x1"],   LEFT_PANEL["y1"],   LEFT_PANEL["x2"],   LEFT_PANEL["y2"])
    draw_panel(overlay, TOP_PANEL["x1"],    TOP_PANEL["y1"],    TOP_PANEL["x2"],    TOP_PANEL["y2"])
    draw_panel(overlay, BOTTOM_PANEL["x1"], BOTTOM_PANEL["y1"], BOTTOM_PANEL["x2"], BOTTOM_PANEL["y2"])

    draw_panel(overlay, JOG_PANEL["x1"], JOG_PANEL["y1"], JOG_PANEL["x2"], JOG_PANEL["y2"], fill=(12, 12, 22))
    draw_jog_wheel(overlay, JOG_PANEL, JOG_WHEEL, DECK_A_COLOR, "A")
    cv2.putText(overlay, "JOG WHEEL", (155, 266), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (120, 120, 140), 1, cv2.LINE_AA)

    draw_panel(overlay, EQ_PANEL["x1"], EQ_PANEL["y1"], EQ_PANEL["x2"], EQ_PANEL["y2"], fill=(12, 12, 22))
    cv2.putText(overlay, "EQ", (455, 266), cv2.FONT_HERSHEY_DUPLEX, 0.52, (180, 180, 180), 1, cv2.LINE_AA)
    for knob in eq_knobs:
        draw_knob(overlay, knob)

    draw_panel(overlay, TRANSPORT_PANEL["x1"], TRANSPORT_PANEL["y1"], TRANSPORT_PANEL["x2"], TRANSPORT_PANEL["y2"], fill=(12, 12, 22))
    draw_button(overlay, CUE_BUTTON)
    draw_button(overlay, PLAY_BUTTON)

    draw_panel(overlay, FX_PANEL["x1"], FX_PANEL["y1"], FX_PANEL["x2"], FX_PANEL["y2"], fill=(12, 12, 22))
    draw_fx_pad(overlay, FX_PAD)

    draw_panel(overlay, BPM_PANEL["x1"], BPM_PANEL["y1"], BPM_PANEL["x2"], BPM_PANEL["y2"], fill=(12, 12, 22))
    draw_vertical_slider(overlay, BPM_SLIDER)

    draw_panel(overlay, VOLUME_PANEL["x1"], VOLUME_PANEL["y1"], VOLUME_PANEL["x2"], VOLUME_PANEL["y2"], fill=(12, 12, 22))
    draw_vertical_slider(overlay, VOLUME_SLIDER)

    # ── RIGHT DECK (B) ─────────────────────────────────────────
    draw_panel(overlay, R_LEFT_PANEL["x1"],   R_LEFT_PANEL["y1"],   R_LEFT_PANEL["x2"],   R_LEFT_PANEL["y2"])
    draw_panel(overlay, R_TOP_PANEL["x1"],    R_TOP_PANEL["y1"],    R_TOP_PANEL["x2"],    R_TOP_PANEL["y2"])
    draw_panel(overlay, R_BOTTOM_PANEL["x1"], R_BOTTOM_PANEL["y1"], R_BOTTOM_PANEL["x2"], R_BOTTOM_PANEL["y2"])

    draw_panel(overlay, R_JOG_PANEL["x1"], R_JOG_PANEL["y1"], R_JOG_PANEL["x2"], R_JOG_PANEL["y2"], fill=(12, 12, 22))
    draw_jog_wheel(overlay, R_JOG_PANEL, R_JOG_WHEEL, DECK_B_COLOR, "B")
    # "JOG WHEEL" label — mirrored position under the right jog wheel
    rjcx = (R_JOG_PANEL["x1"] + R_JOG_PANEL["x2"]) // 2
    cv2.putText(overlay, "JOG WHEEL", (rjcx - 42, 266), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (120, 120, 140), 1, cv2.LINE_AA)

    draw_panel(overlay, R_EQ_PANEL["x1"], R_EQ_PANEL["y1"], R_EQ_PANEL["x2"], R_EQ_PANEL["y2"], fill=(12, 12, 22))
    # "EQ" label — mirrored position
    req_cx = (R_EQ_PANEL["x1"] + R_EQ_PANEL["x2"]) // 2
    cv2.putText(overlay, "EQ", (req_cx - 10, 266), cv2.FONT_HERSHEY_DUPLEX, 0.52, (180, 180, 180), 1, cv2.LINE_AA)
    for knob in r_eq_knobs:
        draw_knob_right(overlay, knob)

    draw_panel(overlay, R_TRANSPORT_PANEL["x1"], R_TRANSPORT_PANEL["y1"], R_TRANSPORT_PANEL["x2"], R_TRANSPORT_PANEL["y2"], fill=(12, 12, 22))
    draw_button(overlay, R_CUE_BUTTON)
    draw_button(overlay, R_PLAY_BUTTON)

    draw_panel(overlay, R_FX_PANEL["x1"], R_FX_PANEL["y1"], R_FX_PANEL["x2"], R_FX_PANEL["y2"], fill=(12, 12, 22))
    draw_fx_pad(overlay, R_FX_PAD)

    draw_panel(overlay, R_BPM_PANEL["x1"], R_BPM_PANEL["y1"], R_BPM_PANEL["x2"], R_BPM_PANEL["y2"], fill=(12, 12, 22))
    draw_vertical_slider(overlay, R_BPM_SLIDER)

    draw_panel(overlay, R_VOLUME_PANEL["x1"], R_VOLUME_PANEL["y1"], R_VOLUME_PANEL["x2"], R_VOLUME_PANEL["y2"], fill=(12, 12, 22))
    draw_vertical_slider(overlay, R_VOLUME_SLIDER)

    # ── WAVEFORMS (shared, full-width) ─────────────────────────
    deck_a_active = active_deck is deck_a
    draw_waveform_bar(overlay, WAVEFORM_A, "DECK A", is_active=deck_a_active)
    draw_waveform_bar(overlay, WAVEFORM_B, "DECK B", is_active=not deck_a_active)

    cv2.addWeighted(overlay, ALPHA, frame, 1 - ALPHA, 0, frame)

# =========================
# MOUSE
# =========================
def on_mouse(event, mx, my, flags, param):
    global active_deck

    # ── shared refs ────────────────────────────────────────────
    bpm = BPM_SLIDER
    vol = VOLUME_SLIDER
    fx  = FX_PAD
    r_bpm = R_BPM_SLIDER
    r_vol = R_VOLUME_SLIDER
    r_fx  = R_FX_PAD

    if event == cv2.EVENT_LBUTTONDOWN:

        # Waveform bar deck selection
        wa = WAVEFORM_A
        if wa["x1"] <= mx <= wa["x2"] and wa["y1"] <= my <= wa["y2"]:
            if active_deck is not deck_a:
                _save_active_state()
                active_deck = deck_a
                _restore_state(state_a)
                print("[UI] Active deck → A")
            return
        wb = WAVEFORM_B
        if wb["x1"] <= mx <= wb["x2"] and wb["y1"] <= my <= wb["y2"]:
            if active_deck is not deck_b:
                _save_active_state()
                active_deck = deck_b
                _restore_state(state_b)
                print("[UI] Active deck → B")
            return

        # ── LEFT DECK (A) controls ──────────────────────────────
        if math.hypot(mx-PLAY_BUTTON["cx"], my-PLAY_BUTTON["cy"]) <= PLAY_BUTTON["r"]:
            PLAY_BUTTON["pressed"] = True
            deck_a.toggle_play_pause()
            return
        if math.hypot(mx-CUE_BUTTON["cx"], my-CUE_BUTTON["cy"]) <= CUE_BUTTON["r"]:
            CUE_BUTTON["pressed"] = True
            deck_a.cue()
            return
        if fx["x1"] <= mx <= fx["x2"] and fx["y1"] <= my <= fx["y2"]:
            cw_ = (fx["x2"]-fx["x1"]) // fx["cols"]
            ch_ = (fx["y2"]-fx["y1"]) // fx["rows"]
            fx["active_pad"] = int((my-fx["y1"])//ch_ * fx["cols"] + (mx-fx["x1"])//cw_)
            print(f"FX pad {fx['active_pad']+1} pressed on Deck A")
            return
        bpm_ratio = (bpm["value"]-bpm["min_value"]) / (bpm["max_value"]-bpm["min_value"])
        bpm_thumb = int(bpm["y2"] - bpm_ratio*(bpm["y2"]-bpm["y1"]))
        if abs(mx-bpm["x"]) <= 24 and abs(my-bpm_thumb) <= 24:
            bpm["dragging"] = True
            bpm["drag_start_y"]   = my
            bpm["drag_start_val"] = bpm["value"]
            return
        vol_ratio = (vol["value"]-vol["min_value"]) / (vol["max_value"]-vol["min_value"])
        vol_thumb = int(vol["y2"] - vol_ratio*(vol["y2"]-vol["y1"]))
        if abs(mx-vol["x"]) <= 24 and abs(my-vol_thumb) <= 24:
            vol["dragging"] = True
            vol["drag_start_y"]   = my
            vol["drag_start_val"] = vol["value"]
            return
        for knob in eq_knobs:
            cx, cy = knob["center"]
            if math.hypot(mx-cx, my-cy) <= KNOB_RADIUS + 10:
                knob["dragging"] = True
                knob["drag_start_y"]  = my
                knob["drag_start_val"] = knob["value"]
                return
        jcx, jcy = _jog_center()
        if math.hypot(mx-jcx, my-jcy) <= _jog_radius():
            JOG_WHEEL["dragging"] = True
            JOG_WHEEL["prev_mouse_angle"] = math.degrees(math.atan2(my-jcy, mx-jcx))
            return

        # ── RIGHT DECK (B) controls ─────────────────────────────
        if math.hypot(mx-R_PLAY_BUTTON["cx"], my-R_PLAY_BUTTON["cy"]) <= R_PLAY_BUTTON["r"]:
            R_PLAY_BUTTON["pressed"] = True
            deck_b.toggle_play_pause()
            return
        if math.hypot(mx-R_CUE_BUTTON["cx"], my-R_CUE_BUTTON["cy"]) <= R_CUE_BUTTON["r"]:
            R_CUE_BUTTON["pressed"] = True
            deck_b.cue()
            return
        if r_fx["x1"] <= mx <= r_fx["x2"] and r_fx["y1"] <= my <= r_fx["y2"]:
            cw_ = (r_fx["x2"]-r_fx["x1"]) // r_fx["cols"]
            ch_ = (r_fx["y2"]-r_fx["y1"]) // r_fx["rows"]
            r_fx["active_pad"] = int((my-r_fx["y1"])//ch_ * r_fx["cols"] + (mx-r_fx["x1"])//cw_)
            print(f"FX pad {r_fx['active_pad']+1} pressed on Deck B")
            return
        r_bpm_ratio = (r_bpm["value"]-r_bpm["min_value"]) / (r_bpm["max_value"]-r_bpm["min_value"])
        r_bpm_thumb = int(r_bpm["y2"] - r_bpm_ratio*(r_bpm["y2"]-r_bpm["y1"]))
        if abs(mx-r_bpm["x"]) <= 24 and abs(my-r_bpm_thumb) <= 24:
            r_bpm["dragging"] = True
            r_bpm["drag_start_y"]   = my
            r_bpm["drag_start_val"] = r_bpm["value"]
            return
        r_vol_ratio = (r_vol["value"]-r_vol["min_value"]) / (r_vol["max_value"]-r_vol["min_value"])
        r_vol_thumb = int(r_vol["y2"] - r_vol_ratio*(r_vol["y2"]-r_vol["y1"]))
        if abs(mx-r_vol["x"]) <= 24 and abs(my-r_vol_thumb) <= 24:
            r_vol["dragging"] = True
            r_vol["drag_start_y"]   = my
            r_vol["drag_start_val"] = r_vol["value"]
            return
        for knob in r_eq_knobs:
            cx, cy = knob["center"]
            if math.hypot(mx-cx, my-cy) <= KNOB_RADIUS + 10:
                knob["dragging"] = True
                knob["drag_start_y"]  = my
                knob["drag_start_val"] = knob["value"]
                return
        rjcx, rjcy = _r_jog_center()
        if math.hypot(mx-rjcx, my-rjcy) <= _r_jog_radius():
            R_JOG_WHEEL["dragging"] = True
            R_JOG_WHEEL["prev_mouse_angle"] = math.degrees(math.atan2(my-rjcy, mx-rjcx))
            return

    elif event == cv2.EVENT_MOUSEMOVE:

        # ── LEFT DECK (A) ───────────────────────────────────────
        if bpm["dragging"]:
            dy = bpm["drag_start_y"] - my
            slider_range = bpm["max_value"] - bpm["min_value"]
            px_range = bpm["y2"] - bpm["y1"]
            bpm["value"] = max(bpm["min_value"], min(bpm["max_value"],
                bpm["drag_start_val"] + dy * (slider_range / px_range)))
            deck_a.set_bpm(bpm["value"])
            state_a.bpm = bpm["value"]
        if vol["dragging"]:
            dy = vol["drag_start_y"] - my
            slider_range = vol["max_value"] - vol["min_value"]
            px_range = vol["y2"] - vol["y1"]
            vol["value"] = max(vol["min_value"], min(vol["max_value"],
                vol["drag_start_val"] + dy * (slider_range / px_range)))
            deck_a.set_volume(vol["value"] / 100.0)
            state_a.volume = vol["value"]
        for i, knob in enumerate(eq_knobs):
            if knob["dragging"]:
                dy = knob["drag_start_y"] - my
                knob["value"] = max(0., min(100., knob["drag_start_val"] + dy*0.6))
                if i == 0: state_a.eq_high = knob["value"]
                elif i == 1: state_a.eq_mid  = knob["value"]
                elif i == 2: state_a.eq_low  = knob["value"]
        if JOG_WHEEL["dragging"]:
            jcx, jcy = _jog_center()
            curr = math.degrees(math.atan2(my-jcy, mx-jcx))
            prev = JOG_WHEEL["prev_mouse_angle"]
            delta = curr - prev
            if delta >  180: delta -= 360
            if delta < -180: delta += 360
            JOG_WHEEL["angle"] = (JOG_WHEEL["angle"] + delta) % 360
            state_a.jog_angle  = JOG_WHEEL["angle"]
            deck_a.jog(int(delta * 50))
            JOG_WHEEL["prev_mouse_angle"] = curr

        # ── RIGHT DECK (B) ──────────────────────────────────────
        if r_bpm["dragging"]:
            dy = r_bpm["drag_start_y"] - my
            slider_range = r_bpm["max_value"] - r_bpm["min_value"]
            px_range = r_bpm["y2"] - r_bpm["y1"]
            r_bpm["value"] = max(r_bpm["min_value"], min(r_bpm["max_value"],
                r_bpm["drag_start_val"] + dy * (slider_range / px_range)))
            deck_b.set_bpm(r_bpm["value"])
            state_b.bpm = r_bpm["value"]
        if r_vol["dragging"]:
            dy = r_vol["drag_start_y"] - my
            slider_range = r_vol["max_value"] - r_vol["min_value"]
            px_range = r_vol["y2"] - r_vol["y1"]
            r_vol["value"] = max(r_vol["min_value"], min(r_vol["max_value"],
                r_vol["drag_start_val"] + dy * (slider_range / px_range)))
            deck_b.set_volume(r_vol["value"] / 100.0)
            state_b.volume = r_vol["value"]
        for i, knob in enumerate(r_eq_knobs):
            if knob["dragging"]:
                dy = knob["drag_start_y"] - my
                knob["value"] = max(0., min(100., knob["drag_start_val"] + dy*0.6))
                if i == 0: state_b.eq_high = knob["value"]
                elif i == 1: state_b.eq_mid  = knob["value"]
                elif i == 2: state_b.eq_low  = knob["value"]
        if R_JOG_WHEEL["dragging"]:
            rjcx, rjcy = _r_jog_center()
            curr = math.degrees(math.atan2(my-rjcy, mx-rjcx))
            prev = R_JOG_WHEEL["prev_mouse_angle"]
            delta = curr - prev
            if delta >  180: delta -= 360
            if delta < -180: delta += 360
            R_JOG_WHEEL["angle"] = (R_JOG_WHEEL["angle"] + delta) % 360
            state_b.jog_angle    = R_JOG_WHEEL["angle"]
            deck_b.jog(int(delta * 50))
            R_JOG_WHEEL["prev_mouse_angle"] = curr

    elif event == cv2.EVENT_LBUTTONUP:
        # Fire EQ updates on release
        if any(k["dragging"] for k in eq_knobs):
            deck_a.set_eq(
                low  = _knob_to_db(eq_knobs[2]["value"]),
                mid  = _knob_to_db(eq_knobs[1]["value"]),
                high = _knob_to_db(eq_knobs[0]["value"]),
            )
        if any(k["dragging"] for k in r_eq_knobs):
            deck_b.set_eq(
                low  = _knob_to_db(r_eq_knobs[2]["value"]),
                mid  = _knob_to_db(r_eq_knobs[1]["value"]),
                high = _knob_to_db(r_eq_knobs[0]["value"]),
            )
        # Reset all dragging flags
        bpm["dragging"]   = False
        vol["dragging"]   = False
        r_bpm["dragging"] = False
        r_vol["dragging"] = False
        PLAY_BUTTON["pressed"]   = False
        CUE_BUTTON["pressed"]    = False
        R_PLAY_BUTTON["pressed"] = False
        R_CUE_BUTTON["pressed"]  = False
        FX_PAD["active_pad"]   = -1
        R_FX_PAD["active_pad"] = -1
        JOG_WHEEL["dragging"]   = False
        R_JOG_WHEEL["dragging"] = False
        for knob in eq_knobs:
            knob["dragging"] = False
        for knob in r_eq_knobs:
            knob["dragging"] = False

# =========================
# HAND GESTURE STATE
# =========================
# Persistent pinch state per hand label ("Left" / "Right")
_hand_state = {
    "Left":  {"pinching": False, "cx": 0, "cy": 0, "pinch_frames": 0},
    "Right": {"pinching": False, "cx": 0, "cy": 0, "pinch_frames": 0},
}

PINCH_THRESHOLD  = 40   # px — raise to make pinch easier, lower to make it stricter
PINCH_DEBOUNCE   = 3    # consecutive frames needed to register a pinch
PINCH_DOT_RADIUS = 14   # visual cursor dot radius

def process_hands(result, frame):
    """
    Converts MediaPipe hand landmarks into on_mouse() calls every frame.
    No existing logic is touched — hands just become another input device.

    Left hand  → Deck A side  |  Right hand → Deck B side
    Cursor     = index fingertip (landmark 8)
    Pinch      = thumb tip (4) ↔ index tip (8) distance < PINCH_THRESHOLD
    """
    if not result.multi_hand_landmarks:
        # All hands gone — release anything still dragging
        for st in _hand_state.values():
            if st["pinching"]:
                on_mouse(cv2.EVENT_LBUTTONUP, st["cx"], st["cy"], 0, None)
                st["pinching"] = False
        return

    # Map label → landmarks for this frame.
    # NOTE: frame is flipped (cv2.flip(frame,1)), so MediaPipe's "Left"/"Right"
    # are mirrored — swap them to match screen coordinates.
    detected = {}
    for hand_lm, hand_info in zip(result.multi_hand_landmarks,
                                   result.multi_handedness):
        raw_label = hand_info.classification[0].label  # "Left" or "Right"
        label = "Right" if raw_label == "Left" else "Left"  # un-mirror
        detected[label] = hand_lm

    # Release any hand that disappeared this frame
    for side, st in _hand_state.items():
        if side not in detected and st["pinching"]:
            on_mouse(cv2.EVENT_LBUTTONUP, st["cx"], st["cy"], 0, None)
            st["pinching"] = False

    for side, hand_lm in detected.items():
        lm = hand_lm.landmark

        # Cursor = index fingertip scaled to frame pixels
        cx = int(lm[8].x * FRAME_W)
        cy = int(lm[8].y * FRAME_H)

        # Pinch distance: thumb tip (4) → index tip (8)
        tx = int(lm[4].x * FRAME_W)
        ty = int(lm[4].y * FRAME_H)
        pinch_dist  = math.hypot(cx - tx, cy - ty)
        is_pinching = pinch_dist < PINCH_THRESHOLD

        st           = _hand_state[side]
        was_pinching = st["pinching"]

        # Debounce: require PINCH_DEBOUNCE consecutive frames before registering
        if pinch_dist < PINCH_THRESHOLD:
            st["pinch_frames"] = min(st["pinch_frames"] + 1, PINCH_DEBOUNCE)
        else:
            st["pinch_frames"] = 0

        is_pinching = st["pinch_frames"] >= PINCH_DEBOUNCE
        if is_pinching and not was_pinching:
            on_mouse(cv2.EVENT_LBUTTONDOWN, cx, cy, 0, None)
        elif is_pinching and was_pinching:
            on_mouse(cv2.EVENT_MOUSEMOVE, cx, cy, 0, None)
        elif not is_pinching and was_pinching:
            on_mouse(cv2.EVENT_LBUTTONUP, cx, cy, 0, None)
        # Hovering → do nothing. No MOUSEMOVE unless pinched.

        st["pinching"] = is_pinching
        st["cx"]       = cx
        st["cy"]       = cy

        # Draw cursor dot — green=pinched, yellow=building up, white=hovering
        if is_pinching:
            dot_color = (0, 255, 80)
        elif st["pinch_frames"] > 0:
            dot_color = (0, 220, 255)   # yellow-ish: almost there
        else:
            dot_color = (220, 220, 220)
        cv2.circle(frame, (cx, cy), PINCH_DOT_RADIUS,     dot_color, -1)
        cv2.circle(frame, (cx, cy), PINCH_DOT_RADIUS + 4, dot_color, 2)
        # Arc shows proximity to pinch threshold
        pct = max(0.0, min(1.0, 1.0 - pinch_dist / PINCH_THRESHOLD))
        cv2.ellipse(frame, (cx, cy),
                    (PINCH_DOT_RADIUS + 9, PINCH_DOT_RADIUS + 9),
                    -90, 0, int(360 * pct), dot_color, 2)

# =========================
# MAIN
# =========================
def main():
    global active_deck

    TRACK_A = "track_a.mp3"
    TRACK_B = "track_b.mp3"

    ok_a = deck_a.load(TRACK_A)
    ok_b = deck_b.load(TRACK_B)
    if not ok_a or not ok_b:
        print("Failed to load one or more tracks. Check your file paths and try again.")
        return

    initial_vol = VOLUME_SLIDER["value"] / 100.0
    deck_a.set_volume(initial_vol)
    deck_b.set_volume(initial_vol)

    active_deck = deck_a
    state_a.bpm = int(deck_a.get_bpm())
    state_b.bpm = int(deck_b.get_bpm())
    BPM_SLIDER["value"]   = state_a.bpm
    R_BPM_SLIDER["value"] = state_b.bpm

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Camera resolution: {actual_w}x{actual_h}")

    mp_drawing  = mp.solutions.drawing_utils
    mp_hands    = mp.solutions.hands
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
                    frame, hand_lm, mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 255, 160), thickness=2, circle_radius=4),
                    mp_drawing.DrawingSpec(color=(0, 180, 100), thickness=2),
                )

        # Hand gesture → mouse event synthesis (draws cursor dots too)
        process_hands(result, frame)

        PLAY_BUTTON["playing"]   = deck_a.is_playing
        R_PLAY_BUTTON["playing"] = deck_b.is_playing
        draw_ui(frame)
        cv2.imshow(win_name, frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    deck_a.release()
    deck_b.release()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()