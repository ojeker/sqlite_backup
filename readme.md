# sqlite-backup

`sqlite-backup` creates safe backups of live SQLite databases using SQLite's
online-backup API.

## Install from Git

Install the latest version directly from the Git repository with
[uv](https://docs.astral.sh/uv/):

```bash
uv tool install "git+https://github.com/ojeker/sqlite_backup.git"
```

To install a particular release, append its Git tag:

```bash
uv tool install "git+https://github.com/ojeker/sqlite_backup.git@v0.1.0"
```

Replace `v0.1.0` with the tag you want to install. `uv` downloads a compatible
Python version when needed and makes the `sqlite-backup` command available on
your machine.

## Use the command

```bash
sqlite-backup SOURCE_DATABASE DESTINATION_DATABASE
```

For example:

```bash
sqlite-backup app.db backups/app.db
```

Run `sqlite-backup --help` to see all available options.

## Development

For local development, testing, and release instructions, see
[dev.md](dev.md).
