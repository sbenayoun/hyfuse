# Review of HyFuse — 2026-10-12, commit 1f36dca

**Scope:** items D, E, I only (end-of-Day-1 checkpoint R1). Items A, B, C, F, G,
H, J were not reviewed. Reviewed as an independent reader of the repo at commit
`1f36dca` on branch `main` (working tree clean). Evidence commands were run
against cached data only (`data/raw/holes/ETG0187`, `data/raw/dasc/`); no
downloads were performed. The 15 holes in `config/holes.yaml` are not yet
fetched — expected at R1.

## Verdict

**Go with fixes** — as an end-of-Day-1 checkpoint. The GSWA data-handling rules
(D) that are implemented are implemented correctly and are backed by executed
evidence on a real NVCL hole (ETG0187). The repo cleanliness rules (no data in
git, `.gitignore`, pinned versions) pass. The remaining items are either
not-yet-built pipeline stages (assay compositing/below-detection, domaining,
fusion, evaluation — all Day 2+) which are correctly UNVERIFIED at R1, or two
concrete gaps that should be fixed before they bite: (1) the `make fetch` default
guard (`--max-holes 5`) refuses the 15-hole `holes.yaml`, so a clean-clone
reproduction stops at fetch; (2) `README.md` is empty (0 bytes), so none of the
reproducibility/package/data-location rules it is supposed to carry exist yet.
No blockers found within scope.

## Checklist results

### D. Data handling rules from GSWA
- **D1 Final Mask applied; non-core rows excluded — PASS.** `qc.apply_final_mask`
  keeps `final_mask == 1`. On ETG0187: 2835 rows/view, 1744 kept, 1091 dropped
  per view (3488 kept total). Row counts match `reports/data_notes.md`.
- **D2 `invalid`/`aspectral` kept as explicit states — PASS.** `EXPLICIT_STATES`
  in `read.py` includes `invalid`, `aspectral`, `maskedoff`, etc. On ETG0187 the
  11 `INVALID` (mineral_group) rows and 11 `Aspectral` rows are all flagged
  `is_explicit_state=True` and survive into the table (not dropped, not zeroed).
- **D3 TSAV ignored — PASS.** `read._discover_suffix` drops any suffix containing
  `tsav` (`_IGNORE_SUFFIX_TOKENS=("tsav",)`); `test_discover_suffix_prefers_system_and_ignores_tsav`
  asserts this. On ETG0187 the resolved suffixes are `sTSAS` (SWIR) / `sjCLST`
  (TIR), never a TSAV variant.
- **D4 Level-1 uses Mineral Group, not individual minerals — PASS (as designed).**
  The tidy table carries both `mineral_group` (`Grp1`) and `mineral` (`Min1`);
  `qc.py` docstring states Group is preferred for Level 1 "downstream". No
  Level-1 consumer exists yet (domaining is Day 2), so the column is present and
  the intent is recorded; full use is UNVERIFIED until T2.4.
- **D5 Wt1 = 1.0 not filtered; `error` used as confidence — PASS.** No code
  filters `abundance == 1.0`; on ETG0187 1452 rows have `abundance == 1.0` and
  are retained. `error` is carried as its own column, sentinel-nulled (range
  7.34–1972.77 on ETG0187), 3469 non-null.
- **D6 SWIR/TIR never pooled into one composition; zeros documented — PASS (so
  far).** `read.read_hole` keeps `view ∈ {swir,tir}` as an explicit row
  dimension and `pd.concat`s the two views as separate rows, never summing them
  into one vector. The planned fusion (`fusion.py` docstring) is explicitly
  *per-view* CLR → per-view PCA → concat of scores, i.e. not a single pooled
  composition. The zero/not-detectable handling is documented as intent only;
  the CLR/zero-handling code does not exist yet (T2.3), so the "zeros = not
  detectable here" rule is UNVERIFIED in code.

### E. Assays
- **E1 Units normalised; ×1000 / implausible values flagged — UNVERIFIED.** No
  assay-ingestion or unit-normalisation code exists at R1 (grep for assay code
  finds only `coverage.py` counting the `Assay_data` flag and docstrings). The
  raw DASC table `wamex_assay_flat_data` has 105 columns with units in the
  suffix (16 `_PCT`, 83 `_PPM`, 0 `_PPB`), which de-risks this, but note
  `Au_PPM` ranges to 421300 ppm (~42% Au) — an implausible value the future QC
  must catch. No check runs yet.
- **E2 Below-detection handling documented — UNVERIFIED (and flag for E).** No
  handling exists yet. Independent check of the raw data shows the below-
  detection convention is **negative values**: 49,541 of 236,719 non-null
  `Au_PPM` rows are < 0 (distinct values include −0.5, −1, −5, −5000, meaning
  "below |x|"). This is a real trap that must be handled before any assay
  compositing or regression (T2.2); currently a naive mean would be corrupted.
- **E3 Overlap-weighted compositing with a test — UNVERIFIED.** The depth-window
  interval-overlap join is T2.1 (next task per `STATUS.md`); `sql/README.sql` is
  a placeholder (`SELECT 42`), the `composite_join.sql` named in docstrings does
  not exist, and there is no compositing test.
- **E4 Assay targets chosen before results; selection bias stated — PARTIAL /
  UNVERIFIED.** `config/params.yaml` has `assay_targets: []` (empty, "decide from
  data") committed at the first commit `a55a57e`, before any results file, so
  pre-registration is intact *so far*. The selection bias is stated in
  `reports/coverage.md` ("Assay coverage is selection-biased (companies sample
  prospective intervals)"). But targets are not yet chosen, and the README that
  should carry the stated bias is empty — so the final selection + its bias
  statement are UNVERIFIED at R1.

### I. Reproducibility and rules
- **I1 Clean clone → sync → fetch → evaluate reproduces tables — FAIL (as a
  reproducibility claim).** Two gaps: (a) `make fetch` refuses the 15-hole
  `config/holes.yaml` because `fetch.py` defaults to `--max-holes 5` ("refusing:
  15 holes > --max-holes=5"), so a clean clone fetches nothing without a manual
  override; (b) `make evaluate` runs `hyfuse.evaluate`, which is a docstring-only
  stub (no `main`, no entry point) and produces no `reports/ablation.md`. No
  result tables exist to reproduce yet (only `coverage.md`, which needs the DASC
  sqlite that is correctly git-ignored). This is expected at R1 but must not be
  claimed as reproducing until Day 2+; flagging now because the fetch guard will
  silently block the documented path.
- **I2 Seeds fixed; versions locked — PARTIAL.** Versions: PASS — `uv.lock` is
  tracked and `pyproject.toml` pins floors for all deps. Seeds: `seed: 42` is in
  `params.yaml` but is not consumed anywhere in `src/` or `tests/` (no
  `random_state`/`np.random` wiring); acceptable at R1 since no stochastic step
  (HDBSCAN/PCA/CV) is implemented yet, but the seed is currently inert.
- **I3 No data in git — PASS.** `git ls-files | grep -Ei '\.(bip|tsg|parquet|zip|duckdb|sqlite|...)'`
  returns nothing. A full-history check (`git log --all --diff-filter=A`) also
  finds zero data files ever added. `.gitignore` covers `data/`, `cache/`,
  `logs/`, and every binary data extension; `reports/` is intentionally not
  ignored (small outputs only).
- **I4 README names packages + data download; latest commit on default branch —
  FAIL (README) / PARTIAL (branch).** `README.md` is 0 bytes, so it names no
  packages and no data-download location — the item cannot pass. Default branch
  is `main` and the latest commit `1f36dca` is on it (HEAD = `main`), but there
  is **no git remote configured** (`git remote -v` empty), so "on the default
  branch" cannot be confirmed against a published repo yet.

## Findings

### F1 [major] `make fetch` guard refuses the pinned 15-hole list
- Where: `src/hyfuse/fetch.py` (`--max-holes` default `5`); `config/holes.yaml`
  (15 holes).
- Evidence: `uv run python -m hyfuse.fetch` →
  `ERROR refusing: 15 holes > --max-holes=5 (raise it deliberately)`. The
  Makefile `fetch` target passes no `--max-holes`, so the documented
  `make fetch` path downloads nothing.
- Why it matters: the stated reproduction recipe (`make fetch && make evaluate`)
  stops at the first step on a clean clone.
- Suggested fix: set the Makefile `fetch` target (or the default) to the number
  of holes actually pinned, or document the required `--max-holes` override in
  the README.

### F2 [major] README is empty — reproducibility/package/data rules absent
- Where: `README.md` (0 bytes, `wc -c README.md` → 0).
- Evidence: file size 0; `git ls-files` lists it but it has no content.
- Why it matters: item I4 and the stated-selection-bias half of E4 depend on the
  README; none of the "packages used / where to download data / default branch /
  assay selection bias" statements exist yet.
- Suggested fix: write the README before submission with: dependency list (or
  point to `pyproject.toml`/`uv.lock`), data-download instructions (THREDDS +
  DASC package), default branch, and the assay selection-bias caveat.

### F3 [major, forward-looking] Assay below-detection encoded as negatives
- Where: raw `wamex_assay_flat_data` (DASC); no handling code yet (T2.2).
- Evidence: 49,541 of 236,719 non-null `Au_PPM` values are < 0 (e.g. −0.5, −1,
  −5, −5000), the "below |detection limit|" convention; `Au_PPM` also reaches
  421300 ppm (~42%), implausible.
- Why it matters: a naive composite/mean over these columns is corrupted and
  would silently poison any assay-target regression (item E).
- Suggested fix: in T2.2, convert negatives to below-detection (e.g. |x|/2 or an
  explicit censored flag), add a plausibility range per element, and add the
  overlap-weighted compositing test the checklist requires.

### F4 [minor] `seed: 42` is declared but unused
- Where: `config/params.yaml` (`seed: 42`); no reader in `src/`.
- Evidence: `grep -rn "seed|random_state|np.random|RandomState" src/ tests/` →
  no matches.
- Why it matters: determinism is not actually wired; the pre-registered seed is
  inert until the stochastic steps are built.
- Suggested fix: thread `params.seed` into HDBSCAN/PCA/GroupKFold/bootstrap when
  those land (T2.4/T3.3) and assert it in a test.

## What I could not verify

- Assay unit normalisation, below-detection handling, overlap-weighted
  compositing, and target selection (E1–E4) — the code does not exist at R1
  (T2.1/T2.2, Day 2). Verified only the raw-data traps they must handle.
- CLR zero-handling / "zeros = not detectable" documentation in code (D6) —
  compositional transform is T2.3; only the per-view separation is in place.
- Level-1 Mineral-Group *use* (D4) — the column exists; no consumer yet (T2.4).
- End-to-end reproduction of any result table (I1) — no result tables exist yet;
  `evaluate.py`/`fusion.py`/`domains.py`/`synth.py` are docstring-only stubs.
- "Latest commit on the published default branch" (I4) — no git remote is
  configured, so this is only confirmable locally (`main` = HEAD).
- Final Mask on/off *direction* is inferred from row-count alignment with empty
  mineral results, not from a core photo; `data_notes.md` itself flags this as a
  still-open visual VERIFY.

## Questions for a human expert

- Confirm the Final Mask direction (1 = keep) by eyeballing one hole's mask
  against the core photo, as `data_notes.md` notes is still outstanding.
- Confirm the GSWA below-detection convention for `wamex_assay_flat_data` (is a
  negative value always "below |x|"?) and the preferred imputation before T2.2
  compositing.
- Confirm the Au_PPM outliers (up to ~42%) are real high-grade intervals vs
  unit/entry errors, so the T2.2 plausibility filter is calibrated correctly.
- Confirm that per-view CLR→PCA→concat (never a single pooled SWIR+TIR
  composition) is the intended fusion, matching the GSWA "never pool" rule.
