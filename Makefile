.PHONY: install test lint fmt api web demo

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

demo:
	@$(PYTHON) -c 'import socket; sockets = [socket.create_server(("127.0.0.1", port)) for port in (8000, 4173)]; [item.close() for item in sockets]' 2>/dev/null || (echo "Demo ports 8000 or 4173 are already in use. Stop the existing servers and retry."; exit 1)
	npm --prefix frontend run build
	@BLACKBOX_DEMO_MODE=1 $(PYTHON) -m uvicorn blackbox.api:app --host 127.0.0.1 --port 8000 & \
	api_pid=$$!; \
	trap 'kill "$$api_pid" 2>/dev/null || true' EXIT INT TERM; \
	npm --prefix frontend run preview -- --host 127.0.0.1 --port 4173
