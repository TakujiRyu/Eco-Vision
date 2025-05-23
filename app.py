from flask import Flask, render_template, Response
import cv2
import time
import cvzone
from ultralytics import YOLO

app = Flask(__name__)

# Load model
model = YOLO("best.pt")
confidence_threshold = 0.6
CRUSHED_HEIGHT_THRESHOLD = 350

# Class names and point mapping
classNames = ["bottle", "crushed_bottle", "none"]
points_map = {"bottle": 2, "crushed_bottle": 1}
total_points = 0
cooldown_active = False
cooldown_duration = 3  # seconds
last_detection_time = 0


def generate_frames():
    global total_points, cooldown_active, last_detection_time

    cap = cv2.VideoCapture(0)
    cap.set(3, 640)
    cap.set(4, 480)

    while True:
        success, img = cap.read()
        if not success:
            break

        current_time = time.time()
        results = model(img, stream=True, verbose=False)

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                w, h = x2 - x1, y2 - y1
                conf = float(box.conf[0])
                if conf < confidence_threshold:
                    continue

                # Determine class
                if h < CRUSHED_HEIGHT_THRESHOLD:
                    cls = 1
                else:
                    cls = 0

                label = classNames[cls]
                color = (0, 255, 0) if label == "bottle" else (255, 165, 0)

                # Draw box
                cvzone.cornerRect(img, (x1, y1, w, h), colorC=color, colorR=color)
                cvzone.putTextRect(
                    img,
                    f'{label.upper()} {int(conf * 100)}%',
                    (max(0, x1), max(35, y1)),
                    scale=1.5,
                    thickness=2,
                    colorR=color,
                    colorB=color
                )

                # Add points if cooldown is off
                if not cooldown_active:
                    total_points += points_map[label]
                    cooldown_active = True
                    last_detection_time = current_time

        # Cooldown timer
        if cooldown_active and (current_time - last_detection_time > cooldown_duration):
            cooldown_active = False

        # Display total points
        cv2.putText(
            img,
            f"Total Points: {total_points}",
            (10, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 255, 255),
            3
        )

        # Encode image to stream
        ret, buffer = cv2.imencode('.jpg', img)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video')
def video():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(debug=True)
