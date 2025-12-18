# Makefile for Movie Recommendation System
# Provides convenient commands for common tasks

.PHONY: help bootstrap_bronze validate_bronze docs clean

help:
	@echo "Available commands:"
	@echo "  make bootstrap_bronze  - Download and extract MovieLens 25M to Bronze layer"
	@echo "  make validate_bronze    - Validate Bronze layer data presence"
	@echo "  make docs               - View documentation (opens docs in browser if possible)"
	@echo "  make clean              - Clean temporary files (does not delete Bronze data)"

bootstrap_bronze:
	@echo "Bootstrap MovieLens 25M dataset..."
	@python scripts/bootstrap_bronze_movielens_25m.py

validate_bronze:
	@echo "Validating Bronze layer..."
	@python scripts/validate_bronze_presence.py

docs:
	@echo "Documentation files:"
	@echo "  - docs/01_data_contracts.md - Data contracts and schemas"
	@echo "  - docs/02_step2_bootstrap_bronze.md - Step 2 bootstrap guide"
	@echo ""
	@echo "Opening documentation..."
	@if command -v xdg-open > /dev/null; then \
		xdg-open docs/01_data_contracts.md 2>/dev/null || true; \
	elif command -v open > /dev/null; then \
		open docs/01_data_contracts.md 2>/dev/null || true; \
	else \
		echo "Please open docs/01_data_contracts.md manually"; \
	fi

clean:
	@echo "Cleaning temporary files..."
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete"

