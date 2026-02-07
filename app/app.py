#!/usr/bin/env python3
# app/app.py
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask, render_template, Response, jsonify
import cv2
from ultralytics import YOLO
from inference.heatmap import make_heatmap
from inference.risk_analysis import analyze_risk
import threading
import time
from inference.alerts import send_email_alert

app = Flask(__name__, template_folder=str(project_root / 'app' / 'templates'))

# Use trained weights path here after training, fallback to pretrained model
MODEL_PATH = 'yolov8n.pt'
try:
    model = YOLO(str(MODEL_PATH))
except Exception:
    model = YOLO(str(project_root / 'yolov8n.pt'))  # fallback

cap = cv2.VideoCapture(0)

# Global variables for real-time data
current_data = {
    'count': 0,
    'risk_level': 'NONE',
    'avg_density': 0.0,
    'max_density': 0.0,
    'timestamp': time.time()
}
data_lock = threading.Lock()

def gen_frames():
    global current_data
    while True:
        success, frame = cap.read()
        if not success:
            break
        results = model(frame, imgsz=640)
        persons = []
        for r in results:
            for box in r.boxes:
                if int(box.cls[0]) == 0:
                    x1,y1,x2,y2 = map(int, box.xyxy[0])
                    persons.append((x1,y1,x2,y2))
                    cv2.rectangle(frame, (x1,y1),(x2,y2),(0,255,0),2)
        
        # Enhanced risk analysis
        h, w = frame.shape[:2]
        risk_data = analyze_risk(persons, w, h)
        risk_level = risk_data['level']
        count = risk_data['count']

        if risk_level == "HIGH":
            print("🔥 HIGH RISK DETECTED")
            send_email_alert(count)
        
        # Update global data for API
        with data_lock:
            current_data = {
                'count': count,
                'risk_level': risk_level,
                'avg_density': risk_data['avg_density'],
                'max_density': risk_data['max_density'],
                'timestamp': time.time()
            }
        
        # Color coding based on risk level
        if risk_level == 'HIGH':
            risk_color = (0, 0, 255)  # Red
        elif risk_level == 'MEDIUM':
            risk_color = (0, 165, 255)  # Orange
        elif risk_level == 'NONE':
            risk_color = (128, 128, 128)  # Gray
        else:
            risk_color = (0, 255, 0)  # Green
        
        heatmap_img = make_heatmap(frame, persons, grid=(3,3))
        overlay = cv2.addWeighted(frame, 0.7, heatmap_img, 0.3, 0)
        
        # Display risk information
        text = f"Count: {count} | Risk: {risk_level}"
        if risk_data['max_density'] > 0:
            text += f" | Density: {risk_data['max_density']:.1f}"
        cv2.putText(overlay, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, risk_color, 2)

        ret, buffer = cv2.imencode('.jpg', overlay)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video')
def video():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/data')
def get_data():
    """API endpoint to get current crowd data"""
    with data_lock:
        return jsonify(current_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
