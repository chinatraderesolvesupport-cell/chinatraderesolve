from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.config import settings


def main() -> None:
    required = {
        "SMTP_HOST": settings.smtp_host,
        "SMTP_USERNAME": settings.smtp_username,
        "SMTP_PASSWORD": settings.smtp_password,
        "ADMIN_EMAIL": settings.admin_email,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise SystemExit("Missing configuration: " + ", ".join(missing))

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = settings.admin_email
    message["Subject"] = "ChinaTradeResolve email connection test"
    message.set_content(
        "The ChinaTradeResolve application successfully connected to the configured SMTP account.\n"
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)

    print(f"Test message sent to {settings.admin_email}")


if __name__ == "__main__":
    main()
