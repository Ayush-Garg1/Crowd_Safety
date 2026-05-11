import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ultralytics import YOLO
import cv2
from heatmap import make_heatmap
from arduino_sender import send_risk_to_arduino
from alerts import send_email_alert
from risk_analysis import analyze_risk

# ── Room setup prompt ──
print("=== Crowd Monitor Setup ===")
print("Enter room dimensions (in metres) or total area.")
choice = input("Do you want to enter [1] Length x Width  or  [2] Direct area? (1/2): ").strip()

if choice == "1":
    length = float(input("Enter room length (m): "))
    width  = float(input("Enter room width  (m): "))
    room_area_m2 = length * width
else:
    room_area_m2 = float(input("Enter room area (m²): "))

print(f"✅ Room area set to {room_area_m2} m²\n")
# ──────────────────────

MODEL_PATH = "yolov8n.pt"
model = YOLO(MODEL_PATH)
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, imgsz=640, conf=0.3)
    persons = []
    for r in results:
        if r.boxes is None:
            continue
        for box in r.boxes:
            if int(box.cls[0]) == 0:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                persons.append((x1, y1, x2, y2))
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    h, w = frame.shape[:2]
    result = analyze_risk(persons, w, h, room_area_m2)
    count   = result["count"]
    risk    = result["level"]
    density = result["density"]

    if risk == "HIGH":
        print(f"🔥 HIGH RISK — {count} people, {density} p/m²")
        send_email_alert(count)

    heatmap_img = make_heatmap(frame, persons, grid=(3, 3))
    overlay = cv2.addWeighted(frame, 0.7, heatmap_img, 0.3, 0)

    cv2.putText(overlay, f"Count: {count} | Density: {density}/m2 | Risk: {risk}",
                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    cv2.imshow("Crowd Monitor", overlay)
    send_risk_to_arduino(risk)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()