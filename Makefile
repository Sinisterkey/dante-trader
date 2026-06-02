.PHONY: help install setup run docker-build docker-up docker-down test clean lint format

help:
	@echo "AI Trading Agent - Makefile Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install        - Install Python dependencies"
	@echo "  make setup          - Full setup (install + init db)"
	@echo ""
	@echo "Running:"
	@echo "  make run            - Run trading agent locally"
	@echo "  make run-debug      - Run with debug logging"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   - Build Docker image"
	@echo "  make docker-up      - Start Docker container"
	@echo "  make docker-down    - Stop Docker container"
	@echo "  make docker-logs    - View Docker logs"
	@echo ""
	@echo "Development:"
	@echo "  make lint           - Run code linting (pylint, flake8)"
	@echo "  make format         - Format code with black and isort"
	@echo "  make test           - Run test suite"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Clean cache and logs"
	@echo "  make db-reset       - Reset database (WARNING: deletes all trades)"
	@echo "  make health-check   - Test system health"

# ==================== Setup ====================

install:
	pip install -r requirements.txt
	python -c "import nltk; nltk.download('vader_lexicon', quiet=True)"

setup: install
	mkdir -p data logs
	python -c "from backend.db import TradingDatabase; TradingDatabase()"
	@echo "✓ Setup complete. Edit .env file with your credentials."

# ==================== Running ====================

run:
	@cd backend && python main.py

run-debug:
	@LOG_LEVEL=DEBUG cd backend && python main.py

# ==================== Docker ====================

docker-build:
	docker build -t ai-trading-agent:latest .

docker-up:
	docker-compose up -d
	@echo "✓ Container started. Check status with 'make docker-logs'"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f trading-agent

docker-restart:
	docker-compose restart

# ==================== Development ====================

lint:
	pylint backend/ telegram/ config.py --disable=C0111,C0103,R0913
	flake8 backend/ telegram/ config.py --max-line-length=120

format:
	black backend/ telegram/ config.py
	isort backend/ telegram/ config.py

test:
	pytest tests/ -v --tb=short

# ==================== Maintenance ====================

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/ htmlcov/ .coverage
	rm -rf logs/*.log

db-reset:
	@echo "⚠️  WARNING: This will delete all trades and data!"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -f data/trades.db; \
		python -c "from backend.db import TradingDatabase; TradingDatabase()"; \
		echo "✓ Database reset"; \
	else \
		echo "Cancelled"; \
	fi

health-check:
	@echo "🔍 Running health checks..."
	@python -c "from backend.db import TradingDatabase; print('✓ Database OK')" || echo "✗ Database failed"
	@python -c "import MetaTrader5; print('✓ MT5 module OK')" || echo "✗ MT5 failed"
	@python -c "import telegram; print('✓ Telegram module OK')" || echo "✗ Telegram failed"
	@python -c "from config import *; print('✓ Config loaded')" || echo "✗ Config failed"
	@curl -s http://localhost:8000/health > /dev/null && echo "✓ API responding" || echo "✗ API not running"

# ==================== Shortcuts ====================

start: docker-up

stop: docker-down

restart: docker-restart

logs: docker-logs
