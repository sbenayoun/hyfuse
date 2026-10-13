# Review of HyFuse — 2026-10-13, commit 44cb119

Scope: ALL items A–J (Day-3 checkpoint R3), on the honest result on `main`.
Reviewer: independent, read the repo as a stranger. No code, params, or result
files were edited; this file is the only output. Evidence was gathered by
running the project's own code and tests against the cached data
(`data/raw/holes/*`, `data/raw/dasc/*`); no data was fetched.

## Verdict

**Go with fixes.** The headline is honest and reproduces exactly: fusion does
**not** beat the best single view on boundary recovery (fused F1 0.140 vs
tir_only 0.139; hole-level bootstrap delta +0.001, 95% CI [-0.017, +0.022]
includes zero) and **no** arm predicts Au on held-out holes (all median
R² ≤ 0). Pre-registration, grouped-by-hole CV, the permutation baseline, the
confounder controls, assay hygiene, and the no-data-in-git rule all check out
with executed evidence. The only blocker to *submission* is documentary, not
scientific: the `README.md` is still the Day-1 stub, so the claims-vs-evidence
and reproducibility narrative (items H, I) are not yet written. One statistical
caveat must be stated prominently: n = 15 holes, 13 of them one deposit
(Bannockburn), so even a positive result could not have claimed generality.

## Checklist results

- **A1 PASS** — Grouped CV everywhere a split exists. `assay_prediction_cv` and
  `confounder_classifier_auc` both use `GroupKFold(group_by=hole_id)`
  (`src/hyfuse/evaluate.py:210,186`). No `train_test_split` / bare `KFold` in
  `src/`. Static guard test enforces this (`tests/test_guards.py::
  test_assay_cv_uses_groupkfold_in_source`). Behavioural guard: target = pure
  hole level → grouped R² ≤ 0 (`test_assay_cv_is_grouped_by_hole_not_leaky`).
- **A2 PASS** — Fitted steps are inside CV pipelines. `StandardScaler`+`Ridge`
  and `StandardScaler`+`LogisticRegression` are `sklearn.Pipeline`s passed to
  `cross_val_score`, so they fit per training fold only
  (`evaluate.py:204-210, 258-266`). The R2 F1 finding (scaler fit before split)
  was fixed and is now the documented pattern.
- **A3 PASS** — Domaining (PCA→HDBSCAN→ruptures) runs **per hole, per arm**
  inside the hole loop (`ablation.py` `_per_hole_features` + the `for hole`
  loop); features are composited per hole (`data_access.composited_views`).
  There is no global normalisation or global PCA across holes before scoring.
  The per-hole PCA scaler is descriptive segmentation of a single hole, not a
  train/test estimator, so it cannot leak test-hole info.
- **A4 PASS (by design)** — No hyperparameter tuning on eval folds: ridge
  `alpha=100`, HDBSCAN `min_cluster_size`, ruptures penalty are fixed
  constants, explicitly "reported, not tuned to a target"
  (`evaluate.py:252-257`). Nothing selects them against the CV score.
- **B PASS** — `git log --diff-filter=A config/params.yaml` → first commit
  2026-10-12 21:53 (scaffold); tolerance/metric/splits frozen in commit
  `96c0454` "T2.5 PRE-REGISTER" at 2026-10-13 00:41. First results file
  (`reports/ablation.md`) added 2026-10-13 15:41 — ~15 h later. `params.yaml`
  has **not** been touched since the pre-registration commit. `depth_tolerance_m`
  and `boundary_scoring.tolerance_m` are **2.0** both at pre-reg and now
  (`grep tolerance config/params.yaml`). No post-hoc change.
- **C1 PASS** — Confounder tested grouped-by-hole. `tir_processing_level`
  genuinely varies (verified: sjCLST ×13, sTSAT ×2 across the 15 holes) and is
  **not flagged** in any arm (max cv_accuracy 0.740 < majority 0.748, i.e. below
  chance). `instrument_gen` is constant (all HL3+, verified) and correctly
  reported as "constant — not testable", not as a pass
  (`reports/confounders.md`, `ablation.py` constant-handling block).
- **C2 PASS** — All four arms scored on the identical window/hole set:
  `all_arms` inner-joins SWIR and TIR on the window index before building any
  arm (`fusion.py::align`, `all_arms`). Reproduced: all 4 arms, 15 holes.
- **C3 PASS (addressed, read as limitation)** — Alternative explanations
  (processing level, instrument gen, single-deposit dominance, assay selection
  bias) are listed in `ablation.md`/`confounders.md`. Weathering/regolith
  profile is **not** yet explicitly tested → see Questions for a human expert.
- **D1 PASS** — Final Mask applied (`qc.apply_final_mask`, keep==1);
  `composite_minerals` composites only `final_mask == 1` rows.
- **D2 PASS** — `invalid`/`aspectral`-type states kept as explicit rows through
  masking; only true non-mineral groups `{"", INVALID, NOTAROK}` are excluded
  from the *composition* (`features._NON_COMPOSITION_GROUPS`), documented as
  "kept elsewhere as flags".
- **D3 PASS** — Level-1 handling uses Mineral Group not individual mineral
  (composition is built on `mineral_group`); TSAV not used as a result.
  (UNVERIFIED detail: that no TSAV column leaks in via `read.py` on every hole —
  not exhaustively traced; the composition path only reads `mineral_group`.)
- **D4 PASS** — Wt1==1.0 explicitly kept (`qc` docstring rule); `error` is the
  documented confidence measure.
- **D5 PASS** — SWIR and TIR never pooled: per-view transform then concatenate;
  columns view-prefixed so same-name groups don't collide
  (`fusion.arm_fused`, `features.view_features`). Zeros treated as structural
  "not detectable" (`composition_matrix` fill_value=0 + Hellinger/CLR handling),
  documented in `params.yaml`.
- **E1 PASS** — Implausible Au flagged, not dropped. Verified on real DASC data:
  236,719 Au_PPM rows, max 421,300 ppm (~42%), 12 rows above the 100,000-ppm
  cap → flagged. `qc.flag_implausible` + plausibility range in `params.yaml`.
- **E2 PASS** — Below-detection handled and documented: negatives mean
  "below |x|", imputed |x|/2 with a `below_detection` flag
  (`qc.resolve_below_detection`). Verified: 49,541/236,719 Au rows are negative,
  min −5000 — exactly the convention the code assumes.
- **E3 PASS** — Compositing to windows is overlap-length weighted
  (`composite.overlap_weight_assays`: `value*overlap / sum(overlap)`); test
  exists (`tests/test_composite.py`).
- **E4 PASS** — Au chosen before results (pre-reg B) and the selection bias
  ("companies sample prospective intervals") is stated in `ablation.md` caveats
  and `params.yaml`. (README statement pending — see H/I.)
- **F1 PASS** — Permutation baseline exists and is reported next to the result:
  per-hole `permutation p` column in `ablation.md`; `permutation_baseline` /
  `boundary_agreement_vs_baseline` in `evaluate.py`; test in `test_boundary.py`.
- **F2 PASS** — Negative controls collapse to chance. Ran the confounder
  detector on random features: cv_accuracy 0.867 == majority 0.867, not flagged;
  with planted signal: 0.993 > majority, flagged. Grouped-CV guard: target =
  hole identity → R² ≤ 0 (test passes). Shuffled-hole-id join collapses
  (`test_corruption.py`). Two+ controls run, all collapse as required.
- **F3 PASS** — Naive `concat` arm exists and is scored alongside fused
  (`fusion.arm_concat`); "fusion helps" is compared to it, not only to single
  views.
- **G1 PASS** — Uncertainty bootstraps **holes**, not windows
  (`bootstrap_hole_delta` resamples the per-hole delta array; `params.bootstrap.
  unit: hole`).
- **G2 PASS (and flagged)** — n stated: 15 holes in every comparison; all 15
  contribute Au windows (verified). This is just above the skill's ~8-hole
  floor, but 13/15 are one deposit (Bannockburn BBDD/BBRD per `holes.yaml`), so
  the report's INCONCLUSIVE verdict and "not general" caveat are appropriate.
- **G3 PASS** — Comparison count is small and the headline is not cherry-picked:
  4 arms × 2 metrics = 8 scores, 1 target; the single headline comparison is
  fused vs best-single via one pre-registered bootstrap. No "best of many" claim.
- **G4 PASS** — Difference is read against spread, not a point estimate: the
  bootstrap CI [-0.017, +0.022] is reported and used to call it inconclusive.
- **H1 PARTIAL / UNVERIFIED** — Every quantitative sentence in **ablation.md /
  confounders.md** traces to the generated run (reproduced bit-for-bit, below).
  But `README.md` is still the Day-1 stub ("Status: work in progress … full
  version written at task T4.2"); the final claims table is not yet in the
  README, so H cannot be fully passed until T4.2. Not a scientific defect.
- **H2 PASS** — Language in the reports is bounded and honest: "INCONCLUSIVE",
  "no reliable difference", "no skill", "not general"; no mineralisation claim.
- **H3 PASS** — The negative/inconclusive result is the headline, stated as
  plainly as any positive would be.
- **I1 UNVERIFIED (not a defect for R3)** — Did not run a clean clone →
  `make fetch` → `make evaluate` end to end (fetch is a multi-GB download and
  the instruction is cached-data-only). Verified the next best thing: `make
  evaluate`'s code path reproduces the committed tables exactly from cached data
  (below). Makefile targets exist and are coherent.
- **I2 PASS** — Seeds fixed (`params.seed: 42`, threaded into PCA/HDBSCAN/
  KMeans/ridge/logreg/bootstrap/permutation); versions locked (`uv.lock`).
- **I3 PASS** — No data in git: `git ls-files | grep -Ei
  '\.(bip|tsg|parquet|zip|duckdb|sqlite|...)$'` returns nothing; `.gitignore`
  covers `data/ cache/ *.parquet *.sqlite` etc. Only small `reports/*.md`
  tracked under reports/.
- **I4 PARTIAL** — Packages and data sources are named in README. Latest commit
  44cb119 is on `main` (default). Remaining README content (team, results,
  licence, AI-tools disclosure, limitations) deferred to T4.2.
- **J PASS (evidence produced; verdict handed to a human)** — Candidate
  intervals listed below for a geologist to eyeball. Regolith/weathering
  coincidence is explicitly left as an open question.

## Reproduced result (executed)

`uv run python -c "from hyfuse.ablation import run_ablation; run_ablation(write=False)"`
(cached data, seed 42) reproduced the committed `reports/ablation.md` exactly:

| arm | mean boundary F1 | assay Au R² (median) |
|---|---:|---:|
| swir_only | 0.102 | −1.7 |
| tir_only | 0.139 | −1.6 |
| concat | 0.129 | −6.0 |
| fused | 0.140 | −6.5 |

Fused − best single (tir_only): **+0.001**, 95% CI **[-0.017, +0.022]**, n=15,
excludes zero = **False**. `uv run pytest -q` → **73 passed**.
`uv run ruff check .` → all checks passed.

## Findings

### F1 [major] README is still the Day-1 stub; final claims/limitations not written
- Where: `README.md` (whole file), `reports/review.md` items H1, I1, I4.
- Evidence: README header says "Status: work in progress (Day 1 complete)…
  full version … written at task T4.2". No results table, no limitations, no
  AI-tools disclosure, no selection-bias statement in the README itself.
- Why it matters: a judge/geologist reads the README first; the honest
  INCONCLUSIVE finding, the 13/15-single-deposit caveat, and the assay
  selection bias must be visible there, not only in `reports/`.
- Suggested fix: complete T4.2 — paste the reproduced table, state n=15 (one
  deposit), the no-Au-skill result, and the selection bias, with links to
  `reports/ablation.md` and `confounders.md`.

### F2 [minor] End-to-end `make fetch && make evaluate` from a clean clone not demonstrated
- Where: reproducibility item I1; `Makefile` `fetch`/`evaluate`.
- Evidence: fetch is a multi-GB NCI download (cache/zips here total tens of GB)
  and was intentionally not run (cached-data-only review). Only the
  `make evaluate` code path was reproduced, from cached parquet.
- Why it matters: the README promises a clean-clone reproduce; it is unproven.
- Suggested fix: either run it once on a fresh checkout and record the log, or
  state precisely in the README that `make fetch` needs ~N GB and name the
  cached-data fallback.

### F3 [minor] Single-deposit dominance deserves a louder caveat than "mostly one deposit"
- Where: `reports/ablation.md` caveats; `config/holes.yaml`.
- Evidence: 11 of 15 holes are Bannockburn BBDD/BBRD (verified in holes.yaml);
  only 3 are regional. Leave-holes-out CV across near-identical holes is a weak
  generality test.
- Why it matters: even the no-skill Au result and the inconclusive fusion result
  are conditioned on essentially one geological setting.
- Suggested fix: state "effectively 1 deposit + 3 regional holes" explicitly in
  the README limitations.

## What I could not verify

- **I1**: clean-clone `make fetch` → `make evaluate` end to end (download size;
  cached-data-only instruction). Mitigated by reproducing `make evaluate` from
  cache.
- **D3 (partial)**: that no TSAV / individual-mineral result leaks into the
  composition on every hole via `read.py` — the composition path reads only
  `mineral_group`, but `read.py` ingestion was not exhaustively audited per hole.
- **Geology itself**: whether the detected boundaries and domains are
  geologically meaningful. Out of scope for a software/stats review (per skill).

## Questions for a human expert (item J)

Candidate intervals to eyeball (hole, logged-boundary count, detected count,
fused F1, permutation p from `reports/ablation.md`). For each, pull the core
photo and logged unit at the detected boundary depths:

1. **BCMH0070** — logged 33, detected 4, F1 **0.216**, p 0.332. A relatively
   "good" case: do the 4 detected domain boundaries land on real lithological
   contacts, or on a weathering/regolith transition near the top of hole?
2. **BBDD0005** — logged 14, detected 3, F1 **0.235** (highest), p 0.553.
   High p means random boundaries do about as well — are these boundaries
   geologically real or coincidental at 5 m resolution?
3. **BBRD0056** — logged 12, detected **0**, F1 **0.000**, p 1.000. A clear
   miss: why did segmentation find no domains? (RC hole — is the spectral
   signal degraded vs diamond core?)
4. **16CADD001** — logged 88, detected 8, F1 0.104, p 0.421. Very fine company
   logging vs coarse 5 m windows: is the 5 m window simply too coarse to recover
   this hole's boundaries?
5. **General**: do detected boundaries systematically coincide with the
   regolith/fresh-rock transition? If so, "geological domains" is partly a
   weathering signal and the README should say so. This is the main untested
   alternative explanation (checklist C3).

Also for the geologist: confirm (a) the SWIR below-detection = negative-value
convention and the |x|/2 imputation are appropriate for these assays, and
(b) that `tir_processing_level` (sjCLST vs sTSAT) truly carries no geological
information that the "not flagged" confounder test might be under-powered to see
at n=15.
