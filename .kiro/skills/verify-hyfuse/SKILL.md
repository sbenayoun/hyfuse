---
name: verify-hyfuse
description: Independent, adversarial verification of the HyFuse project (GSWA HyLogger SWIR/TIR fusion ablation, domaining, assay comparison). Use whenever the user asks to review, verify, referee, audit, sanity-check, stress-test or "red-team" results, an ablation table, README claims, or the repo before submission. Also use when a result looks surprisingly good, when a pipeline stage was just finished, or before the final commit, even if the user does not say "skill" or "verify".
---

# verify-hyfuse — adversarial verification for the HyFuse hackathon project

## Why this skill exists

This project is built by one person, with an AI agent writing much of the code. That creates three specific risks, and this skill is the cheap countermeasure to each:

1. **Shared blind spots.** The agent that wrote the pipeline tends to review it the same way it wrote it. A reviewer in a *fresh context*, given only the repo and results, notices different things.
2. **Agreeableness.** Language models drift toward telling you what you hope to hear. This skill forces every finding to carry executed evidence, so "looks fine" is not an allowed answer.
3. **Failure modes that are specific to this data.** HyLogger work has well-known traps: SWIR and TIR are not commensurate views, processing level can masquerade as geology, assays are unchecked company data concentrated in prospective intervals, and held-out validation is easy to get subtly wrong. A generic reviewer misses these; this checklist names them.

What you get in return: a short, evidence-backed list of problems to fix before judging, a calibrated sense of how far to trust the review (see the planted-flaw test), and a README whose claims you can defend if a GSWA geologist or judge pushes back. It will not prove the geology is right — that needs held-out data, independent assays and expert eyes.

## Ground rules

- **Fresh context.** Do not rely on memory of how the code was written. Read the repo as a stranger would.
- **Read-only on results.** Do not edit result tables, parameters, or reports to make them pass. You may write only `reports/review.md` and, in calibration mode, a separate `calibration` branch.
- **Evidence or it did not happen.** Each finding must include the command you ran and the relevant output, or a file path and line. If you could not run something, label it `UNVERIFIED`, never "fine".
- **No reassurance without a check.** Silence is not a pass. For every checklist item write one of: `PASS (evidence)`, `FAIL (evidence)`, `UNVERIFIED (why)`.
- **Iterate until clean.** After the author fixes findings, rerun the affected checks. Stop only when no open `FAIL` remains, or the remaining ones are explicitly accepted as limitations in the README.
- **Stay in your lane.** You are not a geologist. For plausibility questions, produce the evidence and ask a human expert; do not issue geological verdicts.

## Scope

The prompt may name a scope (for example "items D, E, I" for the end-of-Day-1 checkpoint, or "A–F" for Day 2). Review only those items and say so at the top of `reports/review.md`. If no scope is given, review all items A–J. The project's `AGENT_INSTRUCTIONS.md` (Section 4A) defines the checkpoints R1–R4 and the commit hash to review.

## Inputs to read first

`README.md`, `config/params.yaml`, `reports/*.md` (especially `ablation.md`, `coverage.md`, `confounders.md`), `src/hyfuse/`, `tests/`, `sql/`, and `git log --stat` for `config/params.yaml`.

## Checklist

### A. Leakage between training and test
- Splits are grouped by `hole_id` (and by location group if used). Search the code for `KFold`, `train_test_split`, `cross_val_*`; a window-level random split is a **blocker**.
- Every fitted step (CLR zero handling constants, scalers, PCA, HDBSCAN settings, ridge/PLS, any assay-anchored calibration) is fitted on training folds only. Look for `fit` / `fit_transform` called before the split.
- No test-hole information in feature construction (e.g. global normalisation across all holes, global PCA before CV).
- Hyperparameters are not tuned on the evaluation folds.

### B. Pre-registration
- `git log -p config/params.yaml` shows depth tolerance, metric, splits, assay targets and arm definitions were committed **before** the first results file. Any change afterward needs a written reason in the README.

### C. Confounders
- Domains/clusters are tested for predictability of `processing_level` and `instrument_gen` (grouped by hole). If they predict these well, the claim "geological domains" is **not supported** without further controls.
- All four arms (SWIR, TIR, concat, fused) are scored on the **identical** set of windows and holes. Different coverage between SWIR and TIR is a hidden advantage.
- Alternative explanations are listed and addressed: depth/weathering profile, hole identity, drilling era, logging style.

### D. Data handling rules from GSWA
- Final Mask applied; non-core rows excluded (check the row counts before/after).
- `invalid` and `aspectral` kept as explicit states, not silently dropped or turned into zero abundance.
- TSAV results ignored. Level 1 data use Mineral Group, not individual minerals.
- Wt1 = 1.0 not filtered out as a placeholder; `error` used as the confidence measure.
- SWIR and TIR abundances are never pooled into one composition; zeros are treated as "not detectable here" with the chosen handling documented.

### E. Assays
- Units normalised; ×1000 (ppm vs %) and other implausible values flagged. Run the project's own checks and a few spot queries.
- Below-detection handling documented.
- Compositing to windows weights overlapping intervals by overlap length (test exists).
- Assay targets were chosen before results (see B). The README states the **selection bias**: assays concentrate where companies sampled, often prospective intervals.

### F. Baselines and negative controls
- Permutation baseline for boundary agreement exists and is reported next to the result.
- Negative controls actually collapse to chance: shuffled labels, depth shuffled within hole, swapped views, random features. Run at least two. If a negative control "works", something leaks.
- The naive concatenation arm exists, so "fusion helps" is compared to the obvious alternative, not only to single views.

### G. Statistics
- Uncertainty is computed by bootstrapping **holes**, not windows.
- Number of holes in each comparison is stated. Under about 8 holes with the needed labels, conclusions must be marked inconclusive.
- Count the comparisons made (arms × metrics × targets). Flag headline claims that rely on the single best of many.
- Differences are compared with fold-to-fold variation, not just point estimates.

### H. Claims versus evidence
- Every quantitative sentence in the README traces to a generated file; list any that do not.
- Language is bounded: anomalies are "evidence worth investigating", not mineralisation; no claim of generality beyond the holes tested.
- Negative or inconclusive results are reported as plainly as positive ones.

### I. Reproducibility and rules
- Clean clone → `uv sync` → `make fetch` → `make evaluate` reproduces the tables (or document precisely where it fails).
- Seeds fixed; versions locked.
- No data in git: `git ls-files | grep -Ei '\.(bip|tsg|parquet|zip|duckdb|sqlite)$'` must return nothing. Check `.gitignore`.
- README names the packages used and where to download the data. Latest commit is on the default branch.

### J. Plausibility checks to hand to a human
- Pick up to five intervals (include one the method got right, one wrong, one flagged unusual). For each, write the hole, depth range, predicted domain, logged unit, key minerals, and the core photo path, so a person can eyeball them.
- Note whether detected boundaries coincide with obvious regolith/weathering transitions; if so, this is an alternative explanation to state.

## Planted-flaw calibration (do once, about an hour)

Purpose: learn whether this review process actually catches problems, instead of assuming it does.

1. Create a branch `calibration` (never merge it).
2. Inject three flaws without telling the reviewer:
   - **Leak:** replace grouped CV with a window-level random split in one arm.
   - **Units:** multiply one hole's assays by 1000.
   - **Post-hoc change:** change the depth tolerance in `params.yaml` in a commit made *after* the results file.
3. Run this skill in a fresh context on the `calibration` branch.
4. Score: found / missed for each flaw, plus any false alarms.

| Planted flaw | Found? | Evidence quality (ran code?) | Note |
|---|---|---|---|
| Window-level split | | | |
| Assay ×1000 | | | |
| Post-hoc tolerance | | | |

Interpretation: if it finds all three with executed evidence, trust it for the final pass. If it misses one, strengthen the matching checklist item and rerun. Then run it on the **clean** branch: every finding must reproduce when you check it yourself. Unreproducible findings count against the reviewer.

## Output: `reports/review.md`

```
# Review of HyFuse — <date>, commit <hash>

## Verdict
Go / Go with fixes / No-go for submission, with one-paragraph reason.

## Checklist results
A1 PASS (evidence) ... (one line per item; UNVERIFIED items explained)

## Findings
### F1 [blocker|major|minor] <title>
- Where: <file:line or command>
- Evidence: <command + output>
- Why it matters: <one sentence>
- Suggested fix: <one sentence>

## What I could not verify
<list>

## Questions for a human expert
<list from section J>
```

## Limits

This is a software and statistics review. It cannot confirm the geology, validate company assays, or replace a GSWA expert. A review with no findings is not proof that none exist. Present the results as "checked for these failure modes" and list those modes in the README.
