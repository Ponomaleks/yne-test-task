"""Decide which pipeline stages are "won" from pipeline metadata, never from stage names."""

from decimal import Decimal


def won_stages(pipelines: list[dict]) -> set[tuple[str, str]]:
    """Return (pipeline id, stage id) of every stage closed with probability 1.0."""
    won: set[tuple[str, str]] = set()
    for pipeline in pipelines:
        for stage in pipeline["stages"]:
            metadata = stage["metadata"]
            # HubSpot sends both values as strings; Decimal avoids float comparison.
            if metadata["isClosed"] == "true" and Decimal(metadata["probability"]) == 1:
                won.add((pipeline["id"], stage["id"]))
    return won


def is_won(pipeline_id: str, stage_id: str, won: set[tuple[str, str]]) -> bool:
    return (pipeline_id, stage_id) in won
