# Start Docker services, inc. the local Postgres container
up:
    docker compose up -d

# Stop Docker services, inc. the local Postgres container
down:
    docker compose down

# Run the app, i.e. Django dev server
run:
    uv run python manage.py runserver

# Lock checks
lockcheck:
    uv lock --check

# Ruff checks & auto-fixes
lint:
    uv run ruff check --fix .

# Ruff format
format:
    uv run ruff format .

# Mypy checks
typecheck:
    uv run mypy .

# Run database migrations
migrate:
    uv run python manage.py migrate

# Pytest tests with coverage
test:
    uv run pytest

# Run everything CI would run
check: lockcheck lint format typecheck test