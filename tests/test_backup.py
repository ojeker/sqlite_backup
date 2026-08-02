"""Tests for backup failure safety that do not need a subprocess."""

from __future__ import annotations

import sqlite3
import threading
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


def sqlite_error(error_code: int, message: str = "SQLite error") -> sqlite3.Error:
    """Create an SQLite error with a result code for retry tests."""
    error = sqlite3.OperationalError(message)
    error.sqlite_errorcode = error_code
    return error


def test_busy_error_retries_with_fresh_temporary_databases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_database = tmp_path / "source.sqlite"
    destination_database = tmp_path / "backup.sqlite"
    create_database(source_database)
    original_copy = backup._copy_database
    temporary_databases: list[Path] = []
    delays: list[float] = []

    def busy_twice_then_copy(source: Path, destination: Path) -> None:
        temporary_databases.append(destination)
        if len(temporary_databases) < 3:
            raise sqlite_error(sqlite3.SQLITE_BUSY, "database is busy")
        original_copy(source, destination)

    monkeypatch.setattr(backup, "_copy_database", busy_twice_then_copy)
    monkeypatch.setattr(backup.time, "sleep", delays.append)

    backup.create_backup(source_database, destination_database, overwrite=False, retries=2)

    assert destination_database.is_file()
    assert len(set(temporary_databases)) == 3
    assert delays == [0.25, 0.5]
    assert temporary_backups(tmp_path) == []


def test_busy_error_stops_after_requested_additional_attempts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_database = tmp_path / "source.sqlite"
    destination_database = tmp_path / "backup.sqlite"
    create_database(source_database)
    attempts = 0
    delays: list[float] = []

    def always_busy(source: Path, destination: Path) -> None:
        nonlocal attempts
        attempts += 1
        raise sqlite_error(sqlite3.SQLITE_BUSY, "database is busy")

    monkeypatch.setattr(backup, "_copy_database", always_busy)
    monkeypatch.setattr(backup.time, "sleep", delays.append)

    with pytest.raises(backup.BackupError, match="database is busy"):
        backup.create_backup(source_database, destination_database, overwrite=False, retries=2)

    assert attempts == 3
    assert delays == [0.25, 0.5]
    assert not destination_database.exists()
    assert temporary_backups(tmp_path) == []


def test_retry_delay_caps_at_two_seconds() -> None:
    assert backup._retry_delay(0) == 0.25
    assert backup._retry_delay(1) == 0.5
    assert backup._retry_delay(3) == 2.0
    assert backup._retry_delay(10) == 2.0


@pytest.mark.parametrize(
    ("error_code", "expected"),
    [
        (sqlite3.SQLITE_BUSY, True),
        (sqlite3.SQLITE_LOCKED, True),
        (sqlite3.SQLITE_BUSY | (1 << 8), True),
        (sqlite3.SQLITE_IOERR, False),
    ],
)
def test_retry_classification_uses_sqlite_primary_error_code(
    error_code: int, expected: bool
) -> None:
    assert backup._is_busy_or_locked_error(sqlite_error(error_code)) is expected


def test_permanent_sqlite_error_is_not_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_database = tmp_path / "source.sqlite"
    destination_database = tmp_path / "backup.sqlite"
    create_database(source_database)
    attempts = 0
    delays: list[float] = []

    def fail_with_io_error(source: Path, destination: Path) -> None:
        nonlocal attempts
        attempts += 1
        raise sqlite_error(sqlite3.SQLITE_IOERR, "disk I/O error")

    monkeypatch.setattr(backup, "_copy_database", fail_with_io_error)
    monkeypatch.setattr(backup.time, "sleep", delays.append)

    with pytest.raises(backup.BackupError, match="disk I/O error"):
        backup.create_backup(source_database, destination_database, overwrite=False, retries=3)

    assert attempts == 1
    assert delays == []


def test_failed_integrity_check_preserves_existing_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_database = tmp_path / "source.sqlite"
    destination_database = tmp_path / "backup.sqlite"
    create_database(source_database)
    destination_database.write_text("original destination")
    delays: list[float] = []

    def fail_integrity_check(temporary_database: Path) -> None:
        raise backup.BackupError("backup integrity check failed: damaged page")

    monkeypatch.setattr(backup, "_verify_backup_integrity", fail_integrity_check)
    monkeypatch.setattr(backup.time, "sleep", delays.append)

    with pytest.raises(backup.BackupError, match="integrity check failed"):
        backup.create_backup(
            source_database,
            destination_database,
            overwrite=True,
            integrity_check=True,
            retries=3,
        )

    assert destination_database.read_text() == "original destination"
    assert delays == []
    assert temporary_backups(tmp_path) == []


def test_backup_succeeds_during_a_synchronized_writer_transaction(
    tmp_path: Path,
) -> None:
    source_database = tmp_path / "source.sqlite"
    destination_database = tmp_path / "backup.sqlite"
    create_database(source_database)
    writer_ready = threading.Event()
    release_writer = threading.Event()
    writer_errors: list[Exception] = []

    def write_transaction() -> None:
        try:
            with sqlite3.connect(source_database) as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("INSERT INTO entries VALUES ('live value')")
                writer_ready.set()
                release_writer.wait(timeout=5)
        except Exception as error:
            writer_errors.append(error)

    writer = threading.Thread(target=write_transaction)
    writer.start()
    assert writer_ready.wait(timeout=5)
    try:
        backup.create_backup(
            source_database,
            destination_database,
            overwrite=False,
            integrity_check=True,
        )
    finally:
        release_writer.set()
        writer.join(timeout=5)

    assert not writer.is_alive()
    assert writer_errors == []
    with sqlite3.connect(destination_database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert connection.execute("SELECT COUNT(*) FROM entries").fetchone() == (0,)
