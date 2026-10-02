PY = .venv/bin/python
RUFF = .venv/bin/ruff

.PHONY: sync data lint check verify data-summary

sync:
	uv sync --frozen --all-groups

data:
	$(PY) -m local_elections_uttarakhand.parse.to_parquet
	$(MAKE) verify data-summary

lint:
	$(RUFF) check .
	$(RUFF) format --check .

verify:
	$(PY) -m local_elections_uttarakhand.build.release verify

data-summary:
	$(PY) -m local_elections_uttarakhand.build.release summary

check: lint verify
