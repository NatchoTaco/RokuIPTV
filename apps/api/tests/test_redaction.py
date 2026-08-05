import logging

from streamforge_api.core.logging import JsonFormatter
from streamforge_api.core.redaction import redact_payload, redact_text, redact_url


def test_redact_url_masks_userinfo_and_sensitive_query_values() -> None:
    raw_url = (
        "http://viewer:secret@example.com/get.php?"
        "username=bob&password=hunter2&type=m3u&token=abc&output=ts"
    )

    redacted = redact_url(raw_url)

    assert "viewer" not in redacted
    assert "secret" not in redacted
    assert "bob" not in redacted
    assert "hunter2" not in redacted
    assert "abc" not in redacted
    assert "type=m3u" in redacted
    assert "output=ts" in redacted


def test_redact_payload_masks_sensitive_nested_values() -> None:
    payload = {
        "source_url": "https://example.com/get.php?username=bob&password=hunter2&type=m3u",
        "token": "abc",
        "nested": {"api_key": "secret", "safe": "value"},
    }

    redacted = redact_payload(payload)

    assert "bob" not in str(redacted)
    assert "hunter2" not in str(redacted)
    assert "abc" not in str(redacted)
    assert "secret" not in str(redacted)
    assert "value" in str(redacted)


def test_json_formatter_redacts_credentials_from_messages() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="streamforge.test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="failed url=https://example.com/get.php?username=bob&password=hunter2",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)

    assert "bob" not in formatted
    assert "hunter2" not in formatted
    assert "********" in formatted
