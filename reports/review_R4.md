# Review of HyFuse — 2026-10-13, commit 19785e8

Scope: **FINAL pre-submission review R4 — ALL items A–J**, plus clean-clone
reproduction (item I1). Reviewer: independent, fresh context, read the repo as a
stranger. No code, params, or result files were edited; `reports/review.md` is
the only output. Evidence was gathered by running the project's own code and
tests against cached data only (`data/raw/holes/*`, `data/raw/dasc/*`,
`data/derived/holes/*`); no data was fetched. The clean-clone cold-`make fetch`
path (~8 GB download) was NOT re-run (cached-data-only instruction); the analysis
half (`make features` / `make evaluate`) was re-verified bit-for-bit from cache
and `reports/reproduction.md` was inspected.

## Verdict

**Go for submission.** The headline is honest and reproduces **bit-for-bit** from
cached data: fusion does **not** beat the best single view on boundary recovery
(fused F1 0.140 vs tir_only 0.139; hole-level bootstrap delta +0.001, 95% CI
[-0.017, +0.022] includes zero), and **no** arm predicts Au on held-out holes
(all median R² ≤ 0). Every scientific control the skill asks for is present and
checks out with executed evidence: grouped-by-hole CV everywhere a split exists,
pre-registration verified by git timestamps, permutation baseline, hole-level
bootstrap, a varying confounder tested (and not flagged), assay below-detection
and ×1000 hygiene on real data, the naive-concat straw man, and no data in git.
The three R3 findings are resolved: **F1** — README is now the full honest
version with results, limitations, verification and the GSWA checklist; **F2** —
clean-clone reproduction is demonstrated and documented (`reports/reproduction.md`;
I independently re-verified the analysis path reproduces bit-for-bit); **F3** —
the single-deposit caveat ("11/15 one deposit + 4 regional; weak generality
test") is stated plainly in both the README and `reports/ablation.md`.

Two **minor** documentary nits remain (neither blocks submission, neither is a
scientific defect): a stale "73 tests" in the README (actual: 75), and stale CLR
wording in `config/params.yaml` comments (the live default transform is
Hellinger; code and `ablation.md` are honest about this). Fixes suggested below.

The usual limits apply: this is a software + statistics review. It does not
confirm the geology, validate the company assays, or replace a GSWA expert. "No
findings of scientific defect" is not proof none exist; the failure modes checked
are listed in the README and below.

## Checklist results

- **A1 PASS** — Grouped-by-hole CV everywhere a split exists. `grep` of `src/`
  finds **only** `GroupKFold`; no `train_test_split`, bare `KFold`,
  `StratifiedKFold` or `ShuffleSplit` (`evaluate.py:28,211,279`). Both
  `assay_prediction_cv` and `confounder_classifier_auc` use
  `GroupKFold` grouped by `hole_id`. Static guard test
  (`test_guards.py::test_assay_cv_uses_groupkfold_in_source`) + behavioural guard
  (`test_assay_cv_is_grouped_by_hole_not_leaky`) both pass.
- **A2 PASS** — Fitted steps live inside CV pipelines: `StandardScaler`+`Ridge`
  and `StandardScaler`+`LogisticRegression` are `sklearn.Pipeline`s passed to
  `cross_val_score`, so they fit per training fold only
  (`evaluate.py:204-213,273-281`). The one `StandardScaler().fit_transform`
  outside a split (`fusion._pca_block`) is per-hole descriptive segmentation of a
  single hole, not a train/test estimator — cannot leak test-hole info, and it is
  only reached by the optional `pca_components` ablation (default None, unused in
  the headline run).
- **A3 PASS** — Domaining (PCA→HDBSCAN→ruptures) runs per hole, per arm inside the
  hole loop (`ablation.py` `_per_hole_features` + `for hole` loop); features are
  composited per hole. No global normalisation / global PCA across holes before
  scoring.
- **A4 PASS (by design)** — No tuning on eval folds: ridge `alpha=100`, HDBSCAN
  `min_cluster_size=5`, ruptures penalty are fixed constants, documented as
  "reported, not tuned to a target" (`evaluate.py:267-271`).
- **B PASS** — Pre-registration verified by git. `config/params.yaml` first added
  `a55a57e` (2026-10-12 21:53, scaffold); tolerance/metric/splits/bootstrap frozen
  `96c0454` "T2.5 PRE-REGISTER" (2026-10-13 00:41). First results file
  `reports/ablation.md` added `4f2c1c5` (2026-10-13 15:41) — ~15 h later.
  `params.yaml` has **not** been touched since the pre-reg commit (last param
  commit = the pre-reg commit). `depth_tolerance_m` and
  `boundary_scoring.tolerance_m` are **2.0** now, matching pre-reg. No post-hoc
  change. A runtime guard (`ev.preregistered_tolerance_ok`) warns loudly if the
  scored tolerance ever drifts from 2.0 without a documented reason.
- **C1 PASS** — Confounder tested grouped-by-hole. Verified on cached derived data
  across the 15 pinned holes: `tir_processing_level` genuinely varies (sTSAT ×2 =
  12DHDD0002, 15SYDD0003B; sjCLST ×13) and is **not flagged** in any arm (max
  cv_accuracy 0.740 < majority 0.748). `instrument_gen` is constant (all HL3+) and
  SWIR processing constant (sTSAS) — correctly reported as "constant — not
  testable", not as a pass (`confounders.md`). Matches the committed report
  exactly.
- **C2 PASS** — All four arms scored on the identical window/hole set:
  `fusion.all_arms` inner-joins SWIR and TIR on the window index (`align`) before
  building any arm; reproduced run covers all 4 arms on 15 holes.
- **C3 PASS (read as limitation)** — Alternative explanations (processing level,
  instrument gen, single-deposit dominance, assay selection bias) listed in
  `ablation.md`/`confounders.md`/README. Weathering/regolith coincidence is **not**
  tested in code and is explicitly carried as the main open question for a
  geologist (README limitations + item J below).
- **D1 PASS** — Final Mask applied: `composite.composite_minerals` filters
  `final_mask == 1` (`composite.py:50`); `qc.apply_final_mask` keeps ==1. Verified
  on BBDD0001 derived parquet: final_mask has both 1 (28,788) and 0 (11,372) rows,
  i.e. the column is preserved and filtered downstream, not pre-dropped.
- **D2 PASS** — `aspectral` kept as an explicit state: BBDD0001 has 5,560 rows with
  `is_explicit_state == True`, mineral = "Aspectral", not dropped or zeroed. Only
  true non-mineral groups `{"", INVALID, NOTAROK}` are excluded from the
  *composition* (`features._NON_COMPOSITION_GROUPS`), kept elsewhere as flags.
- **D3 PASS** — Composition is built on `mineral_group` (Level-1 rule); no TSAV
  column present in the tidy table (verified: `any('tsav' ...) == False`).
- **D4 PASS** — Wt1==1.0 kept: 6,860 rows with abundance==1.0 in BBDD0001 are
  retained; `error` is the documented confidence measure (`qc.py` docstring).
- **D5 PASS** — SWIR and TIR never pooled: per-view transform then concatenate,
  columns view-prefixed (`fusion.arm_fused`, `features.view_features`); zeros
  treated as structural "not detectable" (Hellinger closure / CLR multiplicative
  replacement). Documented.
- **E1 PASS** — Implausible Au flagged, not dropped. Verified on real DASC
  (`wamex_assay_flat_data`): 236,719 Au_PPM rows, max 421,300 ppm (~42%), 12 rows
  above the 100,000-ppm cap → flagged by `qc.flag_implausible`.
- **E2 PASS** — Below-detection documented and handled: negatives mean "below |x|",
  imputed |x|/2 with a `below_detection` flag (`qc.resolve_below_detection`).
  Verified: 49,541/236,719 Au rows negative, min −5000 — exactly the convention the
  code assumes.
- **E3 PASS** — Compositing to windows is overlap-length weighted
  (`composite.overlap_weight_assays`); exact test
  (`test_composite.py::test_overlap_weighted_assay_exact` + touching-boundary and
  no-overlap cases) passes.
- **E4 PASS** — Au chosen before results (pre-reg B; `assay_targets: [Au_PPM]`) and
  the single-target choice justified by coverage in `params.yaml`. Selection bias
  ("companies sample prospective intervals") stated in `ablation.md`, `params.yaml`
  **and** the README limitations.
- **F1 PASS** — Permutation baseline exists and is reported next to the result:
  per-hole `permutation p` column in `ablation.md`;
  `evaluate.boundary_agreement_vs_baseline`; tests
  `test_boundary.py::test_good_detection_beats_permutation_pvalue_low` and
  `test_random_detection_pvalue_not_significant` pass.
- **F2 PASS** — Negative controls collapse to chance (ran independently): random
  features + random hole-level confounder → not flagged (cv_acc 0.483 < majority
  0.583); grouped-CV with target = hole identity → R² median −0.296, has_skill
  False. Positive control (feature == confounder) flags, cv_acc 1.000.
  Shuffled-hole-id join collapses (`test_corruption.py`). Two+ controls collapse
  as required; no negative control "works".
- **F3 PASS** — Naive `concat` arm exists (`fusion.arm_concat`) and is scored
  alongside fused; "fusion helps" is compared to it, not only single views.
- **G1 PASS** — Uncertainty bootstraps **holes**, not windows
  (`bootstrap_hole_delta` resamples the per-hole delta array; `params.bootstrap.
  unit: hole`).
- **G2 PASS (and flagged)** — n = 15 holes stated in every comparison; this is just
  above the skill's ~8-hole floor, but 11/15 are one deposit (Bannockburn
  BBDD/BBRD, verified in `holes.yaml`), so the INCONCLUSIVE verdict and the
  "not general" caveat are the right call.
- **G3 PASS** — Comparison count is small (4 arms × 2 metrics = 8 scores, 1
  target); the single headline comparison is fused vs best-single via one
  pre-registered bootstrap. No "best of many" cherry-pick.
- **G4 PASS** — Difference read against spread: the bootstrap CI [-0.017, +0.022]
  is reported and used to call the result inconclusive, not a bare point estimate.
- **H1 PASS** — Every quantitative sentence in the README traces to a generated
  file: the results table (0.102 / 0.139 / 0.129 / 0.140; R² −1.7 / −1.6 / −6.0 /
  −6.5; delta +0.001; CI [-0.017, +0.022]) matches `reports/ablation.md`, which I
  regenerated **bit-for-bit** from cached data. The "11/15 Bannockburn" claim
  matches `config/holes.yaml`. (One non-result number is stale — see F2 below:
  README "73 tests" vs actual 75.)
- **H2 PASS** — Language is bounded and honest: "INCONCLUSIVE", "no reliable
  difference", "no skill", "effectively one deposit … does not generalise",
  "Nothing here claims mineralisation." No mineralisation or generality claim.
- **H3 PASS** — The negative/inconclusive result is the headline, stated as plainly
  as any positive would be (README "Answer … INCONCLUSIVE, reported honestly").
- **I1 PASS (analysis path) / documented (cold fetch)** — Clean-clone reproduction
  is demonstrated in `reports/reproduction.md` (fresh temp clone of the public
  repo, env from `uv.lock`, data from cache): `uv sync` OK, `make doctor` OK,
  `make test` 75 passed, `make features && make evaluate` → `ablation.md`,
  `confounders.md`, `coverage.md` **bit-for-bit identical** to committed. I
  independently re-ran `uv run python -m hyfuse.ablation` from cache at HEAD and
  confirmed the regenerated `ablation.md`/`confounders.md` are byte-identical
  (git shows no change). The cold `make fetch` (~8 GB) was NOT re-run here or in
  the reproduction record; this limitation is stated explicitly in both the README
  and `reproduction.md`. HEAD (19785e8) differs from the reproduced commit
  (c449c87) only by docs (STATUS.md, pitch.md, reproduction.md,
  submission_checklist.md) — no code/params/results — so the reproduction evidence
  carries forward to HEAD.
- **I2 PASS** — Seeds fixed (`params.seed: 42`, threaded into PCA/HDBSCAN/KMeans/
  ridge/logreg/bootstrap/permutation; determinism gives the bit-for-bit repro);
  versions locked (`uv.lock`; `make doctor` prints duckdb 1.5.6, pytsg 1.0.0,
  scikit-learn 1.9.1, ruptures 1.1.10).
- **I3 PASS** — No data in git: `git ls-files | grep -Ei
  '\.(bip|tsg|parquet|duckdb|sqlite|zip)$'` returns nothing; `.gitignore` covers
  `data/ cache/ logs/ *.parquet *.sqlite *.zip *.tsg *.bip` etc. Only small
  `reports/*.md` tracked.
- **I4 PASS** — Packages and data sources named in README; latest commit 19785e8 is
  on `main` (the default branch) and pushed to the public remote
  `https://github.com/sbenayoun/hyfuse.git`.
- **J PASS (evidence produced; verdict handed to a human)** — Candidate intervals
  for a geologist listed below; regolith/weathering coincidence is explicitly left
  open.

## Calibration (planted-flaw) status

`reports/calibration.md` + `reports/calibration_review.md` record a done-once
planted-flaw run on a throwaway `calibration` branch: 3/3 planted defects
(window-level split, assay ×1000, post-hoc tolerance) caught as blockers with
executed evidence, zero false alarms. I verified the branch was **not merged**
and the three injected-defect commits (f275969, e70fc4c, 68fab30) are **not
reachable from main** (`git merge-base --is-ancestor` → all "NOT on main"). The
calibration also surfaced two genuine issues on main (F5 confounder omitted a
varying axis; F7 missing guards), both fixed and now covered by `test_guards.py`
(7 tests pass). The review process is therefore calibrated and trustworthy for
this final pass.

## Reproduced result (executed, cached data, HEAD 19785e8)

`uv run python -m hyfuse.ablation` → `ablation.md` and `confounders.md`
**byte-identical** to committed (`diff -q` → IDENTICAL; `git status` clean after).

| arm | mean boundary F1 | assay Au R² (median) |
|---|---:|---:|
| swir_only | 0.102 | −1.7 (no skill) |
| tir_only | 0.139 | −1.6 (no skill) |
| concat | 0.129 | −6.0 (no skill) |
| fused | 0.140 | −6.5 (no skill) |

Fused − best single (tir_only): **+0.001**, 95% CI **[-0.017, +0.022]**, n=15,
excludes zero = **False**. `uv run pytest -q` → **75 passed**.
`uv run ruff check .` → all checks passed. `make doctor` → DOCTOR OK.

## Findings

### F1 [minor] README states "73 tests"; the suite is now 75
- Where: `README.md:91` ("make test  # 73 tests …"). `reports/reproduction.md`
  correctly says 75.
- Evidence: `uv run pytest -q` → **75 passed** (R2/R3-era guard + viewer tests
  were added after the 73 figure was written).
- Why it matters: minor, but a claims-vs-evidence (item H) review should not leave
  a stale count in the README a judge will run.
- Suggested fix: change "73 tests" → "75 tests" in the README install block.

### F2 [minor] `config/params.yaml` comments still describe CLR as the transform
- Where: `config/params.yaml` lines ~9-20 ("CLR (centered log-ratio) is applied
  PER VIEW …"); the live default is **Hellinger** (`fusion.py`, `features.py`,
  `ablation.md` header "Transform: hellinger").
- Evidence: the planted-truth study found CLR destroyed the domain signal, so the
  default was switched to Hellinger; the code honestly reflects this, but the
  pre-registration file's prose still reads as if CLR is the method. The `clr:`
  block (delta, zero_strategy) is still live for the CLR ablation path, so it is
  not dead config — only the surrounding comment is stale.
- Why it matters: a reviewer reading the pre-registered params could think the
  shipped method is CLR. No scientific impact (the transform choice is documented
  as a post-planted-truth decision in `ablation.md`, `data_notes.md`,
  `planted_truth.md`, and the commit message bf25217), but the comment should
  match the code.
- Suggested fix: add a one-line note in `params.yaml` that Hellinger is the live
  default and CLR is retained as an ablation (do not change any numeric param —
  that would be a post-hoc edit).

## What I could not verify

- **I1 cold path**: a true from-scratch clean clone → `make fetch` (~8 GB from NCI
  THREDDS) → `make evaluate` was NOT run (cached-data-only instruction; download
  size). Mitigated: the analysis half reproduces bit-for-bit from cache, the
  reproduction record documents the same, determinism is seed-fixed, and the fetch
  size + cached-data fallback are stated in the README and `reproduction.md`. The
  `fetch.py` download logic itself (retry/backoff, THREDDS URL correctness) was
  not exercised.
- **D3 (partial)**: that no TSAV / individual-mineral result leaks into the
  composition on *every* hole via `read.py` — confirmed absent on the inspected
  hole and the composition path reads only `mineral_group`, but per-hole ingestion
  was not exhaustively audited across all 15.
- **Geology itself**: whether the detected boundaries/domains are geologically
  meaningful, and whether they track weathering/regolith rather than lithology.
  Out of scope for a software/stats review (per skill); handed to a human below.

## Questions for a human expert (item J)

Candidate intervals to eyeball (hole, logged-boundary count, detected count,
fused F1, permutation p — from `reports/ablation.md`). For each, pull the core
photo and logged unit at the detected boundary depths:

1. **BCMH0070** — logged 33, detected 4, F1 **0.216**, p 0.332. A relatively
   "good" case: do the 4 detected boundaries land on real lithological contacts,
   or on a weathering/regolith transition near the top of hole?
2. **BBDD0005** — logged 14, detected 3, F1 **0.235** (highest), p 0.553. High p
   means random boundaries do about as well — are these geologically real or
   coincidental at 5 m resolution?
3. **BBRD0056** — logged 12, detected **0**, F1 **0.000**, p 1.000. A clear miss on
   the one RC hole — is the spectral signal degraded vs diamond core?
4. **16CADD001** — logged 88, detected 8, F1 0.104, p 0.421. Very fine company
   logging vs coarse 5 m windows: is the window simply too coarse to recover this
   hole's boundaries?
5. **General (the main untested alternative explanation, C3):** do detected
   boundaries systematically coincide with the regolith/fresh-rock transition? If
   so, "geological domains" is partly a weathering signal and the README should say
   so.

Also for the geologist: confirm (a) the below-detection = negative-value
convention and the |x|/2 imputation are appropriate for these assays, and (b) that
`tir_processing_level` (sjCLST vs sTSAT) truly carries no geological information
that the "not flagged" confounder test might be under-powered to detect at n=15
(only 2 holes carry the minority level).

## Failure modes checked (for the README's "what we checked" list)

Leakage across CV folds (grouped by hole; windows from one hole never split);
processing level / instrument masquerading as geology (varying axis tested, not
flagged; constant axes reported as untestable); assay selection bias and ×1000
unit errors (flagged, not dropped); boundary tolerance tuned after seeing results
(pre-registered + runtime guard; git-timestamp verified); SWIR/TIR comparisons
confounded by different depth coverage (all arms on identical inner-joined
windows); results on too few holes presented as general (n=15, one deposit —
reported INCONCLUSIVE and "not general"). Not checked: the geology itself, and
the cold `make fetch` download path.
