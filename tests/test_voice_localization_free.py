from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_voice_ui_uses_real_interim_results_and_preserves_editable_text():
    source = (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
    assert "recognition.interimResults=true" in source
    assert "recognition.continuous=true" in source
    assert "applyAiLiveTranscript" in source
    assert "aiChatInput.disabled=aiChatBusy;" in source
    assert "uploadVoiceRecording(blob,aiVoiceBaseText)" in source
    assert "max-height:min(280px,34dvh)" in source
    assert "voice_live_unavailable" in source


def test_voice_recording_and_email_hint_are_localized():
    translations = json.loads(
        (ROOT / "app" / "static" / "translations-v2.json").read_text(encoding="utf-8")
    )
    expected = {"en", "ru", "sr", "de", "fr", "es"}
    assert set(translations) == expected
    for language in expected:
        assert translations[language]["email_spam_hint"].strip()
        assert "—" in translations[language]["ai_voice_recording"]
        assert translations[language]["description_voice_recording"].strip()

    index = (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
    public_status = (ROOT / "app" / "templates" / "public_status.html").read_text(encoding="utf-8")
    assert 'data-i18n="email_spam_hint"' in index
    assert "message_copy.email_hint" in public_status


def test_legacy_analysis_display_localization_does_not_mutate_report():
    from app.document_analysis import localize_report_for_display

    report = {
        "summary": "Payment was not evidenced in the uploaded materials.",
        "timeline": [{"confidence": "high", "event": "Date not visible"}],
        "missing_evidence": ["Payment not evidenced in the uploaded materials"],
        "source_files": ["invoice.pdf"],
    }
    localized = localize_report_for_display(report, "Russian")
    assert "не подтверждено загруженными материалами" in localized["summary"]
    assert "дата не видна" in localized["timeline"][0]["event"]
    assert report["summary"] == "Payment was not evidenced in the uploaded materials."
    assert report["timeline"][0]["confidence"] == "high"


def test_admin_analysis_uses_localized_confidence_and_missing_evidence():
    source = (ROOT / "app" / "templates" / "admin_case.html").read_text(encoding="utf-8")
    assert '{"high":"Высокая","medium":"Средняя","low":"Низкая"}' in source
    assert "не подтверждено загруженными материалами" in source


def test_free_service_copy_is_explicit_in_future_notification_and_ai_prompt():
    notifications = (ROOT / "app" / "notifications.py").read_text(encoding="utf-8")
    assert "ChinaTradeResolve is a free service and no payment is required." in notifications
    assert "ChinaTradeResolve работает бесплатно, и оплата за помощь не требуется." in notifications
    assert "Key documents are requested only after the application has passed preliminary screening." not in notifications
    assistant = (ROOT / "app" / "ai_assistant.py").read_text(encoding="utf-8")
    assert "A voluntary contribution is optional, is not payment for a service" in assistant
