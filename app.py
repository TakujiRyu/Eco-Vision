import base64
import os
import cv2
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from ultralytics import YOLO
import re

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret')

# MongoDB Setup
client = MongoClient("mongodb+srv://kinchap176:SPhU1Y9DMAFJqSC2@ecovision.ahb7era.mongodb.net/?retryWrites=true&w=majority&appName=EcoVision")
db = client["EcoVision"]
users_collection = db["users"]

# YOLO Model Setup
model = YOLO("best.pt")
classNames = ["bottle", "crushed_bottle", "none"]
CRUSHED_HEIGHT_THRESHOLD = 350
confidence_threshold = 0.6

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signUp():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            email = data.get('email', '').strip().lower()
            password = data.get('password', '')
        else:
            email = request.form['email'].strip().lower()
            password = request.form['password']

        gcit_pattern = r"^[a-zA-Z0-9]+\.gcit@rub\.edu\.bt$"
        if not re.match(gcit_pattern, email):
            flash('Please use your GCIT email address (e.g., studentid.gcit@rub.edu.bt)')
            return redirect(url_for('signUp'))

        student_id = email.split('@')[0].split('.')[0]

        existing_user = users_collection.find_one({
            "$or": [{"email": email}, {"student_id": student_id}]
        })

        if existing_user:
            flash('An account with this email or student ID already exists.')
            return redirect(url_for('signUp', exists=1))  # Pass `exists=1` in URL

        hashed_password = generate_password_hash(password)
        users_collection.insert_one({
            'email': email,
            'student_id': student_id,
            'password': hashed_password,
            'scan_stats': {
                'total_bottles': 0,
                'total_points': 0,
                'last_bottle_type': '—'
            }
        })

        flash('Account created successfully! Please log in.')
        return redirect(url_for('login'))

    return render_template('signUp.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('scan'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = users_collection.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session['user'] = user['email']
            flash('Logged in successfully!')
            return redirect(url_for('scan'))
        else:
            flash('Invalid credentials. Please try again.')
            return redirect(url_for('login'))

    return render_template('login.html', logged_in=('user' in session))

@app.route('/login_qr', methods=['POST'])
def login_qr():
    data = request.get_json()
    student_id = data.get('student_id', '').strip().lower()

    if not student_id:
        return jsonify({'success': False, 'message': 'No student ID provided.'})

    # Find user by student_id
    user = users_collection.find_one({'student_id': student_id})

    if user:
        session['user'] = user['email']
        return jsonify({'success': True, 'redirect_url': url_for('scan')})
    else:
        return jsonify({'success': False, 'message': 'Student ID not found.'})

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.')
    return redirect(url_for('login', logged_out=1))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user_email=session['user'])

@app.route('/aboutUs')
def aboutUs():
    return render_template('aboutUs.html')

@app.route('/learn')
def learn():
    return render_template('learn.html')

@app.route('/contactUs')
def contactUs():
    return render_template('contactUs.html')

@app.route('/scan')
def scan():
    if 'user' not in session:
        flash('You need to be logged in to access this page.', 'warning')
        return redirect(url_for('login'))
    return render_template('scan.html')

@app.after_request
def add_header(response):
    if request.path in ['/scan', '/dashboard']:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

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
                    cls = 1  # crushed_bottle
                    total_points += 1
                else:
                    cls = 0  # bottle
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

@app.route('/user_scan_stats')
def user_scan_stats():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = users_collection.find_one({'email': session['user']}, {'_id': 0, 'scan_stats': 1})
    stats = user.get('scan_stats', {}) if user else {}
    return jsonify({
        'total_bottles': stats.get('total_bottles', 0),
        'total_points': stats.get('total_points', 0),
        'last_bottle_type': stats.get('last_bottle_type', '—')
    })

@app.route('/update_scan_data', methods=['POST'])
def update_scan_data():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    update_data = {
        'scan_stats.total_bottles': data.get('total_bottles', 0),
        'scan_stats.total_points': data.get('total_points', 0),
        'scan_stats.last_bottle_type': data.get('last_bottle_type', '—')
    }
    users_collection.update_one({'email': session['user']}, {'$set': update_data})
    return jsonify({'status': 'success'})

@app.context_processor
def inject_logged_in():
    return {'logged_in': 'user' in session}

# App Runner
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
