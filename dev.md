# sqlite-backup

`sqlite-backup` creates safe backups of live SQLite databases using SQLite's
online-backup API.

## Requirements

- [uv](https://docs.astral.sh/uv/)

## Development setup

```bash
uv python install 3.14
uv sync --extra test
```

The repository tracks the CPython 3.14 minor line in `.python-version`. `uv` installs and
uses that interpreter even if the system Python is a different version.

Run the ordinary tests:

```bash
uv run pytest
```

Run the complete local quality gate:

```bash
uv run ruff check .
uv run pytest
```

## Install the command

Install the current checkout as an isolated command-line tool:

```bash
uv tool install .
sqlite-backup SOURCE_DATABASE DESTINATION_DATABASE
```

The command exits silently on success. It replaces an existing destination only
after a new backup has completed successfully. Use `--no-overwrite` when an
existing destination must be preserved:

```bash
sqlite-backup --no-overwrite SOURCE_DATABASE DESTINATION_DATABASE
```

The source must be an existing regular database file. Backups are created in a
temporary sibling file and only published after SQLite has finished the copy.

To verify a completed temporary backup before it is published, use SQLite's
integrity check:

```bash
sqlite-backup --integrity-check SOURCE_DATABASE DESTINATION_DATABASE
```

SQLite busy or locked errors can be retried with a bounded number of additional
fresh backup attempts. The first delay is 250 ms and doubles up to 2 seconds;
the default is no retry. Other errors, including invalid paths, permissions,
and integrity-check failures, are not retried:

```bash
sqlite-backup --retries 3 SOURCE_DATABASE DESTINATION_DATABASE
```

When either option is used, the new database is published only after the
configured backup operation succeeds. A failed backup preserves an existing
destination; `--no-overwrite` also rejects an existing destination before the
backup begins.

## Install a GitHub release

Install a tagged release directly from GitHub:

```bash
uv tool install "git+https://github.com/ojeker/sqlite_backup.git@v0.1.0"
```

Replace `v0.1.0` with the release tag you want to install. GitHub tags are the
initial distribution channel; no native binary is produced.

### Publish a release

Use stable [Semantic Versioning](https://semver.org/) for releases. The current
release is `1.0.0`; increment the version as follows:

- **MAJOR** for incompatible changes to the command-line interface,
  installation process, or documented behavior.
- **MINOR** for backwards-compatible features, options, or enhancements.
- **PATCH** for backwards-compatible bug fixes and security fixes.

Documentation-only changes do not require a release unless they are included
with another release. Do not publish pre-release versions at this time.

Releases are immutable annotated Git tags. Keep the version in `pyproject.toml`
as `X.Y.Z` and create the matching tag as `vX.Y.Z`. Before tagging, update the
version, refresh the lockfile, and run the full quality gate:

```bash
uv lock
uv sync --locked --extra test
uv run ruff check .
uv run pytest
```

Commit and merge the release version to `main`, then create and push an
annotated tag for that exact commit:

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

Verify that the manifest version matches the tag without its `v` prefix. Never
move, delete, or reuse a published release tag. Publish a new version if a
release needs correction.
