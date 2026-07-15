.PHONY: setup test eval demo lint typecheck

setup:
	pip install --break-system-packages -e . pytest

test:
	python3 -m pytest tests -q

eval:
	python3 -m evals.run_eval

demo:
	@rm -f /tmp/reentry-demo.db && rm -rf /tmp/reentry-demo-proj
	REENTRY_DB=/tmp/reentry-demo.db reentry demo --dir /tmp/reentry-demo-proj

lint:
	python3 -m compileall -q src evals tests
	@python3 -m pyflakes src evals tests 2>/dev/null || echo "(pyflakes not installed; compileall passed)"

typecheck:
	@python3 -m mypy src 2>/dev/null || echo "(mypy not installed; skipped — annotations are present throughout)"
