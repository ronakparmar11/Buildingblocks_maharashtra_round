.PHONY: install test lint fmt api web

PYTHON := .venv/bin/python

install:
	python3 -m venv .venv
	$(PYTHON) -m pip install -e ".[dev]"
	npm --prefix frontend install

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .
	npm --prefix frontend run lint

fmt:
	$(PYTHON) -m ruff format .
	npm --prefix frontend run format

api:
	$(PYTHON) -m uvicorn blackbox.api:app --reload

web:
	npm --prefix frontend run dev
