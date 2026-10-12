NEXT ACTION: T1.2 — dry run on one hole: confirm NCI THREDDS reachable, download one hole zip, unzip, parse with pytsg (NIR + TIR spectra/wavelengths load).

# HyFuse status

## Done
- Environment (AGENT_INSTRUCTIONS section 2A): WSL2 confirmed, Linux filesystem
  (not /mnt/c), 886 GB free, 31 GB RAM.
- System tools: git, curl, unzip, sqlite3, build-essential; gh 2.102.0 installed.
- uv 0.9.15 managing Python 3.12.12. Project at
  ~/opt/hackathon/gswa/hyfuse with its own .venv.
- All runtime deps installed and import-verified: httpx, tenacity, pytsg 1.0.0,
  duckdb 1.5.6, pyarrow, pandas, numpy, scipy, scikit-learn 1.9.1 (incl.
  HDBSCAN), ruptures, plotly, streamlit, pyyaml, nvcl-kit 1.3.5. Dev: pytest, ruff.
- DuckDB sqlite extension autoloads (verified).
- T1.1 scaffold: dir layout, .gitignore (data patterns), config/params.yaml
  (pre-registered), config/holes.yaml (empty), module stubs, Makefile with
  `make doctor`/`make test`, scripts/doctor.py, smoke test.

## Pre-fetched assets (in ../, outside the repo)
- ../datasets/INTERIM_HyLogger_Dataset_Package_GDA2020_DB.zip (DASC package,
  86 MB): SQLite at DATABASES/HyLogger_Dataset_Package.sqlite + data dictionary.
- ../pytsg (clone with example_data: PE257D, SWMB007s/d, SWMB008d, GSNSW_testrocks)
  — real .tsg/.bip files to test read.py without any NVCL download.

## Decided
- Project lives at ~/opt/hackathon/gswa/hyfuse (option 1), next to planning docs
  and pre-fetched data.

## Blocked / to do by human
- `gh auth login` (interactive) before `gh repo create`.

## Verification checkpoints
- None passed yet. R1 due end of Day 1 (scope D, E, I).
