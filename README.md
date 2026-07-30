# Malaria Observer

Malaria Observer is an open-source Wagtail application for exploring publicly available malaria datasets and the scientific studies that produce them. It combines editorial content with interactive data exploration and geographical mapping.

## Requirements

- Python 3.13
- uv
- Docker Desktop
- just

## Initial setup

```sh
git clone <repo>
cd malaria-observer
uv sync
cp .env.example .env
just up
just migrate
uv run python manage.py createsuperuser
just run
```

Visit http://localhost:8000/admin/

## Daily development

```sh
just up
just run
```

## Tooling

- Dependency management: uv
- Database: PostgreSQL (Docker Compose)
- Testing: pytest
- Linting: Ruff
- Type checking: mypy
- Task runner: just
- Pre-commit hooks: pre-commit
- CI: GitHub Actions

## Application structure

The project is organised by domain responsibility.

- `home` — homepage and simple top-level landing pages.
- `core` — shared Wagtail components: base page models, StreamField blocks, utilities, mixins, template tags, and common functionality used across other apps.
- `studies` — Wagtail pages for scientific studies, publications, and associated metadata, including links to data sources.
- `explorer` — a Django app providing interactive exploration of datasets, observations and geographic data.
- `articles` — Wagtail pages for articles, explainers, educational content, and news.
- `search` — Wagtail site search.

## Contributing

See `CONTRIBUTING.md` for setup details, task-runner commands, and development conventions.

## License

AGPL-3.0 — see `LICENSE.txt`.