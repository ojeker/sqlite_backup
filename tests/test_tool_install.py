"""End-to-end test for installation as a uv-managed command-line tool."""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
from pathlib import Path


def test_uv_tool_install_runs_outside_checkout(tmp_path: Path) -> None:
    uv = shutil.which("uv")
    assert uv is not None, "uv must be installed to run the tool-install test"

    repository_root = Path(__file__).resolve().parents[1]
    tool_directory = tmp_path / "tools"
    tool_binary_directory = tmp_path / "bin"
    environment = os.environ | {
        "UV_TOOL_DIR": str(tool_directory),
        "UV_TOOL_BIN_DIR": str(tool_binary_directory),
    }

    subprocess.run(
        [uv, "tool", "install", "--python", "3.14", str(repository_root)],
        check=True,
        cwd=tmp_path,
        env=environment,
    )

    execution_directory = tmp_path / "execution"
    execution_directory.mkdir()
    source_database = execution_directory / "source.sqlite"
    destination_database = execution_directory / "backup.sqlite"
    with sqlite3.connect(source_database) as connection:
        connection.execute("CREATE TABLE entries (value TEXT)")
        connection.execute("INSERT INTO entries VALUES ('installed')")
    result = subprocess.run(
        [
            str(tool_binary_directory / "sqlite-backup"),
            str(source_database),
            str(destination_database),
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=execution_directory,
        env=environment,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    with sqlite3.connect(destination_database) as connection:
        assert connection.execute("SELECT value FROM entries").fetchall() == [
            ("installed",)
        ]
