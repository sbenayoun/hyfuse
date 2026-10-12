NEXT ACTION: T1.3 — on a REAL NVCL hole, confirm the Final Mask scalar name and on/off direction, and whether NVCL exposes a cleaner processing-level flag than the column suffixes (sTSAS/sTSAT/uTSAT). TSG read path + mineral/group/error decoding already validated offline.

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
  `make doctor`/`make test`, scripts/doctor.py, smoke test. Commit a55a57e.
- T1.2 TSG read path validated OFFLINE against pytsg example hole PE257D
  (scripts/explore_tsg.py): nir(380-2500nm)/tir(5350-15000nm) spectra +
  wavelengths load; mineral results decode to names; depth in sampleheaders.D.
- THREDDS catalogue reachable (HTTP 200).
- reports/data_notes.md written with T1.2/T1.3 findings (see Decided/Found).

## Found (T1.2/T1.3, see reports/data_notes.md)
- pytsg decodes Min1/Grp1 to mineral NAME strings; no manual code lookup needed
  for TSG results. Grp1 = harmonised groups (WHITE-MICA, SILICA, KAOLIN, ...).
- Column convention: SWIR=sTSAS (ignore sTSAV), TIR=sTSAT/uTSAT. Error=confidence.
- aspectral/invalid/MaskedOff appear as explicit Min1/Grp1 class values.
- CRITICAL: Wt1/Error carry float32 null sentinel -3.4e38 on masked rows ->
  must null before stats (feeds qc.py + corruption tests T2.7).
- Depth = sampleheaders['D'] (metres).
- Final Mask: no standalone column in the CSIRO example; VERIFY on a real NVCL hole.

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
