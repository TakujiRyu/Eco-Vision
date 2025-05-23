from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import base64
from ultralytics import YOLO
import time
import os

app = Flask(__name__)
model = YOLO("best.pt")

classNames = ["bottle", "crushed_bottle", "none"]
CRUSHED_HEIGHT_THRESHOLD = 350
confidence_threshold = 0.6

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/detect', methods=['POST'])
def detect():
    try:
        data = request.json['image']
        img_data = base64.b64decode(data.split(',')[1])
        np_arr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        total_points = 0

        results = model(img, stream=True, verbose=False)

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                w, h = x2 - x1, y2 - y1
                conf = float(box.conf[0])
                if conf < confidence_threshold:
                    continue

                if h < CRUSHED_HEIGHT_THRESHOLD:
                    cls = 1
                    total_points += 1
                else:
                    cls = 0
                    total_points += 2

                label = classNames[cls]
                color = (0, 255, 0) if label == "bottle" else (255, 165, 0)

                cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
                cv2.putText(img, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        _, buffer = cv2.imencode('.jpg', img)
        result_img = base64.b64encode(buffer).decode('utf-8')
        return jsonify({'points': total_points, 'image': f"data:image/jpeg;base64,{result_img}"})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
