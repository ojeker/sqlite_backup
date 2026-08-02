# sqlite-backup contributor guidance

## Purpose

Build a Linux command-line tool named `sqlite-backup` that creates a safe copy
of a *live* SQLite database by using Python's SQLite online-backup API. The
project is shipped to users as a Python command-line package installed with
uv from tagged GitHub releases.

The primary invocation is:

```bash
sqlite-backup SOURCE_DATABASE DESTINATION_DATABASE
```

`DESTINATION_DATABASE` is the exact destination filename supplied by the
caller. Do not silently add timestamps, extensions, directories, or retention
behaviour.

## Core implementation rules

- Use `sqlite3.Connection.backup()` for the copy. Do **not** copy the database
  file with `shutil`, shell commands, or filesystem snapshots; these can be
  inconsistent while SQLite is being written.
- Open the source as SQLite and create the destination through SQLite. Keep
  the source database unchanged.
- Treat a successful online backup as the baseline behaviour. Do not require
  the database to be offline, and do not mutate its journal mode, locking
  settings, or application data.
- Close both connections deterministically, including on errors. Surface
  useful, non-secret error messages and return a non-zero exit status on
  failure.
- Avoid hidden destructive behaviour. In particular, define and test the
  policy for an existing destination before implementing it; never partially
  replace a destination on a failed backup.
- Prefer the Python standard library. Add a dependency only when it offers a
  clear benefit that is documented in the change or dependency metadata.

## CLI contract

- Keep the two positional arguments in this order: `SOURCE_DATABASE`
  followed by `DESTINATION_DATABASE`.
- Use conventional CLI exit codes and send diagnostics to stderr. Keep normal
  success output brief and script-friendly.
- Integrity checking and retry behaviour are optional CLI flags, not mandatory
  default work. When adding either option, document its exact semantics,
  default values, and failure behaviour in `--help` and the README.
- Any retry implementation must be bounded, configurable, and limited to
  transient SQLite busy/locked failures. Do not retry invalid paths,
  permissions problems, corruption errors, or programmer errors.
- An integrity option should run SQLite's own integrity check on the completed
  backup and fail if the result is not `ok`. Do not claim that it validates the
  source beyond what SQLite reports.
- New options must remain compatible with the simple positional invocation.

## Project and quality standards

- Use the CPython 3.14 minor line, as pinned in `.python-version`; keep the supported range
  explicit in `pyproject.toml` and dependencies resolved in `uv.lock`.
- Keep all packaging, dependency, test, lint, and build configuration in
  `pyproject.toml`.
- Add focused tests for successful live backups, schema/data preservation,
  invalid inputs, destination failure safety, each CLI flag, and exit codes.
  Tests should create temporary SQLite databases and must not rely on machine
  databases or network access.
- Exercise realistic concurrent-writer behaviour where practical. Avoid tests
  that depend on timing alone; use synchronization or deterministic fixtures.
- Update user documentation whenever the CLI, output, error behaviour, or
  packaging process changes.

## Clean Code practices

Apply Robert C. Martin's Clean Code principles pragmatically. Correctness,
backup safety, and the simple public CLI take priority; document a meaningful
exception when one is necessary.

- Use intention-revealing names for modules, functions, variables, flags, and
  exceptions. Prefer domain terms such as `source_database` and
  `destination_database` to vague or abbreviated names.
- Keep functions and modules small, focused, and at one level of abstraction.
  Separate command-line parsing, backup orchestration, SQLite access, and
  output formatting rather than mixing them in a single routine.
- Prefer straightforward control flow. Avoid deep nesting, duplicated logic,
  magic values, unclear boolean arguments, and abstractions that do not reduce
  real complexity.
- Keep error handling explicit and close to its boundary. Include useful
  context in raised or reported errors, keep normal execution readable, and
  manage resources at the narrowest practical scope.
- Write isolated, deterministic tests whose names describe one observable
  behaviour. Refactor design debt that makes a safe change difficult instead
  of extending unclear code paths.

## uv package releases

- Release source through immutable GitHub version tags. Users install a release
  with `uv tool install "git+https://github.com/ojeker/sqlite_backup.git@TAG"`.
- Keep `uv.lock` under version control. Use `uv sync --extra test` for
  development and `uv run pytest` for verification.
- Test that `uv tool install .` creates a working command that can run outside
  the source checkout. Do not introduce native compilation or binary artifacts
  unless the release strategy is explicitly changed.
- Keep virtual environments, caches, test databases, and setuptools build
  outputs out of version control.

## Change discipline

- Keep changes small and reviewable. Preserve unrelated work already present
  in the repository.
- Before handing off a change, run the relevant test and lint/type-check
  commands defined by the project and report what was run.
- When behaviour has safety or compatibility trade-offs (especially existing
  destinations, retries, or packaging), state the chosen policy explicitly in
  code, tests, and documentation.
