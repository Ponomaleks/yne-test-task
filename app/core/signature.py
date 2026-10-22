"""HubSpot webhook signature v3 verification. Pure: no I/O, no env reads."""

import base64
import hashlib
import hmac


def signed_text(method: str, uri: str, body: bytes, timestamp: str) -> bytes:
    """Build the text the CRM signs: concatenated, no separators."""
    return method.encode() + uri.encode() + body + timestamp.encode()


def is_valid_signature(
    secret: str,
    method: str,
    uri: str,
    body: bytes,
    timestamp: str | None,
    signature: str | None,
) -> bool:
    """Compare in constant time. A missing signature or timestamp never matches."""
    if not signature or timestamp is None:
        return False
    digest = hmac.new(
        secret.encode(), signed_text(method, uri, body, timestamp), hashlib.sha256
    ).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected.encode(), signature.encode())
