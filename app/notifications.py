from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import settings
from .db import mark_notification, pending_notifications, queue_notification

_STATUS_LABELS = {
    "Russian": {"submitted":"Получено","needs_information":"Нужна информация","pilot_candidate":"Кандидат на бесплатную помощь","human_review":"Ручная проверка","declined":"Отклонено","accepted":"Принято","closed":"Закрыто"},
    "Serbian": {"submitted":"Primljeno","needs_information":"Potrebne informacije","pilot_candidate":"Kandidat za besplatni pregled","human_review":"Ljudski pregled","declined":"Odbijeno","accepted":"Prihvaćeno","closed":"Zatvoreno"},
    "French": {"submitted":"Reçue","needs_information":"Informations nécessaires","pilot_candidate":"Candidate à l’analyse gratuite","human_review":"Vérification humaine","declined":"Refusée","accepted":"Acceptée","closed":"Clôturée"},
    "German": {"submitted":"Eingegangen","needs_information":"Informationen erforderlich","pilot_candidate":"Kandidat für kostenlose Prüfung","human_review":"Menschliche Prüfung","declined":"Abgelehnt","accepted":"Angenommen","closed":"Abgeschlossen"},
    "Spanish": {"submitted":"Recibida","needs_information":"Se necesita información","pilot_candidate":"Candidato a revisión gratuita","human_review":"Revisión humana","declined":"Rechazada","accepted":"Aceptada","closed":"Cerrada"},
    "English": {"submitted":"Received","needs_information":"Information needed","pilot_candidate":"Free-review candidate","human_review":"Human review","declined":"Declined","accepted":"Accepted","closed":"Closed"},
}
_RISK_LABELS_RU = {"critical":"Критический","high":"Высокий","medium":"Средний","low":"Низкий"}
_PROBLEM_LABELS_RU = {
    "Goods not delivered":"Товар не доставлен","Poor quality or defects":"Низкое качество или дефекты",
    "Wrong material or specification":"Неверный материал или спецификация","Questionable documents":"Сомнительные документы",
    "Supplier refuses refund":"Поставщик отказывается возвращать деньги","Marketplace rejected the claim":"Площадка отклонила претензию",
}


def queue_case_notifications(case: dict) -> None:
    status_url = f"{settings.public_base_url}/case/{case['case_reference']}/{case['public_token']}"
    language = case.get("preferred_language") or "English"
    status_label = _STATUS_LABELS.get(language, _STATUS_LABELS["English"]).get(case["status"], case["status"])
    if language == "Russian":
        client_subject = f"Заявка ChinaTradeResolve {case['case_reference']}"
        client_body = (f"Здравствуйте, {case['full_name']}!\n\nВаша бесплатная заявка ChinaTradeResolve получена.\n" f"Номер дела: {case['case_reference']}\nТекущий автоматический статус: {status_label}\n\n" f"Страница статуса: {status_url}\n\nНа этом этапе оплата и загрузка документов не требуются.\n")
    elif language == "French":
        client_subject = f"Demande ChinaTradeResolve {case['case_reference']}"
        client_body = (f"Bonjour {case['full_name']},\n\nVotre demande gratuite ChinaTradeResolve a bien été reçue.\n" f"Référence du dossier : {case['case_reference']}\nStatut automatique actuel : {status_label}\n\n" f"Page de statut : {status_url}\n\nAucun paiement ni téléchargement de document n’est requis à ce stade.\n")
    elif language == "German":
        client_subject = f"ChinaTradeResolve-Antrag {case['case_reference']}"
        client_body = (f"Guten Tag {case['full_name']},\n\nIhr kostenloser ChinaTradeResolve-Antrag ist eingegangen.\n" f"Fallreferenz: {case['case_reference']}\nAktueller automatischer Status: {status_label}\n\n" f"Statusseite: {status_url}\n\nIn dieser Phase sind weder Zahlung noch Dokumenten-Upload erforderlich.\n")
    elif language == "Spanish":
        client_subject = f"Solicitud ChinaTradeResolve {case['case_reference']}"
        client_body = (f"Hola {case['full_name']},\n\nHemos recibido su solicitud gratuita de ChinaTradeResolve.\n" f"Referencia del caso: {case['case_reference']}\nEstado automático actual: {status_label}\n\n" f"Página de estado: {status_url}\n\nEn esta fase no se requiere pago ni carga de documentos.\n")
    elif language == "Serbian":
        client_subject = f"ChinaTradeResolve prijava {case['case_reference']}"
        client_body = (f"Poštovani/a {case['full_name']},\n\nVaša besplatna ChinaTradeResolve prijava je primljena.\n" f"Broj slučaja: {case['case_reference']}\nTrenutni automatski status: {status_label}\n\n" f"Stranica statusa: {status_url}\n\nU ovoj fazi nisu potrebni plaćanje ni otpremanje dokumenata.\n")
    else:
        client_subject = f"ChinaTradeResolve application {case['case_reference']}"
        client_body = (f"Hello {case['full_name']},\n\nYour ChinaTradeResolve free-access application has been received.\n" f"Case reference: {case['case_reference']}\nCurrent automated status: {status_label}\n\n" f"Status page: {status_url}\n\nNo service fee or document upload is required at this stage.\n")
    queue_notification(case["id"], case["email"], client_subject, client_body)
    if settings.admin_email:
        admin_body = (f"Новое дело: {case['case_reference']}\nСтатус: {_STATUS_LABELS['Russian'].get(case['status'], case['status'])}\nРиск: {_RISK_LABELS_RU.get(case['risk_level'], case['risk_level'])}\nПриоритет: {case['priority']}\n" f"Заявитель: {case['full_name']} <{case['email']}>\nПроблема: {_PROBLEM_LABELS_RU.get(case['main_problem'], case['main_problem'])}\n")
        queue_notification(case["id"], settings.admin_email, f"Новое дело ChinaTradeResolve: {case['case_reference']}", admin_body)


def _deliver_via_bridge(item: dict) -> None:
    if not settings.email_bridge_url or not settings.email_bridge_secret:
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
        settings.email_bridge_url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=settings.email_bridge_timeout_seconds) as response:
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


def deliver_pending() -> dict[str, int]:
    pending = pending_notifications()
    result = {"sent": 0, "failed": 0, "pending": 0}
    bridge_ready = bool(settings.email_bridge_url and settings.email_bridge_secret)
    smtp_ready = bool(settings.smtp_host)
    if not bridge_ready and not smtp_ready:
        result["pending"] = len(pending)
        return result
    for item in pending:
        try:
            if bridge_ready:
                _deliver_via_bridge(item)
            else:
                _deliver_via_smtp(item)
            mark_notification(item["id"], "sent")
            result["sent"] += 1
        except Exception as exc:
            mark_notification(item["id"], "failed", str(exc)[:500])
            result["failed"] += 1
    return result


def queue_completion_notification(case: dict) -> None:
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
    queue_notification(case["id"], case["email"], subject, body)

