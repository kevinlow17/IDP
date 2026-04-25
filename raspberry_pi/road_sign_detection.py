from picamera2 import Picamera2
from libcamera import Transform
from ultralytics import YOLO
import cv2
import numpy as np
import serial
import time
import threading
from flask import Flask, Response, render_template_string

# =========================
# Flask App
# =========================
app = Flask(__name__)
latest_frame = None
roi_frame = None
frame_lock = threading.Lock()

status = {
    "left_speed": 0,
    "right_speed": 0,
    "error": 0,
    "sign": "-"
}

# =========================
# HTML 页面
# =========================
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚗 Robot Car Live</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0a0a;
            color: #fff;
            font-family: 'Courier New', monospace;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }
        h1 { font-size: 1.4rem; letter-spacing: 4px; color: #00ff88; margin-bottom: 16px; text-transform: uppercase; }
        .video-container { width: 100%; max-width: 480px; border: 2px solid #00ff88; border-radius: 8px; overflow: hidden; box-shadow: 0 0 24px #00ff8844; }
        .video-container img { width: 100%; display: block; }
        .stats { margin-top: 16px; width: 100%; max-width: 480px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .stat-box { background: #111; border: 1px solid #333; border-radius: 8px; padding: 12px; text-align: center; }
        .stat-label { font-size: 0.65rem; color: #888; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 4px; }
        .stat-value { font-size: 1.4rem; color: #00ff88; font-weight: bold; }
        .sign-box { grid-column: span 2; background: #111; border: 1px solid #333; border-radius: 8px; padding: 12px; text-align: center; }
        .sign-STOP { color: #ff4444; }
        .sign-GO   { color: #00ff88; }
        .sign-none { color: #555; }
        .dot { display: inline-block; width: 8px; height: 8px; background: #00ff88; border-radius: 50%; margin-right: 6px; animation: pulse 1s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.2; } }
    </style>
</head>
<body>
    <h1><span class="dot"></span>Robot Car Live</h1>
    <div class="video-container">
        <img src="/video_feed" alt="Camera Feed">
    </div>
    <div class="video-container" style="margin-top:10px;">
        <img src="/roi_feed" alt="ROI Feed">
    </div>
    <div class="stats">
        <div class="stat-box">
            <div class="stat-label">Left Speed</div>
            <div class="stat-value" id="left">--</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Right Speed</div>
            <div class="stat-value" id="right">--</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Lane Error</div>
            <div class="stat-value" id="error">--</div>
        </div>
        <div class="sign-box">
            <div class="stat-label">Sign Detected</div>
            <div class="stat-value" id="sign">-</div>
        </div>
    </div>
    <script>
        setInterval(() => {
            fetch('/status')
                .then(r => r.json())
                .then(d => {
                    document.getElementById('left').textContent  = d.left_speed;
                    document.getElementById('right').textContent = d.right_speed;
                    document.getElementById('error').textContent = d.error;
                    const signEl = document.getElementById('sign');
                    signEl.textContent = d.sign;
                    signEl.className = 'stat-value sign-' + (d.sign === '-' ? 'none' : d.sign);
                });
        }, 500);
    </script>
</body>
</html>
"""

# =========================
# Flask Routes
# =========================
def generate_frames():
    global latest_frame
    while True:
        with frame_lock:
            if latest_frame is None:
                continue
            frame = latest_frame.copy()
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.033)

def generate_roi():
    global roi_frame
    while True:
        if roi_frame is None:
            continue
        _, buffer = cv2.imencode('.jpg', roi_frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.033)

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/roi_feed')
def roi_feed():
    return Response(generate_roi(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def get_status():
    from flask import jsonify
    return jsonify(status)

def run_flask():
    app.run(host='0.0.0.0', port=5000, threaded=True, use_reloader=False)

# =========================
# Serial
# =========================
ser = serial.Serial('/dev/ttyUSB0', 9600)
time.sleep(2)

# =========================
# Camera
# ⭐ 提高分辨率，扩大视野
# =========================
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(
    main={"size": (480, 360)},              # ⭐ 原来320x240，提高到480x360
    transform=Transform(hflip=1, vflip=1)
))
picam2.start()

# =========================
# YOLO
# =========================
model = YOLO("road_sign_detection.pt")

print("System started")
threading.Thread(target=run_flask, daemon=True).start()

# =========================
# ⭐ 参数（提高sensitivity关键）
# =========================
# PD控制参数
Kp = 2.0        # 比例（P）
Kd = 0.8        # 微分（D），预测误差变化，防过冲
base_speed = 80
MIN_SPEED = 75
MAX_SPEED = 180

TURN_THRESHOLD = 10
PIVOT_THRESHOLD = 50

frame_count = 0
detect_counter = 0
DETECT_THRESHOLD = 3

stop_until = 0
prev_error = 0
prev_left = 0
prev_right = 0
d_error = 0     # 微分项

# ⭐ 用于记录上一次看到的车道位置（防止丢失车道）
last_left_base = None
last_right_base = None

# =========================
# Main Loop
# =========================
while True:
    frame = picam2.capture_array()
    frame = frame[:, :, :3]
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    height, width = frame.shape[:2]

    # =========================
    # ⭐ ROI 扩大：取画面下方50%（原来40%）
    # 视野更大，更早看到弯道
    # =========================
    roi_y1 = int(height * 0.45)            # ⭐ 原来0.6，现在取更多画面
    roi = frame[roi_y1:height, :]

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)   # ⭐ 增大blur减少噪点

    # ⭐ 白底黑线：用INV让黑线变白色，histogram才能找到线
    _, thresh = cv2.threshold(blur, 80, 255, cv2.THRESH_BINARY)

    # 形态学处理去噪
    kernel = np.ones((3, 3), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    # ⭐ 只取ROI底部1/3来计算histogram（离车最近，最准确）
    roi_height = thresh.shape[0]
    thresh_bottom = thresh[int(roi_height * 0.67):, :]
    histogram = np.sum(thresh_bottom, axis=0)
    midpoint = width // 2
    frame_center = width // 2

    # ⭐ 双黑线追踪：找左线右边缘 和 右线左边缘（朝向路中心）
    if histogram.max() > 500:
        # 左半边：找非零列，取最右边的 = 左黑线右边缘
        left_nonzero = np.nonzero(histogram[:midpoint])[0]
        if len(left_nonzero) > 0:
            left_base = int(left_nonzero[-1])   # 最右边的白色列
        else:
            left_base = last_left_base if last_left_base else midpoint // 2

        # 右半边：找非零列，取最左边的 = 右黑线左边缘
        right_nonzero = np.nonzero(histogram[midpoint:])[0]
        if len(right_nonzero) > 0:
            right_base = int(right_nonzero[0]) + midpoint  # 最左边的白色列
        else:
            right_base = last_right_base if last_right_base else midpoint + midpoint // 2

        last_left_base  = left_base
        last_right_base = right_base
        lane_center = (left_base + right_base) // 2
    elif last_left_base is not None:
        left_base   = last_left_base
        right_base  = last_right_base
        lane_center = (left_base + right_base) // 2
    else:
        left_base   = midpoint // 2
        right_base  = midpoint + midpoint // 2
        lane_center = midpoint

    # =========================
    # ROI Display
    # =========================
    roi_display = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
    cv2.line(roi_display, (left_base, 0),  (left_base, roi_display.shape[0]),  (255, 0, 0), 2)
    cv2.line(roi_display, (right_base, 0), (right_base, roi_display.shape[0]), (0, 255, 255), 2)
    roi_frame = roi_display.copy()

    # =========================
    # PD Error 计算
    # =========================
    raw_error = -(lane_center - frame_center)
    error     = 0.6 * prev_error + 0.4 * raw_error  # 平滑
    d_error   = error - prev_error                   # 微分项（误差变化速度）
    prev_error = error

    # =========================
    # PD 控制逻辑
    # =========================
    if abs(error) > PIVOT_THRESHOLD:
        # 极端转弯：原地pivot
        if error > 0:
            left_speed, right_speed = MAX_SPEED, -100
        else:
            left_speed, right_speed = -100, MAX_SPEED

    else:
        # PD correction：P项纠正位置，D项预测过冲
        correction = int(Kp * error + Kd * d_error * 10)

        left_speed  = base_speed - correction
        right_speed = base_speed + correction

        # 限制最大速度
        left_speed  = min(MAX_SPEED, left_speed)
        right_speed = min(MAX_SPEED, right_speed)

        # ⭐ 每个轮子独立保护：有速度就保证MIN_SPEED
        # 外轮永远不会低于MIN_SPEED
        # 内轮只有在correction极大时才会降到MIN_SPEED
        left_speed  = max(MIN_SPEED, left_speed)
        right_speed = max(MIN_SPEED, right_speed)

    # =========================
    # YOLO
    # =========================
    frame_count += 1
    detected = None

    if frame_count % 4 == 0:
        results = model(frame, imgsz=160, verbose=False)
        boxes = results[0].boxes

        if boxes is not None and len(boxes) > 0:
            best_i = boxes.conf.argmax()
            cls    = int(boxes.cls[best_i])
            conf   = float(boxes.conf[best_i])

            if conf > 0.6:
                detect_counter += 1
                if detect_counter >= DETECT_THRESHOLD:
                    detect_counter = 0
                    if cls in [0, 1]:
                        detected = "STOP"
                    elif cls == 2:
                        detected = "GO"
            else:
                detect_counter = 0
        else:
            detect_counter = 0

        annotated = results[0].plot()
    else:
        annotated = frame.copy()

    # =========================
    # STOP
    # =========================
    if detected == "STOP":
        stop_until = time.time() + 2.0

    if time.time() < stop_until:
        left_speed  = 0
        right_speed = 0

    # =========================
    # Serial
    # =========================
    if left_speed != prev_left or right_speed != prev_right:
        ser.write(f"{left_speed},{right_speed}\n".encode())
        prev_left, prev_right = left_speed, right_speed

    # =========================
    # Debug 画线
    # =========================
    y_top = roi_y1
    cv2.line(annotated, (left_base,   y_top), (left_base,   height), (255, 0, 0),   2)
    cv2.line(annotated, (right_base,  y_top), (right_base,  height), (0, 255, 255), 2)
    cv2.line(annotated, (lane_center, y_top), (lane_center, height), (0, 255, 0),   2)
    cv2.line(annotated, (frame_center,y_top), (frame_center,height), (0, 0, 255),   2)

    # ⭐ 画ROI边界线，方便调整
    cv2.line(annotated, (0, roi_y1), (width, roi_y1), (255, 255, 0), 1)

    cv2.putText(annotated, f"Err:{int(error)}",              (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0),   2)
    cv2.putText(annotated, f"L:{left_speed} R:{right_speed}",(10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0),   2)
    cv2.putText(annotated, f"Sign:{detected or '-'}",        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 2)

    # =========================
    # Flask
    # =========================
    with frame_lock:
        latest_frame = annotated.copy()

    status["left_speed"]  = left_speed
    status["right_speed"] = right_speed
    status["error"]       = int(error)
    status["sign"]        = detected or "-"

    cv2.imshow("FINAL SYSTEM", annotated)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# =========================
# Cleanup
# =========================
ser.write(b"0,0\n")
ser.close()
picam2.stop()
cv2.destroyAllWindows()


