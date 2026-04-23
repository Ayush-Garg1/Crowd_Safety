#!/usr/bin/env python3
# app/app.py
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask, render_template, Response, jsonify, send_file
import cv2
from ultralytics import YOLO
from inference.heatmap import make_heatmap
from inference.risk_analysis import analyze_risk
import threading
import time
from inference.alerts import send_email_alert
import io
from datetime import datetime, timedelta
import os
import json
import sqlite3

from config import get_settings

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

try:
    import winsound  # Windows-only
except Exception:
    winsound = None

app = Flask(__name__, template_folder=str(project_root / 'app' / 'templates'))

# Settings (loaded from .env / environment variables)
settings = get_settings()

# Use trained weights path here after training, fallback to pretrained model
MODEL_PATH = 'yolov8n.pt'
try:
    model = YOLO(str(MODEL_PATH))
except Exception:
    model = YOLO(str(project_root / 'yolov8n.pt'))  # fallback

cap = None
cap_lock = threading.Lock()

def get_capture():
    """Get (or recreate) the webcam capture safely.

    Flask debug reloader can start the app twice; lazy init avoids double-open issues.
    """
    global cap
    with cap_lock:
        if cap is not None and cap.isOpened():
            return cap
        try:
            if cap is not None:
                cap.release()
        except Exception:
            pass
        cap = cv2.VideoCapture(int(settings.camera_index))
        return cap

# Global variables for real-time data
current_data = {
    'count': 0,
    'risk_level': 'NONE',
    'avg_density': 0.0,
    'max_density': 0.0,
    'timestamp': time.time(),
    'last_email_alert': None
}
data_lock = threading.Lock()

# SQLite persistence
db_lock = threading.Lock()

def _db_connect():
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

db = _db_connect()

def init_db():
    with db_lock:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS samples (
                ts REAL NOT NULL,
                count INTEGER NOT NULL,
                risk_level TEXT NOT NULL,
                avg_density REAL NOT NULL,
                max_density REAL NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS email_alerts (
                ts REAL NOT NULL,
                count INTEGER NOT NULL,
                risk_level TEXT NOT NULL,
                recipients_json TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT
            )
            """
        )
        db.execute("CREATE INDEX IF NOT EXISTS idx_samples_ts ON samples(ts);")
        db.execute("CREATE INDEX IF NOT EXISTS idx_alerts_ts ON email_alerts(ts);")
        db.commit()

def insert_sample(row: dict):
    with db_lock:
        db.execute(
            "INSERT INTO samples(ts, count, risk_level, avg_density, max_density) VALUES (?, ?, ?, ?, ?)",
            (
                float(row.get("timestamp", time.time())),
                int(row.get("count", 0)),
                str(row.get("risk_level", "NONE")),
                float(row.get("avg_density", 0.0)),
                float(row.get("max_density", 0.0)),
            ),
        )
        db.commit()

def insert_email_alert(result: dict, risk_level: str):
    ts = float(result.get("timestamp", time.time()))
    recipients = result.get("recipients", []) if isinstance(result.get("recipients"), list) else []
    status = "sent" if result.get("sent") else ("skipped" if result.get("skipped") else "error")
    err = result.get("error")
    with db_lock:
        db.execute(
            "INSERT INTO email_alerts(ts, count, risk_level, recipients_json, status, error) VALUES (?, ?, ?, ?, ?, ?)",
            (ts, int(result.get("count", 0)), str(risk_level), json.dumps(recipients), status, err),
        )
        db.commit()

# Local (server-side) audible alarm: triggers automatically on HIGH.
last_alarm_time = 0.0
ALARM_COOLDOWN_SECONDS = 3.0

def _play_local_alarm_pattern():
    """Non-blocking-ish alarm pattern for Windows."""
    if winsound is None:
        return
    # Short siren-like 2-tone pattern (~0.6s)
    try:
        winsound.Beep(880, 220)
        winsound.Beep(660, 220)
        winsound.Beep(880, 220)
    except Exception:
        # If Beep fails (permissions/driver), ignore.
        pass

def trigger_local_alarm():
    """Rate-limited local alarm trigger."""
    global last_alarm_time
    now = time.time()
    if now - last_alarm_time < ALARM_COOLDOWN_SECONDS:
        return
    last_alarm_time = now
    threading.Thread(target=_play_local_alarm_pattern, daemon=True).start()

def _history_sampler():
    """Background sampler for report generation."""
    while True:
        with data_lock:
            snap = dict(current_data)

        snap["timestamp"] = float(snap.get("timestamp", time.time()))
        try:
            insert_sample(snap)
        except Exception:
            pass

        time.sleep(int(settings.sample_seconds))

def _build_report_pdf(title: str, period_label: str, rows: list[dict]) -> io.BytesIO:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
        title=title,
    )

    styles = getSampleStyleSheet()
    story = []

    brand = Table([[f"{title}", datetime.now().strftime("%b %d, %Y  %H:%M")]], colWidths=[360, 140])
    brand.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0B1220")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, 0), "Helvetica"),
                ("FONTSIZE", (0, 0), (0, 0), 14),
                ("FONTSIZE", (1, 0), (1, 0), 9),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(brand)
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"<font color='#6B7280'>{period_label}</font>", styles["Normal"]))
    story.append(Spacer(1, 12))

    if rows:
        counts = [int(r.get("count", 0)) for r in rows]
        max_count = max(counts) if counts else 0
        avg_count = (sum(counts) / len(counts)) if counts else 0.0
        high_events = sum(1 for r in rows if str(r.get("risk_level", "")).upper() == "HIGH")
        med_events = sum(1 for r in rows if str(r.get("risk_level", "")).upper() == "MEDIUM")
        low_events = sum(1 for r in rows if str(r.get("risk_level", "")).upper() == "LOW")
        none_events = sum(1 for r in rows if str(r.get("risk_level", "")).upper() == "NONE")

        # At-a-glance KPIs
        kpi_data = [
            ["AVG PEOPLE", "PEAK", "HIGH EVENTS", "SAMPLES"],
            [f"{avg_count:.1f}", f"{max_count}", f"{high_events}", f"{len(rows)}"],
        ]
        kpi = Table(kpi_data, colWidths=[120, 100, 120, 100])
        kpi.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#F9FAFB")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#FFF7ED")),
                    ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#0B1220")),
                    ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 1), (-1, 1), 14),
                    ("ALIGN", (0, 1), (-1, 1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(kpi)
        story.append(Spacer(1, 10))

        story.append(
            Paragraph(
                f"<b>Risk distribution:</b> HIGH <b>{high_events}</b> • MEDIUM <b>{med_events}</b> • LOW <b>{low_events}</b> • NONE <b>{none_events}</b>",
                styles["BodyText"],
            )
        )
        story.append(
            Paragraph(
                "<font color='#6B7280'>Tip: Use <b>Peak</b> + <b>HIGH events</b> to assess crowd pressure at a glance.</font>",
                styles["BodyText"],
            )
        )
        story.append(Spacer(1, 12))
    else:
        story.append(Paragraph("No data captured yet. Keep the dashboard running to collect samples.", styles["BodyText"]))
        story.append(Spacer(1, 12))

    # Notable moments (top peaks)
    if rows:
        peaks = sorted(
            rows,
            key=lambda r: (int(r.get("count", 0)), str(r.get("risk_level", ""))),
            reverse=True,
        )[:5]
        peak_table = [["Top moments (highest counts)", "", "", ""]]
        peak_table.append(["Time", "People", "Risk", "Max density"])
        for r in peaks:
            ts = datetime.fromtimestamp(float(r.get("timestamp", time.time()))).strftime("%Y-%m-%d %H:%M:%S")
            peak_table.append([ts, str(r.get("count", 0)), str(r.get("risk_level", "NONE")), f"{float(r.get('max_density', 0.0)):.2f}"])
        pt = Table(peak_table, colWidths=[220, 60, 70, 95])
        pt.setStyle(
            TableStyle(
                [
                    ("SPAN", (0, 0), (-1, 0)),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0EA5E9")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#0B1220")),
                    ("TEXTCOLOR", (0, 1), (-1, 1), colors.white),
                    ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 1), (-1, 1), 9),
                    ("ALIGN", (1, 2), (-1, -1), "CENTER"),
                    ("GRID", (0, 1), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
                    ("ROWBACKGROUNDS", (0, 2), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(pt)
        story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Detailed samples (most recent)</b>", styles["BodyText"]))
    story.append(Spacer(1, 6))
    table_data = [["Time", "People", "Risk", "Avg density", "Max density"]]
    for r in rows[-60:]:  # keep it readable: last 60 samples
        ts = datetime.fromtimestamp(float(r.get("timestamp", time.time()))).strftime("%Y-%m-%d %H:%M:%S")
        table_data.append(
            [
                ts,
                str(r.get("count", 0)),
                str(r.get("risk_level", "NONE")),
                f"{float(r.get('avg_density', 0.0)):.2f}",
                f"{float(r.get('max_density', 0.0)):.2f}",
            ]
        )

    tbl = Table(table_data, colWidths=[150, 55, 60, 90, 90])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1220")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                ("TOPPADDING", (0, 0), (-1, 0), 10),
            ]
        )
    )

    story.append(tbl)
    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "<font color='#6B7280'>Generated by Crowd Monitor • This report summarizes sampled detections (every 10s while the app is running).</font>",
            styles["Normal"],
        )
    )

    doc.build(story)
    buf.seek(0)
    return buf

def gen_frames():
    global current_data
    while True:
        local_cap = get_capture()
        success, frame = local_cap.read()
        if not success:
            # camera might be temporarily unavailable; wait and retry
            time.sleep(0.2)
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

        email_result = None
        if risk_level == "HIGH":
            print("🔥 HIGH RISK DETECTED")
            email_result = send_email_alert(count)
            trigger_local_alarm()
            if isinstance(email_result, dict) and (email_result.get("sent") or email_result.get("skipped") or email_result.get("error")):
                try:
                    insert_email_alert(email_result, risk_level)
                except Exception:
                    pass
        
        # Update global data for API
        with data_lock:
            current_data = {
                'count': count,
                'risk_level': risk_level,
                'avg_density': risk_data['avg_density'],
                'max_density': risk_data['max_density'],
                'timestamp': time.time(),
                'last_email_alert': (email_result if (risk_level == "HIGH" and isinstance(email_result, dict) and email_result.get("sent")) else current_data.get("last_email_alert"))
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

@app.route('/report/daily')
def report_daily():
    now = datetime.now()
    cutoff = now - timedelta(days=1)
    with db_lock:
        cur = db.execute(
            "SELECT ts, count, risk_level, avg_density, max_density FROM samples WHERE ts >= ? ORDER BY ts ASC",
            (cutoff.timestamp(),),
        )
        rows = [
            {"timestamp": r[0], "count": r[1], "risk_level": r[2], "avg_density": r[3], "max_density": r[4]}
            for r in cur.fetchall()
        ]
    title = "Crowd Monitor — Daily Report"
    period = f"Period: last 24 hours • Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}"
    pdf = _build_report_pdf(title, period, rows)
    filename = f"crowd_daily_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(pdf, mimetype="application/pdf", as_attachment=True, download_name=filename)

@app.route('/report/weekly')
def report_weekly():
    now = datetime.now()
    cutoff = now - timedelta(days=7)
    with db_lock:
        cur = db.execute(
            "SELECT ts, count, risk_level, avg_density, max_density FROM samples WHERE ts >= ? ORDER BY ts ASC",
            (cutoff.timestamp(),),
        )
        rows = [
            {"timestamp": r[0], "count": r[1], "risk_level": r[2], "avg_density": r[3], "max_density": r[4]}
            for r in cur.fetchall()
        ]
    title = "Crowd Monitor — Weekly Report"
    period = f"Period: last 7 days • Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}"
    pdf = _build_report_pdf(title, period, rows)
    filename = f"crowd_weekly_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(pdf, mimetype="application/pdf", as_attachment=True, download_name=filename)

if __name__ == '__main__':
    settings = get_settings()
    init_db()
    threading.Thread(target=_history_sampler, daemon=True).start()
    # Disable the reloader to prevent double-opening the camera on restart.
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
