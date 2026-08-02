# sqlite-backup implementation plan

## Decisions

- Ship a standalone Linux `x86_64` executable named `sqlite-backup`.
- Compile with Nuitka and CPython 3.13. Python 3.13 is selected for stable
  Nuitka compatibility.
- Use Python's `sqlite3.Connection.backup()` online-backup API to copy live
  SQLite databases.
- The command shape is:

  ```text
  sqlite-backup [--overwrite] [--integrity-check] [--retries COUNT] SOURCE_DATABASE DESTINATION_DATABASE
  ```

- Existing destinations fail without modification by default. `--overwrite`
  permits replacement only after a successful new backup is ready.

## 1. Prove binary delivery

- Create `pyproject.toml`, a `src/` package layout, and the `sqlite-backup`
  console entry point.
- Add Nuitka as a pinned build dependency and document a repeatable one-file
  Linux build command.
- Implement only `hello world` at this stage; do not implement backup logic.
- Build the executable as `sqlite-backup`, run it from a temporary directory
  outside the checkout, and verify that it prints `hello world`.
- Add build output to `.gitignore` and add an automated binary smoke test for
  this milestone.

## 2. Implement and test the CLI

- Replace the placeholder with `argparse` parsing for the two positional paths
  and `--overwrite`, `--integrity-check`, and `--retries COUNT`.
- Keep CLI parsing, backup orchestration, and SQLite/filesystem work in focused
  modules.
- Use exit code 0 for success, 2 for argument errors, and 1 for operational
  failures. Send diagnostics to stderr.
- Validate that the source is an existing regular file, source and destination
  are different, the destination parent exists and is writable, and retry count
  is a non-negative integer.
- Add tests with this implementation for `--help`, positional ordering, flag
  parsing, validation failures, and exit codes.

## 3. Implement and test safe online backups

- Open the source database read-only and create the copy only with
  `sqlite3.Connection.backup()`; never manipulate its journal mode, locks, or
  data.
- Write every backup to a uniquely named temporary database in the destination
  directory. Close both SQLite connections before publishing it.
- Reject an existing destination by default. With `--overwrite`, atomically
  replace it only after the temporary backup has succeeded.
- Without `--overwrite`, atomically publish without clobbering a destination
  that appears during the backup. On failure, delete only the temporary file
  created by this invocation.
- Add tests at the same time for schema/data preservation, invalid database
  inputs, source-equals-destination rejection, failed-backup cleanup, default
  destination preservation, overwrite, and concurrent destination creation.

## 4. Implement and test optional verification and retries

- `--integrity-check` runs `PRAGMA integrity_check` on the completed temporary
  backup before publication. A result other than `ok` fails and preserves the
  destination.
- `--retries COUNT` retries only SQLite `busy` and `locked` errors for at most
  `COUNT` additional attempts. Back off from 250 ms, doubling to a 2-second
  maximum; every retry starts with a fresh temporary destination.
- Do not retry validation, permissions, path, corruption, or unexpected
  failures.
- Add tests alongside the feature for integrity-check success and failure,
  retry classification, retry count and delay bounds, no retry for permanent
  errors, and live-writer behavior. The live-writer test must synchronize its
  writer rather than rely on timing and must confirm the backup is readable and
  passes SQLite integrity checking.

## 5. Integrate, release-test, and document

- Run the complete test and lint suite defined in `pyproject.toml`.
- Build the final Nuitka one-file binary and run an end-to-end smoke test from
  outside the repository: `--help` works and it backs up a sample database
  without relying on the project checkout or a project Python environment.
- Document binary usage, all CLI flags, destination-safety semantics, build
  prerequisites, the reproducible build command, and supported platform.

At every implementation step, write focused deterministic tests with the code
being added. The final stage adds integration and release validation; it is not
the first time testing occurs.
