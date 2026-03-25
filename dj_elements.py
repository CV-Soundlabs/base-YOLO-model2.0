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
    volume:    float = 75.0  
    eq_high:   float = 50.0   
    eq_mid:    float = 50.0   
    eq_low:    float = 50.0   
    jog_angle: float = 0.0    

state_a = DeckState()
state_b = DeckState()

def _active_state() -> DeckState:
    return state_a if active_deck is deck_a else state_b


deck_a, deck_b = create_decks()
active_deck     = deck_a          #points to whichever deck the UI controls

DECK_A_COLOR = (0,  210, 255)     
DECK_B_COLOR = (220, 0,  255)     

def active_color() -> tuple:
    return DECK_A_COLOR if active_deck is deck_a else DECK_B_COLOR

def active_label() -> str:
    return "A" if active_deck is deck_a else "B"

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

WAVEFORM_A = {
    "x1": 20, "y1": 520,
    "x2": FRAME_W - 20, "y2": 595,
    "deck": "A"
}

WAVEFORM_B = {
    "x1": 20, "y1": 605,
    "x2": FRAME_W - 20, "y2": 680,
    "deck": "B"
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
    "angle": 0.0,
    "prev_mouse_angle": 0.0,
}

eq_knobs = [
    {"label": "HIGH", "center": (472, 88), "value": 50, "color": (0, 230, 255),
     "dragging": False, "drag_start_y": 0, "drag_start_val": 0},
    {"label": "MID",  "center": (472, 150), "value": 50, "color": (0, 255, 160),
     "dragging": False, "drag_start_y": 0, "drag_start_val": 0},
    {"label": "LOW",  "center": (472, 212), "value": 50, "color": (80, 80, 255),
     "dragging": False, "drag_start_y": 0, "drag_start_val": 0},
]

def _knob_to_db(v: float) -> float:
    """Map knob value 0–100 → -20.0 to +20.0 dB."""
    return (v - 50.0) * 0.4


def _save_active_state():
    """Snapshot current UI control values into the active deck's DeckState."""
    s = _active_state()
    s.volume    = VOLUME_SLIDER["value"]
    s.eq_high   = eq_knobs[0]["value"]
    s.eq_mid    = eq_knobs[1]["value"]
    s.eq_low    = eq_knobs[2]["value"]
    s.jog_angle = JOG_WHEEL["angle"]


def _restore_state(s: DeckState):
    """Push a DeckState back into the shared UI controls so they redraw correctly."""
    VOLUME_SLIDER["value"]    = s.volume
    eq_knobs[0]["value"]      = s.eq_high
    eq_knobs[1]["value"]      = s.eq_mid
    eq_knobs[2]["value"]      = s.eq_low
    JOG_WHEEL["angle"]        = s.jog_angle

def _jog_center() -> tuple[int, int]:
    return ((JOG_PANEL["x1"] + JOG_PANEL["x2"]) // 2,
            (JOG_PANEL["y1"] + JOG_PANEL["y2"]) // 2)

def _jog_radius() -> int:
    return min(JOG_PANEL["x2"] - JOG_PANEL["x1"],
               JOG_PANEL["y2"] - JOG_PANEL["y1"]) // 2 - 18

# ---------------------------------------------------------------------------
# Draw helpers
# ---------------------------------------------------------------------------

def draw_panel(overlay, x1, y1, x2, y2,
               fill=(10, 10, 20), border=(50, 50, 80), thickness=1):
    cv2.rectangle(overlay, (x1, y1), (x2, y2), fill, -1)
    cv2.rectangle(overlay, (x1, y1), (x2, y2), border, thickness)


def draw_knob(overlay, knob):
    cx, cy = knob["center"]
    val, color, r = knob["value"], knob["color"], KNOB_RADIUS
    cv2.circle(overlay, (cx, cy), r+5, tuple(max(20, c//4) for c in color), 2)
    cv2.circle(overlay, (cx, cy), r,   (30, 30, 30), -1)
    for ang in range(-225, 45, 4):
        rad = math.radians(ang)
        cv2.circle(overlay,
                   (int(cx+(r-7)*math.cos(rad)), int(cy+(r-7)*math.sin(rad))),
                   2, (60, 60, 60), -1)
    active_end = -225 + int(270*val/100)
    steps = list(range(-225, active_end, 4))
    total = max(len(steps), 1)
    for i, ang in enumerate(steps):
        rad = math.radians(ang)
        brightness = 0.4 + 0.6*i/total
        c = tuple(int(ch*brightness) for ch in color)
        cv2.circle(overlay,
                   (int(cx+(r-7)*math.cos(rad)), int(cy+(r-7)*math.sin(rad))),
                   2, c, -1)
    nr = math.radians(-225 + int(270*val/100))
    cv2.line(overlay, (cx, cy),
             (int(cx+(r-13)*math.cos(nr)), int(cy+(r-13)*math.sin(nr))), color, 2)
    cv2.circle(overlay, (cx, cy), 4, color, -1)
    (tw, th), _ = cv2.getTextSize(str(int(val)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
    cv2.putText(overlay, str(int(val)), (cx-tw//2, cy+th//2+1),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (220, 220, 220), 1, cv2.LINE_AA)
    (lw, lh), _ = cv2.getTextSize(knob["label"], cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
    cv2.putText(overlay, knob["label"], (cx-r-16-lw, cy+lh//2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)
    if knob["dragging"]:
        cv2.circle(overlay, (cx, cy), r+2, color, 2)


def draw_button(overlay, button):
    cx, cy, r = button["cx"], button["cy"], button["r"]
    color = button["color"]
    fill  = (25, 25, 35)
    if button.get("playing"):
        fill = tuple(min(255, int(c*0.30)+35) for c in color)
    if button["pressed"]:
        fill = tuple(min(255, int(c*0.50)+45) for c in color)
    cv2.circle(overlay, (cx, cy), r,   fill,  -1)
    cv2.circle(overlay, (cx, cy), r,   color,  2)
    cv2.circle(overlay, (cx, cy), r+5, tuple(max(20, c//4) for c in color), 2)
    label = ("PAUSE" if button.get("playing") and button["label"] == "PLAY"
             else button["label"])
    fs = 0.44 if label == "PAUSE" else 0.62
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, fs, 1)
    cv2.putText(overlay, label, (cx-tw//2, cy+th//2),
                cv2.FONT_HERSHEY_DUPLEX, fs, (230, 230, 230), 1, cv2.LINE_AA)
    caption = "PLAY/PAUSE" if button["label"] == "PLAY" else "CUE"
    (cw, _), _ = cv2.getTextSize(caption, cv2.FONT_HERSHEY_SIMPLEX, 0.30, 1)
    cv2.putText(overlay, caption, (cx-cw//2, cy+r+15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.30, color, 1, cv2.LINE_AA)


def draw_vertical_slider(overlay, slider):
    x, y1, y2 = slider["x"], slider["y1"], slider["y2"]
    value, lo, hi = slider["value"], slider["min_value"], slider["max_value"]
    color, label = slider["color"], slider["label"]
    tw = 5
    cv2.rectangle(overlay, (x-tw, y1), (x+tw, y2), (40, 40, 40), -1)
    cv2.rectangle(overlay, (x-tw, y1), (x+tw, y2), (80, 80, 80),  1)
    ratio  = (value-lo) / (hi-lo)
    fill_y = int(y2 - ratio*(y2-y1))
    cv2.rectangle(overlay, (x-tw, fill_y), (x+tw, y2), color, -1)
    cv2.circle(overlay, (x, fill_y), 12, (20, 20, 20), -1)
    cv2.circle(overlay, (x, fill_y), 12, color,         2)
    cv2.circle(overlay, (x, fill_y),  4, color,        -1)
    (vtw, vth), _ = cv2.getTextSize(str(int(value)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
    cv2.putText(overlay, str(int(value)), (x-vtw//2, y1-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)
    (lw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
    cv2.putText(overlay, label, (x-lw//2, y2+18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)


def draw_fx_pad(overlay, pad):
    x1, y1, x2, y2 = pad["x1"], pad["y1"], pad["x2"], pad["y2"]
    rows, cols, color = pad["rows"], pad["cols"], pad["color"]
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (15, 15, 25), -1)
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (60, 60, 90),  1)
    cw_ = (x2-x1) // cols
    ch_ = (y2-y1) // rows
    for row in range(rows):
        for col in range(cols):
            idx = row*cols + col
            cx1, cy1 = x1+col*cw_, y1+row*ch_
            cx2, cy2 = cx1+cw_,    cy1+ch_
            fill = ((30, 30, 40) if pad["active_pad"] != idx
                    else tuple(min(255, int(v*0.4)+40) for v in color))
            cv2.rectangle(overlay, (cx1+5, cy1+5), (cx2-5, cy2-5), fill,  -1)
            cv2.rectangle(overlay, (cx1+5, cy1+5), (cx2-5, cy2-5), color,  2)
            lbl = f"FX {idx+1}"
            (tw, th), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
            cv2.putText(overlay, lbl,
                        (cx1+cw_//2-tw//2, cy1+ch_//2+th//2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (220, 220, 220), 1, cv2.LINE_AA)
    cv2.putText(overlay, "FX PAD", (x1+48, y2+18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.46, (220, 220, 220), 1, cv2.LINE_AA)


def draw_jog_wheel(overlay, panel):
    """Draw jog wheel. Marker rotates with JOG_WHEEL['angle']; ring colour
    matches the active deck."""
    x1, y1, x2, y2 = panel["x1"], panel["y1"], panel["x2"], panel["y2"]
    cx, cy  = (x1+x2)//2, (y1+y2)//2
    r_outer = _jog_radius()
    r_mid   = r_outer - 18
    r_inner = r_mid   - 26
    deck_col = active_color()

    # Rings
    cv2.circle(overlay, (cx, cy), r_outer,    deck_col,      2)   # active deck colour
    cv2.circle(overlay, (cx, cy), r_outer-6,  (35, 35, 50),  2)
    cv2.circle(overlay, (cx, cy), r_mid,      (22, 22, 30), -1)
    cv2.circle(overlay, (cx, cy), r_mid,      (90, 90,120),  1)
    cv2.circle(overlay, (cx, cy), r_inner,    (35, 35, 45), -1)
    cv2.circle(overlay, (cx, cy), r_inner,    (100,100,130), 1)
    cv2.circle(overlay, (cx, cy), 12,         (60, 60, 70), -1)
    cv2.circle(overlay, (cx, cy), 12,         (140,140,160), 1)

    # Tick marks
    for ang in range(0, 360, 18):
        rad = math.radians(ang)
        cv2.line(overlay,
                 (int(cx+(r_outer-12)*math.cos(rad)), int(cy+(r_outer-12)*math.sin(rad))),
                 (int(cx+(r_outer-4) *math.cos(rad)), int(cy+(r_outer-4) *math.sin(rad))),
                 (120, 120, 145), 1)

    # Rotating marker
    mr  = math.radians(JOG_WHEEL["angle"])
    mx_ = int(cx + (r_mid-12)*math.cos(mr))
    my_ = int(cy + (r_mid-12)*math.sin(mr))
    cv2.line(overlay, (cx, cy), (mx_, my_), deck_col, 2)
    cv2.circle(overlay, (mx_, my_), 4, deck_col, -1)

    # Drag highlight
    if JOG_WHEEL["dragging"]:
        cv2.circle(overlay, (cx, cy), r_outer+4, deck_col, 2)

    # Deck label in centre
    lbl = f"DECK {active_label()}"
    (lw, lh), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
    cv2.putText(overlay, lbl, (cx-lw//2, cy+lh//2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, deck_col, 1, cv2.LINE_AA)


def draw_waveform_bar(overlay, panel, title, is_active=False):
    """Draw a waveform placeholder. Active deck gets a coloured highlight border."""
    x1, y1, x2, y2 = panel["x1"], panel["y1"], panel["x2"], panel["y2"]
    border_color = active_color() if is_active else (50, 50, 80)
    border_thick = 2             if is_active else 1

    draw_panel(overlay, x1, y1, x2, y2, fill=(12, 12, 22),
               border=border_color, thickness=border_thick)

    mid_y = (y1+y2)//2
    cv2.line(overlay, (x1+14, mid_y), (x2-14, mid_y), (60, 60, 80), 1)
    for i in range(0, (x2-x1)-28, 8):
        px = x1+14+i
        h  = 8 + int(12*abs(math.sin(i*0.035)))
        wv_color = active_color() if is_active else (0, 100, 130)
        cv2.line(overlay, (px, mid_y-h), (px, mid_y+h), wv_color, 1)

     # Left title
    cv2.putText(
        overlay, title, (x1 + 18, y1 + 24),
        cv2.FONT_HERSHEY_DUPLEX, 0.55, (180, 180, 180), 1, cv2.LINE_AA
    )





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


    deck_a_active = active_deck is deck_a

    draw_waveform_bar(overlay, WAVEFORM_A, "DECK A", is_active=deck_a_active)
    draw_waveform_bar(overlay, WAVEFORM_B, "DECK B", is_active=not deck_a_active)

    cv2.addWeighted(overlay, ALPHA, frame, 1 - ALPHA, 0, frame)

# =========================
# MOUSE
# =========================

def on_mouse(event, mx, my, flags, param):
    global active_deck

    bpm = BPM_SLIDER
    vol = VOLUME_SLIDER
    fx = FX_PAD

    if event == cv2.EVENT_LBUTTONDOWN:

     #Deck selection via waveform bars 
        wa = WAVEFORM_A
        if wa["x1"] <= mx <= wa["x2"] and wa["y1"] <= my <= wa["y2"]:
            if active_deck is not deck_a:
                _save_active_state()          # save Deck B's current UI values
                active_deck = deck_a
                _restore_state(state_a)       # load Deck A's saved UI values
                print("[UI] Active deck → A")
            return
        wb = WAVEFORM_B
        if wb["x1"] <= mx <= wb["x2"] and wb["y1"] <= my <= wb["y2"]:
            if active_deck is not deck_b:
                _save_active_state()          # save Deck A's current UI values
                active_deck = deck_b
                _restore_state(state_b)       # load Deck B's saved UI values
                print("[UI] Active deck → B")
            return

        #PLAY/PAUSE 
        if math.hypot(mx-PLAY_BUTTON["cx"], my-PLAY_BUTTON["cy"]) <= PLAY_BUTTON["r"]:
            PLAY_BUTTON["pressed"] = True
            active_deck.toggle_play_pause()
            return

        #CUE 
        if math.hypot(mx-CUE_BUTTON["cx"], my-CUE_BUTTON["cy"]) <= CUE_BUTTON["r"]:
            CUE_BUTTON["pressed"] = True
            active_deck.cue()
            return

        #FX pads
        if fx["x1"] <= mx <= fx["x2"] and fx["y1"] <= my <= fx["y2"]:
            cw_ = (fx["x2"]-fx["x1"]) // fx["cols"]
            ch_ = (fx["y2"]-fx["y1"]) // fx["rows"]
            fx["active_pad"] = int((my-fx["y1"])//ch_ * fx["cols"] + (mx-fx["x1"])//cw_)
            print(f"FX pad {fx['active_pad']+1} pressed on Deck {active_label()}")
            return

        #BPM slider
        bpm_ratio = (bpm["value"]-bpm["min_value"]) / (bpm["max_value"]-bpm["min_value"])
        bpm_thumb = int(bpm["y2"] - bpm_ratio*(bpm["y2"]-bpm["y1"]))
        if abs(mx-bpm["x"]) <= 24 and abs(my-bpm_thumb) <= 24:
            bpm["dragging"] = True; return
        if abs(mx-bpm["x"]) <= 20 and bpm["y1"] <= my <= bpm["y2"]:
            bpm["dragging"] = True
            r = (bpm["y2"]-my) / (bpm["y2"]-bpm["y1"])
            bpm["value"] = bpm["min_value"] + max(0.,min(1.,r))*(bpm["max_value"]-bpm["min_value"])
            return

        #Volume slider 
        vol_ratio = (vol["value"]-vol["min_value"]) / (vol["max_value"]-vol["min_value"])
        vol_thumb = int(vol["y2"] - vol_ratio*(vol["y2"]-vol["y1"]))
        if abs(mx-vol["x"]) <= 24 and abs(my-vol_thumb) <= 24:
            vol["dragging"] = True; return
        if abs(mx-vol["x"]) <= 20 and vol["y1"] <= my <= vol["y2"]:
            vol["dragging"] = True
            r = (vol["y2"]-my) / (vol["y2"]-vol["y1"])
            vol["value"] = vol["min_value"] + max(0.,min(1.,r))*(vol["max_value"]-vol["min_value"])
            active_deck.set_volume(vol["value"] / 100.0)
            return

        #EQ knobs
        for knob in eq_knobs:
            cx, cy = knob["center"]
            if math.hypot(mx-cx, my-cy) <= KNOB_RADIUS + 10:
                knob["dragging"]       = True
                knob["drag_start_y"]   = my
                knob["drag_start_val"] = knob["value"]
                return

        #Jog wheel 
        jcx, jcy = _jog_center()
        if math.hypot(mx-jcx, my-jcy) <= _jog_radius():
            JOG_WHEEL["dragging"] = True
            JOG_WHEEL["prev_mouse_angle"] = math.degrees(math.atan2(my-jcy, mx-jcx))
            return

    elif event == cv2.EVENT_MOUSEMOVE:
        #BPM
        if bpm["dragging"]:
            r = (bpm["y2"]-my) / (bpm["y2"]-bpm["y1"])
            bpm["value"] = bpm["min_value"] + max(0.,min(1.,r))*(bpm["max_value"]-bpm["min_value"])

        #Volume
        if vol["dragging"]:
            r = (vol["y2"]-my) / (vol["y2"]-vol["y1"])
            vol["value"] = vol["min_value"] + max(0.,min(1.,r))*(vol["max_value"]-vol["min_value"])
            active_deck.set_volume(vol["value"] / 100.0)
            _active_state().volume = vol["value"]

        #EQ knobs 
        for i, knob in enumerate(eq_knobs):
            if knob["dragging"]:
                dy = knob["drag_start_y"] - my
                knob["value"] = max(0., min(100., knob["drag_start_val"] + dy*0.6))
                # keep DeckState in sync as the knob moves
                if   i == 0: _active_state().eq_high = knob["value"]
                elif i == 1: _active_state().eq_mid  = knob["value"]
                elif i == 2: _active_state().eq_low  = knob["value"]

        #Jog wheel
        if JOG_WHEEL["dragging"]:
            jcx, jcy = _jog_center()
            curr_mouse_angle = math.degrees(math.atan2(my-jcy, mx-jcx))
            prev             = JOG_WHEEL["prev_mouse_angle"]

            delta = curr_mouse_angle - prev
            if delta >  180: delta -= 360
            if delta < -180: delta += 360

            JOG_WHEEL["angle"] = (JOG_WHEEL["angle"] + delta) % 360
            _active_state().jog_angle = JOG_WHEEL["angle"]
            active_deck.jog(int(delta * 50))         
            JOG_WHEEL["prev_mouse_angle"] = curr_mouse_angle

    elif event == cv2.EVENT_LBUTTONUP:
         #Fire EQ update once on release — VLC applies instantly, no buffer rebuild
        if any(k["dragging"] for k in eq_knobs):
            active_deck.set_eq(
                low   = _knob_to_db(eq_knobs[2]["value"]),
                mid   = _knob_to_db(eq_knobs[1]["value"]),
                high  = _knob_to_db(eq_knobs[0]["value"]),
            )
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
        
        PLAY_BUTTON["playing"] = active_deck.is_playing

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