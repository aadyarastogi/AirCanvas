"""
AirCanvas - Virtual Augmented Reality Painting Studio

Controls:
- Draw:         Raise ONLY your Index Finger
- Select Color: Raise Index + Middle Fingers, hover over header buttons
- Clear Canvas: Hover over CLEAR button
- Exit:         Press 'Q'
"""

import cv2
import numpy as np
import mediapipe as mp
import math  # NEW — needed for math.hypot in min-movement check

#1. MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.85, min_tracking_confidence=0.8)
mp_draw = mp.solutions.drawing_utils

#2. Colors, brush sizes, canvas
colors = [
    (255, 0, 0),    # Blue
    (0, 255, 0),    # Green
    (0, 0, 255),    # Red
    (0, 255, 255),  # Yellow
    (0, 0, 0)       # Black (Eraser)
]
color_index = 0
brush_size  = 5
eraser_size = 30
prev_point  = None

paint_canvas = np.zeros((480, 640, 3), dtype=np.uint8)

#Precision constants
SMOOTHING_ALPHA     = 0.5    # 0.3 = smoother/laggier | 0.7 = snappier/jitterier
MIN_MOVEMENT_PX     = 4      # ignore moves < 4px → kills tremor dots
FINGER_RAISE_MARGIN = 0.025  # buffer before finger counted as "raised" → stops mode flicker
smooth_cx, smooth_cy = 0, 0  # smoothed cursor state

#3. Buttons 
buttons = [
    {"area": (40,  10, 140, 70), "label": "CLEAR",  "color": (120, 120, 120)},
    {"area": (160, 10, 260, 70), "label": "BLUE",   "color": (255,   0,   0)},
    {"area": (280, 10, 380, 70), "label": "GREEN",  "color": (  0, 255,   0)},
    {"area": (400, 10, 500, 70), "label": "RED",    "color": (  0,   0, 255)},
    {"area": (520, 10, 620, 70), "label": "ERASER", "color": (200, 200, 200)},
]

#4. Webcam 
cap = cv2.VideoCapture(0)

print("--------------------------------------------------")
print("AirCanvas Pro launched!")
print("- Stand in front of your webcam.")
print("- Raise index finger to draw.")
print("- Raise index & middle fingers to select colors.")
print("- Press 'q' inside the webcam window to exit.")
print("--------------------------------------------------")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read frame from webcam.")
        break

   
    frame = cv2.flip(frame, 1)
    h, w, c = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb_frame)

    # A. Draw Virtual Buttons 
    for btn in buttons:
        cv2.rectangle(frame, (btn["area"][0], btn["area"][1]),
                              (btn["area"][2], btn["area"][3]), btn["color"], cv2.FILLED)
        cv2.putText(frame, btn["label"],
                    (btn["area"][0] + 12, btn["area"][1] + 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # B. Process Hand Landmarks
    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:
            landmarks = hand_landmarks.landmark

            # Index Finger Tip
            index_tip = landmarks[8]
            # NEW PRECISION: MCP (#5) instead of PIP (#6) — stabler "finger up" base
            index_mcp = landmarks[5]

            raw_cx = int(index_tip.x * w)
            raw_cy = int(index_tip.y * h)

            #PRECISION: Exponential smoothing → reduces hand jitter
            smooth_cx = int(SMOOTHING_ALPHA * raw_cx + (1 - SMOOTHING_ALPHA) * smooth_cx)
            smooth_cy = int(SMOOTHING_ALPHA * raw_cy + (1 - SMOOTHING_ALPHA) * smooth_cy)
            cx, cy = smooth_cx, smooth_cy

            # Middle Finger Tip 
            middle_tip = landmarks[12]
            # NEW PRECISION: MCP (#9) instead of PIP (#10)
            middle_mcp = landmarks[9]
            mx, my = int(middle_tip.x * w), int(middle_tip.y * h)

            # NEW PRECISION: Hysteresis margin → stops Selection↔Draw mode flicker
            index_raised  = index_tip.y  < index_mcp.y  - FINGER_RAISE_MARGIN
            middle_raised = middle_tip.y < middle_mcp.y - FINGER_RAISE_MARGIN

            # Case 1: SELECTION MODE 
            if index_raised and middle_raised:
                prev_point = None
                cv2.circle(frame, (cx, cy), 10, (255, 255, 255), cv2.FILLED)

                if cy < 70:
                    if 40 <= cx <= 140:
                        paint_canvas = np.zeros((480, 640, 3), dtype=np.uint8)
                    elif 160 <= cx <= 260:
                        color_index = 0
                    elif 280 <= cx <= 380:
                        color_index = 1
                    elif 400 <= cx <= 500:
                        color_index = 2
                    elif 520 <= cx <= 620:
                        color_index = 4

                #PRECISION: mode label
                cv2.putText(frame, "MODE: SELECT", (10, 460),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # Case 2: DRAWING MODE
            elif index_raised and not middle_raised:
                active_color = colors[color_index]
                size = brush_size if color_index != 4 else eraser_size

                cv2.circle(frame, (cx, cy), size, active_color, cv2.FILLED)  # UNCHANGED

                if prev_point is None:
                    prev_point = (cx, cy)

                #PRECISION: only draw if moved MIN_MOVEMENT_PX pixels → no tremor dots
                dist = math.hypot(cx - prev_point[0], cy - prev_point[1])
                if dist >= MIN_MOVEMENT_PX:
                    #PRECISION: cv2.LINE_AA → anti-aliased smooth strokes
                    cv2.line(paint_canvas, prev_point, (cx, cy),
                             active_color, size, lineType=cv2.LINE_AA)
                    prev_point = (cx, cy)

                #PRECISION: mode label
                cv2.putText(frame, "MODE: DRAW", (10, 460),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, active_color, 2)

            # Case 3: No gesture 
            else:
                prev_point = None

          
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

    else:
        prev_point = None  

    # C. Overlay drawings on camera feed
    gray_canvas = cv2.cvtColor(paint_canvas, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray_canvas, 10, 255, cv2.THRESH_BINARY)
    mask_inv = cv2.bitwise_not(mask)
    img_bg = cv2.bitwise_and(frame, frame, mask=mask_inv)
    img_fg = cv2.bitwise_and(paint_canvas, paint_canvas, mask=mask)
    augmented_frame = cv2.add(img_bg, img_fg)

    # D. Display Windows
    cv2.imshow("AirCanvas Pro - Live Video Feed", augmented_frame)
    cv2.imshow("AirCanvas Pro - Whiteboard Canvas", paint_canvas)

    if cv2.waitKey(1) & 0xFF == ord('q'):  
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
print("AirCanvas Pro closed successfully.")