from pathlib import Path


def test_language_sensitive_links_have_server_rendered_fallbacks():
    template = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "templates"
        / "index.html"
    ).read_text(encoding="utf-8")

    expected = (
        'href="/static/sample_case_assessment.html?lang={{ page_language }}"',
        'href="/privacy?lang={{ page_language }}"',
        'href="/static/terms.html?lang={{ page_language }}"',
        'href="/static/refund.html?lang={{ page_language }}"',
        'href="/static/ai-notice.html?lang={{ page_language }}"',
        'href="/static/disclaimer.html?lang={{ page_language }}"',
        'href="/support?lang={{ page_language }}"',
    )
    for marker in expected:
        assert marker in template
