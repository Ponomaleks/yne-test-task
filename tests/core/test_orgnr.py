import pytest

from app.core.orgnr import is_foreign, normalize_orgnr


@pytest.mark.parametrize(
    "raw",
    [
        "123456789",
        "123 456 789",
        "NO123456789",
        "NO 123 456 789",
        "123456789MVA",
        "123 456 789 MVA",
        "NO123456789MVA",
        "NO 123 456 789 MVA",
        "no 123 456 789 mva",
        "  123456789  ",
    ],
)
def test_normalize_valid_shapes(raw):
    assert normalize_orgnr(raw) == "123456789"


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "   ",
        "12345678",
        "1234567890",
        "123A56789",
        "NO 12345678",
        "NO 1234567890 MVA",
        "MVA",
        "NO",
        "DE 123 456 789",
        "SE123456789",
    ],
)
def test_normalize_invalid_returns_none(raw):
    assert normalize_orgnr(raw) is None


@pytest.mark.parametrize("raw", ["DE 123 456 789", "SE123456789MVA", "gb 123456789"])
def test_foreign_prefix_is_foreign(raw):
    assert is_foreign(raw, "Norway") is True
    assert normalize_orgnr(raw) != "123456789"


@pytest.mark.parametrize("country", ["Germany", "Sweden", "germany"])
def test_foreign_country_is_foreign(country):
    assert is_foreign("123456789", country) is True


@pytest.mark.parametrize(
    "raw, country",
    [
        ("123456789", "Norway"),
        ("NO 123 456 789 MVA", "Norway"),
        ("123456789", "norway"),
        ("123456789", None),
        ("123456789", ""),
        (None, None),
        (None, "Norway"),
        ("", None),
        ("12345678", "Norway"),
    ],
)
def test_not_foreign(raw, country):
    assert is_foreign(raw, country) is False


@pytest.mark.parametrize("raw", [None, ""])
def test_missing_orgnr_with_foreign_country_is_foreign(raw):
    assert is_foreign(raw, "Germany") is True
