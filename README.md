# 🧠 Crowd Monitoring and Alert System using YOLOv8

> An AI-powered real-time surveillance solution that detects people in a video stream, analyzes crowd density, generates heatmaps, and automatically sends alerts when crowd levels exceed predefined thresholds.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-Web%20App-black?logo=flask)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-purple)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-green?logo=opencv)
![Arduino](https://img.shields.io/badge/Arduino-IoT-teal?logo=arduino)

---

## 👥 Team

| Name | GitHub |
|------|--------|
| Ayush Nainwal | [@Ayush-nain](https://github.com/Ayush-nain) |
| Mayank Chandel | [@Mayank89544](https://github.com/Mayank89544) |
| Himanshu Negi | [@Himanshu-Negi08](https://github.com/Himanshu-Negi08) |
| Ayush Garg | [@Ayush-Garg1](https://github.com/Ayush-Garg1) |

---

## 📌 Overview

The **Crowd Monitoring and Alert System** integrates deep learning, computer vision, and automated notification mechanisms to provide an intelligent crowd management solution suitable for:

- 🏙️ Smart cities
- 🚨 Public safety monitoring
- 🎪 Large-scale event management

---

## 🎯 Objectives

- Detect people in real-time using **YOLOv8**
- Count individuals and analyze crowd density
- Classify risk levels dynamically (Safe → Caution → High Risk → Critical)
- Visualize crowd distribution using **heatmaps**
- Trigger automated **email alerts** via SMTP when thresholds are exceeded
- Support **IoT integration** via Arduino for physical alerting

---

## 🏗️ System Architecture

```
Video Input (Webcam / File / IP Camera)
        ↓
YOLOv8 Person Detection
        ↓
Crowd Count & Density Analysis
        ↓
Heatmap Overlay (OpenCV)
        ↓
Risk Level Classification
        ↓
Flask Web Dashboard  ──→  Email Alert (SMTP)
                     ──→  Arduino IoT (Serial)
```

---

## ⚙️ Technologies Used

| Technology | Package | Purpose |
|------------|---------|---------|
| Deep Learning | `ultralytics` | YOLOv8 person detection |
| Computer Vision | `opencv-python` | Frame processing & heatmap rendering |
| Web Framework | `flask` | Dashboard UI & video stream |
| Numerical Ops | `numpy` | Heatmap accumulation |
| Scientific Utils | `scipy` | Density calculations |
| Image Processing | `Pillow` | Image manipulation & snapshots |
| Config Management | `python-dotenv` | Loads `.env` for secrets |
| PDF Reports | `reportlab` | Downloadable crowd reports |
| IoT Serial | `pyserial` | Arduino communication |
| Config Files | `pyyaml` | YAML threshold configs |
| Email Alerts | `smtplib` | Built-in Python SMTP |

---

## 📂 Project Structure

```
Crowd_Safety/
├── app/                        ← Flask web application
│   ├── app.py                  ← Entry point (run this)
│   ├── templates/              ← HTML pages (dashboard, alerts, settings)
│   └── static/                 ← CSS, JS, assets
├── aurdino/                    ← Arduino C++ sketch
│   └── crowd_alert.ino
├── data/                       ← Sample images/videos for testing
├── inference/                  ← Standalone detection scripts
├── runs/detect/                ← YOLOv8 output (auto-generated)
├── scripts/                    ← Utility scripts
├── train/                      ← Model training configs
├── yolov8n.pt                  ← Pre-trained model weights (included)
├── requirements.txt
├── .env                        ← Your local config (NOT committed to git)
└── README.md
```

---

## 🚀 Setup & Run Guide

### Prerequisites

- Python 3.8 – 3.11
- Git
- A webcam or video file
- A Gmail account (for email alerts)
- Arduino Uno *(optional, for IoT alerts)*

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/Ayush-Garg1/Crowd_Safety.git
cd Crowd_Safety
```

---

### Step 2 — Create a Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

> You should see `(venv)` at the start of your terminal prompt.

---

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

> ✅ The `yolov8n.pt` model file is **already included** in the repo — no separate download needed.

---

### Step 4 — Create the `.env` File

Create a file named `.env` in the **root of the repository** (same folder as `requirements.txt`):

```env
# Email Alert Settings
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=abcd efgh ijkl mnop
EMAIL_RECEIVER=receiver@example.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Crowd Thresholds
THRESHOLD_LOW=10
THRESHOLD_MEDIUM=25
THRESHOLD_HIGH=50

# Video Source (0 = webcam, or path to video file)
CAMERA_SOURCE=0

# Arduino (optional)
ARDUINO_PORT=COM3
ARDUINO_BAUD=9600
ARDUINO_ENABLED=False

# Flask
FLASK_DEBUG=False
FLASK_PORT=5000
```

> ⚠️ **Never commit `.env` to GitHub.** It is already listed in `.gitignore`.

---

### Step 5 — Generate a Gmail App Password

Standard Gmail passwords do **not** work with SMTP. You need an App Password:

1. Go to [myaccount.google.com](https://myaccount.google.com) → **Security**
2. Enable **2-Step Verification** (required)
3. Search for **App Passwords** in the search bar
4. Select `Mail` → `Other` → name it `CrowdSafety`
5. Copy the **16-character password** and paste it into `EMAIL_PASSWORD` in your `.env`

---

### Step 6 — Run the Application

```bash
cd app
python app.py
```

Then open your browser at:

```
http://localhost:5000
```

---

## 🖥️ Web Dashboard Features

| Feature | Description |
|---------|-------------|
| 📹 Live Video Feed | Real-time stream with YOLOv8 bounding boxes |
| 🔢 Person Count | Live count of detected individuals per frame |
| 🚦 Risk Level Badge | Color-coded: Safe / Caution / High Risk / Critical |
| 🌡️ Heatmap Overlay | Density map showing crowd concentration over time |
| 📧 Alert History | Log of past email alerts with timestamps |
| 📄 PDF Reports | Downloadable crowd reports via reportlab |
| ⚙️ Settings Page | Configure thresholds & camera source from browser |

---

## ⚠️ Crowd Risk Levels

| Level | People Count | Indicator | Action |
|-------|-------------|-----------|--------|
| ✅ Safe | 0 – 10 | 🟢 Green | No action |
| ⚠️ Caution | 11 – 25 | 🟡 Yellow | Monitor closely |
| 🔶 High Risk | 26 – 50 | 🟠 Orange | Prepare response |
| 🚨 Critical | 51+ | 🔴 Red | Email alert + Arduino trigger |

---

## 🔌 Arduino IoT Setup (Optional)

Upload the sketch from the `aurdino/` folder to your Arduino Uno using the Arduino IDE.

```cpp
// crowd_alert.ino
const int RED_LED   = 13;
const int GREEN_LED = 12;
const int BUZZER    = 11;

void setup() {
  Serial.begin(9600);
  pinMode(RED_LED,   OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(BUZZER,    OUTPUT);
}

void loop() {
  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == 'A') {           // Alert: Critical crowd
      digitalWrite(RED_LED,   HIGH);
      digitalWrite(GREEN_LED, LOW);
      tone(BUZZER, 1000, 500);
    } else if (cmd == 'S') {   // Safe
      digitalWrite(RED_LED,   LOW);
      digitalWrite(GREEN_LED, HIGH);
      noTone(BUZZER);
    }
  }
}
```

After uploading, set `ARDUINO_ENABLED=True` and your correct `ARDUINO_PORT` in `.env`.

---


## 🔮 Future Scope

- 🌐 Multi-camera support with aggregated crowd analysis
- 📊 Historical analytics with database logging (SQLite / PostgreSQL)
- 📱 SMS & push notification alerts via Twilio / Firebase
- 🗺️ Zone-based monitoring (divide frame into regions)
- 🚦 Crowd flow direction analysis using optical flow
- 🔗 REST API integration with city emergency response systems

---

## 📄 License

This project is licensed under the terms in the [License](./License) file.

---

<div align="center">
  <sub>Built with ❤️ by Ayush Nainwal, Himanshu Negi, Mayank Chandel & Ayush Garg</sub>
</div>