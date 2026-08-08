import json
from pathlib import Path

import pytest

from app.ai_assistant import (
    ERROR_COPY,
    LANGUAGE_NAMES,
    UPLOAD_DESTINATION_COPY,
    _clean_output_text,
    _developer_prompt,
    _normalise_scope_text,
    assistant_scope_reply,
    localized_error,
)
from app.schemas import AssistantChatRequest
from app.voice_transcription import LANGUAGE_CODES


ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("en", "fr", "de", "es", "ru", "sr")


def _payload(language: str, *messages: str) -> AssistantChatRequest:
    conversation = []
    for index, message in enumerate(messages):
        if index:
            conversation.append({"role": "assistant", "content": "OK"})
        conversation.append({"role": "user", "content": message})
    return AssistantChatRequest(language=language, messages=conversation)


def test_all_public_languages_have_complete_local_error_copy() -> None:
    expected_kinds = set(ERROR_COPY["en"])
    assert set(ERROR_COPY) == set(LANGUAGES)
    for language in LANGUAGES:
        assert set(ERROR_COPY[language]) == expected_kinds
        assert all(value.strip() for value in ERROR_COPY[language].values())

    # A present key is not enough: the regression that triggered this audit was
    # an English fallback shown inside the Serbian UI.
    for language in ("fr", "de", "es", "ru", "sr"):
        for kind in expected_kinds:
            assert ERROR_COPY[language][kind] != ERROR_COPY["en"][kind]
            assert localized_error(language, kind) == ERROR_COPY[language][kind]


@pytest.mark.parametrize("language", LANGUAGES)
def test_ai_prompt_forces_selected_website_language(language: str) -> None:
    prompt = _developer_prompt(language)
    assert f"Answer in {LANGUAGE_NAMES[language]}." in prompt
    assert "The selected website language is authoritative." in prompt


def test_serbian_prompt_explicitly_supports_both_scripts() -> None:
    prompt = _developer_prompt("sr")
    assert "both Latin and Cyrillic Serbian" in prompt
    assert "mirror the Serbian script" in prompt


def test_serbian_cyrillic_normalization_keeps_original_and_adds_latin_match_form() -> None:
    normalized = _normalise_scope_text(
        "Кинески добављач, поруџбина и плаћање"
    )
    assert "добављач" in normalized
    assert "dobavljac" in normalized
    assert "porudzbina" in normalized
    assert "placanje" in normalized


def test_serbian_cyrillic_supplier_dispute_reaches_ai_scope() -> None:
    payload = _payload(
        "sr",
        "Кинески добављач није испоручио робу и не враћа новац. Шта да радим?",
    )
    assert assistant_scope_reply(payload) is None


def test_serbian_cyrillic_upload_question_gets_serbian_local_reply() -> None:
    payload = _payload(
        "sr",
        "Где да пошаљем документе за спор са кинеским добављачем?",
    )
    assert assistant_scope_reply(payload) == UPLOAD_DESTINATION_COPY["sr"]
    assert assistant_scope_reply(payload) != UPLOAD_DESTINATION_COPY["en"]


def test_serbian_cyrillic_followup_stays_in_supplier_context() -> None:
    payload = _payload(
        "sr",
        "Кинески добављач није испоручио поруџбину и не враћа новац.",
        "Шта да радим?",
    )
    assert assistant_scope_reply(payload) is None


def test_russian_scope_and_upload_matching_are_not_regressed_by_serbian_support() -> None:
    assert assistant_scope_reply(
        _payload("ru", "Китайский поставщик не прислал товар и не возвращает деньги.")
    ) is None
    assert assistant_scope_reply(
        _payload("ru", "Куда отправить документы по спору с поставщиком?")
    ) == UPLOAD_DESTINATION_COPY["ru"]


def test_unicode_cleaner_preserves_serbian_latin_and_cyrillic() -> None:
    value = "Dobavljač nije odgovorio. Добављач није одговорио."
    assert _clean_output_text(value) == value


def test_voice_language_sets_cover_all_public_languages() -> None:
    assert LANGUAGE_CODES == set(LANGUAGES)
    index_html = (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
    assert "sr:'sr-RS'" in index_html
    assert "data.append('language',document.documentElement.lang)" in index_html
    assert "language:document.documentElement.lang" in index_html


def test_language_runtime_patch_loads_after_base_translation_bundle() -> None:
    index_html = (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
    base_pos = index_html.index('/static/translations-v2.js')
    patch_pos = index_html.index('/static/launch-i18n-v3.js')
    assert base_pos < patch_pos


def test_primary_home_copy_is_language_specific() -> None:
    translations = json.loads(
        (ROOT / "app" / "static" / "translations-v2.json").read_text(encoding="utf-8")
    )
    critical_keys = (
        "hero_title",
        "form_title",
        "ai_chat_button",
        "ai_chat_welcome",
        "ai_voice_cta",
        "description_voice_cta",
    )
    for language in ("fr", "de", "es", "ru", "sr"):
        for key in critical_keys:
            assert translations[language][key].strip()
            assert translations[language][key] != translations["en"][key]


def test_runtime_ai_and_voice_fallbacks_are_localized() -> None:
    launcher = (ROOT / "app" / "static" / "launch-i18n-v3.js").read_text(encoding="utf-8")
    expected = {
        "ru": "Сообщение отправить не удалось. Попробуйте ещё раз.",
        "sr": "Poruka nije mogla da se pošalje. Pokušajte ponovo.",
        "fr": "Le message n’a pas pu être envoyé. Veuillez réessayer.",
        "de": "Die Nachricht konnte nicht gesendet werden. Bitte versuchen Sie es erneut.",
        "es": "No se pudo enviar el mensaje. Inténtelo de nuevo.",
    }
    for text in expected.values():
        assert text in launcher

    # The same patch layer also protects microphone errors from silently falling
    # back to English when a newer runtime key is missing from an older bundle.
    for key in ("ai_chat_error", "ai_voice_error", "description_voice_error", "voice_timeout"):
        assert launcher.count(f'{key}:') == len(LANGUAGES)
