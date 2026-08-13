# AirCanvas🎨

> **A real-time hand-tracking painting app — draw in the air, see it on screen.**

AirCanvas turns your webcam into a canvas. It uses **MediaPipe Hands** to track your hand's 21 skeletal landmarks and translates your index fingertip's movement into brush strokes, rendered live over your video feed with **OpenCV**.

---

## How It Works

1. Your webcam feed is captured and flipped horizontally (mirror view) each frame.
2. **MediaPipe Hands** detects up to 1 hand and returns 21 3D landmark points per hand.
3. The app checks the position of your index and middle fingertips relative to their knuckles to decide which "mode" you're in (draw / select / idle).
4. Strokes are drawn onto a separate in-memory canvas (`paint_canvas`), which is then masked and composited on top of the live camera frame so strokes appear to float on your hand.
5. Two windows are shown: the live augmented feed, and the raw whiteboard canvas.

---

## Gestures

| Gesture | Fingers | Mode | Action |
|---|---|---|---|
| ☝️ | Index up, Middle down | **Draw** | Paints a stroke that follows your index fingertip |
| ✌️ | Index up, Middle up | **Select** | Cursor mode — hover over the top toolbar to pick a color, the eraser, or clear the canvas |
| ✊ | Neither raised | **Idle** | No drawing; stroke resets so the next draw starts fresh |
| ⌨️ `q` | — | — | Quits the application |

A "MODE: DRAW" / "MODE: SELECT" label is shown in the bottom-left of the video window so you always know your current state.

### Toolbar (top of the video window)
| Button | Effect |
|---|---|
| CLEAR | Wipes the canvas |
| BLUE / GREEN / RED | Switches the active brush color |
| ERASER | Switches to a large black "eraser" brush |

*(Yellow is available in the color list but isn't wired to a toolbar button in the current UI — see [Known Limitations](#known-limitations).)*

---

## Precision Features

The gesture logic isn't just raw landmark comparisons — a few refinements make tracking noticeably steadier:

- **MCP-based finger detection** — "is this finger raised?" is measured against the MCP (knuckle-at-the-palm) joint rather than the closer PIP joint, giving a more stable reference point.
- **Hysteresis margin** (`FINGER_RAISE_MARGIN = 0.025`) — a small buffer added to the raised/lowered threshold so the mode doesn't flicker between Draw and Select when your finger is near the boundary.
- **Exponential smoothing** (`SMOOTHING_ALPHA = 0.5`) — the cursor position is smoothed frame-to-frame to reduce hand jitter. Lower = smoother but laggier; higher = snappier but jitterier.
- **Minimum movement threshold** (`MIN_MOVEMENT_PX = 4`) — tiny sub-pixel tremors below 4px don't register as strokes, which prevents stray dots when your hand is nearly still.
- **Anti-aliased strokes** — lines are drawn with `cv2.LINE_AA` for smoother-looking brush strokes.

---

## Tech Stack

- **Python 3**
- **OpenCV** (`opencv-python`) — video capture, drawing, frame compositing
- **MediaPipe** — hand landmark detection
- **NumPy** — canvas array operations

---

## Project Structure

```
aircanvas/
├── app.py              # Main application — capture loop, hand tracking, drawing logic
├── requirements.txt    # Python dependencies
└── README.md
```

---

## Getting Started

### Prerequisites
- Python 3.8+
- A working webcam

### Installation
```bash
pip install -r requirements.txt
```

### Run
```bash
python app.py
```

Two windows will open: the live augmented video feed and the whiteboard canvas. Press **`q`** in either window to exit.

> **Tip:** Make sure no other app (Zoom, Teams, etc.) is holding the webcam, and give yourself good, even lighting — MediaPipe's hand detection is confidence-thresholded (`min_detection_confidence=0.85`), so poor lighting can cause tracking to drop out.

---

## Known Limitations

- Only one hand is tracked at a time (`max_num_hands=1`).
- The toolbar's **YELLOW** color option exists in the `colors` list but has no corresponding button in the current UI layout — selecting it isn't currently possible via gestures.
- Canvas and video resolution are fixed at 640×480; strokes won't scale if your webcam captures at a different resolution.
- No save/export function yet — drawings are lost when the app closes.
