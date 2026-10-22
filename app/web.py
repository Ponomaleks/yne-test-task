import hashlib
import json
import logging
from collections.abc import Callable
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app import store
from app.core.signature import is_valid_signature

logger = logging.getLogger(__name__)

SIGNATURE_HEADER = "X-HubSpot-Signature-v3"
TIMESTAMP_HEADER = "X-HubSpot-Request-Timestamp"


class Event(BaseModel):
    # Extra fields are ignored; propertyValue and sourceId are never read or stored.
    model_config = ConfigDict(extra="ignore")

    event_id: int = Field(alias="eventId")
    deal_id: int = Field(alias="objectId")
    subscription_type: str = Field(alias="subscriptionType")
    property_name: str | None = Field(default=None, alias="propertyName")


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "message": message})


def create_app(
    *,
    store_path: str | Path | None = None,
    secret: str | None = None,
    webhook_uri: str | None = None,
    process: Callable[[int, list[dict]], None] | None = None,
) -> FastAPI:
    app = FastAPI(title="yne-test-task")
    if store_path is None or secret is None or webhook_uri is None:
        return app

    @app.post("/webhooks/hubspot")
    async def receive_delivery(request: Request, background_tasks: BackgroundTasks) -> Response:
        body = await request.body()
        body_sha256 = hashlib.sha256(body).hexdigest()
        signature = request.headers.get(SIGNATURE_HEADER)
        timestamp = request.headers.get(TIMESTAMP_HEADER)
        timestamp_ok = timestamp is not None and timestamp.isdigit()

        if not signature or not timestamp_ok or not is_valid_signature(
            secret, "POST", webhook_uri, body, timestamp, signature
        ):
            code = "delivery.signature_missing" if not signature else "delivery.signature_mismatch"
            try:
                store.save_rejection(store_path, timestamp, body_sha256, code)
            except Exception:
                logger.exception("rejection not recorded body_sha256=%s", body_sha256)
            logger.warning("delivery rejected reason=%s body_sha256=%s", code, body_sha256)
            return _error(401, code, "The delivery signature is missing or does not match.")

        try:
            payload = json.loads(body)
        except ValueError:
            payload = None
        if not isinstance(payload, list):
            return _error(400, "delivery.invalid_body", "The body must be a JSON array of events.")

        events: list[dict] = []
        invalid = 0
        for item in payload:
            try:
                event = Event.model_validate(item)
            except ValidationError:
                invalid += 1
                continue
            events.append(event.model_dump())
        if invalid:
            logger.warning("events failed validation count=%d", invalid)

        try:
            delivery_id = store.save_delivery(
                store_path, int(timestamp), body_sha256, len(payload)
            )
            store.save_events(store_path, events)
        except Exception:
            logger.exception("delivery not persisted body_sha256=%s", body_sha256)
            return _error(500, "delivery.not_persisted", "The delivery could not be stored.")

        if process is not None:
            background_tasks.add_task(process, delivery_id, events)
        return Response(status_code=204)

    return app
