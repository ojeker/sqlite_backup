"""Tests for the initial command-line entry point."""

from __future__ import annotations

import subprocess
import sys


def test_module_prints_hello_world() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "sqlite_backup"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout == "hello world\n"
    assert result.stderr == ""
