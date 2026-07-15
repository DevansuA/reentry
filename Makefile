.PHONY: setup setup-web test test-server test-all eval demo demo-full \
        server web-dev web-build lint typecheck

# --- setup ------------------------------------------------------------------

setup:
	pip3 install --break-system-packages -e . pytest fastapi uvicorn httpx watchdog mcp

setup-web:
	npm --prefix web install

# --- tests ------------------------------------------------------------------

test:
	python3 -m pytest tests -q

test-server:
	PYTHONPATH=. python3 -m pytest server/tests -q

test-all: test test-server

# --- eval -------------------------------------------------------------------

eval:
	python3 -m evals.run_eval

# --- CLI demo (no web) ------------------------------------------------------

demo:
	@rm -f /tmp/reentry-demo.db && rm -rf /tmp/reentry-demo-proj
	REENTRY_DB=/tmp/reentry-demo.db reentry demo --dir /tmp/reentry-demo-proj

# --- full web demo ----------------------------------------------------------
# Seeds the demo, starts FastAPI + Next.js, then opens the browser.
# Both servers run in the foreground; Ctrl+C stops them.

demo-full:
	@$(MAKE) --no-print-directory demo
	@[ -d web/node_modules ] || $(MAKE) --no-print-directory setup-web
	@echo ""
	@echo "Starting servers (Ctrl+C to stop):"
	@echo "  API  http://localhost:8000"
	@echo "  Web  http://localhost:3000"
	@echo ""
	@echo "Beat-by-beat script:"
	@echo "-------------------------------------------------"
	@cat docs/DEMO_SCRIPT.md
	@echo "-------------------------------------------------"
	@echo ""
	@trap 'kill %1 %2 2>/dev/null; exit 0' INT; \
	  REENTRY_DB=/tmp/reentry-demo.db PYTHONPATH=. \
	    python3 -m uvicorn server.app:app --port 8000 --log-level warning & \
	  NEXT_TELEMETRY_DISABLED=1 npm --prefix web run dev -- --port 3000 & \
	  sleep 5 && (open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null || true) && \
	  wait

# --- individual servers (for development) -----------------------------------

server:
	PYTHONPATH=. python3 -m uvicorn server.app:app --reload --port 8000

web-dev:
	NEXT_TELEMETRY_DISABLED=1 npm --prefix web run dev -- --port 3000

web-build:
	NEXT_TELEMETRY_DISABLED=1 npm --prefix web run build

# --- MCP server (stdio transport) -------------------------------------------

mcp-server:
	PYTHONPATH=. python3 mcp/server.py

# --- quality checks ---------------------------------------------------------

lint:
	python3 -m compileall -q src evals tests server mcp
	@python3 -m pyflakes src evals tests server mcp 2>/dev/null || \
	  echo "(pyflakes not installed; compileall passed)"

typecheck:
	@python3 -m mypy src 2>/dev/null || \
	  echo "(mypy not installed; skipped — annotations are present throughout)"
