# email_service.py - Email sending service
import os
import smtplib
import mimetypes 
from email.message import EmailMessage
import oracledb
import pandas as pd
from typing import Dict, Any, Optional, Iterable
from config import SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD

def send_email_with_report(to_email: str, subject: str, body: str, attachment_path: str):
    """
    Sends an email with an attached report.
    """
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg.set_content(body)

        # Attach file if it exists
        if attachment_path and os.path.exists(attachment_path):
            ctype, encoding = mimetypes.guess_type(attachment_path)
            if ctype is None:
                ctype = "application/octet-stream"
            maintype, subtype = ctype.split("/", 1)

            with open(attachment_path, "rb") as f:
                file_data = f.read()
                file_name = os.path.basename(attachment_path)
                msg.add_attachment(file_data, maintype=maintype, subtype=subtype, filename=file_name)
        else:
            print("⚠️ No attachment found. Sending email without file.")

        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        print("✅ Email sent successfully!")

    except Exception as e:
        print(f"❌ Error while sending email: {e}")
