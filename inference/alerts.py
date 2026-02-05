import smtplib
from email.mime.text import MIMEText
import time

LAST_ALERT_TIME = 0
COOLDOWN = 60

def send_email_alert(count):
    global LAST_ALERT_TIME

    if time.time() - LAST_ALERT_TIME < COOLDOWN:
        print("⏳ Alert skipped (cooldown)")
        return

    LAST_ALERT_TIME = time.time()

    sender = "safetycrowd@gmail.com"
    password = "ysjz lbkt wukp grfe"
    receivers = [
        "mayankchandel830@gmail.com",
        "ayushgr2811@gmail.com",
        "n.hemunegi11@gmail.com",
        "ayushnainwal135@gmail.com"
    ]


    print("📧 Trying to send email...")

    msg = MIMEText(f"⚠ Crowd Alert!\nPeople Count: {count}\nRisk Level: HIGH")
    msg["Subject"] = "Crowd Alert System"
    msg["From"] = sender
    msg["To"] = ", ".join(receivers)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receivers, msg.as_string())
        server.quit()
        print("✅ Email sent successfully!")
    except Exception as e:
        print("❌ Email error:", e)
