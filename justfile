# Start Docker services, inc. the local Postgres container
up:
    docker compose up -d

# Stop Docker services, inc. the local Postgres container
down:
    docker compose down

# Run the app, i.e. Django dev server
run:
    uv run python manage.py runserver

# Run database migrations
migrate:
    uv run python manage.py migrate

# Run tests
test:
    uv run pytest

# Run linters
lint:
    uv run ruff check .
    uv run mypy .

# Format code
format:
    uv run ruff format .

# Run type checking
typecheck:
    uv run mypy .

# Run everything CI would run
check: lint typecheck test