from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[1] / "app/templates/index.html").read_text()


def test_voice_timer_is_cumulative_and_pauses_on_stop():
    assert "voiceCaptureElapsedBeforeSegment" in SOURCE
    assert "voiceCapturePauseTimer();" in SOURCE
    assert "voiceCaptureStartTimer();" in SOURCE
    assert "voiceCaptureResetTimer();" in SOURCE


def test_voice_segments_use_real_line_breaks_and_capitalization_helper():
    assert "function joinVoiceTranscript(baseText,transcript)" in SOURCE
    assert "capitalizeVoiceSegment(text)" in SOURCE
    assert "joinVoiceTranscript(base,transcript)" in SOURCE
    assert "joinVoiceTranscript(baseText,transcript)" in SOURCE
    assert "join('\\\\n\\\\n')" not in SOURCE


def test_ai_uses_the_large_composer_modal_for_manual_input():
    assert "openVoiceCaptureModal('assistant',aiChatInput.value)" in SOURCE
    assert "voiceCaptureApplyAction=()=>{const text=voiceCaptureDraft.slice(0,1500).trim();" in SOURCE
    assert "assistantLabel:'Вопрос для ИИ-помощника'" in SOURCE
    assert "assistantApply:'Отправить ИИ'" in SOURCE
