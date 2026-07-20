from __future__ import annotations

import smtplib
from email.message import EmailMessage

from .config import settings
from .db import mark_notification, pending_notifications, queue_notification


def queue_case_notifications(case: dict) -> None:
    status_url = f"{settings.public_base_url}/case/{case['case_reference']}/{case['public_token']}"
    client_body = (
        f"Hello {case['full_name']},\n\n"
        "Your ChinaTradeResolve free-access application has been received.\n"
        f"Case reference: {case['case_reference']}\n"
        f"Current automated status: {case['status']}\n\n"
        f"Status page: {status_url}\n\n"
        "No service fee or document upload is required at this stage.\n"
    )
    queue_notification(
        case["id"],
        case["email"],
        f"ChinaTradeResolve application {case['case_reference']}",
        client_body,
    )
    if settings.admin_email:
        admin_body = (
            f"New case: {case['case_reference']}\n"
            f"Status: {case['status']}\n"
            f"Risk: {case['risk_level']}\n"
            f"Priority: {case['priority']}\n"
            f"Applicant: {case['full_name']} <{case['email']}>\n"
            f"Problem: {case['main_problem']}\n"
        )
        queue_notification(
            case["id"],
            settings.admin_email,
            f"New CTR exception/lead: {case['case_reference']}",
            admin_body,
        )


def deliver_pending() -> dict[str, int]:
    pending = pending_notifications()
    result = {"sent": 0, "failed": 0, "pending": 0}
    if not settings.smtp_host:
        result["pending"] = len(pending)
        return result
    for item in pending:
        msg = EmailMessage()
        msg["From"] = settings.smtp_from
        msg["To"] = item["recipient"]
        msg["Subject"] = item["subject"]
        msg.set_content(item["body"])
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
                smtp.starttls()
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password or "")
                smtp.send_message(msg)
            mark_notification(item["id"], "sent")
            result["sent"] += 1
        except Exception as exc:
            mark_notification(item["id"], "failed", str(exc)[:500])
            result["failed"] += 1
    return result


def queue_completion_notification(case: dict) -> None:
    status_url = f"{settings.public_base_url}/case/{case['case_reference']}/{case['public_token']}"
    body = (
        f"Hello {case['full_name']},\n\n"
        f"Your ChinaTradeResolve case {case['case_reference']} has been marked complete.\n\n"
        "You can leave optional feedback on your private status page. "
        "If the service helped you, the same page may also show a voluntary project-support option. "
        "Support is never required and never affects service priority or outcome.\n\n"
        f"Status and feedback page: {status_url}\n"
    )
    queue_notification(
        case["id"],
        case["email"],
        f"ChinaTradeResolve feedback request {case['case_reference']}",
        body,
    )
