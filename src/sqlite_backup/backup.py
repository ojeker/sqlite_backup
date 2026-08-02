"""Safe online SQLite backup operations."""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path


class BackupError(Exception):
    """An expected failure while preparing or publishing a backup."""


def create_backup(
    source_database: Path, destination_database: Path, *, overwrite: bool
) -> None:
    """Create and atomically publish an online backup of ``source_database``."""
    temporary_database: Path | None = None

    try:
        _validate_paths(source_database, destination_database, overwrite=overwrite)
        temporary_database = _create_temporary_database(destination_database.parent)
        _copy_database(source_database, temporary_database)
        _publish_backup(temporary_database, destination_database, overwrite=overwrite)
    except BackupError:
        raise
    except (OSError, sqlite3.Error) as error:
        raise BackupError(str(error)) from error
    finally:
        if temporary_database is not None:
            temporary_database.unlink(missing_ok=True)


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


def _publish_backup(
    temporary_database: Path, destination_database: Path, *, overwrite: bool
) -> None:
    """Make a completed temporary backup visible at its requested destination."""
    if overwrite:
        os.replace(temporary_database, destination_database)
        return

    os.link(temporary_database, destination_database)
    temporary_database.unlink()
