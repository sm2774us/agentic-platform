.PHONY: install lint format typecheck test cov run docker-build ci

install:
	pip install -e ".[dev]"

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy src

test:
	python -m pytest

cov:
	python -m pytest --cov-report=html && echo "open htmlcov/index.html"

run:
	uvicorn agentic_platform.api.main:app --reload --port 8000

docker-build:
	docker build -t agentic-platform:local .

ci: lint typecheck test
