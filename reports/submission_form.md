# Submission-form text (draft)

Paste the relevant piece into each field of the GSWA submission form
(github.com/Geological-Survey-of-Western-Australia/gswa-hackathon-2026, "New
issue" → submission template). `VERIFY:` field names against the live form — this
maps to the fields documented in PROJECT_BRIEF. Keep every number consistent with
`reports/ablation.md`.

---

## Team name
HyFuse Team

## Team members
Stephane Benayoun

## Team captain
Stephane Benayoun

## Challenge theme
Data Crunch

## Repository link
https://github.com/sbenayoun/hyfuse

## Project title
HyFuse — view-aware fusion of SWIR + TIR HyLogger mineralogy

## Short description (1–2 sentences)
HyFuse tests whether combining SWIR and TIR HyLogger mineral results recovers
geological domains and gold-assay-related properties better than either view
alone, on held-out drillholes. On 15 gold holes the answer is inconclusive —
fusion is no better than the best single view — and the contribution is a
rigorous, reproducible, independently-reviewed pipeline that produces a
trustworthy answer either way.

## What problem did you tackle, and what did you build?
GSWA notes that combining SWIR and TIR HyLogger results is an unsolved problem:
the two sensors detect different minerals, so a rock that is 97% quartz / 3%
chlorite reads quartz-dominant in TIR but chlorite-only in SWIR. We asked whether
a view-aware fusion of the two beats a single view at recovering geology.

We built a reproducible pipeline + interactive viewer that: fetches per-hole TSG
packages (NCI THREDDS); applies GSWA data-quality rules (Final Mask, unit and
below-detection checks, Mineral Group); composites to 5 m windows and
overlap-weights logged lithology and assays (DuckDB); and compares four arms on
identical windows — SWIR only, TIR only, naive concatenation, and a view-aware
fused representation — scoring each on HELD-OUT holes by boundary agreement vs
logged lithology (with a permutation baseline) and gold prediction (leave-
holes-out CV), with hole-level bootstrap uncertainty and a processing-level
confounder check.

## Result
Inconclusive, reported honestly. On 15 gold holes, fused boundary-recovery F1 is
0.140 vs 0.139 for the best single view (TIR); the hole-level bootstrap delta is
+0.001 with a 95% CI of [-0.017, +0.022] (includes zero) — no reliable
difference. No arm predicts gold grade on held-out holes (all median R² ≤ 0).
Detected domains are not explained by processing level. Key limitation: n = 15
and 11/15 are one deposit (Bannockburn), so this is a weak generality test. All
numbers reproduce bit-for-bit from a clean clone (`make fetch` → `make evaluate`).

## Which HyLogger data did you use, and where is it?
- TSG packages: NCI THREDDS WA catalogue
  (https://thredds.nci.org.au/thredds/catalog/rs07/WA/catalog.html).
- Collar / survey / logged lithology / assays: GSWA DASC "HyLogger Drillholes
  package" (interim, GDA2020; https://dasc.dmirs.wa.gov.au/).
- 15 gold holes, pinned in `config/holes.yaml`. No HyLogger data is committed to
  the repo (only small summary tables/figures under `reports/`).

## How to install and run
`uv sync`, then `make fetch` (downloads the TSG packages, ~8 GB, not in git),
`make features`, `make evaluate` (produces reports/ablation.md), `make viewer`
(Streamlit app), `make test` (75 tests). Full details in the README.

## Were AI tools used? (disclosure)
Yes. Development was assisted by Kiro (an agentic CLI). The independent
verification steps (four code/stats reviews and a planted-flaw calibration) were
run as separate fresh agent sessions to check the build. Disclosed per the
hackathon rules; see the README "AI tools used" section.

## Licence
MIT (see LICENSE).

---

### Attachments / reminders for the captain
- Attach the pitch slides as a PDF (max 25 MB) — build from `reports/pitch.md`
  (content) + `reports/pitch_notes.md` (what to say) + `docs/viewer.png`.
- Submit before Thu 15 Oct 2026, 23:59 AWST; the repo must be public and on the
  default branch (`main`) — both already true.
- Pitch in person Fri 16 Oct.
