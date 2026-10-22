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
