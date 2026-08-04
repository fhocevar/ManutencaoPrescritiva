.PHONY: up down logs test lint format migrate bootstrap-data export-openapi demo-seed smoke

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f api dashboard worker

migrate:
	docker compose exec api alembic upgrade head

test:
	docker compose exec api pytest -q --cov=app --cov-report=term-missing

lint:
	docker compose exec api ruff check .

typecheck:
	docker compose exec api mypy app

format:
	docker compose exec api ruff format .

bootstrap-data:
	docker compose exec api python -m scripts.train_models --csv data/banner.csv
	docker compose exec api python -m scripts.ingest_csv --csv data/banner.csv
	docker compose exec api python -m scripts.ingest_documents --directory data/documents

export-openapi:
	docker compose exec api python -m scripts.export_openapi --output docs/openapi.json

demo-seed:
	docker compose exec api python -m scripts.seed_demo

smoke:
	curl -fsS http://localhost:8000/health/live
	curl -fsS http://localhost:8000/health/ready
