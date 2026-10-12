# Review of HyFuse — 2026-10-13, commit e9eafa0

Reviewer: independent (fresh-context, read-only). Scope: **R2 end-of-Day-2
checkpoint, items A, B, C, D, E, F only.** Items G–J are out of scope for this
pass. Per the prompt, the four-arm fusion (`fusion.py`), the `evaluate.py` result
TABLES, `synth.py`, and `reports/confounders.md` are Day-3 (T3.x) deliverables and
are expected UNVERIFIED at R2; the scoring / confounder / boundary ENGINES exist
and are unit-tested now, and are reviewed here.

All findings carry an executed command or a file:line. Nothing was edited except
this file. Cached data only: `data/raw/holes/ETG0187` (TSG) and
`data/raw/dasc/HyLogger_Dataset_Package.sqlite`. No bulk fetch was run.

## Verdict

**Go with fixes (none blocking at R2).** For the scope reviewed, the pre-registration
is intact, the data-handling and assay-hygiene rules are correctly implemented and
verified on real cached data, and the boundary / confounder / corruption engines are
present with negative controls that collapse to chance. One **minor** leakage pattern
exists in the confounder classifier (scaler fit before the CV split); it is
conservative for its purpose (a negative control) but should be moved inside the CV
pipeline before the T3.3 ablation reuses it. The headline fusion result does not exist
yet, so no results-level claim can pass or fail at R2.

56/56 tests pass:
`uv run pytest -q` → `56 passed in 3.70s`.

## Checklist results

- **A1 (grouped CV)** PASS — `cv.scheme: GroupKFold`, `group_by: hole_id` in
  `config/params.yaml`; `evaluate.confounder_classifier_auc` uses
  `GroupKFold(groups=hole)`. No `train_test_split`/`KFold`/window-level random
  split anywhere in `src/` (grep below).
- **A2 (fit on train folds only)** PASS **with one minor exception (F1)** — the
  only supervised CV path (`confounder_classifier_auc`) puts `LogisticRegression`
  inside `cross_val_score`, but calls `StandardScaler().fit_transform(x)` on the
  full matrix *before* the split (`evaluate.py:180`). See F1.
- **A3 (no test-hole info in features / no global PCA before split)** PASS at R2 —
  CLR features (`features.clr_features`) are computed per window independently;
  `domains._pca_scores` fits PCA/scaler per hole for *unsupervised* down-hole
  domaining (no train/test split inside a hole), so there is no cross-hole leakage
  in the R2 engines. The cross-hole predictive ablation (T3.3) does not exist yet.
- **A4 (no tuning on eval folds)** PASS — no hyperparameter search exists; domain
  params (`seg_penalty`, `min_cluster_size`, PCA `n_components`) are fixed defaults
  / params, not tuned against a score.
- **B1 (pre-registration)** PASS — boundary tolerance/metric/permutation frozen in
  commit `96c0454` (00:41:39), 5 min *before* the scoring code `e6f0786`
  (00:46:28); CV scheme + bootstrap unit + success criterion present since the
  scaffold `a55a57e`; `assay_targets: [Au_PPM]` set at `c8de80e` (T2.2). **No
  results/ablation file exists in the tree at all**, so nothing could precede the
  freeze. `depth_tolerance_m` has always been `2.0` (only the comment changed).
- **C1 (confounder test, grouped)** PASS (engine) — `confounder_report` runs MI vs
  shuffle + GroupKFold-by-hole classifier vs majority rate; flags when accuracy
  exceeds majority by >0.10 or MI exceeds shuffle p95. Unit-tested
  (`tests/test_confounders.py`, 6 tests).
- **C2 (all four arms on identical windows/holes)** UNVERIFIED — the four-arm
  fusion and the ablation that scores arms on a shared window/hole set are T3.x;
  `fusion.py` is a docstring-only stub (no symbols). Cannot be checked at R2.
- **C3 (alternative explanations addressed)** UNVERIFIED — depends on
  `reports/confounders.md` (T3.3), not yet produced.
- **D1 (Final Mask applied, non-core excluded)** PASS — verified on ETG0187:
  mask kept=3488 / dropped=2182; `qc.apply_final_mask` filters `final_mask==1`;
  mask is stored as a column, not pre-filtered.
- **D2 (invalid/aspectral kept explicit)** PASS — `read.EXPLICIT_STATES` keeps
  them; `is_explicit_state` column present; `aspectral` observed in real ETG0187.
- **D3 (TSAV ignored; Mineral Group for Level 1)** PASS — `read._IGNORE_SUFFIX_TOKENS
  = ("tsav",)`; real ETG0187 resolved to `sTSAS`(SWIR)/`sjCLST`(TIR), no TSAV;
  features use `mineral_group` (Grp1), not individual mineral.
- **D4 (Wt1=1.0 kept; error used as confidence)** PASS — 1452 rows with
  `abundance==1.0` retained; `error` column 61% non-null, carried as confidence.
- **D5 (SWIR/TIR never pooled; zeros = not-detectable, documented)** PASS —
  `features.clr_features` runs per view, view-prefixed columns (`swir_`/`tir_`);
  zero handling documented in `params.clr` (multiplicative replacement, delta=1e-6).
- **E1 (units normalised; x1000 / implausible flagged)** PASS — units are explicit
  column suffixes (`_PPM`/`_PCT`/`_PPB`); `qc.flag_implausible` + `assay_unit_sanity`
  flag out-of-range; real DASC `Au_PPM` max = 421300 ppm (~42%) and 12 rows
  >100000 ppm are catchable by the Au cap [0,100000].
- **E2 (below-detection documented)** PASS — negatives = censored, impute |x|/2 +
  `below_detection` flag (`qc.resolve_below_detection`); real data has
  49541/236719 negative Au_PPM rows, min −5000 — matches the params note exactly.
- **E3 (overlap-weighted compositing + test)** PASS — `composite.overlap_weight_assays`
  weights by overlap length; exact straddling test asserts 80/6 vs blind-mean 15
  (`tests/test_composite.py::test_overlap_weighted_assay_exact`).
- **E4 (target chosen before results; selection bias stated)** PASS — `Au_PPM`
  fixed at T2.2 before any results; selection bias stated in committed
  `reports/coverage.md:60` ("companies sample prospective intervals") and
  `coverage.py:147`. Full README statement is T4.2 (out of R2 scope).
- **F1 (permutation baseline present + reported)** PASS (engine) —
  `evaluate.permutation_baseline` / `boundary_agreement_vs_baseline` return the
  baseline F1 distribution + one-sided p next to the observed F1; frozen in params
  (`n: 1000`, `same_count_per_hole`).
- **F2 (negative controls collapse to chance)** PASS — ran the tests:
  `test_good_detection_beats_permutation_pvalue_low` (perfect → p<0.05),
  `test_random_detection_pvalue_not_significant` (random → p>0.05),
  corruption controls (x1e6 → frac_implausible↑, +10 m depth → F1 1.0→0.0,
  mask-ignored → rows/metres change, shuffled ids → join collapses). All pass.
- **F3 (naive-concat arm exists)** UNVERIFIED (as expected) — named in `fusion.py`
  docstring (arm 3, "Naive concatenation (straw man)") but not implemented; the
  arm is T3.2.

## Findings

### F1 [minor] Scaler fit outside the CV split in the confounder classifier
- Where: `src/hyfuse/evaluate.py:180` (`confounder_classifier_auc`).
- Evidence:
  ```
  $ grep -rnE 'fit_transform|\.fit\(|cross_val|GroupKFold' src/hyfuse/evaluate.py
  180:    xs = StandardScaler().fit_transform(x)
  184:        scores = cross_val_score(clf, xs, y, groups=g,
  185:                                 cv=GroupKFold(n_splits=n_splits), ...)
  ```
  The `StandardScaler` is fit on the entire feature matrix (including the held-out
  fold rows) before `cross_val_score` draws the GroupKFold splits. The classifier
  itself is correctly inside the CV, and grouping is by hole.
- Why it matters: it is a textbook leakage pattern (A2). Here the function is a
  *negative control* that we want to collapse to chance, and scaler leakage can only
  make the confounder look *more* predictable, so it biases toward flagging a
  confounder (conservative, safe) rather than toward a false pass. But if the T3.3
  ablation reuses this helper for a claim we want to be *high*, the same pattern would
  inflate it.
- Suggested fix: wrap scaler + classifier in a `sklearn.pipeline.Pipeline` and pass
  that to `cross_val_score`, so the scaler is fit per training fold.

### F2 [minor] Confounder confounders are near-constant in the single cached hole
- Where: data availability, not code. `data/derived/holes/ETG0187.parquet`.
- Evidence:
  ```
  instrument_gen values: ['unknown']
  processing_level unique within a view: swir=1 (sTSAS), tir=1 (sjCLST)
  ```
  `instrument_gen` is a constructor argument defaulting to `"unknown"` and is never
  populated from the package in `features.build_hole`; `processing_level` is
  constant within a view for a hole.
- Why it matters: the confounder check (C1) can only do real work across holes with
  *varying* processing level / instrument generation. With one cached hole both are
  degenerate, so the engine is tested only on synthetic planted data. This is
  expected at R2 (one hole fetched), but the T3.3 confounder report must draw on
  holes that actually differ, or the control is vacuous.
- Suggested fix: populate `instrument_gen` from the index at build time, and in T3.3
  confirm the fetched shortlist spans ≥2 processing levels / instrument generations.

## What I could not verify (expected UNVERIFIED at R2)

- C2/C3: four arms scored on identical windows/holes, and the written
  alternative-explanations list — depend on `fusion.py` (stub) and
  `reports/confounders.md` (not produced). Both T3.x.
- F3: the naive-concat arm as runnable code — docstring only in `fusion.py`.
- Any headline "fusion beats best single view" claim — no results/ablation file
  exists in the tree (`git ls-files | grep -i ablation` → none). Nothing to score.
- Multi-hole leakage behaviour of the full ablation (A3 at the cross-hole level) —
  the cross-hole predictive pipeline is T3.3 and not present.
- Geology plausibility (whether detected boundaries are real) — out of scope and
  requires a GSWA expert (SKILL section J).

## Questions for a human expert (carry into Day 3 / T3.x)

1. Below-detection convention: confirm with GSWA that a negative assay value
   encodes "< |value|" and that imputing |x|/2 is acceptable (currently an
   ASSUMPTION in `params.assay_hygiene`).
2. Au_PPM = 421300 (~42%) and the 12 values >100000 ppm: real high-grade intercepts,
   or unit/entry errors? The pipeline flags, does not drop — confirm that is correct.
3. SWIR-active mineral set in `params.swir_active_minerals` (for the T3.1 planted
   truth) against the GSWA SKOS vocabulary; confirm chlorite as the SWIR/TIR bridge.
4. Processing suffix preference (sTSAS/sjCLST, ignore TSAV) — confirm the
   system-constrained variant is the right choice per view.

## Reproduction commands (for the author to re-run)

```
git -C ~/opt/hackathon/gswa/hyfuse rev-parse HEAD        # e9eafa0...
uv run pytest -q                                          # 56 passed
git log -p -- config/params.yaml | grep -nE 'depth_tolerance_m'   # always 2.0
git show -s --format='%ci' 96c0454 e6f0786                # freeze precedes scoring
git ls-files | grep -Ei '\.(bip|tsg|parquet|duckdb|sqlite|zip)$'  # none tracked
# D/E spot-checks: read ETG0187.parquet (mask 3488/2182, aspectral, sTSAS/sjCLST,
#   no TSAV, Wt1=1.0 kept) and DASC sqlite (Au_PPM: 236719 nonnull, 49541 neg,
#   min -5000, max 421300, 12 rows >100000).
```
