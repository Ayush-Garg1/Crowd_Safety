# app/app.py
from flask import Flask, render_template, Response
import cv2
from ultralytics import YOLO
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from inference.heatmap import make_heatmap

app = Flask(__name__)
model = YOLO('../runs/detect/crowd_merged/weights/best.pt')
cap = cv2.VideoCapture(0)

def gen_frames():
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
        count = len(persons)
        risk = 'LOW' if count<20 else ('MEDIUM' if count<40 else 'HIGH')
        heatmap_img = make_heatmap(frame, persons, grid=(3,3))
        overlay = cv2.addWeighted(frame, 0.7, heatmap_img, 0.3, 0)
        cv2.putText(overlay, f"Count: {count} | Risk: {risk}", (20,40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255),2)

        ret, buffer = cv2.imencode('.jpg', overlay)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video')
def video():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
