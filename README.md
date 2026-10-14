# HyFuse — view-aware fusion of SWIR + TIR HyLogger mineralogy

**GSWA HyLogger Hackathon 2026 · Challenge theme: Data Crunch**

> **Question.** Does combining SWIR and TIR HyLogger mineral results
> (a *view-aware* fusion) recover geological domains and gold-assay-related
> properties better than SWIR alone, TIR alone, or a naive concatenation — when
> tested on drillholes the method has never seen?
>
> **Answer (on 15 gold holes): INCONCLUSIVE, reported honestly.** Fusion is **no
> better than the best single view** for domaining, and **no representation
> predicts gold grade on held-out holes**. The value here is a rigorous,
> reproducible, independently-reviewed pipeline that produces a *trustworthy*
> answer — positive or not.

## Team

- **Team name:** HyFuse Team
- **Members:** Stephane Benayoun
- **Team captain:** Stephane Benayoun

## What we built

A reproducible pipeline + interactive viewer that:

1. Fetches per-hole TSG packages from NCI THREDDS and reads SWIR/TIR mineral
   results, groups, error and **Final Mask** with `pytsg`.
2. Applies GSWA data-quality rules (keep Final-Mask core, keep
   `invalid`/`aspectral` explicit, ignore TSAV, prefer Mineral Group, use
   `error` as confidence), composites to 5 m depth windows, and overlap-weights
   logged lithology and assays onto those windows (DuckDB).
3. Builds four comparison **arms** — SWIR-only, TIR-only, naive concatenation,
   and a view-aware **fused** representation (per-view compositional transform
   then concatenate; SWIR and TIR are never pooled into one composition).
4. Domains each arm (PCA → HDBSCAN → `ruptures` change-point segmentation) and
   scores them, on **held-out holes**, against logged lithology boundaries (with
   a permutation baseline) and against gold assays (leave-holes-out CV), with
   hole-level bootstrap uncertainty and a processing-level confounder check.
5. A **planted-truth** simulator and **corruption tests** that fail loudly if the
   method or data are wrong.

## Headline results (generated — see `reports/ablation.md`)

15 gold holes. Every number below is produced by `make evaluate`; nothing here
is hand-entered.

| arm | boundary F1 vs logged lithology | gold Au R² (median, leave-holes-out) |
|---|---:|---:|
| SWIR only | 0.102 | −1.7 (no skill) |
| TIR only | 0.139 | −1.6 (no skill) |
| naive concat | 0.129 | −6.0 (no skill) |
| **fused (view-aware)** | **0.140** | −6.5 (no skill) |

- **Fusion vs best single view (TIR):** boundary-F1 delta **+0.001**, hole-level
  bootstrap 95% CI **[−0.017, +0.022]** — **includes zero**. No reliable
  difference: fusion does **not** beat the best single view.
- **Gold prediction:** no arm has cross-hole skill (all median R² ≤ 0) —
  mineralogy windows alone do not predict Au grade on held-out holes.
- **Confounder:** detected domains are **not** explained by TIR processing level
  (`reports/confounders.md`).
- **Window-size sensitivity** (`reports/sensitivity.md`): the headline uses the
  pre-registered **5 m** window. The verdict is *sensitive to resolution* — at
  **~1 m fusion does beat** the best single view (delta +0.028, CI [+0.008,
  +0.051]), but at 0.5 m it is inconclusive again. We report this honestly and do
  **not** move the headline off 5 m post-hoc: **any fusion benefit is not robust
  across resolutions.**

See `reports/planted_truth.md` for the known-answer study that drove our method
choices (notably: CLR destroyed the domain signal, so we use a Hellinger
transform; naive concatenation is a strong baseline).

## Limitations (read before trusting the result)

- **n = 15 holes, effectively one deposit.** 11/15 are the Bannockburn
  (BBDD/BBRD) deposit; only 4 are other projects (12DHDD0002, 15SYDD0003B,
  16CADD001, BCMH0070). Leave-holes-out across near-identical holes is a **weak
  generality test** — the result is conditioned on essentially one geological
  setting and does not generalise.
- **Assay selection bias.** Company assays concentrate where mineralisation was
  expected (prospective intervals); Au is the only broadly-covered target.
- **Logged lithology is company-specific** and far finer than 5 m; we score
  boundary *agreement within tolerance* at the window resolution, not code
  equality.
- **Not geologically validated.** Detected domains have not been checked against
  core by a geologist; whether boundaries track weathering/regolith rather than
  lithology is an open question (see `reports/review_R3.md`, item J).
- This is a software + statistics project. Nothing here claims mineralisation.

## Install and run

Requires `uv` (and, for a fresh fetch, internet access to NCI THREDDS + the DASC
package). Python 3.12.

```bash
uv sync
make doctor            # environment smoke test
make test              # 75 tests (planted-truth + corruption tests included)

make fetch             # downloads TSG packages for config/holes.yaml (~8 GB; NOT in git)
make features          # tidy per-hole Parquet + coverage audit
make evaluate          # four-arm ablation -> reports/ablation.md + confounders.md
make viewer            # Streamlit hole viewer at http://localhost:8501
```

`make fetch` downloads ~8 GB of per-hole TSG packages (sequential, cached). If
you only want to reproduce the analysis from already-fetched data, run
`make features && make evaluate`. A clean clone with no cache must run
`make fetch` first.

## Data (not committed)

No HyLogger data or row-level derived data is in git (see `.gitignore`); only
small summary tables/figures under `reports/`.

- **HyLogger TSG packages:** NCI THREDDS WA catalogue —
  <https://thredds.nci.org.au/thredds/catalog/rs07/WA/catalog.html>
- **Collar / survey / logged lithology / assays:** GSWA DASC "HyLogger
  Drillholes package" (interim, GDA2020) — <https://dasc.dmirs.wa.gov.au/>
  (search "HyLogger Drillholes package"). Join key: `NVCL_HoleName` /
  `WAMEX_CollarId` in `hylogger_dataset_index`.

The 15 holes used are pinned in `config/holes.yaml`.

## How it is verified

- **Pre-registration:** success criteria, depth tolerance (2.0 m), metric, CV
  scheme and bootstrap unit are frozen in `config/params.yaml`, committed
  **before** any results file (`git log -p config/params.yaml`).
- **Leave-holes-out CV** (`GroupKFold` by `hole_id`) and a **permutation
  baseline** for boundary agreement; **hole-level bootstrap** for uncertainty.
- **Planted-truth** simulation and **corruption tests** (×1000 units, depth
  offset, ignored Final Mask, shuffled hole IDs) that must flag or degrade.
- **Independent reviews** in separate fresh sessions (R1–R3, see
  `reports/review_R1.md`..`review_R3.md`) plus a **reviewer calibration**
  (`reports/calibration.md`) that planted three defects and confirmed the review
  process caught all three.

Failure modes checked and accepted limitations are listed in
`reports/review_response.md`.

## Packages

Python 3.12 via `uv`; see `pyproject.toml` / `uv.lock`. Core: `pytsg`, `httpx`,
`tenacity`, `duckdb`, `pyarrow`, `pandas`, `numpy`, `scipy`, `scikit-learn`,
`ruptures`, `plotly`, `streamlit`, `pyyaml`, `nvcl-kit`.

## AI tools used

Developed with assistance from **Kiro** (agentic CLI) for implementation, and the
independent review/calibration steps were run as separate fresh agent sessions.
Disclosed per the hackathon rules.

## Licence

MIT — see `LICENSE`.

## Screenshots / demo

The interactive viewer (`make viewer`) — hole depth log with mineral-group
stacks, detected domain boundaries (red) and logged lithology boundaries (grey),
plus an **Ablation summary** tab showing the generated results:

![HyFuse viewer](docs/viewer.png)

*(If the image is missing, run `make viewer` and open http://localhost:8501.)*

## Reproducing the figures

`make fetch && make evaluate` on a clean clone reproduces `reports/ablation.md`
and `reports/confounders.md`. Runtime: features+evaluate on cached data is a few
minutes; `make fetch` dominates (~8 GB download). Disk: budget ~15 GB for the
cached zips + extracted TSG.
