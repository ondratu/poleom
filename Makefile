.PHONY: install test lint typecheck check wheel dev clean help

PYTHON ?= .venv/bin/python

install:
	uv pip install -e ".[lint,typecheck,test,server,dev,build]"

test:
	$(PYTHON) -m pytest

lint:
	.venv/bin/ruff check poleom tests
	.venv/bin/pylint poleom
	.venv/bin/pylint --rcfile=tests/.pylintrc tests

typecheck:
	.venv/bin/mypy poleom

# the same checks as in CI
check:
	PATH=$(CURDIR)/.venv/bin:$$PATH pre-commit run --all-files --show-diff-on-failure

wheel:
	rm -rf dist
	$(PYTHON) -m build
	.venv/bin/twine check --strict dist/*
	tools/check-wheel.sh dist/*.whl

dev:
	uwsgi --ini example/etc/uwsgi.ini

clean:
	find . -type f -name "*.pyc" -not -path "./.venv/*" -delete
	find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} +
	rm -rf build dist .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml

help:
	@echo "install   - install the package and dev dependencies into .venv"
	@echo "test      - run tests with coverage report"
	@echo "lint      - run ruff and pylint"
	@echo "typecheck - run mypy"
	@echo "check     - run all pre-commit hooks, like CI does"
	@echo "wheel     - build and check the wheel"

	@echo "dev       - run the uWSGI development server"
	@echo "clean     - remove caches and coverage data"
