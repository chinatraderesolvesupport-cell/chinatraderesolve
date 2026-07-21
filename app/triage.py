from __future__ import annotations

import re
from typing import Any

from .schemas import ApplicationCreate, TriageResult


URGENT_TERMS = {
    "court", "lawsuit", "hearing", "arbitration", "police", "criminal", "subpoena",
    "limitation", "deadline expires", "statute of limitations", "bankruptcy", "insolvency",
    "customs seizure", "sanctions", "extortion", "threat", "identity theft", "account takeover",
    "суд", "арбитраж", "полиция", "уголов", "срок давности", "срок истекает", "банкрот",
    "таможня задержала", "угроз", "вымогатель", "краже личности",
    "sud", "arbitraža", "policija", "krivič", "rok zastare", "stečaj", "pretnj", "iznuda",
}

ILLEGAL_REQUEST_TERMS = {
    "fake evidence", "forge document", "alter evidence", "hide evidence", "delete messages",
    "подделать доказ", "изменить доказ", "скрыть доказ", "удалить переписку",
    "falsifikovati dokaz", "sakriti dokaz", "izmeniti dokaz",
}

TECHNICAL_EXPERT_TERMS = {
    "ce certification", "laboratory", "safety test", "chemical composition", "medical device",
    "customs classification", "regulated product", "сертификац", "лаборатор", "безопасност",
    "химический состав", "медицинское изделие", "классификация товара",
    "sertifikacija", "laboratorija", "bezbednost", "hemijski sastav", "medicinski uređaj",
}

EVIDENCE_TERMS = {
    "invoice", "order", "contract", "message", "chat", "photo", "video", "inspection", "receipt",
    "инвойс", "заказ", "договор", "переписк", "сообщен", "фото", "видео", "инспекц", "чек",
    "faktura", "porudžbina", "ugovor", "poruka", "prepiska", "fotograf", "inspekcija",
}

IN_SCOPE_ISSUES = {
    "Goods not delivered", "Poor quality or defects", "Wrong material or specification",
    "Questionable documents", "Supplier refuses refund", "Marketplace rejected the claim",
}


def _contains(text: str, terms: set[str]) -> list[str]:
    low = text.lower()
    return sorted(term for term in terms if term in low)


def _parse_amount(text: str) -> float | None:
    cleaned = re.sub(r"[^0-9.,]", "", text or "")
    if not cleaned:
        return None
    if cleaned.count(",") == 1 and cleaned.count(".") == 0:
        tail = cleaned.split(",")[-1]
        cleaned = cleaned.replace(",", ".") if len(tail) <= 2 else cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None



_RU = {
"The request may involve altering, concealing or fabricating evidence.": "Запрос может предполагать изменение, сокрытие или изготовление доказательств.",
"The description indicates an urgent legal, authority or deadline-sensitive issue.": "Описание указывает на срочный юридический вопрос, обращение органов или критический срок.",
"A laboratory, compliance, customs or technical specialist may be required.": "Может потребоваться лабораторный, сертификационный, таможенный или технический специалист.",
"The stated dispute value is high and requires human scope review.": "Указана высокая сумма спора, поэтому требуется ручная проверка объёма помощи.",
"The selected issue does not clearly match the current free-access scope.": "Выбранная проблема не полностью соответствует текущему объёму бесплатной помощи.",
"Supplier or company name": "Название поставщика или компании",
"Order number or transaction reference": "Номер заказа или идентификатор транзакции",
"Approximate amount in dispute or order value": "Примерная сумма спора или стоимость заказа",
"Which written records or photographs are available": "Какие письменные материалы или фотографии имеются",
"A more detailed chronology of what happened": "Более подробная хронология событий",
"Preferred practical outcome": "Желаемый практический результат",
"This application cannot be accepted because the requested assistance may involve improper handling of evidence.": "Заявка не может быть принята, поскольку запрос может предполагать ненадлежащее обращение с доказательствами.",
"Decline and preserve an internal audit record.": "Отклонить заявку и сохранить внутреннюю запись аудита.",
"Your description may involve an urgent legal or authority matter. The automated free-access system cannot safely assess it without human review.": "Описание может касаться срочного юридического вопроса или действий государственных органов. Без ручной проверки автоматическая система не может безопасно оценить такую заявку.",
"Escalate immediately; advise the applicant to seek a qualified professional where deadlines may apply.": "Немедленно передать на ручную проверку; при наличии сроков рекомендовать заявителю обратиться к квалифицированному специалисту.",
"The case appears potentially relevant, but its value or technical complexity requires human scope review.": "Дело может соответствовать направлению сервиса, но его стоимость или техническая сложность требуют ручной проверки.",
"Review scope and decide whether an external specialist is required.": "Проверить объём помощи и определить, нужен ли внешний специалист.",
"More information is needed to determine whether the case fits the free-access service.": "Нужно больше информации, чтобы определить, подходит ли дело для бесплатной помощи.",
"Request a clearer description of the supplier dispute and requested outcome.": "Запросить более точное описание спора и желаемого результата.",
"The application appears suitable for free-access review, subject to capacity and a final scope check.": "Заявка предварительно подходит для бесплатного рассмотрения при наличии мощности и после окончательной проверки объёма помощи.",
"Place in the free-access candidate queue and request up to five key files if selected.": "Поместить в очередь кандидатов и при отборе запросить не более пяти ключевых файлов.",
"The case may fit the free-access service, but additional information is needed before selection.": "Дело может подходить для бесплатной помощи, но до отбора требуется дополнительная информация.",
"Request the missing information listed by the triage result.": "Запросить недостающую информацию, указанную в результате проверки.",
"The case was assessed against the current free-access scope and evidence indicators.": "Дело оценено с учётом текущего объёма бесплатной помощи и имеющихся признаков доказательств.",
}
_SR = {
"Supplier or company name":"Naziv dobavljača ili kompanije", "Order number or transaction reference":"Broj porudžbine ili oznaka transakcije", "Approximate amount in dispute or order value":"Približan iznos spora ili vrednost porudžbine", "Which written records or photographs are available":"Koji pisani dokazi ili fotografije postoje", "A more detailed chronology of what happened":"Detaljnija hronologija događaja", "Preferred practical outcome":"Željeni praktični ishod",
"The case may fit the free-access service, but additional information is needed before selection.":"Slučaj može odgovarati besplatnoj usluzi, ali su potrebne dodatne informacije pre izbora.",
"The case appears potentially relevant, but its value or technical complexity requires human scope review.":"Slučaj može biti relevantan, ali njegova vrednost ili tehnička složenost zahtevaju ljudsku proveru obima.",
"The case was assessed against the current free-access scope and evidence indicators.":"Slučaj je procenjen prema trenutnom obimu besplatne usluge i pokazateljima dokaza.",
}

def _localize_result(result: TriageResult, language: str) -> TriageResult:
    mapping = _RU if language == "Russian" else _SR if language == "Serbian" else None
    if not mapping:
        return result
    return result.model_copy(update={
        "reasons": [mapping.get(x, x) for x in result.reasons],
        "missing_information": [mapping.get(x, x) for x in result.missing_information],
        "recommended_action": mapping.get(result.recommended_action, result.recommended_action),
        "public_message": mapping.get(result.public_message, result.public_message),
    })


def rules_triage(app: ApplicationCreate) -> TriageResult:
    combined = f"{app.main_problem} {app.description} {app.requested_result}"
    urgent = _contains(combined, URGENT_TERMS)
    illegal = _contains(combined, ILLEGAL_REQUEST_TERMS)
    technical = _contains(combined, TECHNICAL_EXPERT_TERMS)
    evidence_hits = _contains(combined, EVIDENCE_TERMS)
    amount = _parse_amount(app.amount_in_dispute or app.order_value)

    reasons: list[str] = []
    missing: list[str] = []
    flags: list[str] = []
    hard_stop = False
    in_scope = app.main_problem in IN_SCOPE_ISSUES
    priority = 35

    if illegal:
        hard_stop = True
        flags.append("possible_request_to_alter_or_conceal_evidence")
        reasons.append("The request may involve altering, concealing or fabricating evidence.")
    if urgent:
        hard_stop = True
        flags.append("urgent_legal_or_authority_issue")
        reasons.append("The description indicates an urgent legal, authority or deadline-sensitive issue.")
    if technical:
        flags.append("technical_expert_may_be_required")
        reasons.append("A laboratory, compliance, customs or technical specialist may be required.")
        priority += 15
    if amount is not None and amount >= 50000:
        flags.append("high_value_dispute")
        reasons.append("The stated dispute value is high and requires human scope review.")
        priority += 20
    if not in_scope:
        flags.append("scope_unclear")
        reasons.append("The selected issue does not clearly match the current free-access scope.")
    if not app.supplier_name:
        missing.append("Supplier or company name")
    if not app.order_number:
        missing.append("Order number or transaction reference")
    if not app.amount_in_dispute and not app.order_value:
        missing.append("Approximate amount in dispute or order value")
    if not evidence_hits:
        missing.append("Which written records or photographs are available")
    if len(app.description) < 120:
        missing.append("A more detailed chronology of what happened")
    if app.requested_result == "Not sure":
        missing.append("Preferred practical outcome")

    score = 0
    score += 20 if in_scope else 0
    score += 12 if app.supplier_name else 0
    score += 10 if app.order_number else 0
    score += 10 if app.amount_in_dispute or app.order_value else 0
    score += min(20, len(evidence_hits) * 5)
    score += 15 if len(app.description) >= 200 else 5 if len(app.description) >= 120 else 0
    score += 10 if app.requested_result != "Not sure" else 0
    score -= 40 if hard_stop else 0
    score -= 10 if technical else 0
    score = max(0, min(100, score))

    if illegal:
        decision = "declined"
        risk = "critical"
        strength = "insufficient"
        public = "This application cannot be accepted because the requested assistance may involve improper handling of evidence."
        action = "Decline and preserve an internal audit record."
    elif urgent:
        decision = "human_review"
        risk = "critical"
        strength = "unclear"
        public = "Your description may involve an urgent legal or authority matter. The automated free-access system cannot safely assess it without human review."
        action = "Escalate immediately; advise the applicant to seek a qualified professional where deadlines may apply."
    elif technical or (amount is not None and amount >= 50000):
        decision = "human_review"
        risk = "high"
        strength = "potentially_supportable" if evidence_hits else "unclear"
        public = "The case appears potentially relevant, but its value or technical complexity requires human scope review."
        action = "Review scope and decide whether an external specialist is required."
    elif not in_scope:
        decision = "needs_information"
        risk = "medium"
        strength = "unclear"
        public = "More information is needed to determine whether the case fits the free-access service."
        action = "Request a clearer description of the supplier dispute and requested outcome."
    elif score >= 65 and len(missing) <= 2:
        decision = "pilot_candidate"
        risk = "low" if amount is None or amount < 10000 else "medium"
        strength = "supportable_for_review"
        public = "The application appears suitable for free-access review, subject to capacity and a final scope check."
        action = "Place in the free-access candidate queue and request up to five key files if selected."
    else:
        decision = "needs_information"
        risk = "medium"
        strength = "potentially_supportable" if evidence_hits else "unclear"
        public = "The case may fit the free-access service, but additional information is needed before selection."
        action = "Request the missing information listed by the triage result."

    priority += score // 2
    if decision == "human_review":
        priority = max(priority, 85)
    elif decision == "pilot_candidate":
        priority = max(priority, 60)
    priority = min(100, priority)

    confidence = 0.88 if hard_stop else 0.78 if decision == "pilot_candidate" else 0.72
    result = TriageResult(
        decision=decision,
        risk_level=risk,
        priority=priority,
        confidence=confidence,
        position_strength=strength,
        in_scope=in_scope,
        hard_stop=hard_stop,
        reasons=reasons or ["The case was assessed against the current free-access scope and evidence indicators."],
        missing_information=missing,
        risk_flags=flags,
        recommended_action=action,
        public_message=public,
        source="rules",
    )
    return _localize_result(result, app.preferred_language)


def merge_triage(rule_result: TriageResult, ai_result: TriageResult | None) -> TriageResult:
    if ai_result is None:
        return rule_result
    # AI may add nuance, but cannot override deterministic hard stops or lower risk flags.
    if rule_result.hard_stop:
        return rule_result.model_copy(update={"source": "rules+ai"})
    risk_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    risk = ai_result.risk_level if risk_rank[ai_result.risk_level] >= risk_rank[rule_result.risk_level] else rule_result.risk_level
    decision = ai_result.decision
    if rule_result.decision == "human_review" and decision == "pilot_candidate":
        decision = "human_review"
    combined_reasons = list(dict.fromkeys(rule_result.reasons + ai_result.reasons))[:12]
    combined_missing = list(dict.fromkeys(rule_result.missing_information + ai_result.missing_information))[:12]
    combined_flags = list(dict.fromkeys(rule_result.risk_flags + ai_result.risk_flags))[:12]
    return ai_result.model_copy(update={
        "decision": decision,
        "risk_level": risk,
        "priority": max(rule_result.priority, ai_result.priority),
        "confidence": min(rule_result.confidence, ai_result.confidence),
        "hard_stop": rule_result.hard_stop or ai_result.hard_stop,
        "reasons": combined_reasons,
        "missing_information": combined_missing,
        "risk_flags": combined_flags,
        "source": "rules+ai",
    })
