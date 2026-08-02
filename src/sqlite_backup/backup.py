"""Safe online SQLite backup operations."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import time
from pathlib import Path

INITIAL_RETRY_DELAY_SECONDS = 0.25
MAXIMUM_RETRY_DELAY_SECONDS = 2.0


class BackupError(Exception):
    """An expected failure while preparing or publishing a backup."""


def create_backup(
    source_database: Path,
    destination_database: Path,
    *,
    overwrite: bool,
    integrity_check: bool = False,
    retries: int = 0,
) -> None:
    """Create and atomically publish an online backup of ``source_database``."""
    _validate_paths(source_database, destination_database, overwrite=overwrite)

    for attempt_number in range(retries + 1):
        try:
            _create_and_publish_backup(
                source_database,
                destination_database,
                overwrite=overwrite,
                integrity_check=integrity_check,
            )
            return
        except sqlite3.Error as error:
            if not _can_retry(error, attempt_number, retries):
                raise BackupError(str(error)) from error
            time.sleep(_retry_delay(attempt_number))
        except BackupError:
            raise
        except OSError as error:
            raise BackupError(str(error)) from error


def _create_and_publish_backup(
    source_database: Path,
    destination_database: Path,
    *,
    overwrite: bool,
    integrity_check: bool,
) -> None:
    """Run one complete backup attempt using a private temporary database."""
    temporary_database = _create_temporary_database(destination_database.parent)

    try:
        _copy_database(source_database, temporary_database)
        if integrity_check:
            _verify_backup_integrity(temporary_database)
        _publish_backup(temporary_database, destination_database, overwrite=overwrite)
    finally:
        temporary_database.unlink(missing_ok=True)


def _can_retry(error: sqlite3.Error, attempt_number: int, retries: int) -> bool:
    """Return whether an SQLite error qualifies for another backup attempt."""
    return attempt_number < retries and _is_busy_or_locked_error(error)


def _is_busy_or_locked_error(error: sqlite3.Error) -> bool:
    """Return whether ``error`` has a busy or locked primary SQLite result code."""
    error_code = getattr(error, "sqlite_errorcode", None)
    if not isinstance(error_code, int):
        return False
    return (error_code & 0xFF) in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}


def _retry_delay(attempt_number: int) -> float:
    """Return the bounded delay before the retry after ``attempt_number``."""
    return min(
        INITIAL_RETRY_DELAY_SECONDS * (2**attempt_number),
        MAXIMUM_RETRY_DELAY_SECONDS,
    )


def _validate_paths(
    source_database: Path, destination_database: Path, *, overwrite: bool
) -> None:
    """Reject paths that cannot safely participate in a backup."""
    if not source_database.is_file():
        raise BackupError(f"source database is not an existing regular file: {source_database}")

    destination_parent = destination_database.parent
    if not destination_parent.is_dir():
        raise BackupError(
            f"destination directory does not exist: {destination_parent}"
        )
    if not os.access(destination_parent, os.W_OK | os.X_OK):
        raise BackupError(f"destination directory is not writable: {destination_parent}")

    if _paths_identify_same_file(source_database, destination_database):
        raise BackupError("source and destination databases must be different files")

    if not overwrite and os.path.lexists(destination_database):
        raise BackupError(f"destination already exists: {destination_database}")


def _paths_identify_same_file(source_database: Path, destination_database: Path) -> bool:
    """Return whether two paths refer to the same existing or intended file."""
    if os.path.lexists(destination_database):
        try:
            return os.path.samefile(source_database, destination_database)
        except OSError:
            return source_database.resolve() == destination_database.resolve()
    return source_database.resolve() == destination_database.resolve()


def _create_temporary_database(destination_directory: Path) -> Path:
    """Reserve a private temporary path on the destination filesystem."""
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=".sqlite-backup-", suffix=".sqlite", dir=destination_directory
    )
    os.close(descriptor)
    return Path(temporary_path)


def _copy_database(source_database: Path, temporary_database: Path) -> None:
    """Copy a database with SQLite's online-backup API."""
    source_uri = f"{source_database.resolve().as_uri()}?mode=ro"
    source_connection = sqlite3.connect(source_uri, uri=True)
    destination_connection = sqlite3.connect(temporary_database)

    try:
        source_connection.execute("PRAGMA schema_version").fetchone()
        source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()


def _verify_backup_integrity(temporary_database: Path) -> None:
    """Raise ``BackupError`` unless SQLite reports an intact backup database."""
    with sqlite3.connect(temporary_database) as connection:
        results = connection.execute("PRAGMA integrity_check").fetchall()

    if results != [("ok",)]:
        details = "; ".join(str(result[0]) for result in results)
        raise BackupError(f"backup integrity check failed: {details}")


def _publish_backup(
    temporary_database: Path, destination_database: Path, *, overwrite: bool
) -> None:
    """Make a completed temporary backup visible at its requested destination."""
    if overwrite:
        os.replace(temporary_database, destination_database)
        return

    os.link(temporary_database, destination_database)
    temporary_database.unlink()
