"""Tests for backup failure safety that do not need a subprocess."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from sqlite_backup import backup


def create_database(path: Path) -> None:
    """Create a valid SQLite source database."""
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE entries (value TEXT)")


def temporary_backups(directory: Path) -> list[Path]:
    """Return temporary databases belonging to sqlite-backup."""
    return list(directory.glob(".sqlite-backup-*.sqlite"))


def test_failed_copy_removes_its_temporary_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_database = tmp_path / "source.sqlite"
    destination_database = tmp_path / "backup.sqlite"
    create_database(source_database)

    def fail_copy(source: Path, destination: Path) -> None:
        raise sqlite3.DatabaseError("copy failed")

    monkeypatch.setattr(backup, "_copy_database", fail_copy)

    with pytest.raises(backup.BackupError, match="copy failed"):
        backup.create_backup(source_database, destination_database, overwrite=False)

    assert not destination_database.exists()
    assert temporary_backups(tmp_path) == []


def test_destination_created_during_copy_is_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_database = tmp_path / "source.sqlite"
    destination_database = tmp_path / "backup.sqlite"
    create_database(source_database)

    original_copy = backup._copy_database

    def copy_then_create_destination(source: Path, destination: Path) -> None:
        original_copy(source, destination)
        destination_database.write_text("created by another process")

    monkeypatch.setattr(backup, "_copy_database", copy_then_create_destination)

    with pytest.raises(backup.BackupError):
        backup.create_backup(source_database, destination_database, overwrite=False)

    assert destination_database.read_text() == "created by another process"
    assert temporary_backups(tmp_path) == []
