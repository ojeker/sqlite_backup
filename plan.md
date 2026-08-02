# sqlite-backup implementation plan

## Decisions

- Ship `sqlite-backup` as a Python command installed by uv from tagged GitHub
  releases.
- Use the CPython 3.14 minor line, pinned by `.python-version` and managed by uv.
- Use Python's `sqlite3.Connection.backup()` online-backup API to copy live
  SQLite databases.
- The command shape is:

  ```text
  sqlite-backup [--no-overwrite] [--integrity-check] [--retries COUNT] SOURCE_DATABASE DESTINATION_DATABASE
  ```

- Existing destinations are replaced by default only after a successful new
  backup is ready. `--no-overwrite` instead fails without modification.

## 1. Prove package delivery

- Create `pyproject.toml`, a `src/` package layout, and the `sqlite-backup`
  console entry point.
- Implement only `hello world` at this stage; do not implement backup logic.
- Pin the CPython 3.14 minor line with `.python-version`, lock dependencies with uv, and
  install the local package with `uv tool install .`.
- Run the installed command from a temporary directory outside the checkout
  and verify that it prints `hello world`.

## 2. Implement and test the CLI and safe online backups

- Replace the placeholder with `argparse` parsing for the two positional paths
  and `--no-overwrite`. Add `--integrity-check` and `--retries` only together with
  their behavior in the following milestone.
- Keep CLI parsing, backup orchestration, and SQLite/filesystem work in focused
  modules. Use exit code 0 for success, 2 for argument errors, and 1 for
  operational failures. Send diagnostics to stderr and keep success silent.
- Validate that the source is an existing regular file, the source and
  destination are different, and the destination parent exists and is writable.
- Open the source read-only and create the copy only with
  `sqlite3.Connection.backup()`; never manipulate its journal mode, locks, or
  data. Write to a uniquely named temporary database in the destination
  directory and close both connections before publishing it.
- Atomically replace an existing destination by default only after a successful
  temporary backup. With `--no-overwrite`, reject an existing destination and
  atomically avoid clobbering one that appears during the backup. On failure,
  delete only the temporary file created by this invocation.
- Add focused tests alongside the implementation for help and exit codes,
  validation failures, schema/data preservation, an open source connection,
  destination preservation, default replacement, no-overwrite, and package installation.

## 3. Implement and test optional verification and retries

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

## 4. Integrate, release-test, and document

- Run the complete test and lint suite defined in `pyproject.toml`.
- Run an end-to-end `uv tool install .` smoke test from outside the repository.
- Add GitHub Actions CI for pushes and pull requests to `main`; it installs
  CPython 3.14 through uv and runs the test suite.
- Publish releases as immutable GitHub tags. Document installation with
  `uv tool install "git+https://github.com/ojeker/sqlite_backup.git@TAG"`, all
  CLI flags, and destination-safety semantics.

At every implementation step, write focused deterministic tests with the code
being added. The final stage adds integration and release validation; it is not
the first time testing occurs.
