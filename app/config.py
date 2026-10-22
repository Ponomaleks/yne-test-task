from collections.abc import Mapping
from dataclasses import dataclass

REQUIRED = (
    "HUBSPOT_BASE_URL",
    "HUBSPOT_APP_TOKEN",
    "HUBSPOT_WEBHOOKS_SECRET",
    "HUBSPOT_WEBHOOK_URI",
    "POWEROFFICE_BASE_URL",
    "POWEROFFICE_CLIENT_ID",
    "POWEROFFICE_CLIENT_SECRET",
)


class ConfigError(Exception):
    """Configuration is unusable. The message holds variable names only, never values."""


@dataclass(frozen=True)
class Config:
    hubspot_base_url: str
    hubspot_app_token: str
    hubspot_webhooks_secret: str
    hubspot_webhook_uri: str
    poweroffice_base_url: str
    poweroffice_client_id: str
    poweroffice_client_secret: str
    dry_run: bool


def load_config(env: Mapping[str, str]) -> Config:
    missing = [name for name in REQUIRED if not env.get(name, "").strip()]
    if missing:
        raise ConfigError("Missing configuration: " + ", ".join(missing))
    # Safe default: writes turn on only when DRY_RUN is exactly "false".
    dry_run = env.get("DRY_RUN", "true").strip().lower() != "false"
    return Config(
        hubspot_base_url=env["HUBSPOT_BASE_URL"].strip(),
        hubspot_app_token=env["HUBSPOT_APP_TOKEN"].strip(),
        hubspot_webhooks_secret=env["HUBSPOT_WEBHOOKS_SECRET"].strip(),
        hubspot_webhook_uri=env["HUBSPOT_WEBHOOK_URI"].strip(),
        poweroffice_base_url=env["POWEROFFICE_BASE_URL"].strip(),
        poweroffice_client_id=env["POWEROFFICE_CLIENT_ID"].strip(),
        poweroffice_client_secret=env["POWEROFFICE_CLIENT_SECRET"].strip(),
        dry_run=dry_run,
    )
