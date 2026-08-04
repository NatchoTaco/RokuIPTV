# StreamForge API

FastAPI backend for the StreamForge Milestone 1 foundation.

## Local Commands

Install dependencies:

```sh
pip install -e ".[dev]"
```

Run the API:

```sh
uvicorn streamforge_api.main:app --reload
```

Run migrations from the repository root:

```sh
alembic -c apps/api/alembic.ini upgrade head
```

Run tests:

```sh
pytest apps/api/tests
```
