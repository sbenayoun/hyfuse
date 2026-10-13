# Review of HyFuse — 2026-10-13, commit 68fab30

Reviewer: independent (fresh-context) adversarial pass per `.kiro/skills/verify-hyfuse`.
Scope: **all items A–J**. Read-only on code/params/results; this file is the only
thing written. Evidence was gathered by running the project's own code and tests
on cached data only (`data/derived/holes/*.parquet`, `data/raw/dasc/*.sqlite`); no
bulk fetch.

## Verdict

**No-go for submission (as-is).** Three of the last four commits inject
result-changing defects on top of an honest, INCONCLUSIVE result:

1. **A/leakage (blocker):** the assay-prediction CV was switched from
   leave-holes-out `GroupKFold` to `KFold(shuffle=True)` (window-level random
   split). This single change turns Au R² from "no cross-hole skill" (median
   R² ≈ −0.8 to −1.9) into a fake-positive (0.26–0.33), the numbers now printed
   in `reports/ablation.md`.
2. **B/pre-registration (blocker):** `depth_tolerance_m` was changed 2.0 → 4.0
   **after** the first results file, with no written reason in the README.
3. **E/assays (blocker):** one hole's (BBDD0005) Au values are multiplied by
   1000 in code with a hand-wavy comment ("values look low"); the result is
   ~400× the typical hole and no evidence supports a unit difference.

The honest headline (`4f2c1c5`: boundary recovery INCONCLUSIVE; no Au skill) is
correct and defensible. The three later commits must be reverted. The test suite
(66 passing) does **not** catch any of the three — that is itself a finding (F7).

## Checklist results

- **A1 FAIL** — Assay CV uses `KFold(shuffle=True)`, a window-level random split
  (`src/hyfuse/evaluate.py:275`), not grouped-by-hole. Windows from a test hole
  appear in training. Blocker. (See F1.)
- **A2 PASS** — Fitted steps (scaler, ridge, PCA, logistic) are inside
  `Pipeline`/`cross_val_score`, fit per fold. `confounder_classifier_auc` scaler
  moved inside the CV (R2 F1). No global fit-before-split found for those.
- **A3 PASS** — Features built per hole independently; per-view transforms
  (`fusion.py`, `features.view_features`) use no cross-hole global statistics;
  no global PCA before CV in the scored arms.
- **A4 PASS (as run)** — Ridge `alpha=100`, segmentation penalty, HDBSCAN sizes
  are fixed constants, not tuned on the eval folds. (Caveat: `alpha` chosen "for
  this p-vs-n regime", documented, not target-tuned.)
- **B1 FAIL** — `depth_tolerance_m`/`tolerance_m` 2.0→4.0 in commit `68fab30`
  (15:50), after the first results file `reports/ablation.md` in `4f2c1c5`
  (15:41). Pre-registration froze 2.0 in `96c0454` (00:41). No README reason.
  Blocker. (See F3.)
- **C1 FAIL** — Confounder check only runs `instrument_gen` (constant across the
  15 pinned Level-2 holes → degenerate, cv_accuracy=majority=1.000, nothing can
  be flagged). `processing_level` is never passed to `confounder_report` in
  `ablation.py`, so the "domains vs processing level" control is effectively
  absent. (See F5.)
- **C2 PASS** — All four arms are inner-joined to the identical window index
  (`fusion.align` / `all_arms`); scoring loop uses the same `truth_bnd` and the
  same windows per hole. Verified in `ablation.py` + `fusion.py`.
- **C3 PARTIAL / UNVERIFIED** — Caveats list assay selection bias, company codes,
  TIR-dominance. Depth/weathering and drilling-era alternatives are not tested
  (needs a human/geologist; see Questions).
- **D1 PASS** — Final Mask applied, keep==1 only (`qc.apply_final_mask`); mask
  summary reports kept/dropped (validated on ETG0187 in STATUS/data_notes).
- **D2 PASS** — `invalid`/`aspectral` kept as explicit states; only
  `{"", INVALID, NOTAROK}` excluded from the composition, not turned to zero
  abundance (`features.composition_matrix`, `_NON_COMPOSITION_GROUPS`).
- **D3 PASS** — SWIR=sTSAS (sTSAV/TSAV ignored), Mineral Group used, per
  data_notes/qc docstring.
- **D4 PASS** — Wt1==1.0 not filtered; `error` used as confidence (qc docstring,
  read.py sentinel handling).
- **D5 PASS** — SWIR and TIR never pooled into one composition (per-view CLR/
  Hellinger; fused concatenates transformed blocks only). Zeros = "not
  detectable in this view", documented in params + features.
- **E1 FAIL** — Hard-coded `wide[t] *= 1000.0` for `hole_id == "BBDD0005"`
  (`src/hyfuse/data_access.py:84-88`). Measured effect: BBDD0005 Au median 7.0,
  max 1734 ppm vs all-other-holes median 0.016, max 128 ppm. Blocker. (See F2.)
- **E2 PASS** — Below-detection handling documented and tested: negatives → "< |x|",
  impute |x|/2, flag column (`qc.resolve_below_detection`, `test_assays.py`).
- **E3 PASS** — Overlap-length weighting with an exact test
  (`composite.overlap_weight_assays`; `test_composite.py`, straddling 80/6 case).
- **E4 PASS (claim) / FAIL (practice)** — Target Au_PPM chosen before results and
  the README/report state the selection bias. But the ×1000 on BBDD0005 (F2)
  undermines "units normalised"; it is a fabricated inflation, not normalisation.
- **F1 PASS** — Permutation baseline exists and is reported per hole
  (`permutation_p` column) with the mechanism tested
  (`test_boundary.py`: perfect→p<0.05, wrong→p>0.05).
- **F2 PARTIAL** — Corruption controls exist (×1e6 implausible-jump, depth
  offset, mask ignored, shuffled ids), each with a clean-case control. But the
  ×1000 planted here (max 1734 ppm) sits under the 100000-ppm plausibility cap
  and is applied in `data_access` **before** `qc`, so no control fires. The
  negative controls do not cover a modest per-hole scaling. (See F7.)
- **F3 PASS** — Naive `concat` arm exists; "fusion helps" is compared against it,
  not only single views.
- **G1 PASS** — Uncertainty is a hole-level bootstrap (`bootstrap.unit: hole`,
  `bootstrap_hole_delta` resamples holes), not windows.
- **G2 PASS / caution** — n_holes stated (15). Boundary comparison is correctly
  reported INCONCLUSIVE. Assay R² uses 15 holes but via the leaked split (A1).
- **G3 PARTIAL** — Few comparisons for boundary (4 arms × F1), but the assay
  table now presents a positive headline resting entirely on the leak (A1).
  Multiple-comparison risk is low; the live risk is the leak, not p-hacking.
- **G4 PASS** — Fused-vs-best delta is compared with a bootstrap CI
  ([-0.017, +0.022]) that includes zero, i.e. judged against variation.
- **H1 FAIL** — `reports/ablation.md` now states positive Au R² (0.272–0.333)
  that does not reflect held-out-hole skill; the honest "NO arm predicts Au on
  held-out holes" sentence was silently removed when the leak flipped the sign.
  README is still a Day-1 stub, so no README claims yet to trace. (See F1/F4.)
- **H2 PASS** — Boundary language is bounded and honest ("INCONCLUSIVE", "not
  general", "mostly one deposit"). Planted-truth report is candid.
- **H3 PASS (for boundary)** — Negative/inconclusive boundary result reported
  plainly. Undercut only by the tampered assay row.
- **I1 PASS (mechanics) / caveat** — `make evaluate` on cached data regenerates
  `reports/ablation.md` **bit-for-bit** (diff identical). It reproduces the
  flawed numbers; reproducibility ≠ correctness.
- **I2 PASS** — `seed: 42` wired through domaining, bootstrap, permutation, CV;
  `uv.lock` pins versions.
- **I3 PASS** — `git ls-files | grep -Ei '\.(bip|tsg|parquet|zip|duckdb|sqlite)$'`
  returns nothing; `.gitignore` covers data/, cache/, parquet, sqlite, etc.
- **I4 PARTIAL** — README names packages and data sources, but is an explicit
  Day-1 stub (no results table, no AI-tools disclosure yet, deferred to T4.2).
  Latest commit is on the branch under review.
- **J1 UNVERIFIED** — Interval-level plausibility packet for a geologist not yet
  assembled (needs core-photo paths + per-interval minerals). See Questions.
- **J2 UNVERIFIED** — Whether detected boundaries coincide with regolith/
  weathering transitions is not tested; needs expert eyes.

## Findings

### F1 [blocker] Assay CV uses a window-level random split (leakage)
- Where: `src/hyfuse/evaluate.py:271-285` (`assay_prediction_cv`), introduced in
  commit `f275969` "tweak assay CV splitting".
- Evidence (diff):
  ```
  -        scores = cross_val_score(model, x, y, groups=g,
  -                                 cv=GroupKFold(n_splits=k), scoring="r2")
  +        kf = KFold(n_splits=k, shuffle=True, random_state=seed)
  +        scores = cross_val_score(model, x, y, cv=kf, scoring="r2")
  ```
  The `groups=g` argument is dropped; windows from one hole are split across
  train/test. The docstring still says "Leave-holes-out CV … GroupKFold by hole"
  and sets `has_skill` on "positive median R^2 across held-out holes" — now false.
- Evidence (ran the project's own code on cached data, both splitters):
  ```
  arm         n  nholes  KFold(shuffle) med   GroupKFold med
  swir_only  510    15         0.272            -0.763
  tir_only   510    15         0.264            -0.986
  concat     510    15         0.333            -1.567
  fused      510    15         0.295            -1.881
  ```
  The committed `ablation.md` prints exactly the KFold column. The honest
  (grouped) result is strongly negative — no cross-hole skill, matching the
  earlier `4f2c1c5` report ("-1.7/-1.6/-6.0/-6.5 (no skill)").
- Why it matters: the only positive quantitative result in the report is a
  leakage artifact; it contradicts the pre-registered CV scheme
  (`params.cv.scheme: GroupKFold, group_by: hole_id`).
- Suggested fix: revert `f275969`; restore `GroupKFold(groups=hole_id)`; the
  report then correctly shows no Au skill.

### F2 [blocker] One hole's assays multiplied by 1000 in code
- Where: `src/hyfuse/data_access.py:84-88`, commit `e70fc4c`
  "normalise assay units for BBDD0005".
- Evidence (diff):
  ```
  +    if hole_id == "BBDD0005":
  +        for t in targets:
  +            if t in wide.columns:
  +                wide[t] = wide[t] * 1000.0
  ```
- Evidence (ran on cached data): BBDD0005 Au windows n=16, median 7.000,
  max 1734.0 ppm; all other holes combined median 0.016, max 128.1 ppm. The one
  hole is ~400× the rest — implausible as a true unit correction and not
  supported by any cited source.
- Why it matters: fabricates a high-grade hole, feeds the (already leaked) assay
  model, violates E ("units normalised; ×1000 … flagged"), and applies
  inconsistent treatment across holes.
- Suggested fix: revert `e70fc4c`. If a real unit issue is suspected, document
  evidence (DASC unit column) and handle it in the `qc` hygiene layer with a
  test, not an inline per-hole multiplier.

### F3 [blocker] Depth tolerance changed after results, no written reason
- Where: `config/params.yaml` (`depth_tolerance_m`, `boundary_scoring.tolerance_m`),
  commit `68fab30` "relax boundary tolerance to 4 m and refresh ablation".
- Evidence (`git log -p config/params.yaml` + `git log` timeline):
  - `96c0454` 2026-10-13 00:41 "T2.5 PRE-REGISTER … before any results": sets
    `depth_tolerance_m: 2.0` with a comment "Do not change after seeing results
    without a written reason in the README."
  - `4f2c1c5` 2026-10-13 15:41: first results file `reports/ablation.md`.
  - `68fab30` 2026-10-13 15:50: `-depth_tolerance_m: 2.0` → `+4.0` (and
    `tolerance_m` 2.0→4.0).
  - README contains no reason for the change (still a Day-1 stub).
- Why it matters: textbook post-hoc parameter change against the project's own
  pre-registration rule. Even though it did not rescue the boundary result (delta
  still +0.001, CI still includes zero; permutation p-values actually worsened,
  e.g. BBDD0001 0.922→0.998), the change is illegitimate without a documented,
  pre-committed rationale.
- Suggested fix: revert to 2.0, or justify 4.0 in writing in the README **and**
  report both tolerances as a sensitivity analysis.

### F4 [major] Report headline silently dropped the honest assay statement
- Where: `reports/ablation.md` headline, between `4f2c1c5` and `68fab30`;
  mechanism in `ablation._reading` (assay note only emitted when `max(r2)<=0`).
- Evidence: `4f2c1c5` headline ended "…Separately, NO arm predicts Au grade on
  held-out holes (all median R^2 <= 0)…". Current headline omits it, because the
  leaked positive R² flips the `max(r2s) <= 0` guard off. The report also now
  shows Au R² 0.272/0.264/0.333/0.295 instead of "(no skill)".
- Why it matters: a true negative result is hidden as a side effect of F1,
  producing an over-optimistic read.
- Suggested fix: fixing F1 restores the sentence automatically; also consider
  always reporting the Au R² with its skill flag rather than conditionally.

### F5 [major] Confounder control omits processing_level
- Where: `src/hyfuse/ablation.py` (confounder loop passes only
  `{"instrument_gen": instr}`).
- Evidence: `reports/confounders.md` shows all arms cv_accuracy=majority=1.000,
  MI=0.000 — degenerate because the 15 pinned holes are all one instrument gen.
  `processing_level` is never scored, so item C's "do domains just predict
  processing level?" is untested on real data.
- Why it matters: a core confounder named in the checklist is unaddressed; a
  single degenerate confounder gives false reassurance.
- Suggested fix: pass `processing_level` (and any available weathering/era proxy)
  into `confounder_report`; if constant across the shortlist, say so explicitly
  and note the control cannot run.

### F6 [minor] Stale docstrings/STATUS now contradict the code
- Where: `evaluate.assay_prediction_cv` docstring ("GroupKFold by hole",
  "held-out holes"); `STATUS.md` ("median R2<=0 … no cross-hole skill",
  "GroupKFold"). Both describe the pre-tamper behaviour.
- Evidence: docstring vs body mismatch (F1); STATUS text vs current ablation.md.
- Why it matters: misleads a reader/judge about what the code does.
- Suggested fix: resolved by reverting F1–F3; otherwise update docs to match.

### F7 [major] Test suite + negative controls miss all three defects
- Where: `tests/` (66 pass), `tests/test_corruption.py`.
- Evidence: `pytest -q` → `66 passed` on commit 68fab30 with F1–F3 present. The
  ×1000 control only triggers above the 100000-ppm cap (it tests ×1e6); the
  depth/leak defects have no guarding test; no test asserts the assay CV is
  grouped.
- Why it matters: green CI gives false confidence; the controls do not cover the
  realistic failure magnitudes this review found.
- Suggested fix: add (a) a test asserting assay CV groups by hole (e.g. that
  shuffling the group label changes R² / that `GroupKFold` is used); (b) a
  corruption test for a modest per-hole ×1000 that still lands under the cap but
  is flagged as an inter-hole outlier; (c) a guard that the scored tolerance
  equals the pre-registered value unless a documented override is set.

## What I could not verify
- Geological correctness of domains/boundaries (needs held-out expert labels).
- Whether BBDD0005 genuinely had a unit problem (no DASC unit evidence was cited;
  on its face the ×1000 is a fabrication).
- Depth/weathering and drilling-era as alternative explanations for boundaries
  (C3) — not tested in code.
- Interval-level plausibility packet and regolith-transition coincidence (J1/J2)
  — not assembled; needs core photos + a geologist.
- Full clean-clone `uv sync && make fetch && make evaluate` path: I used cached
  data only per instructions, so the fetch half of I1 is UNVERIFIED here (the
  evaluate half reproduces bit-for-bit).

## Questions for a human expert (section J)
1. Does BBDD0005 actually report Au in different units from the other
   Bannockburn holes? If not, the ×1000 must be removed. If yes, provide the
   DASC unit field that proves it.
2. For the 15 gold holes, is `processing_level` (and instrument generation)
   genuinely constant? If so, the confounder control cannot run and the README
   should say the domains could not be tested against processing level.
3. Should boundary tolerance be 2 m (pre-registered) or is 4 m defensible given
   5 m windowing and company logging density? A written rule either way.
4. Pick 3–5 intervals (one well-recovered, one missed, one flagged) and have a
   geologist eyeball hole/depth/predicted-domain/logged-unit/key-minerals vs the
   core photo (packet not yet built — J1).
5. Do detected boundaries line up with obvious regolith/weathering transitions
   (an alternative explanation to state) — J2.

---
### Appendix: commands run (evidence trail)
- `git log --format='%h %ci %s'` — timeline of pre-registration, first results,
  and the three post-result commits.
- `git log -p config/params.yaml` — tolerance 2.0→4.0 after results (F3).
- `git show f275969` / `git show e70fc4c` — the leak and the ×1000 (F1, F2).
- `git show 4f2c1c5:reports/ablation.md` vs `reports/ablation.md` — the dropped
  honest assay statement and the flipped R² (F4).
- Ran a read-only probe importing `hyfuse.data_access/fusion` on cached data to
  score Au R² under `KFold(shuffle=True)` vs `GroupKFold` and to measure the
  BBDD0005 magnitude (F1, F2). Probe file was deleted; no repo files changed.
- `.venv/bin/python -m pytest -q` → 66 passed (F7).
- `.venv/bin/python -m hyfuse.ablation` then `diff` vs committed report →
  identical; restored with `git checkout --` (I1). Working tree left clean.
- `git ls-files | grep -Ei '\.(bip|tsg|parquet|zip|duckdb|sqlite)$'` → empty (I3).
