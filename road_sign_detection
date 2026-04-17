from picamera2 import Picamera2
from ultralytics import YOLO
import cv2
import serial
import time

# =========================
# Serial
# =========================
ser = serial.Serial('/dev/ttyUSB0', 9600)
time.sleep(2)

# =========================
# Camera
# =========================
picam2 = Picamera2()
picam2.start()

# =========================
# YOLO
# =========================
model = YOLO("road_sign_detection.pt")

print("System started")

last_command = None
detect_counter = 0
DETECT_THRESHOLD = 3   

# =========================
# Main
# =========================
while True:
    frame = picam2.capture_array()

    frame = frame[:, :, :3]

    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    # YOLO
    results = model(frame, imgsz=320)

    boxes = results[0].boxes

    command = None

    # =========================
    # Detection + Decision
    # =========================
    if boxes is not None and len(boxes) > 0:
        best_i = boxes.conf.argmax()

        cls = int(boxes.cls[best_i])
        confidence = float(boxes.conf[best_i])

        if confidence > 0.6:
            detect_counter += 1

            if detect_counter >= DETECT_THRESHOLD:
                if cls == 0:   # STOP
                    command = 'S'
                elif cls == 1: # RED
                    command = 'S'
                elif cls == 2: # GREEN
                    command = 'F'
        else:
            detect_counter = 0

    else:
        detect_counter = 0

    # =========================
    # Default decision
    # =========================
    if command is None:
        command = 'F'

    # =========================
    # Only send the command when the command changes
    # =========================
    if command != last_command:
        print("Send:", command)
        ser.write(command.encode())
        last_command = command

    # =========================
    # Show camera
    # =========================
    annotated = results[0].plot()
    cv2.imshow("YOLO Pi", annotated)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()






