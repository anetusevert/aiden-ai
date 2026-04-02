.PHONY: up down logs api-test web-test lint format typecheck db-migrate clean lock lock-api lock-web verify

# Docker Compose commands
up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

logs-api:
	docker compose logs -f api

logs-web:
	docker compose logs -f web

# Testing
api-test:
	docker compose exec api uv run pytest -v

web-test:
	docker compose exec web pnpm test

# Linting and formatting
lint:
	docker compose exec api uv run ruff check .
	docker compose exec web pnpm lint

format:
	docker compose exec api uv run ruff format .
	docker compose exec web pnpm format

typecheck:
	docker compose exec api uv run mypy .
	docker compose exec web pnpm typecheck

# Lockfile generation
lock: lock-api lock-web

lock-api:
	cd apps/api && uv lock

lock-web:
	cd apps/web && pnpm install --lockfile-only

# Database (placeholder)
db-migrate:
	@echo "Database migrations not yet implemented"

# Verification (basic - use PowerShell for full verification on Windows)
verify:
	@echo "For full verification on Windows, use: .\\infra\\dev.ps1 verify"
	docker compose up -d --build
	@echo "Waiting for services..."
	sleep 30
	curl -f http://localhost:8000/health
	docker compose exec api uv run pytest -v
	docker compose exec api uv run ruff check .
	docker compose exec web pnpm lint

# Cleanup
clean:
	docker compose down -v --remove-orphans
	docker system prune -f
