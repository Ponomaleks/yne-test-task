import pytest

from app.config import ConfigError, load_config

VALID = {
    "HUBSPOT_BASE_URL": "https://hubspot.test/api",
    "HUBSPOT_APP_TOKEN": "tok-secret-value",
    "HUBSPOT_WEBHOOKS_SECRET": "whs-secret-value",
    "HUBSPOT_WEBHOOK_URI": "https://example.test/webhooks/hubspot",
    "POWEROFFICE_BASE_URL": "https://po.test/api",
    "POWEROFFICE_CLIENT_ID": "cid-secret-value",
    "POWEROFFICE_CLIENT_SECRET": "cs-secret-value",
}


def test_missing_variables_are_named_without_values():
    drop = ("HUBSPOT_APP_TOKEN", "POWEROFFICE_CLIENT_ID")
    env = {k: v for k, v in VALID.items() if k not in drop}

    with pytest.raises(ConfigError) as error:
        load_config(env)

    message = str(error.value)
    assert "HUBSPOT_APP_TOKEN" in message
    assert "POWEROFFICE_CLIENT_ID" in message
    assert "HUBSPOT_BASE_URL" not in message
    assert not any(value in message for value in VALID.values())


def test_empty_variable_counts_as_missing():
    with pytest.raises(ConfigError, match="HUBSPOT_APP_TOKEN"):
        load_config({**VALID, "HUBSPOT_APP_TOKEN": "  "})


def test_dry_run_defaults_to_true_when_unset():
    assert load_config(VALID).dry_run is True


@pytest.mark.parametrize("value", ["true", "False0", "0", "", "no"])
def test_dry_run_stays_true_unless_exactly_false(value):
    assert load_config({**VALID, "DRY_RUN": value}).dry_run is True


@pytest.mark.parametrize("value", ["false", " FALSE "])
def test_dry_run_false_turns_writes_on(value):
    assert load_config({**VALID, "DRY_RUN": value}).dry_run is False
