PY = .venv/bin/python
RUFF = .venv/bin/ruff

.PHONY: sync data links infer lint check verify data-summary

sync:
	uv sync --frozen --all-groups

data:
	$(PY) -m local_elections_uttarakhand.parse.to_parquet
	$(MAKE) verify data-summary

# research derivatives: pradhan seat links and name-based winner sex
links:
	$(PY) -m local_elections_uttarakhand.linkage.gp_links

infer:
	$(PY) -m local_elections_uttarakhand.infer.winner_sex

lint:
	$(RUFF) check .
	$(RUFF) format --check .

verify:
	$(PY) -m local_elections_uttarakhand.build.release verify

data-summary:
	$(PY) -m local_elections_uttarakhand.build.release summary

check: lint verify
