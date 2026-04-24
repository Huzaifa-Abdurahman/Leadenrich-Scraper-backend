import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

class EmailService:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 465
        self.sender_email = os.getenv("SMTP_EMAIL")
        self.sender_password = os.getenv("SMTP_PASSWORD")

    def send_verification_code(self, receiver_email, code):
        if not self.sender_email or not self.sender_password:
            print("⚠️ SMTP credentials missing. Code:", code)
            return False

        message = MIMEMultipart("alternative")
        message["Subject"] = f"{code} is your LeadEnrich Access Code"
        message["From"] = f"LeadEnrich Intelligence <{self.sender_email}>"
        message["To"] = receiver_email

        html = f"""
        <html>
        <body style="font-family: sans-serif; background-color: #f4f4f4; padding: 20px;">
            <div style="max-width: 500px; margin: auto; background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
                <h1 style="color: #0ea5e9; margin-bottom: 20px; font-size: 24px;">LeadEnrich Engine</h1>
                <p style="color: #475569; line-height: 1.6;">Welcome to the next generation of B2B intelligence. Use the code below to unlock 3 high-performance extractions.</p>
                <div style="background: #f1f5f9; padding: 20px; border-radius: 12px; text-align: center; margin: 30px 0;">
                    <span style="font-family: monospace; font-size: 32px; font-weight: bold; letter-spacing: 10px; color: #0f172a;">{code}</span>
                </div>
                <p style="color: #94a3b8; font-size: 12px; text-align: center;">If you didn't request this, you can safely ignore this email.</p>
            </div>
        </body>
        </html>
        """
        message.attach(MIMEText(html, "html"))

        try:
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, receiver_email, message.as_string())
            return True
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False

email_service = EmailService()
