.PHONY: help install test validate analyze train score plan clean

help:
	@echo "CashFlowGuard - Makefile commands:"
	@echo "  make install    - Install package and dependencies"
	@echo "  make test       - Run tests"
	@echo "  make generate   - Generate sample data"
	@echo "  make validate   - Validate sample data"
	@echo "  make analyze    - Run AR analysis"
	@echo "  make clean      - Clean generated files"

install:
	pip install -e ".[dev]" --break-system-packages

test:
	pytest tests/ -v

generate:
	python scripts/generate_synthetic_data.py --customers 50 --invoices 200 --months 6

validate:
	python -m cashflowguard.cli validate

analyze:
	python -m cashflowguard.cli analyze

clean:
	rm -rf outputs/* models/* *.egg-info build/ dist/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
