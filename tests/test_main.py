from app.__main__ import main


def test_main_without_command_exits_zero():
    assert main([]) == 0


def test_unknown_command_exits_two():
    assert main(["no-such-command"]) == 2


def test_serve_with_missing_config_exits_one_naming_variables_only(capsys):
    code = main(["serve"], env={"HUBSPOT_APP_TOKEN": "tok-secret-value"})

    err = capsys.readouterr().err
    assert code == 1
    assert "HUBSPOT_BASE_URL" in err
    assert "tok-secret-value" not in err


def test_replay_with_missing_config_exits_one(capsys):
    assert main(["replay"], env={}) == 1
    assert "HUBSPOT_APP_TOKEN" in capsys.readouterr().err


def test_serve_wires_process_delivery_as_the_web_callback(monkeypatch, tmp_path):
    import app.__main__ as cli

    env = {
        "HUBSPOT_BASE_URL": "https://crm.example.test",
        "HUBSPOT_APP_TOKEN": "placeholder",
        "HUBSPOT_WEBHOOKS_SECRET": "placeholder",
        "HUBSPOT_WEBHOOK_URI": "https://hooks.example.test/webhooks/hubspot",
        "POWEROFFICE_BASE_URL": "https://acc.example.test",
        "POWEROFFICE_CLIENT_ID": "placeholder",
        "POWEROFFICE_CLIENT_SECRET": "placeholder",
    }
    captured = {}
    monkeypatch.setattr(cli, "STORE_PATH", str(tmp_path / "store.db"))
    monkeypatch.setattr(cli, "create_app", lambda **kwargs: captured.update(kwargs))
    monkeypatch.setattr(cli.uvicorn, "run", lambda *args, **kwargs: None)

    levels = []
    monkeypatch.setattr(cli.logging, "basicConfig", lambda **kwargs: levels.append(kwargs["level"]))

    assert main(["serve"], env=env) == 0
    assert levels == [cli.logging.INFO]
    # httpx INFO lines print full URLs with query values (orgnr); keep them out of the log.
    assert cli.logging.getLogger("httpx").level == cli.logging.WARNING
    process = captured["process"]
    assert process.func is cli.process_delivery
    assert process.keywords["dry_run"] is True
