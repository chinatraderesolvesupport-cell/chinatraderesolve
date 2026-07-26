from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


# Platform names are strong source indicators on their own.
_PLATFORM_TERMS = (
    "alibaba",
    "1688",
    "1688.com",
    "made-in-china",
    "made in china",
    "madeinchina",
    "global sources",
    "globalsources",
    "aliexpress",
    "ali express",
    "алибаба",
    "алиэкспресс",
    "али экспресс",
    "dhgate",
    "taobao",
    "таобао",
    "trade assurance",
)

# Geographic terms are intentionally broad, but they only become a source
# signal when the same message/context also mentions a commercial actor or
# transaction. This catches natural wording such as "из Китая пришёл брак"
# without alerting on every unrelated mention of China.
_GEOGRAPHY_TERMS = (
    "china",
    "chinese",
    "from china",
    "in china",
    "китай",
    "кита",
    "китая",
    "китае",
    "китайск",
    "из китая",
    "kina",
    "kine",
    "kini",
    "kinesk",
    "iz kine",
    "u kini",
    "chine",
    "chinois",
    "chinoise",
    "de chine",
    "en chine",
    "chinesisch",
    "aus china",
    "in china",
    "chino",
    "china",
    "de china",
    "en china",
)

_ACTOR_TERMS = (
    "supplier",
    "seller",
    "factory",
    "manufacturer",
    "vendor",
    "поставщик",
    "продавец",
    "фабрик",
    "производител",
    "посредник",
    "dobavljac",
    "dobavljač",
    "prodavac",
    "fabrika",
    "proizvodjac",
    "proizvođač",
    "fournisseur",
    "vendeur",
    "usine",
    "fabricant",
    "lieferant",
    "verkaufer",
    "verkäufer",
    "fabrik",
    "hersteller",
    "proveedor",
    "vendedor",
    "fabrica",
    "fábrica",
    "fabricante",
)

_TRANSACTION_TERMS = (
    # English
    "order",
    "goods",
    "product",
    "shipment",
    "cargo",
    "container",
    "sample",
    "batch",
    "invoice",
    "payment",
    "deposit",
    "prepayment",
    "paid",
    "transferred money",
    "wire transfer",
    "procurement",
    "purchasing",
    "sourcing",
    "business",
    "commerce",
    "import",
    # Russian
    "товар",
    "заказ",
    "партия",
    "груз",
    "посылк",
    "контейнер",
    "образец",
    "счет",
    "счёт",
    "инвойс",
    "оплат",
    "предоплат",
    "депозит",
    "перевел деньги",
    "перевёл деньги",
    "перечислил деньги",
    "деньги отправил",
    "закупк",
    "покупк",
    "бизнес",
    "торговл",
    "импорт",
    "ввоз",
    # Serbian
    "roba",
    "porudzbina",
    "porudžbina",
    "posiljka",
    "pošiljka",
    "uzorak",
    "faktura",
    "uplata",
    "depozit",
    "platio",
    "platila",
    "nabavka",
    "kupovina",
    "poslovanje",
    "trgovina",
    "uvoz",
    # French
    "commande",
    "marchandise",
    "produit",
    "expedition",
    "expédition",
    "cargaison",
    "echantillon",
    "échantillon",
    "facture",
    "paiement",
    "acompte",
    "depot",
    "dépôt",
    "achat",
    "approvisionnement",
    "commerce",
    "affaires",
    "importation",
    "import",
    # German
    "bestellung",
    "ware",
    "produkt",
    "lieferung",
    "sendung",
    "muster",
    "rechnung",
    "zahlung",
    "anzahlung",
    "einkauf",
    "beschaffung",
    "geschaft",
    "geschäft",
    "handel",
    "import",
    # Spanish
    "pedido",
    "mercancia",
    "mercancía",
    "producto",
    "envio",
    "envío",
    "carga",
    "muestra",
    "factura",
    "pago",
    "deposito",
    "depósito",
    "compra",
    "abastecimiento",
    "negocio",
    "comercio",
    "importacion",
    "importación",
    "import",
)

_PROBLEM_TERMS = (
    # English: refund/payment/dispute
    "refund",
    "money back",
    "chargeback",
    "dispute",
    "claim rejected",
    "claim closed",
    "refuses to refund",
    "refused a refund",
    "did not refund",
    "no refund",
    "kept the deposit",
    "lost my deposit",
    # English: delivery / quantity / quality / silence
    "not shipped",
    "never shipped",
    "did not ship",
    "not delivered",
    "never delivered",
    "never arrived",
    "did not arrive",
    "missing items",
    "short shipment",
    "less than ordered",
    "defective",
    "damaged",
    "broken",
    "poor quality",
    "bad quality",
    "terrible quality",
    "wrong product",
    "wrong material",
    "wrong size",
    "wrong color",
    "not as described",
    "does not match the sample",
    "counterfeit",
    "fake certificate",
    "invalid certificate",
    "seller disappeared",
    "supplier disappeared",
    "seller stopped replying",
    "supplier stopped replying",
    "does not reply",
    "blocked me",
    "scam",
    "fraud",
    "customs problem",
    "stuck in customs",
    # Russian
    "возврат",
    "вернуть деньги",
    "не возвращ",
    "не вернул",
    "не вернули",
    "деньги не вернули",
    "удержал предоплату",
    "удержали предоплату",
    "пропала предоплата",
    "спор",
    "закрыли спор",
    "спор закрыт",
    "отклонили спор",
    "отказали в споре",
    "алибаба не помог",
    "не отправ",
    "не достав",
    "не приш",
    "не получил",
    "не получила",
    "недостач",
    "недолож",
    "прислали меньше",
    "меньше товар",
    "не комплект",
    "бракован",
    "товар с браком",
    "пришел брак",
    "пришёл брак",
    "весь брак",
    "дефект",
    "поврежден",
    "повреждён",
    "сломал",
    "сломано",
    "плохое качество",
    "ужасное качество",
    "некачествен",
    "не соответствует",
    "не совпадает",
    "не тот товар",
    "не тот материал",
    "другой материал",
    "другого материала",
    "не тот размер",
    "не тот цвет",
    "поддел",
    "ложный сертификат",
    "недействительный сертификат",
    "сертификат не действ",
    "продавец пропал",
    "поставщик пропал",
    "пропал",
    "исчез",
    "перестал отвечать",
    "не отвечает",
    "игнорирует",
    "заблокировал",
    "кинул",
    "кинули",
    "обман",
    "мошен",
    "застрял на таможне",
    "проблема с таможней",
    # Serbian (Latin)
    "povracaj",
    "povraćaj",
    "vrati novac",
    "nije vratio novac",
    "nije vratila novac",
    "spor",
    "odbijen spor",
    "zatvoren spor",
    "nije poslato",
    "nije poslao",
    "nije isporuceno",
    "nije isporučeno",
    "nije stiglo",
    "nedostaje roba",
    "manje robe",
    "neispravno",
    "neispravn",
    "osteceno",
    "oštećeno",
    "los kvalitet",
    "loš kvalitet",
    "loseg kvalitet",
    "lošeg kvalitet",
    "pogresan proizvod",
    "pogrešan proizvod",
    "pogresan materijal",
    "pogrešan materijal",
    "ne odgovara uzorku",
    "lazni sertifikat",
    "lažni sertifikat",
    "prodavac ne odgovara",
    "dobavljac ne odgovara",
    "dobavljač ne odgovara",
    "prodavac je nestao",
    "nestao",
    "nestala",
    "prevara",
    "carina",
    # French
    "remboursement",
    "ne rembourse pas",
    "n a pas rembourse",
    "n'a pas remboursé",
    "litige",
    "litige refuse",
    "litige rejeté",
    "non expedie",
    "non expédié",
    "pas expedie",
    "pas expédié",
    "non livre",
    "non livré",
    "jamais arrive",
    "jamais arrivé",
    "articles manquants",
    "quantite insuffisante",
    "quantité insuffisante",
    "defectueux",
    "défectueux",
    "endommage",
    "endommagé",
    "mauvaise qualite",
    "mauvaise qualité",
    "mauvais produit",
    "mauvais materiau",
    "mauvais matériau",
    "ne correspond pas",
    "faux certificat",
    "certificat invalide",
    "vendeur ne repond pas",
    "vendeur ne répond pas",
    "fournisseur a disparu",
    "a disparu",
    "disparu",
    "arnaque",
    "fraude",
    "douane",
    # German
    "ruckerstattung",
    "rückerstattung",
    "geld nicht zuruck",
    "geld nicht zurück",
    "streitfall",
    "fall abgelehnt",
    "nicht versendet",
    "nicht geliefert",
    "nicht angekommen",
    "fehlende ware",
    "zu wenig ware",
    "mangelhaft",
    "beschadigt",
    "beschädigt",
    "schlechte qualitat",
    "schlechte qualität",
    "falsches produkt",
    "falsches material",
    "entspricht nicht dem muster",
    "gefalschtes zertifikat",
    "gefälschtes zertifikat",
    "ungultiges zertifikat",
    "ungültiges zertifikat",
    "verkaufer antwortet nicht",
    "verkäufer antwortet nicht",
    "lieferant verschwunden",
    "verschwunden",
    "antwortet nicht",
    "fehlt ware",
    "betrug",
    "zoll",
    # Spanish
    "reembolso",
    "no devuelve el dinero",
    "no devolvio el dinero",
    "no devolvió el dinero",
    "disputa",
    "disputa rechazada",
    "disputa cerrada",
    "no enviado",
    "no envio",
    "no envió",
    "no entregado",
    "nunca llego",
    "nunca llegó",
    "faltan productos",
    "menos mercancia",
    "menos mercancía",
    "defectuoso",
    "defectuosa",
    "danado",
    "dañado",
    "danada",
    "dañada",
    "mala calidad",
    "producto equivocado",
    "material equivocado",
    "no coincide con la muestra",
    "certificado falso",
    "certificado invalido",
    "certificado inválido",
    "vendedor no responde",
    "proveedor desaparecio",
    "proveedor desapareció",
    "desaparecio",
    "desapareció",
    "estafa",
    "fraude",
    "aduana",
)

_HELP_TERMS = (
    # English
    "what should i do",
    "what can i do",
    "how can i get my money back",
    "how to get a refund",
    "where can i complain",
    "please help",
    "need help",
    "need advice",
    "has anyone dealt with",
    "anyone had this problem",
    "lawyer",
    "legal help",
    # Russian
    "что делать",
    "как вернуть деньги",
    "как получить возврат",
    "куда жаловаться",
    "куда обратиться",
    "помогите",
    "нужна помощь",
    "нужен совет",
    "подскажите",
    "кто сталкивался",
    "у кого было",
    "нужен юрист",
    "юридическая помощь",
    # Serbian
    "sta da radim",
    "šta da radim",
    "kako da vratim novac",
    "gde da se zalim",
    "gde da se žalim",
    "molim za pomoc",
    "molim za pomoć",
    "treba mi pomoc",
    "treba mi pomoć",
    "treba mi savet",
    "da li je neko imao",
    "pravna pomoc",
    "pravna pomoć",
    # French
    "que faire",
    "comment recuperer mon argent",
    "comment récupérer mon argent",
    "ou porter plainte",
    "où porter plainte",
    "aidez-moi",
    "besoin d aide",
    "besoin d'aide",
    "besoin de conseil",
    "quelqu un a deja",
    "quelqu'un a déjà",
    "aide juridique",
    # German
    "was soll ich tun",
    "wie bekomme ich mein geld zuruck",
    "wie bekomme ich mein geld zurück",
    "wo kann ich mich beschweren",
    "bitte helfen",
    "brauche hilfe",
    "brauche rat",
    "hat jemand erfahrung",
    "rechtliche hilfe",
    # Spanish
    "que puedo hacer",
    "qué puedo hacer",
    "como recuperar mi dinero",
    "cómo recuperar mi dinero",
    "donde reclamar",
    "dónde reclamar",
    "ayuda por favor",
    "necesito ayuda",
    "necesito consejo",
    "alguien ha pasado por esto",
    "ayuda legal",
)

# Direct phrases are reserved for high-confidence China/platform-specific cases.
# Generic phrases such as "supplier scam" are intentionally not direct matches;
# they require China/platform context from the message or chat title.
_DIRECT_PHRASES = (
    "alibaba dispute",
    "alibaba refund",
    "alibaba scam",
    "alibaba claim rejected",
    "trade assurance claim",
    "trade assurance rejected",
    "1688 refund",
    "1688 dispute",
    "chinese supplier scam",
    "supplier from china disappeared",
    "goods from china are defective",
    "defective goods from china",
    "товар из китая не отправлен",
    "товар из китая не пришел",
    "товар из китая не пришёл",
    "из китая пришел брак",
    "из китая пришёл брак",
    "из китая пришли бракованные товары",
    "китайский поставщик не отправил",
    "китайский продавец не отправил",
    "китайский продавец пропал",
    "китайский поставщик пропал",
    "вернуть деньги с alibaba",
    "алибаба закрыла спор",
    "алибаба отказала в возврате",
    "kineski dobavljac prevara",
    "kineski dobavljač prevara",
    "litige alibaba",
    "remboursement alibaba",
    "alibaba streitfall",
    "alibaba ruckerstattung",
    "alibaba rückerstattung",
    "disputa alibaba",
    "reembolso alibaba",
)

_GENERIC_PROBLEM_TERMS = frozenset(
    {
        "refund",
        "money back",
        "chargeback",
        "dispute",
        "возврат",
        "спор",
        "povracaj",
        "povraćaj",
        "spor",
        "remboursement",
        "litige",
        "ruckerstattung",
        "rückerstattung",
        "streitfall",
        "reembolso",
        "disputa",
    }
)


_DEFAULT_EXCLUDES = (
    "job vacancy",
    "hiring",
    "вакансия",
    "ищем сотрудника",
    "курс обучения",
    "webinar",
    "вебинар",
    "crypto signal",
    "bitcoin signal",
    "alibaba stock",
    "alibaba shares",
    "акции alibaba",
    "акции алибаба",
    "курс акций alibaba",
    "инвестиции в alibaba",
    "alibaba aktie",
    "acciones de alibaba",
    "actions alibaba",
)


@dataclass(frozen=True)
class MatchResult:
    relevant: bool
    source_hits: tuple[str, ...] = ()
    problem_hits: tuple[str, ...] = ()
    direct_hits: tuple[str, ...] = ()
    help_hits: tuple[str, ...] = ()
    transaction_hits: tuple[str, ...] = ()
    excluded_hits: tuple[str, ...] = ()
    reason: str = ""

    @property
    def labels(self) -> tuple[str, ...]:
        labels: list[str] = []

        platform_names = []
        for hit in self.source_hits:
            normalized = normalize_text(hit)
            if normalized in {normalize_text(item) for item in _PLATFORM_TERMS}:
                platform_names.append(hit)
        if platform_names:
            labels.extend(f"платформа: {value}" for value in dict.fromkeys(platform_names))
        elif self.source_hits:
            labels.append("источник: Китай / китайский поставщик")

        problem_text = " ".join(normalize_text(item) for item in self.problem_hits)
        category_rules = (
            (
                ("not ship", "not deliver", "never arriv", "не отправ", "не достав", "не приш", "nije pos", "nije ispor", "non exped", "non livr", "nicht versendet", "nicht geliefert", "no envi", "no entreg"),
                "проблема: неотправка или недоставка",
            ),
            (
                ("refund", "money back", "возврат", "не вернул", "povrac", "rembourse", "ruckerst", "rückerst", "reembolso"),
                "проблема: возврат денег",
            ),
            (
                ("defect", "damag", "broken", "quality", "брак", "дефект", "повреж", "качеств", "neispr", "ostec", "ošteć", "kvalitet", "défect", "endommag", "qualit", "mangel", "beschad", "beschäd", "defectuos", "danad", "dañad", "calidad"),
                "проблема: брак или плохое качество",
            ),
            (
                ("wrong", "not as described", "does not match", "не соответствует", "не совпадает", "не тот", "другой материал", "pogres", "pogreš", "ne odgovara", "mauvais", "ne correspond", "falsch", "entspricht nicht", "equivocado", "no coincide"),
                "проблема: несоответствие заказу или образцу",
            ),
            (
                ("missing", "short shipment", "less than", "недостач", "недолож", "меньше товар", "nedostaje", "manje robe", "articles manquants", "quantit", "fehlende ware", "zu wenig", "faltan", "menos mercanc"),
                "проблема: недостача или неполная комплектация",
            ),
            (
                ("dispute", "claim", "спор", "litige", "streitfall", "disputa"),
                "проблема: спор или отклонённая претензия",
            ),
            (
                ("certificate", "customs", "сертификат", "тамож", "sertifikat", "carin", "certificat", "douane", "zertifikat", "zoll", "certificado", "aduana"),
                "проблема: сертификат или таможня",
            ),
            (
                ("disappear", "reply", "blocked", "scam", "fraud", "пропал", "исчез", "отвеч", "игнор", "заблок", "кинул", "обман", "мошен", "nestao", "odgovara", "prevara", "disparu", "répond", "repond", "arnaque", "fraude", "verschwunden", "antwortet", "betrug", "desaparec", "responde", "estafa"),
                "проблема: продавец исчез или не отвечает",
            ),
        )
        for needles, label in category_rules:
            if any(needle in problem_text for needle in needles):
                labels.append(label)

        if self.help_hits:
            labels.append("сообщение: человек просит помощи")
        if self.direct_hits and not labels:
            labels.append("прямая фраза о споре с китайским поставщиком")

        return tuple(dict.fromkeys(labels))[:8]


def parse_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def normalize_text(value: str | None) -> str:
    text = (value or "").casefold()
    text = text.replace("ё", "е")
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^\w\s\-]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _hits(text: str, terms: Iterable[str]) -> tuple[str, ...]:
    found = [term for term in terms if normalize_text(term) in text]
    return tuple(dict.fromkeys(found))


def classify_message(
    text: str | None,
    *,
    context_text: str | None = None,
    extra_phrases: Iterable[str] = (),
    exclude_phrases: Iterable[str] = (),
) -> MatchResult:
    """Classify one Telegram message using message and public-chat context.

    Problem/help terms must be present in the message itself. The public chat
    title/username may only contribute China/platform source context. This lets
    a message such as "Мне не вернули деньги, что делать?" match inside a chat
    called "Закупки из Китая", while the same sentence in an unrelated chat is
    ignored.
    """

    normalized = normalize_text(text)
    if len(normalized) < 8:
        return MatchResult(False)

    context = normalize_text(context_text)
    source_space = f"{normalized} {context}".strip()

    excludes = _hits(normalized, (*_DEFAULT_EXCLUDES, *exclude_phrases))
    if excludes:
        return MatchResult(False, excluded_hits=excludes, reason="excluded")

    direct = _hits(normalized, (*_DIRECT_PHRASES, *extra_phrases))

    message_platform_hits = _hits(normalized, _PLATFORM_TERMS)
    context_platform_hits = _hits(context, _PLATFORM_TERMS)
    message_geography_hits = _hits(normalized, _GEOGRAPHY_TERMS)
    context_geography_hits = _hits(context, _GEOGRAPHY_TERMS)
    message_actor_hits = _hits(normalized, _ACTOR_TERMS)
    context_actor_hits = _hits(context, _ACTOR_TERMS)

    problems = _hits(normalized, _PROBLEM_TERMS)
    specific_problems = tuple(
        item for item in problems if item not in _GENERIC_PROBLEM_TERMS
    )
    help_hits = _hits(normalized, _HELP_TERMS)
    transactions = _hits(normalized, _TRANSACTION_TERMS)
    context_transactions = _hits(context, _TRANSACTION_TERMS)

    source_from_message = bool(
        message_platform_hits
        or (
            message_geography_hits
            and (message_actor_hits or transactions)
        )
    )
    source_from_context = bool(
        context_platform_hits
        or (
            context_geography_hits
            and (context_actor_hits or context_transactions)
        )
    )
    source_context = source_from_message or source_from_context

    source_hits: tuple[str, ...] = ()
    if source_context:
        source_hits = tuple(
            dict.fromkeys(
                message_platform_hits
                + context_platform_hits
                + message_geography_hits
                + context_geography_hits
                + message_actor_hits
                + context_actor_hits
            )
        )[:12]

    if direct:
        relevant = True
        reason = "direct_china_supplier_phrase"
    elif source_from_message and problems:
        relevant = True
        reason = "source_and_problem"
    elif source_from_context and specific_problems:
        relevant = True
        reason = "chat_context_and_specific_problem"
    elif source_context and help_hits and transactions:
        relevant = True
        reason = "source_help_and_transaction"
    else:
        relevant = False
        reason = "insufficient_context"

    return MatchResult(
        relevant,
        source_hits=source_hits,
        problem_hits=problems,
        direct_hits=direct,
        help_hits=help_hits,
        transaction_hits=transactions,
        reason=reason,
    )


def public_message_link(username: str | None, message_id: int | None) -> str | None:
    clean = (username or "").strip().lstrip("@")
    if not clean or not message_id or message_id <= 0:
        return None
    return f"https://t.me/{clean}/{message_id}"


def message_fingerprint(chat_id: int | str, message_id: int | str) -> str:
    raw = f"{chat_id}:{message_id}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def compact_excerpt(text: str | None, limit: int = 700) -> str:
    value = re.sub(r"\s+", " ", (text or "")).strip()
    if len(value) <= limit:
        return value
    return value[: max(1, limit - 1)].rstrip() + "…"


def _format_author(author_name: str | None, author_username: str | None) -> str:
    name = (author_name or "").strip()
    username = (author_username or "").strip().lstrip("@")
    if name and username:
        return f"{name} (@{username})"
    if username:
        return f"@{username}"
    if name:
        return name
    return "не указан Telegram"


def _format_time(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        suffix = " UTC" if value.tzinfo is not None else ""
        return value.strftime("%d.%m.%Y %H:%M") + suffix
    return str(value).strip() or None


def _format_reason(value: str | None) -> str | None:
    mapping = {
        "direct_china_supplier_phrase": "прямая формулировка о споре с китайским поставщиком",
        "source_and_problem": "источник сделки + конкретная проблема",
        "chat_context_and_specific_problem": "китайский контекст группы + конкретная проблема",
        "source_help_and_transaction": "источник сделки + просьба о помощи",
    }
    if not value:
        return None
    return mapping.get(value, value)


def format_alert(
    *,
    chat_title: str,
    username: str | None,
    text: str,
    labels: Iterable[str],
    link: str | None,
    author_name: str | None = None,
    author_username: str | None = None,
    source_type: str | None = None,
    message_time: datetime | str | None = None,
    match_reason: str | None = None,
    test_mode: bool = False,
) -> str:
    handle = f" (@{username.lstrip('@')})" if username else ""
    label_text = ", ".join(dict.fromkeys(labels)) or "supplier dispute context"
    headline = "🧪 ТЕСТ МОНИТОРА — РЕАЛЬНОГО КЛИЕНТА НЕТ" if test_mode else "🚨 РЕАЛЬНАЯ НАХОДКА В TELEGRAM"
    parts = [
        headline,
        "",
        f"Где найдено: {chat_title}{handle}",
    ]
    if source_type:
        parts.append(f"Тип источника: {source_type}")
    if not test_mode:
        parts.append(f"Кто написал: {_format_author(author_name, author_username)}")
    formatted_time = _format_time(message_time)
    if formatted_time:
        parts.append(f"Когда: {formatted_time}")
    readable_reason = _format_reason(match_reason)
    if readable_reason:
        parts.append(f"Причина отбора: {readable_reason}")
    parts.extend(
        (
            f"Совпадения: {label_text}",
            "",
            "Текст сообщения:",
            compact_excerpt(text),
        )
    )
    if link:
        parts.extend(("", "Открыть исходное сообщение:", link))
    return html.unescape("\n".join(parts))[:3900]
