import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import time
from config import get_settings

LAST_ALERT_TIME = 0

def send_email_alert(count):
    global LAST_ALERT_TIME

    s = get_settings()

    if time.time() - LAST_ALERT_TIME < int(s.email_cooldown_seconds):
        print("⏳ Alert skipped (cooldown)")
        return {"sent": False, "skipped": True, "reason": "cooldown"}

    LAST_ALERT_TIME = time.time()

    sender = s.email_sender
    password = s.email_password.replace("_", " ")
    receivers = s.email_recipients
    

    if not sender or not password or not receivers:
        return {
            "sent": False,
            "skipped": False,
            "error": "Email is not configured. Set CM_EMAIL_SENDER, CM_EMAIL_PASSWORD, CM_EMAIL_RECIPIENTS.",
        }

    print("📧 Trying to send email...")

    # Timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    subject = "Crowd Monitor — High Crowd Risk Detected"

    body = f"""
Crowd Monitor — High Risk Alert
================================

This is an automated notification from Crowd Monitor. The system detected a HIGH crowd-risk condition.

At a glance
-----------
Time detected      : {timestamp}
Source             : Camera 1
Risk level         : HIGH
People detected    : {count}

Recommended actions
-------------------
1) Verify the live feed and confirm congestion.
2) Deploy crowd-control guidance (signage / staff) to reduce density.
3) If sustained, initiate escalation per safety protocol.

If this alert appears repeatedly, consider adjusting thresholds or camera placement for improved accuracy.

— Crowd Monitor
(Automated message. Replies are not monitored.)
"""

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(receivers)
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(s.smtp_host, int(s.smtp_port))
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receivers, msg.as_string())
        server.quit()
        print("✅ Email sent successfully!")
        return {
            "sent": True,
            "skipped": False,
            "recipients": receivers,
            "count": count,
            "timestamp": time.time(),
        }
    except Exception as e:
        print("❌ Email error:", e)
        return {"sent": False, "skipped": False, "error": str(e)}
