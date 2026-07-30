# Contributing

## Prerequisites

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- [Docker](https://www.docker.com/) (for local PostgreSQL)
- [just](https://github.com/casey/just)

## Setup

1. Clone the repo and install dependencies:

```bash
   uv sync
```

2. Copy the example environment file and fill in values:

```bash
   cp .env.example .env
```

3. Start PostgreSQL:

```bash
   just up
```

4. Run migrations:

```bash
   just migrate
```

5. Create a superuser:

```bash
   uv run python manage.py createsuperuser
```

6. Run the dev server:

```bash
   just run
```

   Visit http://localhost:8000/admin/

## Common tasks

| Command       | What it does                          |
|---------------|----------------------------------------|
| `just up`     | Start Postgres (Docker)               |
| `just down`   | Stop Postgres                         |
| `just run`    | Run the Django dev server             |
| `just migrate`| Apply database migrations             |
| `just test`   | Run the test suite                    |
| `just lint`   | Run Ruff                              |
| `just format` | Auto-format code with Ruff            |
| `just typecheck` | Run Mypy                           |
| `just check`  | Run everything CI would run           |

## Pre-commit hooks

Install once, so lint/type/migration checks run automatically on commit:

```bash
uv run pre-commit install
```

## Testing

Tests use a dedicated PostgreSQL test database and Wagtail's `WagtailPageTestCase`
for page-model tests. See `studies/tests.py` for an example pattern.

## Conventions

- Commit frequently, in small logical units.
- Rely on pre-commit hooks to catch issues before they reach CI.
- Run `just test` before pushing; run `just check` before opening a PR.
- Avoid manual edits to generated migration files unless there is a clear reason and the change has been reviewed.
- Every Wagtail page model must have a corresponding template.
- StreamField blocks should live in `core.blocks`, not duplicated per-app.

## Application structure

See `README.md` for the app breakdown.