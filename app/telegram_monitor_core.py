from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass
from typing import Iterable


_SOURCE_TERMS = (
    "alibaba",
    "1688",
    "made-in-china",
    "made in china",
    "chinese supplier",
    "china supplier",
    "chinese seller",
    "china seller",
    "chinese factory",
    "china factory",
    "supplier in china",
    "supplier from china",
    "поставщик из китая",
    "китайский поставщик",
    "китайский продавец",
    "китайская фабрика",
    "продавец на алибаба",
    "алибаба",
    "dobavljač iz kine",
    "kineski dobavljač",
    "kineski prodavac",
    "fournisseur chinois",
    "fournisseur en chine",
    "vendeur chinois",
    "chinesischer lieferant",
    "lieferant aus china",
    "chinesischer verkäufer",
    "proveedor chino",
    "proveedor de china",
    "vendedor chino",
)

_PROBLEM_TERMS = (
    "refund",
    "money back",
    "chargeback",
    "dispute",
    "trade assurance",
    "not shipped",
    "never shipped",
    "did not ship",
    "not delivered",
    "never arrived",
    "did not arrive",
    "defective",
    "poor quality",
    "bad quality",
    "wrong product",
    "fake product",
    "counterfeit",
    "scam",
    "fraud",
    "seller refuses",
    "supplier refuses",
    "возврат",
    "вернуть деньги",
    "спор",
    "не отправил",
    "не отправлен",
    "не доставлен",
    "не пришел",
    "не пришёл",
    "брак",
    "дефект",
    "плохое качество",
    "некачественный",
    "не тот товар",
    "подделка",
    "обман",
    "мошенник",
    "отказывается вернуть",
    "povraćaj",
    "spor",
    "nije poslato",
    "nije isporučeno",
    "nije stiglo",
    "neispravno",
    "loš kvalitet",
    "prevara",
    "remboursement",
    "litige",
    "non expédié",
    "non livré",
    "défectueux",
    "mauvaise qualité",
    "arnaque",
    "rückerstattung",
    "streitfall",
    "nicht versendet",
    "nicht geliefert",
    "mangelhaft",
    "schlechte qualität",
    "betrug",
    "reembolso",
    "disputa",
    "no enviado",
    "no entregado",
    "defectuoso",
    "mala calidad",
    "estafa",
)

_DIRECT_PHRASES = (
    "alibaba dispute",
    "alibaba refund",
    "alibaba scam",
    "trade assurance claim",
    "товар не отправлен",
    "товар не пришел",
    "товар не пришёл",
    "поставщик не отправил",
    "продавец не отправил",
    "вернуть деньги с alibaba",
    "спор с поставщиком",
    "supplier scam",
    "supplier did not ship",
    "seller did not ship",
    "supplier refuses refund",
    "kineski dobavljač prevara",
    "litige alibaba",
    "alibaba streitfall",
    "disputa alibaba",
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
)


@dataclass(frozen=True)
class MatchResult:
    relevant: bool
    source_hits: tuple[str, ...] = ()
    problem_hits: tuple[str, ...] = ()
    direct_hits: tuple[str, ...] = ()
    excluded_hits: tuple[str, ...] = ()

    @property
    def labels(self) -> tuple[str, ...]:
        values = self.direct_hits + self.source_hits + self.problem_hits
        return tuple(dict.fromkeys(values))


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
    extra_phrases: Iterable[str] = (),
    exclude_phrases: Iterable[str] = (),
) -> MatchResult:
    normalized = normalize_text(text)
    if len(normalized) < 12:
        return MatchResult(False)

    excludes = _hits(normalized, (*_DEFAULT_EXCLUDES, *exclude_phrases))
    if excludes:
        return MatchResult(False, excluded_hits=excludes)

    direct = _hits(normalized, (*_DIRECT_PHRASES, *extra_phrases))
    sources = _hits(normalized, _SOURCE_TERMS)
    problems = _hits(normalized, _PROBLEM_TERMS)

    relevant = bool(direct or (sources and problems))
    return MatchResult(
        relevant,
        source_hits=sources,
        problem_hits=problems,
        direct_hits=direct,
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


def format_alert(
    *,
    chat_title: str,
    username: str | None,
    text: str,
    labels: Iterable[str],
    link: str | None,
) -> str:
    handle = f" (@{username.lstrip('@')})" if username else ""
    label_text = ", ".join(dict.fromkeys(labels)) or "relevant supplier dispute"
    parts = [
        "🔎 Найдено релевантное сообщение в Telegram",
        f"Источник: {chat_title}{handle}",
        f"Совпадения: {label_text}",
        "",
        compact_excerpt(text),
    ]
    if link:
        parts.extend(("", link))
    return html.unescape("\n".join(parts))[:3900]
