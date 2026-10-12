# HyFuse

**GSWA HyLogger Hackathon 2026 — theme: Data Crunch.**

Does combining SWIR and TIR HyLogger mineral results (view-aware fusion) recover
geological domains and assay-related properties better than SWIR alone, TIR
alone, or naive concatenation, tested on held-out drillholes?

> **Status: work in progress (Day 1 complete).** This README is a stub; the full
> version (team, install/run, results table, screenshots, licence, AI-tools
> disclosure, limitations) is written at task T4.2 before submission. See
> `AGENT_INSTRUCTIONS.md` for the plan and `STATUS.md` for current state.

## Reproduce (once the pipeline is complete)

```bash
uv sync
make fetch       # downloads TSG packages for config/holes.yaml (not in git)
make evaluate    # builds reports/ablation.md   (Day 3)
make test
```

## Data (not committed)

- HyLogger TSG packages: NCI THREDDS WA catalogue
  <https://thredds.nci.org.au/thredds/catalog/rs07/WA/catalog.html>
- Associated collar/survey/logging/assays: GSWA DASC "HyLogger Drillholes
  package" (interim, GDA2020) <https://dasc.dmirs.wa.gov.au/>

No HyLogger data or derived row-level data is committed (see `.gitignore`); only
small derived outputs under `reports/`.

## Packages

Python 3.12 via `uv`; see `pyproject.toml` / `uv.lock`. Core: httpx, tenacity,
pytsg, duckdb, pyarrow, pandas, numpy, scipy, scikit-learn, ruptures, plotly,
streamlit, pyyaml, nvcl-kit.

## AI tools

Built with assistance from Kiro (disclosed per hackathon rules); full disclosure
in the T4.2 README.
