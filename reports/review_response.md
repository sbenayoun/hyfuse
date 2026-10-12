# HyFuse — builder response to review R2

Reviewer report: `reports/review_R2.md` (independent fresh session, commit
`e9eafa0`, scope A-F). Verdict: **Go with fixes, none blocking.** The builder
session does not edit the review; dispositions below (AGENT_INSTRUCTIONS §4A).

## Dispositions (R2)

### F1 [minor] Scaler fit outside the CV split in confounder_classifier_auc
**FIXED (commit <this>).** Replaced `StandardScaler().fit_transform(x)` before
`cross_val_score` with a `sklearn.pipeline.Pipeline([scaler, LogisticRegression])`
passed to `cross_val_score`, so the scaler is fit per training fold (GroupKFold by
hole). Verified: confounder tests still pass (planted-confounded flagged, clean
not), 57 tests green. This also hardens the helper before T3.3 reuses it for a
metric we want to be HIGH (where the leak would have inflated the result).

### F2 [minor] instrument_gen never populated (constant 'unknown')
**FIXED (commit <this>).** read.read_hole now accepts instrument_gen='infer' and
features.build_hole defaults to 'infer', deriving the HyLogger generation from the
present spectral views (MIR->HL4, TIR->HL3+, VNIR/SWIR only->HL2+) per the GSWA
Spectral Regions slide. Rebuilt ETG0187 -> instrument_gen='HL3+' (has TIR, no MIR),
no longer constant. New test test_infer_instrument_gen_from_views. VERIFY against a
firmer package metadata field if one exists. T3.3 must confirm the fetched shortlist
spans >=2 processing levels / instrument generations for the confounder control to
be non-vacuous (carried into Day-3 plan).

## Checklist items UNVERIFIED at R2 (expected; Day-3 T3.x)
C2 (four arms on identical windows/holes), C3 (alternative-explanations list),
F3 (naive-concat arm as runnable code), the headline fusion claim, and cross-hole
leakage of the full ablation — all depend on fusion.py / evaluate.py result tables
/ confounders.md, which are T3.2/T3.3. The scoring/confounder/boundary ENGINES are
present and unit-tested now, and were reviewed as such.

## Confirmed PASS at R2 (no action needed)
Pre-registration verified by git timestamps (params freeze 96c0454 precedes
scoring e6f0786; no ablation file exists). Final Mask / invalid-aspectral / TSAV /
Mineral-Group / Wt1=1.0 / never-pool-views all PASS on real ETG0187. Assay units/
below-detection/overlap-weighting/target-selection all PASS. Permutation baseline
+ negative controls collapse to chance. 56/56 tests at review time (57 after fixes).

## Questions for a human expert (carried into Day 3)
Reviewer raised 4 (below-detection |x|/2 convention; Au >100000 ppm real vs error;
SWIR-active set vs GSWA SKOS; processing-suffix choice). All already logged as
VERIFY items; to be put to GSWA and reflected in T3.1 (synth) and the README.


Reviewer report: `reports/review_R1.md` (independent fresh session, commit
`1f36dca`, scope D/E/I). The builder session does NOT edit the review itself;
each finding gets a disposition here, per AGENT_INSTRUCTIONS.md §4A.

Verdict received: **Go with fixes** (end-of-Day-1). No blockers in scope.

## Dispositions

### F1 [major] `make fetch` guard refuses the pinned 15-hole list
**FIXED (commit <this>).** The Makefile `fetch` target now computes `--max-holes`
from the length of `config/holes.yaml` (15), so the documented `make fetch` path
no longer refuses the pinned list. The `--max-holes` guard still protects against
stray/bulk CLI runs. Verified: computed value = 15; fetch accepts it (ran against
the cached ETG0187, no new download).

### F2 [major] README is empty — reproducibility/package/data rules absent
**PARTIALLY FIXED now; full fix scheduled T4.2.** Added a README stub (commit
<this>) that already carries: the question, the reproduce recipe (`uv sync` →
`make fetch` → `make evaluate`), data-download locations (THREDDS + DASC),
package list (pyproject/uv.lock), the no-data-in-git statement, and the AI-tools
disclosure. The FULL README (team, results table, screenshots, licence,
limitations incl. assay selection bias) is task T4.2 (Day 4) by plan and cannot
be completed until results exist. ACCEPTED LIMITATION until T4.2; tracked in the
T4.4 submission checklist.

### F3 [major, forward-looking] Assay below-detection encoded as negatives
**ACCEPTED (forward-looking); recorded so it cannot be forgotten.** Independently
re-confirmed: 49,541/236,719 non-null `Au_PPM` < 0 (down to −5000); max 421300
(~42%). No handling exists yet because assay ingestion is T2.2 (Day 2). Recorded
the required rules in `config/params.yaml -> assay_hygiene`: treat negatives as
below-detection (impute |x|/2, ASSUMPTION to ablate), per-element plausibility
ranges, flag-not-drop. T2.2 will implement + test these, and the T2.7 corruption
tests already plan the ×1000 unit-error case. A VERIFY for a GSWA expert on the
exact convention is logged (review §"Questions for a human expert").

### F4 [minor] `seed: 42` declared but unused
**ACCEPTED (forward-looking).** Correct: no stochastic step exists yet. The seed
will be threaded into PCA/HDBSCAN/GroupKFold/bootstrap when those land (T2.4,
T3.3), with a test asserting determinism. Tracked here and in STATUS.md.

## Checklist items left UNVERIFIED at R1 (expected; not failures)
Assay units/below-detection/compositing/target-selection (E1–E4), CLR
zero-handling (D6 code), Level-1 Mineral-Group use (D4 consumer), end-to-end
reproduction of result tables (I1), published default branch (I4 remote), and
the Final Mask visual direction check — all are not-yet-built pipeline stages
(Day 2+) or need a human/remote. They will be covered at R2/R3/R4.

## Net effect on Day 2 plan
- F3 sharpens T2.2 (negatives = below-detection; Au plausibility cap).
- F1 fixed; `make fetch` path is clean for the eventual clean-clone repro (R4).
- No change to the headline or GATE 1 (PASS stands).
