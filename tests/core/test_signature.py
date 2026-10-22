import base64
import hashlib
import hmac

from app.core.signature import is_valid_signature, signed_text

SECRET = "synthetic-secret"
METHOD = "POST"
URI = "https://example.test/webhooks/hubspot"
BODY = b'[{"eventId": 1}]'
TIMESTAMP = "1700000000000"


def _sign(secret=SECRET, method=METHOD, uri=URI, body=BODY, timestamp=TIMESTAMP):
    digest = hmac.new(
        secret.encode(), method.encode() + uri.encode() + body + timestamp.encode(), hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode()


def test_signed_text_is_concatenated_without_separators():
    assert signed_text(METHOD, URI, BODY, TIMESTAMP) == (
        b"POST" + URI.encode() + BODY + TIMESTAMP.encode()
    )


def test_correct_signature_is_valid():
    assert is_valid_signature(SECRET, METHOD, URI, BODY, TIMESTAMP, _sign())


def test_changed_body_fails():
    assert not is_valid_signature(SECRET, METHOD, URI, BODY + b" ", TIMESTAMP, _sign())


def test_changed_uri_fails():
    assert not is_valid_signature(SECRET, METHOD, URI + "x", BODY, TIMESTAMP, _sign())


def test_changed_timestamp_fails():
    assert not is_valid_signature(SECRET, METHOD, URI, BODY, "1700000000001", _sign())


def test_wrong_secret_fails():
    assert not is_valid_signature("other", METHOD, URI, BODY, TIMESTAMP, _sign())


def test_missing_or_empty_signature_fails():
    assert not is_valid_signature(SECRET, METHOD, URI, BODY, TIMESTAMP, None)
    assert not is_valid_signature(SECRET, METHOD, URI, BODY, TIMESTAMP, "")


def test_missing_timestamp_fails():
    assert not is_valid_signature(SECRET, METHOD, URI, BODY, None, _sign())
