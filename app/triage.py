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
    "tribunal", "procès", "arbitrage", "police", "pénal", "délai", "prescription", "faillite", "douane", "menace", "extorsion",
    "gericht", "klage", "schiedsverfahren", "polizei", "straf", "frist", "verjähr", "insolvenz", "zoll", "drohung", "erpressung",
    "tribunal", "demanda", "arbitraje", "policía", "penal", "plazo", "prescripción", "quiebra", "aduana", "amenaza", "extorsión",
}

ILLEGAL_REQUEST_TERMS = {
    "fake evidence", "forge document", "alter evidence", "hide evidence", "delete messages",
    "подделать доказ", "изменить доказ", "скрыть доказ", "удалить переписку",
    "falsifikovati dokaz", "sakriti dokaz", "izmeniti dokaz",
    "falsifier les preuves", "modifier les preuves", "cacher les preuves", "supprimer les messages",
    "beweise fälschen", "beweise ändern", "beweise verbergen", "nachrichten löschen",
    "falsificar pruebas", "alterar pruebas", "ocultar pruebas", "borrar mensajes",
}

TECHNICAL_EXPERT_TERMS = {
    "ce certification", "laboratory", "safety test", "chemical composition", "medical device",
    "customs classification", "regulated product", "сертификац", "лаборатор", "безопасност",
    "химический состав", "медицинское изделие", "классификация товара",
    "sertifikacija", "laboratorija", "bezbednost", "hemijski sastav", "medicinski uređaj",
    "certification", "laboratoire", "sécurité", "composition chimique", "dispositif médical", "classement douanier",
    "zertifizierung", "labor", "sicherheit", "chemische zusammensetzung", "medizinprodukt", "zolltarif",
    "certificación", "laboratorio", "seguridad", "composición química", "dispositivo médico", "clasificación aduanera",
}

EVIDENCE_TERMS = {
    "invoice", "order", "contract", "message", "chat", "photo", "video", "inspection", "receipt",
    "инвойс", "заказ", "договор", "переписк", "сообщен", "фото", "видео", "инспекц", "чек",
    "faktura", "porudžbina", "ugovor", "poruka", "prepiska", "fotograf", "inspekcija",
    "facture", "commande", "contrat", "message", "photo", "vidéo", "inspection", "reçu",
    "rechnung", "bestellung", "vertrag", "nachricht", "foto", "video", "inspektion", "beleg",
    "factura", "pedido", "contrato", "mensaje", "foto", "vídeo", "inspección", "recibo",
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


def _detect_currency(text: str) -> str | None:
    value = (text or "").upper()
    markers = (
        ("RSD", ("RSD", "DIN", "ДИН")),
        ("CNY", ("CNY", "RMB", "YUAN", "ЮАН", "¥")),
        ("EUR", ("EUR", "EURO", "ЕВРО", "€")),
        ("GBP", ("GBP", "POUND", "ФУНТ", "£")),
        ("USD", ("USD", "US$", "DOLLAR", "ДОЛЛАР", "$")),
    )
    for currency, candidates in markers:
        if any(candidate in value for candidate in candidates):
            return currency
    return None


# These are conservative service-scope thresholds, not exchange-rate quotes.
# An amount without a recognised currency is never escalated automatically.
HIGH_VALUE_THRESHOLDS = {
    "USD": 50_000, "EUR": 45_000, "GBP": 40_000,
    "CNY": 350_000, "RSD": 5_300_000,
}
MEDIUM_VALUE_THRESHOLDS = {
    "USD": 10_000, "EUR": 9_000, "GBP": 8_000,
    "CNY": 70_000, "RSD": 1_050_000,
}


def _amount_reaches_threshold(text: str, thresholds: dict[str, float]) -> bool:
    amount = _parse_amount(text)
    currency = _detect_currency(text)
    return bool(amount is not None and currency and amount >= thresholds[currency])



_RU = {
"The request may involve altering, concealing or fabricating evidence.": "Запрос может предполагать изменение, сокрытие или изготовление доказательств.",
"The description indicates an urgent legal, authority or deadline-sensitive issue.": "Описание указывает на срочный юридический вопрос, обращение органов или критический срок.",
"A laboratory, compliance, customs or technical specialist may be required.": "Может потребоваться лабораторный, сертификационный, таможенный или технический специалист.",
"The stated dispute value is high and requires human scope review.": "Указана высокая сумма спора, поэтому требуется ручная проверка объёма помощи.",
"The selected issue does not clearly match the current free-access scope.": "Выбранная проблема не полностью соответствует текущему объёму бесплатной помощи.",
"Supplier or company name": "Название поставщика или компании",
"Order number or transaction reference": "Номер заказа или идентификатор транзакции",
"Approximate amount in dispute or order value": "Примерная сумма спора или стоимость заказа",
"Currency of the disputed amount": "Валюта спорной суммы",
"Which written records or photographs are available": "Какие письменные материалы или фотографии имеются",
"A more detailed chronology of what happened": "Более подробная хронология событий",
"Preferred practical outcome": "Желаемый практический результат",
"This application cannot be accepted because the requested assistance may involve improper handling of evidence.": "Заявка не может быть принята, поскольку запрос может предполагать ненадлежащее обращение с доказательствами.",
"Decline and preserve an internal audit record.": "Отклонить заявку и сохранить внутреннюю запись аудита.",
"The description mentions possible alteration, concealment or fabrication of evidence. The context requires human review and the application has not been automatically rejected.": "В описании упоминается возможное изменение, сокрытие или изготовление доказательств. Контекст требует ручной проверки; заявка не была автоматически отклонена.",
"Review the context and speaker before making any decision; preserve the applicant's original materials.": "До принятия решения проверить контекст и автора высказывания; сохранить оригинальные материалы заявителя.",
"Your description may involve an urgent legal or authority matter. The automated free-access system cannot safely assess it without human review.": "Описание может касаться срочного юридического вопроса или действий государственных органов. Без ручной проверки автоматическая система не может безопасно оценить такую заявку.",
"Escalate immediately; advise the applicant to seek a qualified professional where deadlines may apply.": "Немедленно передать на ручную проверку; при наличии сроков рекомендовать заявителю обратиться к квалифицированному специалисту.",
"The case appears potentially relevant, but its value or technical complexity requires human scope review.": "Дело может соответствовать направлению сервиса, но его стоимость или техническая сложность требуют ручной проверки.",
"Review scope and decide whether an external specialist is required.": "Проверить объём помощи и определить, нужен ли внешний специалист.",
"More information is needed to determine whether the case fits the free-access service.": "Нужно больше информации, чтобы определить, подходит ли дело для бесплатной помощи.",
"Request a clearer description of the supplier dispute and requested outcome.": "Запросить более точное описание спора и желаемого результата.",
"The application appears suitable for free-access review, subject to capacity and a final scope check.": "Заявка предварительно подходит для бесплатного рассмотрения при наличии мощности и после окончательной проверки объёма помощи.",
"Place in the free-access candidate queue and request up to twenty key files if selected.": "Поместить в очередь кандидатов и при отборе запросить не более двадцати ключевых файлов.",
"The case may fit the free-access service, but additional information is needed before selection.": "Дело может подходить для бесплатной помощи, но до отбора требуется дополнительная информация.",
"Request the missing information listed by the triage result.": "Запросить недостающую информацию, указанную в результате проверки.",
"The case was assessed against the current free-access scope and evidence indicators.": "Дело оценено с учётом текущего объёма бесплатной помощи и имеющихся признаков доказательств.",
}
_FR = {
"The request may involve altering, concealing or fabricating evidence.": "La demande peut impliquer la modification, la dissimulation ou la fabrication de preuves.",
"The description indicates an urgent legal, authority or deadline-sensitive issue.": "La description indique une question juridique urgente, une intervention des autorités ou une échéance critique.",
"A laboratory, compliance, customs or technical specialist may be required.": "Un spécialiste de laboratoire, de conformité, des douanes ou un expert technique peut être nécessaire.",
"The stated dispute value is high and requires human scope review.": "Le montant indiqué est élevé et nécessite une vérification humaine du périmètre.",
"The selected issue does not clearly match the current free-access scope.": "Le problème sélectionné ne correspond pas clairement au périmètre actuel de l’accès gratuit.",
"Supplier or company name": "Nom du fournisseur ou de l’entreprise",
"Order number or transaction reference": "Numéro de commande ou référence de transaction",
"Approximate amount in dispute or order value": "Montant approximatif du litige ou valeur de la commande",
"Currency of the disputed amount": "Devise du montant contesté",
"Which written records or photographs are available": "Documents écrits ou photographies disponibles",
"A more detailed chronology of what happened": "Chronologie plus détaillée des événements",
"Preferred practical outcome": "Résultat pratique souhaité",
"This application cannot be accepted because the requested assistance may involve improper handling of evidence.": "Cette demande ne peut pas être acceptée, car l’assistance sollicitée peut impliquer une manipulation inadéquate des preuves.",
"Decline and preserve an internal audit record.": "Refuser la demande et conserver une trace d’audit interne.",
"The description mentions possible alteration, concealment or fabrication of evidence. The context requires human review and the application has not been automatically rejected.": "La description mentionne une possible modification, dissimulation ou fabrication de preuves. Le contexte exige une vérification humaine et la demande n’a pas été rejetée automatiquement.",
"Review the context and speaker before making any decision; preserve the applicant's original materials.": "Vérifier le contexte et l’auteur des propos avant toute décision et conserver les éléments originaux du demandeur.",
"Your description may involve an urgent legal or authority matter. The automated free-access system cannot safely assess it without human review.": "Votre description peut concerner une question juridique urgente ou une intervention des autorités. Le système automatisé d’accès gratuit ne peut pas l’évaluer de manière sûre sans vérification humaine.",
"Escalate immediately; advise the applicant to seek a qualified professional where deadlines may apply.": "Transmettre immédiatement à un humain et recommander au demandeur de consulter un professionnel qualifié lorsque des délais peuvent s’appliquer.",
"The case appears potentially relevant, but its value or technical complexity requires human scope review.": "Le dossier semble potentiellement pertinent, mais sa valeur ou sa complexité technique exige une vérification humaine du périmètre.",
"Review scope and decide whether an external specialist is required.": "Vérifier le périmètre et déterminer si un spécialiste externe est nécessaire.",
"More information is needed to determine whether the case fits the free-access service.": "Des informations supplémentaires sont nécessaires pour déterminer si le dossier correspond au service gratuit.",
"Request a clearer description of the supplier dispute and requested outcome.": "Demander une description plus claire du litige avec le fournisseur et du résultat souhaité.",
"The application appears suitable for free-access review, subject to capacity and a final scope check.": "La demande semble adaptée à une analyse gratuite, sous réserve de la capacité disponible et d’une vérification finale du périmètre.",
"Place in the free-access candidate queue and request up to twenty key files if selected.": "Placer la demande dans la file des candidats et demander jusqu’à vingt fichiers essentiels si elle est sélectionnée.",
"The case may fit the free-access service, but additional information is needed before selection.": "Le dossier peut correspondre au service gratuit, mais des informations supplémentaires sont nécessaires avant la sélection.",
"Request the missing information listed by the triage result.": "Demander les informations manquantes indiquées dans le résultat de l’analyse.",
"The case was assessed against the current free-access scope and evidence indicators.": "Le dossier a été évalué selon le périmètre actuel de l’accès gratuit et les indices de preuve disponibles.",
}
_DE = {
"The request may involve altering, concealing or fabricating evidence.": "Die Anfrage könnte das Verändern, Verbergen oder Herstellen von Beweisen betreffen.",
"The description indicates an urgent legal, authority or deadline-sensitive issue.": "Die Beschreibung weist auf eine dringende rechtliche, behördliche oder fristgebundene Angelegenheit hin.",
"A laboratory, compliance, customs or technical specialist may be required.": "Möglicherweise ist ein Labor-, Compliance-, Zoll- oder technischer Spezialist erforderlich.",
"The stated dispute value is high and requires human scope review.": "Der angegebene Streitwert ist hoch und erfordert eine menschliche Prüfung des Leistungsumfangs.",
"The selected issue does not clearly match the current free-access scope.": "Das ausgewählte Problem passt nicht eindeutig zum aktuellen Umfang des kostenlosen Zugangs.",
"Supplier or company name": "Name des Lieferanten oder Unternehmens",
"Order number or transaction reference": "Bestellnummer oder Transaktionsreferenz",
"Approximate amount in dispute or order value": "Ungefährer Streitbetrag oder Bestellwert",
"Currency of the disputed amount": "Währung des Streitbetrags",
"Which written records or photographs are available": "Verfügbare schriftliche Unterlagen oder Fotos",
"A more detailed chronology of what happened": "Ausführlichere Chronologie des Geschehens",
"Preferred practical outcome": "Gewünschtes praktisches Ergebnis",
"This application cannot be accepted because the requested assistance may involve improper handling of evidence.": "Dieser Antrag kann nicht angenommen werden, weil die gewünschte Unterstützung einen unsachgemäßen Umgang mit Beweisen betreffen könnte.",
"Decline and preserve an internal audit record.": "Antrag ablehnen und einen internen Prüfvermerk aufbewahren.",
"The description mentions possible alteration, concealment or fabrication of evidence. The context requires human review and the application has not been automatically rejected.": "Die Beschreibung erwähnt möglicherweise die Veränderung, Verbergung oder Herstellung von Beweisen. Der Kontext muss menschlich geprüft werden; der Antrag wurde nicht automatisch abgelehnt.",
"Review the context and speaker before making any decision; preserve the applicant's original materials.": "Vor einer Entscheidung Kontext und Sprecher prüfen und die Originalunterlagen des Antragstellers bewahren.",
"Your description may involve an urgent legal or authority matter. The automated free-access system cannot safely assess it without human review.": "Ihre Beschreibung könnte eine dringende rechtliche oder behördliche Angelegenheit betreffen. Das automatisierte kostenlose System kann sie ohne menschliche Prüfung nicht sicher bewerten.",
"Escalate immediately; advise the applicant to seek a qualified professional where deadlines may apply.": "Sofort zur menschlichen Prüfung weiterleiten und bei möglichen Fristen zu qualifizierter Fachberatung raten.",
"The case appears potentially relevant, but its value or technical complexity requires human scope review.": "Der Fall scheint grundsätzlich relevant zu sein, aber sein Wert oder seine technische Komplexität erfordert eine menschliche Prüfung des Umfangs.",
"Review scope and decide whether an external specialist is required.": "Leistungsumfang prüfen und entscheiden, ob ein externer Spezialist erforderlich ist.",
"More information is needed to determine whether the case fits the free-access service.": "Weitere Informationen sind erforderlich, um zu beurteilen, ob der Fall zum kostenlosen Dienst passt.",
"Request a clearer description of the supplier dispute and requested outcome.": "Eine klarere Beschreibung des Lieferantenstreits und des gewünschten Ergebnisses anfordern.",
"The application appears suitable for free-access review, subject to capacity and a final scope check.": "Der Antrag scheint für eine kostenlose Prüfung geeignet zu sein, vorbehaltlich verfügbarer Kapazität und einer abschließenden Umfangsprüfung.",
"Place in the free-access candidate queue and request up to twenty key files if selected.": "In die Kandidatenliste für den kostenlosen Zugang aufnehmen und bei Auswahl bis zu zwanzig zentrale Dateien anfordern.",
"The case may fit the free-access service, but additional information is needed before selection.": "Der Fall könnte zum kostenlosen Dienst passen, vor der Auswahl sind jedoch zusätzliche Informationen erforderlich.",
"Request the missing information listed by the triage result.": "Die im Prüfergebnis aufgeführten fehlenden Informationen anfordern.",
"The case was assessed against the current free-access scope and evidence indicators.": "Der Fall wurde anhand des aktuellen Umfangs des kostenlosen Zugangs und der vorhandenen Beweisindikatoren bewertet.",
}
_ES = {
"The request may involve altering, concealing or fabricating evidence.": "La solicitud puede implicar la alteración, ocultación o fabricación de pruebas.",
"The description indicates an urgent legal, authority or deadline-sensitive issue.": "La descripción indica un asunto jurídico urgente, relacionado con autoridades o sujeto a un plazo crítico.",
"A laboratory, compliance, customs or technical specialist may be required.": "Puede ser necesario un especialista de laboratorio, cumplimiento, aduanas o un experto técnico.",
"The stated dispute value is high and requires human scope review.": "El valor indicado de la disputa es elevado y requiere una revisión humana del alcance.",
"The selected issue does not clearly match the current free-access scope.": "El problema seleccionado no coincide claramente con el alcance actual del acceso gratuito.",
"Supplier or company name": "Nombre del proveedor o de la empresa",
"Order number or transaction reference": "Número de pedido o referencia de la transacción",
"Approximate amount in dispute or order value": "Importe aproximado en disputa o valor del pedido",
"Currency of the disputed amount": "Moneda del importe en disputa",
"Which written records or photographs are available": "Documentos escritos o fotografías disponibles",
"A more detailed chronology of what happened": "Cronología más detallada de lo ocurrido",
"Preferred practical outcome": "Resultado práctico deseado",
"This application cannot be accepted because the requested assistance may involve improper handling of evidence.": "Esta solicitud no puede aceptarse porque la ayuda solicitada puede implicar un manejo inadecuado de las pruebas.",
"Decline and preserve an internal audit record.": "Rechazar la solicitud y conservar un registro interno de auditoría.",
"The description mentions possible alteration, concealment or fabrication of evidence. The context requires human review and the application has not been automatically rejected.": "La descripción menciona una posible alteración, ocultación o fabricación de pruebas. El contexto requiere revisión humana y la solicitud no se ha rechazado automáticamente.",
"Review the context and speaker before making any decision; preserve the applicant's original materials.": "Revisar el contexto y quién hizo la afirmación antes de decidir; conservar los materiales originales del solicitante.",
"Your description may involve an urgent legal or authority matter. The automated free-access system cannot safely assess it without human review.": "Su descripción puede referirse a un asunto jurídico urgente o relacionado con autoridades. El sistema automatizado de acceso gratuito no puede evaluarlo de forma segura sin revisión humana.",
"Escalate immediately; advise the applicant to seek a qualified professional where deadlines may apply.": "Escalar inmediatamente y recomendar al solicitante que consulte a un profesional cualificado cuando puedan aplicarse plazos.",
"The case appears potentially relevant, but its value or technical complexity requires human scope review.": "El caso parece potencialmente relevante, pero su valor o complejidad técnica requiere una revisión humana del alcance.",
"Review scope and decide whether an external specialist is required.": "Revisar el alcance y decidir si es necesario un especialista externo.",
"More information is needed to determine whether the case fits the free-access service.": "Se necesita más información para determinar si el caso encaja en el servicio gratuito.",
"Request a clearer description of the supplier dispute and requested outcome.": "Solicitar una descripción más clara de la disputa con el proveedor y del resultado deseado.",
"The application appears suitable for free-access review, subject to capacity and a final scope check.": "La solicitud parece adecuada para una revisión gratuita, sujeta a la capacidad disponible y a una comprobación final del alcance.",
"Place in the free-access candidate queue and request up to twenty key files if selected.": "Colocar la solicitud en la cola de candidatos y pedir hasta veinte archivos clave si se selecciona.",
"The case may fit the free-access service, but additional information is needed before selection.": "El caso puede encajar en el servicio gratuito, pero se necesita información adicional antes de la selección.",
"Request the missing information listed by the triage result.": "Solicitar la información faltante indicada en el resultado de la evaluación.",
"The case was assessed against the current free-access scope and evidence indicators.": "El caso se evaluó conforme al alcance actual del acceso gratuito y a los indicios de prueba disponibles.",
}
_SR = {
"Supplier or company name":"Naziv dobavljača ili kompanije", "Order number or transaction reference":"Broj porudžbine ili oznaka transakcije", "Approximate amount in dispute or order value":"Približan iznos spora ili vrednost porudžbine", "Which written records or photographs are available":"Koji pisani dokazi ili fotografije postoje", "A more detailed chronology of what happened":"Detaljnija hronologija događaja", "Preferred practical outcome":"Željeni praktični ishod",
"Currency of the disputed amount":"Valuta spornog iznosa",
"The description mentions possible alteration, concealment or fabrication of evidence. The context requires human review and the application has not been automatically rejected.":"Opis pominje moguće menjanje, skrivanje ili izradu dokaza. Kontekst zahteva ljudsku proveru i prijava nije automatski odbijena.",
"Review the context and speaker before making any decision; preserve the applicant's original materials.":"Pre odluke proveriti kontekst i govornika i sačuvati originalne materijale podnosioca.",
"The case may fit the free-access service, but additional information is needed before selection.":"Slučaj može odgovarati besplatnoj usluzi, ali su potrebne dodatne informacije pre izbora.",
"The case appears potentially relevant, but its value or technical complexity requires human scope review.":"Slučaj može biti relevantan, ali njegova vrednost ili tehnička složenost zahtevaju ljudsku proveru obima.",
"The case was assessed against the current free-access scope and evidence indicators.":"Slučaj je procenjen prema trenutnom obimu besplatne usluge i pokazateljima dokaza.",
"Place in the free-access candidate queue and request up to twenty key files if selected.":"Staviti u red kandidata za besplatan pristup i, ako bude izabran, zatražiti do dvadeset ključnih fajlova.",
}

def _localize_result(result: TriageResult, language: str) -> TriageResult:
    mapping = {"Russian": _RU, "Serbian": _SR, "French": _FR, "German": _DE, "Spanish": _ES}.get(language)
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
    amount_text = app.amount_in_dispute or app.order_value
    amount = _parse_amount(amount_text)
    currency = _detect_currency(amount_text)
    high_value = _amount_reaches_threshold(amount_text, HIGH_VALUE_THRESHOLDS)
    medium_value = _amount_reaches_threshold(amount_text, MEDIUM_VALUE_THRESHOLDS)

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
    if high_value:
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
    elif amount is not None and not currency:
        missing.append("Currency of the disputed amount")
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
        # Keyword matching cannot reliably identify the speaker or a negation.
        # A buyer reporting that a supplier requested evidence destruction must
        # never be auto-rejected. Reserve rejection for a human administrator.
        decision = "human_review"
        risk = "critical"
        strength = "unclear"
        public = "The description mentions possible alteration, concealment or fabrication of evidence. The context requires human review and the application has not been automatically rejected."
        action = "Review the context and speaker before making any decision; preserve the applicant's original materials."
    elif urgent:
        decision = "human_review"
        risk = "critical"
        strength = "unclear"
        public = "Your description may involve an urgent legal or authority matter. The automated free-access system cannot safely assess it without human review."
        action = "Escalate immediately; advise the applicant to seek a qualified professional where deadlines may apply."
    elif technical or high_value:
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
        risk = "medium" if medium_value else "low"
        strength = "supportable_for_review"
        public = "The application appears suitable for free-access review, subject to capacity and a final scope check."
        action = "Place in the free-access candidate queue and request up to twenty key files if selected."
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
    # No model-generated classification may reject a person automatically.
    # Human administrators retain the explicit declined status in the dashboard.
    if decision == "declined":
        decision = "human_review"
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
