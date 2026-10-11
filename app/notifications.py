from __future__ import annotations

import json
import logging
import smtplib
import threading
from email.message import EmailMessage
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .config import settings

logger = logging.getLogger("chinatraderesolve.notifications")
MAX_NOTIFICATION_ATTEMPTS = 5
from .db import claim_pending_notifications, mark_notification, pending_notifications, queue_notification

_STATUS_LABELS = {
    "Russian": {"submitted":"Получено","needs_information":"Нужна информация","pilot_candidate":"Кандидат на бесплатную помощь","human_review":"Ручная проверка","declined":"Отклонено","accepted":"Принято","closed":"Закрыто"},
    "Serbian": {"submitted":"Primljeno","needs_information":"Potrebne informacije","pilot_candidate":"Pogodno za preliminarni pregled","human_review":"Ljudski pregled","declined":"Odbijeno","accepted":"Prihvaćeno","closed":"Zatvoreno"},
    "French": {"submitted":"Reçue","needs_information":"Informations nécessaires","pilot_candidate":"Éligible à l’examen préliminaire","human_review":"Vérification humaine","declined":"Refusée","accepted":"Acceptée","closed":"Clôturée"},
    "German": {"submitted":"Eingegangen","needs_information":"Informationen erforderlich","pilot_candidate":"Für die Vorprüfung geeignet","human_review":"Menschliche Prüfung","declined":"Abgelehnt","accepted":"Angenommen","closed":"Abgeschlossen"},
    "Spanish": {"submitted":"Recibida","needs_information":"Se necesita información","pilot_candidate":"Apta para revisión preliminar","human_review":"Revisión humana","declined":"Rechazada","accepted":"Aceptada","closed":"Cerrada"},
    "English": {"submitted":"Received","needs_information":"Information needed","pilot_candidate":"Eligible for preliminary review","human_review":"Human review","declined":"Declined","accepted":"Accepted","closed":"Closed"},
}
_RISK_LABELS_RU = {"critical":"Критический","high":"Высокий","medium":"Средний","low":"Низкий"}
_PROBLEM_LABELS_RU = {
    "Goods not delivered":"Товар не доставлен","Poor quality or defects":"Низкое качество или дефекты",
    "Wrong material or specification":"Неверный материал или спецификация","Questionable documents":"Сомнительные документы",
    "Supplier refuses refund":"Поставщик отказывается возвращать деньги","Marketplace rejected the claim":"Площадка отклонила претензию",
    "Other or multiple issues":"Другая или несколько проблем",
}


def build_case_notifications(case: dict) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    status_url = f"{settings.public_base_url}/case/{case['case_reference']}/{case['public_token']}"
    language = case.get("preferred_language") or "English"
    status_label = _STATUS_LABELS.get(language, _STATUS_LABELS["English"]).get(case["status"], case["status"])
    if language == "Russian":
        client_subject = f"Заявка ChinaTradeResolve {case['case_reference']}"
        client_body = (f"Здравствуйте, {case['full_name']}!\n\nChinaTradeResolve работает бесплатно, и оплата за помощь не требуется.\n" f"Номер дела: {case['case_reference']}\nТекущий автоматический статус: {status_label}\n\n" f"Страница статуса: {status_url}\n\nСохраните приватную ссылку выше, чтобы вернуться к делу. Добровольная поддержка проекта необязательна, не является оплатой и не влияет на приоритет, проверку или результат.\n")
    elif language == "French":
        client_subject = f"Demande ChinaTradeResolve {case['case_reference']}"
        client_body = (f"Bonjour {case['full_name']},\n\nChinaTradeResolve est un service gratuit et aucun paiement n’est requis.\n" f"Référence du dossier : {case['case_reference']}\nStatut automatique actuel : {status_label}\n\n" f"Page de statut : {status_url}\n\nConservez le lien privé ci-dessus pour revenir au dossier. Le soutien volontaire est facultatif, ne constitue pas un paiement et n’influence ni la priorité, ni la vérification, ni le résultat.\n")
    elif language == "German":
        client_subject = f"ChinaTradeResolve-Antrag {case['case_reference']}"
        client_body = (f"Guten Tag {case['full_name']},\n\nChinaTradeResolve ist ein kostenloser Dienst; eine Zahlung ist nicht erforderlich.\n" f"Fallreferenz: {case['case_reference']}\nAktueller automatischer Status: {status_label}\n\n" f"Bewahren Sie den obigen privaten Link auf, um zum Fall zurückzukehren. Freiwillige Unterstützung ist optional, keine Bezahlung und beeinflusst weder Priorität noch Prüfung oder Ergebnis.\n")
    elif language == "Spanish":
        client_subject = f"Solicitud ChinaTradeResolve {case['case_reference']}"
        client_body = (f"Hola {case['full_name']},\n\nChinaTradeResolve es un servicio gratuito y no se requiere ningún pago.\n" f"Referencia del caso: {case['case_reference']}\nEstado automático actual: {status_label}\n\n" f"Página de estado: {status_url}\n\nGuarde el enlace privado anterior para volver al caso. El apoyo voluntario es opcional, no constituye un pago y no afecta a la prioridad, la revisión ni el resultado.\n")
    elif language == "Serbian":
        client_subject = f"ChinaTradeResolve prijava {case['case_reference']}"
        client_body = (f"Poštovani/a {case['full_name']},\n\nChinaTradeResolve je besplatna usluga i plaćanje nije potrebno.\n" f"Broj slučaja: {case['case_reference']}\nTrenutni automatski status: {status_label}\n\n" f"Stranica statusa: {status_url}\n\nSačuvajte privatni link iznad da biste se vratili na slučaj. Dobrovoljna podrška je opciona, nije plaćanje i ne utiče na prioritet, pregled ili ishod.\n")
    else:
        client_subject = f"ChinaTradeResolve application {case['case_reference']}"
        client_body = (f"Hello {case['full_name']},\n\nChinaTradeResolve is a free service and no payment is required.\n" f"Case reference: {case['case_reference']}\nCurrent automated status: {status_label}\n\n" f"Status page: {status_url}\n\nSave the private link above to return to the case. Voluntary support is optional, is not payment for a service, and does not affect priority, review or outcome.\n")
    messages.append({"recipient": case["email"], "subject": client_subject, "body": client_body})
    if settings.admin_email:
        admin_body = (f"Новое дело: {case['case_reference']}\nСтатус: {_STATUS_LABELS['Russian'].get(case['status'], case['status'])}\nРиск: {_RISK_LABELS_RU.get(case['risk_level'], case['risk_level'])}\nПриоритет: {case['priority']}\n" f"Заявитель: {case['full_name']} <{case['email']}>\nПроблема: {_PROBLEM_LABELS_RU.get(case['main_problem'], case['main_problem'])}\n")
        messages.append({"recipient": settings.admin_email, "subject": f"Новое дело ChinaTradeResolve: {case['case_reference']}", "body": admin_body})
    return messages


def build_case_message_notification(case: dict, author: str) -> dict[str, str] | None:
    """Build a minimal private-link notification without including message content."""
    language = case.get("preferred_language") or "English"
    reference = str(case["case_reference"])
    private_url = f"{settings.public_base_url}/case/{reference}/{case['public_token']}"
    if author == "admin":
        recipient = str(case.get("email") or "").strip()
        if not recipient:
            return None
        if language == "Russian":
            subject = f"ChinaTradeResolve: новое сообщение по делу {reference}"
            body = f"Здравствуйте, {case.get('full_name') or ''}!\n\nПо вашему делу появилось новое сообщение. Откройте приватную страницу дела:\n{private_url}\n\nСодержание сообщения доступно только на защищённой странице дела.\n"
        elif language == "Serbian":
            subject = f"ChinaTradeResolve: nova poruka za slučaj {reference}"
            body = f"Poštovani/a {case.get('full_name') or ''},\n\nNa vašem slučaju je dostupna nova poruka. Otvorite privatnu stranicu slučaja:\n{private_url}\n\nSadržaj poruke dostupan je samo na zaštićenoj stranici slučaja.\n"
        elif language == "French":
            subject = f"ChinaTradeResolve : nouveau message pour le dossier {reference}"
            body = f"Bonjour {case.get('full_name') or ''},\n\nUn nouveau message est disponible pour votre dossier. Ouvrez la page privée du dossier :\n{private_url}\n\nLe contenu est disponible uniquement sur la page protégée du dossier.\n"
        elif language == "German":
            subject = f"ChinaTradeResolve: neue Nachricht zu Fall {reference}"
            body = f"Guten Tag {case.get('full_name') or ''},\n\nZu Ihrem Fall ist eine neue Nachricht verfügbar. Öffnen Sie die private Fallseite:\n{private_url}\n\nDer Inhalt ist nur auf der geschützten Fallseite sichtbar.\n"
        elif language == "Spanish":
            subject = f"ChinaTradeResolve: nuevo mensaje sobre el caso {reference}"
            body = f"Hola {case.get('full_name') or ''},\n\nHay un nuevo mensaje disponible para su caso. Abra la página privada del caso:\n{private_url}\n\nEl contenido solo está disponible en la página protegida del caso.\n"
        else:
            subject = f"ChinaTradeResolve: new message for case {reference}"
            body = f"Hello {case.get('full_name') or ''},\n\nA new message is available for your case. Open the private case page:\n{private_url}\n\nThe message content is available only on the protected case page.\n"
        return {"recipient": recipient, "subject": subject, "body": body}

    recipient = str(settings.admin_email or "").strip()
    if not recipient:
        return None
    if language == "Russian":
        subject = f"Ответ клиента ChinaTradeResolve: {reference}"
        body = f"По делу {reference} появился ответ клиента. Откройте админ-панель для просмотра переписки.\n"
    elif language == "Serbian":
        subject = f"Odgovor klijenta ChinaTradeResolve: {reference}"
        body = f"Na slučaju {reference} postoji odgovor klijenta. Otvorite administratorsku tablu da biste videli prepisku.\n"
    elif language == "French":
        subject = f"Réponse du client ChinaTradeResolve : {reference}"
        body = f"Le client a répondu dans le dossier {reference}. Ouvrez le panneau d’administration pour voir le fil.\n"
    elif language == "German":
        subject = f"Antwort des Kunden ChinaTradeResolve: {reference}"
        body = f"Der Kunde hat im Fall {reference} geantwortet. Öffnen Sie das Admin-Panel, um den Verlauf zu sehen.\n"
    elif language == "Spanish":
        subject = f"Respuesta del cliente ChinaTradeResolve: {reference}"
        body = f"El cliente ha respondido en el caso {reference}. Abra el panel de administración para ver el hilo.\n"
    else:
        subject = f"ChinaTradeResolve client reply: {reference}"
        body = f"The client replied in case {reference}. Open the administrator panel to view the thread.\n"
    return {"recipient": recipient, "subject": subject, "body": body}


def queue_case_notifications(case: dict) -> None:
    """Backward-compatible helper; new applications queue these transactionally."""
    for message in build_case_notifications(case):
        queue_notification(case.get("id"), message["recipient"], message["subject"], message["body"])


_DELIVERY_LOCK = threading.Lock()


def safe_email_bridge_url() -> str | None:
    """Return a bridge URL only when it is safe for an outbound HTTP request."""
    raw = (settings.email_bridge_url or "").strip()
    if not raw or any(ord(char) < 33 for char in raw):
        return None
    try:
        parsed = urlparse(raw)
        hostname = (parsed.hostname or "").casefold()
        parsed.port
        hostname.encode("idna")
    except (UnicodeError, ValueError):
        return None
    if not parsed.netloc or not hostname or parsed.username or parsed.password:
        return None
    if parsed.scheme == "https":
        return raw
    if parsed.scheme == "http" and hostname in {"localhost", "127.0.0.1", "::1"}:
        return raw
    return None


def email_delivery_is_configured() -> bool:
    bridge_ready = bool(safe_email_bridge_url() and settings.email_bridge_secret)
    smtp_ready = bool(
        settings.smtp_host
        and (not settings.smtp_username or settings.smtp_password)
    )
    return bridge_ready or smtp_ready



def _deliver_via_bridge(item: dict) -> None:
    bridge_url = safe_email_bridge_url()
    if not bridge_url or not settings.email_bridge_secret:
        raise RuntimeError("Email bridge is not configured")
    payload = json.dumps(
        {
            "secret": settings.email_bridge_secret,
            "to": item["recipient"],
            "subject": item["subject"],
            "body": item["body"],
        }
    ).encode("utf-8")
    request = Request(
        bridge_url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        # The URL is restricted above to HTTPS or a loopback-only HTTP endpoint.
        with urlopen(request, timeout=settings.email_bridge_timeout_seconds) as response:  # nosec B310
            raw = response.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Email bridge request failed: {exc}") from exc
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Email bridge returned invalid JSON") from exc
    if result.get("ok") is not True:
        raise RuntimeError(f"Email bridge rejected the message: {result.get('error', 'unknown_error')}")


def _deliver_via_smtp(item: dict) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = item["recipient"]
    msg["Subject"] = item["subject"]
    msg.set_content(item["body"])
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password or "")
        smtp.send_message(msg)


def deliver_pending(max_messages: int = 25) -> dict[str, int]:
    # Claim one row immediately before delivery. Leasing a large batch up front can
    # let later leases expire while an earlier slow message is still being sent.
    if not _DELIVERY_LOCK.acquire(blocking=False):
        return {"sent": 0, "failed": 0, "pending": len(pending_notifications())}
    try:
        result = {"sent": 0, "failed": 0, "pending": 0}
        bridge_ready = bool(safe_email_bridge_url() and settings.email_bridge_secret)
        smtp_ready = bool(settings.smtp_host and (not settings.smtp_username or settings.smtp_password))
        if not bridge_ready and not smtp_ready:
            result["pending"] = len(pending_notifications())
            return result

        for _ in range(max(1, min(int(max_messages), 100))):
            leased = claim_pending_notifications(limit=1)
            if not leased:
                break
            item = leased[0]
            claim_token = str(item.get("claim_token") or "")
            attempt_number = int(item.get("attempts") or 0) + 1
            try:
                if bridge_ready:
                    _deliver_via_bridge(item)
                else:
                    _deliver_via_smtp(item)
                if mark_notification(
                    item["id"], "sent", expected_claim_token=claim_token
                ):
                    result["sent"] += 1
            except Exception as exc:
                logger.exception(
                    "Email delivery failed for outbox_id=%s attempt=%s",
                    item.get("id"), attempt_number,
                )
                if attempt_number >= MAX_NOTIFICATION_ATTEMPTS:
                    saved = mark_notification(
                        item["id"], "failed", str(exc)[:500],
                        expected_claim_token=claim_token,
                    )
                    if saved:
                        result["failed"] += 1
                else:
                    retry_delay = min(900, 30 * (2 ** (attempt_number - 1)))
                    saved = mark_notification(
                        item["id"], "pending", str(exc)[:500],
                        retry_delay_seconds=retry_delay,
                        expected_claim_token=claim_token,
                    )
                    if saved:
                        result["pending"] += 1

        result["pending"] += len(pending_notifications())
        return result
    finally:
        _DELIVERY_LOCK.release()


def build_completion_notifications(case: dict) -> list[dict[str, str]]:
    status_url = f"{settings.public_base_url}/case/{case['case_reference']}/{case['public_token']}"
    language = case.get("preferred_language") or "English"
    if language == "Russian":
        subject = f"ChinaTradeResolve: дело {case['case_reference']} завершено"
        body = (f"Здравствуйте, {case['full_name']}!\n\nДело {case['case_reference']} отмечено как завершённое.\n\n" "На приватной странице статуса можно оставить необязательный отзыв.\n\n" f"Статус и отзыв: {status_url}\n")
    elif language == "French":
        subject = f"ChinaTradeResolve : dossier {case['case_reference']} clôturé"
        body = (f"Bonjour {case['full_name']},\n\nLe dossier {case['case_reference']} a été marqué comme clôturé.\n\n" "Vous pouvez laisser un avis facultatif sur votre page de statut privée.\n\n" f"Statut et avis : {status_url}\n")
    elif language == "German":
        subject = f"ChinaTradeResolve: Fall {case['case_reference']} abgeschlossen"
        body = (f"Guten Tag {case['full_name']},\n\nDer Fall {case['case_reference']} wurde als abgeschlossen markiert.\n\n" "Auf Ihrer privaten Statusseite können Sie freiwillig eine Rückmeldung hinterlassen.\n\n" f"Status und Rückmeldung: {status_url}\n")
    elif language == "Spanish":
        subject = f"ChinaTradeResolve: caso {case['case_reference']} cerrado"
        body = (f"Hola {case['full_name']},\n\nEl caso {case['case_reference']} se ha marcado como cerrado.\n\n" "Puede dejar una opinión opcional en su página privada de estado.\n\n" f"Estado y opinión: {status_url}\n")
    elif language == "Serbian":
        subject = f"ChinaTradeResolve: slučaj {case['case_reference']} je završen"
        body = (f"Poštovani/a {case['full_name']},\n\nSlučaj {case['case_reference']} je označen kao završen.\n\n" "Na privatnoj stranici statusa možete ostaviti opcione povratne informacije.\n\n" f"Status i povratne informacije: {status_url}\n")
    else:
        subject = f"ChinaTradeResolve feedback request {case['case_reference']}"
        body = (f"Hello {case['full_name']},\n\nYour ChinaTradeResolve case {case['case_reference']} has been marked complete.\n\n" "You can leave optional feedback on your private status page.\n\n" f"Status and feedback page: {status_url}\n")
    return [{"recipient": case["email"], "subject": subject, "body": body}]


def queue_completion_notification(case: dict) -> None:
    """Backward-compatible helper; status changes queue these transactionally."""
    for message in build_completion_notifications(case):
        queue_notification(case.get("id"), message["recipient"], message["subject"], message["body"])
