from app.core.won import is_won, won_stages


def _stage(stage_id: str, closed: str, probability: str) -> dict:
    return {"id": stage_id, "metadata": {"isClosed": closed, "probability": probability}}


PIPELINES = [
    {
        "id": "default",
        "stages": [
            _stage("appointmentscheduled", "false", "0.2"),
            _stage("contractsent", "false", "0.9"),
            _stage("closedwon", "true", "1.0"),
            _stage("closedlost", "true", "0.0"),
        ],
    },
    {
        "id": "84512397",
        "stages": [
            _stage("84512400", "true", "1.0"),
            _stage("84512401", "true", "0.0"),
        ],
    },
]


def test_won_stages_contains_won_stage_of_every_pipeline():
    assert won_stages(PIPELINES) == {("default", "closedwon"), ("84512397", "84512400")}


def test_non_default_pipeline_won_stage_is_won():
    assert is_won("84512397", "84512400", won_stages(PIPELINES))


def test_closed_lost_is_not_won():
    won = won_stages(PIPELINES)
    assert not is_won("default", "closedlost", won)
    assert not is_won("84512397", "84512401", won)


def test_open_stage_with_high_probability_is_not_won():
    assert not is_won("default", "contractsent", won_stages(PIPELINES))


def test_unknown_stage_is_not_won():
    assert not is_won("default", "nope", won_stages(PIPELINES))
    assert not is_won("unknown", "closedwon", won_stages(PIPELINES))


def test_probability_one_without_decimal_part_is_won():
    pipelines = [{"id": "p", "stages": [_stage("s", "true", "1")]}]
    assert won_stages(pipelines) == {("p", "s")}
