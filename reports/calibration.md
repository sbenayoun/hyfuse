# Reviewer calibration (T3.4)

Purpose: test whether the `verify-hyfuse` review process actually catches
planted defects, so we know how much to trust R3/R4. Done once, on a throwaway
`calibration` branch (NEVER merged), per AGENT_INSTRUCTIONS §4A.

## Setup

Three defects were injected on top of the honest result (`main` @ 4f2c1c5),
each as a commit with an innocuous message, then the ablation was regenerated:
- `f275969` "tweak assay CV splitting"  — the leak
- `e70fc4c` "normalise assay units for BBDD0005"  — the ×1000
- `68fab30` "relax boundary tolerance to 4 m and refresh ablation"  — post-hoc

A fresh independent reviewer session ran the `verify-hyfuse` skill at commit
`68fab30`, scope A–J, told nothing about the plants. Full report:
`reports/calibration_review.md`.

## Score: 3 / 3 found, with executed evidence

| Planted flaw | Found? | Evidence quality (ran code?) | Reviewer item |
|---|---|---|---|
| Window-level split (leak) | **YES** | Ran BOTH splitters on cached data: KFold R² +0.27..+0.33 vs GroupKFold −0.76..−1.9; matched the printed ablation.md; found commit f275969. | A1 / F1 (blocker) |
| Assay ×1000 (BBDD0005) | **YES** | Measured BBDD0005 Au median 7.0 / max 1734 vs others 0.016 / 128 (~400×); found commit e70fc4c. | E1 / F2 (blocker) |
| Post-hoc tolerance 2→4 | **YES** | `git log -p config/params.yaml` timeline: pre-reg 00:41 → results 15:41 → tolerance change 15:50; no README reason. | B1 / F3 (blocker) |

False alarms: none. The reviewer verdict was correctly **No-go for submission**.

## Interpretation

The review process is **well-calibrated**: it caught all three planted defects
as blockers, with reproducible executed evidence, and did not raise false
alarms. R3 and R4 can be trusted. No skill-checklist strengthening was required
for the three planted modes (they were all caught).

## Bonus real findings (NOT planted — genuine issues on main to act on)

The reviewer exceeded the planted set and surfaced two legitimate issues that
exist on `main` and should be addressed (tracked for R3 / Day 3-4):

- **F5 (major): confounder control omits `processing_level`.** `ablation.py`
  passes only `instrument_gen`, which is constant across the 15 Level-2 holes
  (degenerate → nothing can flag). Fix: also pass `processing_level` (and state
  explicitly if it is constant across the shortlist so the control cannot run).
- **F7 (major): tests + corruption controls miss these realistic magnitudes.**
  The ×1000 control only fires above the 100000-ppm cap (it tests ×1e6); no test
  asserts the assay CV is grouped; no guard that the scored tolerance equals the
  pre-registered value. Fix: add (a) a test asserting assay CV groups by hole,
  (b) a modest-per-hole-scaling corruption test flagged as an inter-hole outlier,
  (c) a guard tying the scored tolerance to the pre-registered value.

Also noted (F4): the leak *silently removed* the honest "no Au skill" sentence
from the headline — a subtle, correct observation about how one defect hid a
true negative result.

## Disposition

- `calibration` branch to be **deleted, never merged**. `main` (4f2c1c5) is the
  honest result and is untouched.
- Planted modes: all caught → review process trusted for R3/R4.
- Real findings F5, F7 (and the F4 reporting robustness): fix on `main` before
  R3, then let R3 confirm.
