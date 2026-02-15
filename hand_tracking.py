import mediapipe as mp
import cv2

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands
hand = mp_hands.Hands()

while True:
    success, frame = cap.read()
    if success:
        RGB_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hand.process(RGB_frame)
        if result.multi_hand_landmarks:
            for hand_landmarks in result.multi_hand_landmarks:
                print(hand_landmarks)
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        # to add translucent elements onto the frame, we need to blend a frame with a copy of itself that contains the translucent elements
        # we can use the cv2.addWeighted() function to blend the two frames together
        # these elements are just examples, you can add any cv2 functions on the overlay frame
        overlay = frame.copy()
        overlay_alpha = 0.5

        cv2.rectangle(overlay, (420, 205), (595, 385), (0, 0, 255), -1)
        cv2.putText(overlay, f"Text example, alpha={overlay_alpha}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
        cv2.addWeighted(overlay, overlay_alpha, frame, 1 - overlay_alpha, 0, frame)

        cv2.imshow("capture image", frame)
        if cv2.waitKey(1) == ord('q'):
            break

cv2.destroyAllWindows()
