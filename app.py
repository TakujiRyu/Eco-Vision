import base64
from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
from ultralytics import YOLO
import os

app = Flask(__name__)
model = YOLO("best.pt")

classNames = ["bottle", "crushed_bottle", "none"]
CRUSHED_HEIGHT_THRESHOLD = 350
confidence_threshold = 0.6

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signUp')
def signUp():
    return render_template('signUp.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/aboutUs')
def aboutUs():
    return render_template('aboutUs.html')

@app.route('/learn')
def learn():
    return render_template('learn.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/contactUs')
def contactUs():
    return render_template('contactUs.html')

@app.route('/scan')
def scan():
    return render_template('scan.html')

@app.route('/detect', methods=['POST'])
def detect():
    try:
        data = request.json['image']
        img_data = data.split(',')[1]
        img_bytes = base64.b64decode(img_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        total_points = 0
        detections = []

        results = model(img, stream=True, verbose=False)

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                if conf < confidence_threshold:
                    continue

                h = y2 - y1
                if h < CRUSHED_HEIGHT_THRESHOLD:
                    cls = 1
                    total_points += 1
                else:
                    cls = 0
                    total_points += 2

                label = classNames[cls]
                color = [0, 255, 0] if label == "bottle" else [255, 165, 0]

                detections.append({
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "label": label,
                    "color": color
                })

        return jsonify({'points': total_points, 'detections': detections})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
