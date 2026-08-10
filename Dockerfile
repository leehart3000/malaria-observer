# Stage 1 — build
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

RUN apt-get update --yes --quiet && apt-get install --yes --quiet --no-install-recommends \
    build-essential \
    libpq-dev \
    libmariadb-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libwebp-dev \
 && rm -rf /var/lib/apt/lists/*

RUN pip install uv

# Copy dependency files first so Docker can cache this layer
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Add gunicorn into the same venv uv created
RUN uv pip install "gunicorn==25.1.0"

# Copy all the files except the ones in .dockerignore
COPY . .


# Stage 2 — runtime
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

RUN apt-get update --yes --quiet && apt-get install --yes --quiet --no-install-recommends \
    libpq5 \
    libmariadb3 \
    libjpeg62-turbo \
    libwebp7 \
 && rm -rf /var/lib/apt/lists/*

RUN useradd django

COPY --from=builder --chown=django:django /app /app

RUN chown django:django /app

ENV PATH="/app/.venv/bin:$PATH"

USER django

EXPOSE 8000

# Collect static files (dummy values — this step never touches the real DB)
RUN SECRET_KEY=dummy DATABASE_URL=sqlite:///dummy.db DJANGO_SETTINGS_MODULE=malaria_observer.settings.production \
    python manage.py collectstatic --noinput --clear

CMD ["gunicorn", "malaria_observer.wsgi:application", "--bind", "0.0.0.0:8000"]