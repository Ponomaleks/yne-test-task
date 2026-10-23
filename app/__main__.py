import argparse
import functools
import logging
import os
import sys
from collections.abc import Mapping

import httpx
import uvicorn

from app.clients.hubspot import HubSpotClient
from app.clients.poweroffice import PowerOfficeClient
from app.config import ConfigError, load_config
from app.processor import process_delivery
from app.replay import replay
from app.store import init_store
from app.web import create_app

STORE_PATH = "data/store.db"
HOST = "127.0.0.1"
PORT = 8000
WEBHOOK_URL = f"http://{HOST}:{PORT}/webhooks/hubspot"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("serve", help="receive webhook deliveries on 127.0.0.1:8000")
    commands.add_parser("replay", help="post the recorded deliveries to the local endpoint")
    return parser


def main(argv: list[str], env: Mapping[str, str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exit_:
        return int(exit_.code or 0)

    if args.command is None:
        # With no command, building the app proves the wiring imports and constructs.
        create_app()
        return 0

    try:
        config = load_config(os.environ if env is None else env)
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 1

    if args.command == "serve":
        # uvicorn configures only its own loggers; the app's outcome lines need the root one.
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
        )
        init_store(STORE_PATH)
        # The clients live as long as the server; each delivery is processed in the background.
        with httpx.Client() as http:
            process = functools.partial(
                process_delivery,
                hubspot=HubSpotClient(config.hubspot_base_url, config.hubspot_app_token, http),
                poweroffice=PowerOfficeClient(
                    config.poweroffice_base_url,
                    config.poweroffice_client_id,
                    config.poweroffice_client_secret,
                    http,
                ),
                store_path=STORE_PATH,
                dry_run=config.dry_run,
            )
            app = create_app(
                store_path=STORE_PATH,
                secret=config.hubspot_webhooks_secret,
                webhook_uri=config.hubspot_webhook_uri,
                process=process,
            )
            uvicorn.run(app, host=HOST, port=PORT, workers=1)
        return 0

    with httpx.Client(timeout=30) as http:
        hubspot = HubSpotClient(config.hubspot_base_url, config.hubspot_app_token, http)
        counts = replay(hubspot, http, WEBHOOK_URL)
    print(counts)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
