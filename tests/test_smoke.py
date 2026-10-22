from fastapi.testclient import TestClient

from app.__main__ import main
from app.web import create_app


def test_app_boots_and_answers_unknown_path_with_404():
    client = TestClient(create_app())

    response = client.get("/no-such-path")

    assert response.status_code == 404


def test_main_without_command_exits_zero():
    assert main([]) == 0
