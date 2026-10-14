# Review of HyFuse — 2026-10-14, commit 63181da

Independent pre-submission review **R5**, scope **ALL items A–J**, with special
focus on the newly-added window-size sensitivity analysis (B, F, H) and
re-confirmation of the R4-resolved items. Reviewer worked read-only from a fresh
context; every finding below carries an executed command or a file:line. Cached
data only (`data/raw/*`, `data/derived/*`); no bulk fetch.

Commit under review:
```
63181da window-size sensitivity (geologist feedback): headline stays pre-reg 5m;
         1m fusion helps but NOT robust across resolutions; add
         reports/sensitivity.md, README note, declared sweep in params
```
HEAD == `origin/main`, branch `main`, working tree clean (`git status`).

## Verdict

**Go for submission.** No blockers, no open majors. The window-size sensitivity
addition is implemented and reported honestly: the pre-registered 5 m headline is
unchanged and frozen before results; the 1 m "fusion helps" result is presented
explicitly as a non-robust declared sensitivity, not as the headline; the
permutation baseline still controls at each window; and every quantitative claim
in README/sensitivity.md reproduces bit-for-bit from the generated code on cached
data. All R4-resolved items (grouped CV, no data in git, reproducibility, honest
single-deposit limitation) still hold. The remaining items are accepted
limitations already disclosed in the README (single deposit, assay selection
bias, no geological validation).

## Checklist results

- **A1 PASS** — Only grouped CV in the code: `evaluate.py:211,279` use
  `GroupKFold(... groups=g)` by `hole_id`. `grep -rn "KFold(" src/hyfuse/` returns
  only the two GroupKFold sites; no window-level random split anywhere.
- **A2 PASS** — Fitted steps are inside the CV pipeline, fit per training fold:
  `assay_prediction_cv` uses `Pipeline([StandardScaler, Ridge(alpha=100)])` passed
  to `cross_val_score` (`evaluate.py:270-279`); confounder classifier likewise
  (`evaluate.py:205-211`). No `fit`/`fit_transform` on the full matrix before the
  split.
- **A3 PASS** — Per-hole features built independently per hole
  (`_per_hole_features`, `ablation.py:38`); no global normalisation/PCA across all
  holes before CV.
- **A4 PASS** — Ridge `alpha=100` and `seg_penalty=1.0` are fixed in code/params,
  not tuned on evaluation folds (`evaluate.py:272` comment states "reported, not
  tuned to a target").
- **B1 PASS (headline frozen before results, unchanged)** —
  `git log --reverse -- config/params.yaml`: freeze commit **96c0454**
  (2026-10-13 00:41) predates the first results file **4f2c1c5**
  (`reports/ablation.md`, 2026-10-13 15:41). `git diff 96c0454 63181da --
  config/params.yaml` shows the ONLY non-comment change since the freeze is the
  added `window_sensitivity_m: [5.0, 1.0, 0.5]`. `window_size_m: 5.0`,
  `depth_tolerance_m: 2.0`, `boundary_metric: f1`, `cv.scheme: GroupKFold`,
  `bootstrap.unit: hole`, `assay_targets: [Au_PPM]`, and the success criterion are
  **byte-identical** at freeze and HEAD. The sweep is a declared addition, not a
  post-hoc headline change. See Finding N1 (positive).
- **C1 PASS** — Confounder test present and grouped by hole;
  `reports/confounders.md`: `tir_processing_level` not flagged for any arm (cv_acc
  0.50–0.74 vs majority 0.748); `instrument_gen` reported as constant (HL3+) "not
  testable", not falsely passed. The code only flags confounders that actually
  vary (`ablation.py` + `evaluate.py:confounder_report`).
- **C2 PASS** — All four arms built from an inner join on the identical window
  index (`fusion.py:34,90` "identical windows", item C2); scored on the same
  per-hole windows. `min_iw = round(min_interval_m / win)` and `seg_pen` are the
  same for every arm (`ablation.py:64-65`), so no arm gets a segmentation edge at
  finer windows.
- **C3 PASS** — Alternative explanations (processing level, hole identity,
  weathering/regolith) are listed; README limitations call out that weathering vs
  lithology is unresolved and defer to a geologist.
- **D1 PASS** — Final Mask applied (`qc.apply_final_mask`, keep==1), documented in
  STATUS/data_notes. (No bulk re-fetch run; verified via code + derived parquet
  presence for all 15 holes.)
- **D2 PASS** — `invalid`/`aspectral` kept as explicit states (STATUS "Found" +
  `read.py` keeps explicit class values), not silently dropped.
- **D3 PASS** — TSAV ignored, Mineral Group used (SWIR=sTSAS, ignore sTSAV; group
  columns), per data_notes/STATUS.
- **D4 PASS** — `error` used as confidence; -3.4e38 null sentinel nulled before
  stats (STATUS "CRITICAL"); Wt1=1.0 not filtered.
- **D5 PASS** — SWIR and TIR never pooled into one composition; per-view transform
  with `swir_`/`tir_` prefixes (`params.clr` comment; `fusion.all_arms`). Zeros =
  "not detectable", handling documented in params.
- **E1 PASS** — Assay hygiene enforced: `qc.resolve_below_detection` (negatives =
  censored, impute |x|/2) and `qc.flag_implausible` (flag, never drop) with Au
  plausibility [0, 100000] ppm; applied via `data_access.assays_long`.
- **E2 PASS** — Below-detection handling documented in `params.assay_hygiene` and
  `qc.py` header.
- **E3 PASS** — Overlap-weighted assay compositing with an exact test (STATUS T2.1
  "straddling interval -> 80/6"; `composite_minerals`/`overlap_weight_assays`).
- **E4 PASS** — Au_PPM chosen before results from coverage (only broadly-covered
  target); README states the prospective-interval selection bias plainly.
- **F1 PASS** — Permutation baseline exists and is reported next to the result
  (`boundary_agreement_vs_baseline`, per-hole `permutation p` column in
  `ablation.md`). It still controls at each window: at 5 m 0/15 holes beat chance
  (median p=0.433); at 1 m only 4/15 beat chance (median p=0.302) — not degenerate.
  See Finding N2 (positive).
- **F2 PASS** — Negative controls collapse to chance: corruption tests (T2.7) +
  guard tests; the slow sensitivity test and 76 others pass
  (`HYFUSE_SLOW_TESTS=1 uv run pytest` → **77 passed**). Boundary negative control
  (perfect→p<0.05, wrong→p>0.05) exists (STATUS T2.5).
- **F3 PASS** — Naive concat arm present in all tables; "fusion helps" is always
  compared against concat and the best single view, at every window.
- **G1 PASS** — Uncertainty bootstraps HOLES not windows (`bootstrap_hole_delta`
  resamples holes; `params.bootstrap.unit: hole`).
- **G2 PASS** — n=15 holes stated everywhere; honest INCONCLUSIVE headline given
  the weak generality (11/15 one deposit).
- **G3 PASS** — Comparison count is modest (4 arms × 2 metrics × 1 target) and the
  headline does NOT cherry-pick: it reports the 5 m result as inconclusive even
  though a 1 m slice is favourable. The favourable slice is disclosed as
  non-robust rather than promoted.
- **G4 PASS** — Delta is judged against hole-level bootstrap CI (fold/hole
  variation), not a bare point estimate.
- **H1 PASS** — Every quantitative README sentence traces to a generated file.
  README 1 m claim "delta +0.028, CI [+0.008, +0.051]" matches `sensitivity.md`
  row and reproduces from `run_window_sensitivity`. Headline table matches
  `ablation.md` and reproduces from `run_ablation`.
- **H2 PASS** — Language is bounded: "INCONCLUSIVE", "no skill", "not robust", no
  mineralisation claim, no generality claim beyond the tested holes.
- **H3 PASS** — Negative/inconclusive results stated as plainly as any positive;
  the 1 m favourable result is explicitly framed as non-robust and NOT moved to
  the headline.
- **I1 PASS (on cached data)** — `make features && make evaluate` path reproduces
  the tables; headline + sensitivity both reproduced here from cached data (see
  Evidence). Full clean-clone `make fetch` not re-run (per instructions, cached
  only) — see "What I could not verify".
- **I2 PASS** — Seed fixed (`params.seed: 42`); `uv.lock` present; results
  reproduced bit-for-bit.
- **I3 PASS** — `git ls-files | grep -Ei '\.(bip|tsg|parquet|zip|duckdb|sqlite)$'`
  → nothing committed. No row-level data in git.
- **I4 PASS** — README names packages and data sources; HEAD == origin/main on the
  default branch.
- **J1 UNVERIFIED (requires geologist)** — Per-hole intervals for eyeballing are
  prepared (geologist packet + 4 HTML figures per STATUS); not a software check.
  Hand to a human expert.
- **J2 UNVERIFIED (requires geologist)** — Whether detected ~1 m boundaries track
  weathering/regolith vs lithology is explicitly flagged OPEN in `sensitivity.md`
  and README; needs core/expert review.

## Findings

### N1 [positive] Pre-registration integrity held across the sensitivity addition
- Where: `git diff 96c0454 63181da -- config/params.yaml`;
  `git log --reverse -- config/params.yaml`
- Evidence:
  ```
  freeze commit 96c0454 2026-10-13 00:41  (params frozen)
  first result 4f2c1c5 2026-10-13 15:41  (reports/ablation.md)
  only non-comment diff since freeze: + window_sensitivity_m: [5.0, 1.0, 0.5]
  window_size_m: 5.0  — byte-identical at 96c0454 and 63181da (lines 24 / 31)
  ```
- Why it matters: confirms the headline window is still the pre-registered 5 m,
  frozen before any results, and the sweep is a declared addition — not a
  post-hoc goalpost move. This is the central risk of the geologist-feedback
  change, and it is clean.

### N2 [positive] Sensitivity results reproduce and the permutation baseline controls
- Where: `uv run python -c "from hyfuse.ablation import run_window_sensitivity ..."`
- Evidence:
  ```
  win=5.0 (headline) fused=0.140 tir=0.139 delta=+0.001 CI=[-0.017,+0.022] excl0=False
  win=1.0            fused=0.262 tir=0.234 delta=+0.028 CI=[+0.008,+0.051] excl0=True
  win=0.5            fused=0.337 tir=0.353 delta=-0.016 CI=[-0.044,+0.015] excl0=False
  permutation p (fused): 5m frac p<0.05 = 0.00 (median 0.433);
                         1m frac p<0.05 = 0.27 (median 0.302)
  ```
  Matches `reports/sensitivity.md` and the README numbers exactly. The sweep
  reuses the identical `run_ablation` scoring path (same per-view transform, same
  arms on identical windows, same permutation baseline, same hole-level
  bootstrap) with only `win_override` changed (`ablation.py:42,48`), and the
  pre-registered tolerance guard (`preregistered_tolerance_ok`) is still enforced.
- Why it matters: the favourable 1 m result is a genuine, reproducible, declared
  sensitivity — not hand-entered and not produced by weakening the baseline. Only
  27% of holes individually beat permutation at 1 m, consistent with the honest
  "modest / not robust" framing.

### Minor observations (no action required for submission)
- **M1 [minor]** `make evaluate` writes `sensitivity.md` via `main()` calling
  `run_window_sensitivity()` after `run_ablation()` (`ablation.py:main`). The slow
  path is only gated in the *test* (`HYFUSE_SLOW_TESTS=1`), so a normal
  `make evaluate` will spend extra time running the 1 m / 0.5 m ablations. This is
  expected and documented; noted only so the runtime note in the README ("a few
  minutes") stays accurate on slower machines.

## What I could not verify
- **Clean-clone `make fetch` end-to-end (I1).** Per the review instructions I used
  cached data only and did not bulk-fetch ~8 GB from NCI THREDDS. The analysis
  reproduced fully from cached `data/raw`/`data/derived`; the download step itself
  was not re-exercised in this session (it was previously demonstrated per
  STATUS/R4).
- **Geological plausibility (J1, J2).** Whether detected domains — especially the
  finer 1 m boundaries — track lithology rather than weathering/regolith is a
  geological judgement outside a software review. The repo already flags this as
  OPEN.

## Questions for a human expert
1. At ~1 m, boundary F1 rises for all arms and fusion edges ahead (CI excludes
   zero). Is this real lithological structure, or finer windows coincidentally
   matching dense company logging? (sensitivity.md OPEN item.)
2. Do detected boundaries coincide with obvious regolith/weathering transitions in
   the 4 flagged holes (geologist packet)? If so, that is the alternative
   explanation to state.
3. Confirm the DASC below-detection convention (negatives = censored) and that
   Au_PPM outliers up to ~42% are data-entry/unit errors, per `assay_hygiene`.
