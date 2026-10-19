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


def test_ai_opens_text_first_and_keeps_large_composer_for_voice():
    opening=SOURCE.split('function openAiChat(){',1)[1].split('function closeAiChat',1)[0]
    assert 'openVoiceCaptureModal' not in opening
    assert 'aiChatInput.focus' in opening
    assert "openVoiceCaptureModal('assistant',startText)" in SOURCE
    assert "voiceCaptureApplyAction=()=>{const text=voiceCaptureDraft.slice(0,1500).trim();" in SOURCE
    assert "assistantLabel:'Вопрос для ИИ-помощника'" in SOURCE
    assert "assistantApply:'Отправить ИИ'" in SOURCE


def test_ai_consent_in_large_composer_does_not_leave_recording_pending():
    assert "function requestAiVoiceStart()" in SOURCE
    assert "const modalOpen=voiceCaptureMode==='assistant'&&voiceCaptureModal&&!voiceCaptureModal.hidden" in SOURCE
    assert "if(modalOpen&&!voiceCaptureRecordingStarted)requestAiVoiceStart()" in SOURCE


def test_completed_voice_text_gets_safe_readable_formatting():
    assert "function joinVoiceTranscript(baseText,transcript)" in SOURCE
    assert "function joinVoiceTranscript(baseText,formatFinalVoiceText(transcript))" not in SOURCE
    assert "function formatFinalVoiceText(value)" in SOURCE
    assert "message.type==='completed'?formatFinalVoiceText" in SOURCE
    assert "joinVoiceTranscript(normalizedBase,formatFinalVoiceText(transcript))" in SOURCE
