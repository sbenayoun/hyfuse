# HyFuse Makefile — every target runs project code through `uv run`.
# Pipeline: make fetch && make evaluate must reproduce results on a clean clone.

.DEFAULT_GOAL := help
.PHONY: help doctor test lint fetch features domains fusion evaluate viewer clean

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	 | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

doctor:  ## Environment smoke test (versions, disk, venv, duckdb)
	@uv run python scripts/doctor.py
	@echo "--- free disk on \$$HOME ---"
	@df -h "$$HOME" | tail -1

test:  ## Run the test suite (planted-truth + corruption tests included later)
	uv run pytest -q

lint:  ## Lint with ruff
	uv run ruff check .

fetch:  ## T1.4: fetch TSG data for holes in config/holes.yaml (cached, sequential)
	uv run python -m hyfuse.fetch --max-holes $$(uv run python -c "import yaml;print(len(yaml.safe_load(open('config/holes.yaml'))['holes']))")

features:  ## T1.6/T1.7: tidy depth-aligned tables + coverage audit
	uv run python -m hyfuse.features
	uv run python -m hyfuse.coverage

domains:  ## T2.4: per-view domaining
	uv run python -m hyfuse.domains

fusion:  ## T3.2: four-arm ablation feature matrices
	uv run python -m hyfuse.fusion

evaluate:  ## T3.3: score all arms, write reports/ablation.md
	uv run python -m hyfuse.evaluate

viewer:  ## T2.8/T4.1: launch the Streamlit hole viewer
	uv run streamlit run app/viewer.py --server.headless true

clean:  ## Remove caches (keeps data/ and reports/)
	rm -rf .pytest_cache .ruff_cache **/__pycache__
