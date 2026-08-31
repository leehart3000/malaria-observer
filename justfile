# Start Docker services in the background
up:
    docker compose up -d

# Stop Docker services
down:
    docker compose down

# Run the Django dev server
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

# Run Django check
djangocheck:
    uv run python manage.py check

# Make database migrations
makemigrations:
    uv run python manage.py makemigrations

# Run database migrations
migrate:
    uv run python manage.py migrate

# Pytest tests with coverage and fresh db
test:
    uv run pytest --create-db

# Run all checks, without migrate
check: lockcheck lint format typecheck test djangocheck