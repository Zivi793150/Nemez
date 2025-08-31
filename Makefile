.PHONY: help install test run clean docker-build docker-run docker-stop

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install pytest pytest-cov black isort flake8

test: ## Run tests
	pytest --cov=app --cov-report=html

test-watch: ## Run tests in watch mode
	pytest-watch -- --cov=app

lint: ## Run linting
	black app/
	isort app/
	flake8 app/

format: ## Format code
	black app/
	isort app/

run: ## Run the application
	python run.py

run-dev: ## Run in development mode
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

clean: ## Clean up generated files
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "htmlcov" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type d -name ".tox" -delete
	find . -type d -name "build" -delete
	find . -type d -name "dist" -delete
	find . -type d -name "*.egg-info" -delete

docker-build: ## Build Docker image
	docker build -t apartment-finder .

docker-run: ## Run with Docker Compose
	docker-compose up -d

docker-stop: ## Stop Docker Compose
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

docker-shell: ## Open shell in web container
	docker-compose exec web bash

db-init: ## Initialize database
	alembic init migrations
	alembic revision --autogenerate -m "Initial migration"
	alembic upgrade head

db-migrate: ## Create new migration
	alembic revision --autogenerate -m "$(message)"

db-upgrade: ## Apply migrations
	alembic upgrade head

db-downgrade: ## Rollback migrations
	alembic downgrade -1

setup: ## Initial setup
	@echo "Setting up the project..."
	@if [ ! -f .env ]; then \
		echo "Creating .env file from template..."; \
		cp env_web_example.txt .env; \
		echo "Please edit .env file with your configuration"; \
	fi
	@echo "Installing dependencies..."
	@make install
	@echo "Setup complete! Edit .env file and run 'make run' to start"

deploy: ## Deploy to production
	@echo "Deploying to production..."
	git push origin main
	@echo "Deployment triggered via GitHub Actions"
