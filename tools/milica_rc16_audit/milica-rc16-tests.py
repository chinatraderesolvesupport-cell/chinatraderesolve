#!/usr/bin/env python3
from __future__ import annotations
import argparse, re, sys, zipfile
from pathlib import Path


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"missing {label}: {needle}")


def forbid(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise AssertionError(f"forbidden {label}: {needle}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--apk')
    args = parser.parse_args()
    root = Path(args.root)
    service = (root/'app/src/main/java/rs/milicamusic/app/MilicaWakeService.java').read_text()
    activity = (root/'app/src/main/java/rs/milicamusic/app/MainActivity.java').read_text()
    js = (root/'app/src/main/assets/web/app.js').read_text()
    html = (root/'app/src/main/assets/web/index.html').read_text()
    manifest = (root/'app/src/main/AndroidManifest.xml').read_text()
    gradle = (root/'app/build.gradle').read_text()

    checks = [
        (gradle, 'versionCode 26', 'version code'),
        (gradle, "versionName '1.1-rc16'", 'version name'),
        (activity, 'MilicaMusicAndroid/1.1-rc16', 'user agent'),
        (service, 'putInt(PREF_MODEL_VERSION, 16)', 'model migration'),
        (service, 'ACTION_PAUSE', 'manual recognizer pause'),
        (service, 'ACTION_RESUME', 'manual recognizer resume'),
        (service, 'rc16CaptureGeneration', 'capture generation ownership'),
        (service, 'captureThread == Thread.currentThread()', 'capture owner check'),
        (service, 'rc16CaptureRestartPending', 'deferred restart'),
        (service, 'MediaRecorder.AudioSource.MIC', 'primary microphone'),
        (service, 'MediaRecorder.AudioSource.VOICE_RECOGNITION', 'fallback microphone'),
        (service, 'Audio source returns digital silence', 'dead-silence fallback'),
        (service, 'THREAD_PRIORITY_AUDIO', 'audio thread priority'),
        (service, 'if (!force && now - lastTelemetryAt < 500L) return;', 'telemetry throttle'),
        (service, 'putString(PREF_AUDIO_SOURCE, rc16AudioSource)', 'audio-source telemetry'),
        (service, 'if (level < 110.0 || features.length < 10)', 'tablet enrollment sensitivity'),
        (service, 'for (int i = 0; i < 8; i++)', 'stale template cleanup'),
        (activity, 'onJsPrompt', 'origin checked prompt bridge'),
        (activity, '__MILICA_NATIVE__', 'native bridge marker'),
        (activity, 'if (!isLocalUrl(url))', 'bridge origin rejection'),
        (activity, 'MIXED_CONTENT_NEVER_ALLOW', 'mixed-content hardening'),
        (activity, 'setAllowContentAccess(false)', 'content access hardening'),
        (activity, 'newFixedThreadPool(4)', 'bounded local server'),
        (activity, 'connection.setSoTimeout(15000)', 'socket timeout'),
        (activity, 'contentLength > 128 * 1024', 'request size rejection'),
        (manifest, 'android:allowBackup="false"', 'backup disabled'),
        (js, 'Milica Music RC16 — origin-checked native bridge', 'JS native shim'),
        (js, 'youtubeApiPromise = null;', 'YouTube API retry'),
        (js, 'const controller = new AbortController();', 'fetch timeout'),
        (js, 'source: "none"', 'source telemetry model'),
        (js, 'Повторить обучение имени', 'visible retraining button'),
        (js, 'audio_fallback', 'fallback UI state'),
        (js, 'paused_manual', 'manual handoff UI state'),
        (js, 'Recite „Milice“ četiri puta.', 'four sample instruction'),
        (js, 'if (!document.hidden) milicaRc10PollNativeDiagnostics();', 'low-rate diagnostics poll'),
    ]
    for text, needle, label in checks:
        require(text, needle, label)

    forbidden = [
        (service, 'AcousticEchoCanceler', 'OEM echo canceller'),
        (service, 'NoiseSuppressor', 'OEM noise suppressor'),
        (service, 'Thread.MAX_PRIORITY', 'Java max priority'),
        (activity, 'addJavascriptInterface', 'cross-frame JS interface'),
        (activity, 'JavascriptInterface', 'JS interface annotation'),
        (activity, 'MIXED_CONTENT_ALWAYS_ALLOW', 'mixed content always allow'),
        (activity, 'newCachedThreadPool', 'unbounded local server'),
        (manifest, 'android:allowBackup="true"', 'backup enabled'),
        (js, 'setInterval(rc15ExposeStatus, 350)', 'RC15 polling loop'),
        (js, 'enroll_5:', 'stale five-sample state'),
        (js, 'Recite „Milice“ tri puta.', 'stale three-sample instruction'),
    ]
    for text, needle, label in forbidden:
        forbid(text, needle, label)

    for match in re.finditer(r'<button\b([^>]*)>', html, flags=re.I):
        if not re.search(r'\btype\s*=', match.group(1), flags=re.I):
            raise AssertionError(f'button without type at offset {match.start()}')

    if args.apk:
        apk = Path(args.apk)
        if not apk.is_file() or apk.stat().st_size < 50_000:
            raise AssertionError('APK missing or unexpectedly small')
        with zipfile.ZipFile(apk) as archive:
            bad = archive.testzip()
            if bad:
                raise AssertionError(f'APK archive corruption at {bad}')
            names = set(archive.namelist())
            for needed in ('classes.dex', 'assets/web/app.js', 'assets/web/index.html', 'AndroidManifest.xml'):
                if needed not in names:
                    raise AssertionError(f'APK missing {needed}')
            if any(name.lower().endswith(('.jks', '.keystore')) for name in names):
                raise AssertionError('signing keystore embedded in APK')
            embedded_js = archive.read('assets/web/app.js').decode('utf-8')
            require(embedded_js, 'Milica Music RC16 — origin-checked native bridge', 'embedded RC16 JS')
            forbid(embedded_js, 'setInterval(rc15ExposeStatus, 350)', 'embedded RC15 loop')

    print('RC16 AUDIT TEST PASS')
    for label in [
        'capture-thread ownership and deferred restart',
        'MIC to VOICE_RECOGNITION fallback including digital silence',
        'bounded telemetry and server resources',
        'origin-checked native bridge',
        'manual recognizer microphone handoff',
        'four-step visible enrollment and retraining control',
        'YouTube and network timeout recovery',
        'backup, mixed-content and APK secret hardening',
    ]:
        print('  ✓', label)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f'RC16 AUDIT TEST FAIL: {error}', file=sys.stderr)
        raise SystemExit(1)
