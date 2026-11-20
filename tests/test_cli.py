import json
import sys

from flipper_diag.cli import main


def test_history_command_initializes_empty_local_database(tmp_path, monkeypatch, capsys):
    database = tmp_path / "history.sqlite3"
    monkeypatch.setattr(
        sys,
        "argv",
        ["flipper-diag", "history", "--db", str(database), "--json"],
    )

    main()

    assert database.exists()
    assert json.loads(capsys.readouterr().out) == []
