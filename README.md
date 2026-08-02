# sqlite-backup

`sqlite-backup` creates safe backups of live SQLite databases using SQLite's
online-backup API.

## Requirements

- [uv](https://docs.astral.sh/uv/)

## Development setup

```bash
uv python install 3.13.14
uv sync --extra test
```

The repository pins CPython 3.13.14 in `.python-version`. `uv` installs and
uses that interpreter even if the system Python is a different version.

Run the ordinary tests:

```bash
uv run pytest
```

## Install the command

Install the current checkout as an isolated command-line tool:

```bash
uv tool install .
sqlite-backup SOURCE_DATABASE DESTINATION_DATABASE
```

The command exits silently on success. It refuses to replace an existing
destination. Use `--overwrite` only when replacement is intended:

```bash
sqlite-backup --overwrite SOURCE_DATABASE DESTINATION_DATABASE
```

The source must be an existing regular database file. Backups are created in a
temporary sibling file and only published after SQLite has finished the copy.

## Install a GitHub release

Install a tagged release directly from GitHub:

```bash
uv tool install "git+https://github.com/ojeker/sqlite_backup.git@v0.1.0"
```

Replace `v0.1.0` with the release tag you want to install. GitHub tags are the
initial distribution channel; no native binary is produced.
