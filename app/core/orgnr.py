"""Norwegian organization number (orgnr) normalization and foreign detection."""

import re

_NORWAY_NAMES = {"norway", "norge"}
_ORGNR = re.compile(r"(?:NO)?(\d{9})(?:MVA)?")
_PREFIX = re.compile(r"([A-Z]{2})\d")


def _compact(raw: str | None) -> str:
    return "".join((raw or "").split()).upper()


def normalize_orgnr(raw: str | None) -> str | None:
    """Return exactly nine digits, or None when the value is not a valid Norwegian orgnr."""
    match = _ORGNR.fullmatch(_compact(raw))
    return match.group(1) if match else None


def is_foreign(raw: str | None, country: str | None) -> bool:
    """True for a letter prefix other than NO, or a present country other than Norway."""
    prefix = _PREFIX.match(_compact(raw))
    if prefix and prefix.group(1) != "NO":
        return True
    country = (country or "").strip().lower()
    return bool(country) and country not in _NORWAY_NAMES
