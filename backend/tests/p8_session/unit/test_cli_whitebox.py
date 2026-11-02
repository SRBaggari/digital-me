import pytest

from digital_me import __main__ as cli
from digital_me.config import InstanceError, create


def test_pick_instance_explicit_name_wins(instances_home):
    assert cli._pick_instance("bob") == "bob"


def test_pick_instance_single_instance_default(instances_home):
    create("alice")
    assert cli._pick_instance(None) == "alice"


def test_pick_instance_none(instances_home):
    with pytest.raises(InstanceError, match="No instances"):
        cli._pick_instance(None)


def test_pick_instance_ambiguous(instances_home):
    create("alice")
    create("bob")
    with pytest.raises(InstanceError, match="Several"):
        cli._pick_instance(None)


def test_serve_port_override_validated(instances_home, monkeypatch, capsys):
    create("alice")
    monkeypatch.setattr("uvicorn.run", lambda *a, **k: pytest.fail("should not start"))
    assert cli.main(["serve", "--port", "80"]) == 1
    assert "port" in capsys.readouterr().err


def test_serve_uses_loopback_and_port(instances_home, monkeypatch):
    create("alice")
    calls = {}
    monkeypatch.setattr("uvicorn.run", lambda app, host, port, log_level: calls.update(host=host, port=port))
    assert cli.main(["serve", "-i", "alice", "--port", "9000"]) == 0
    assert calls == {"host": "127.0.0.1", "port": 9000}
