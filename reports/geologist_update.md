# HyFuse — update for the geologist (SWIR + TIR fusion)

*GSWA HyLogger Hackathon 2026 · Data Crunch theme. Written for a geologist
advising the project; backed by the current repo state (commit history + reports).*

## What we're testing

Whether a **view-aware fusion** of SWIR and TIR mineral results recovers
geological domains and gold-related assay signal better than SWIR alone, TIR
alone, or a naive concatenation — scored on drillholes the method has not seen.
A negative result is an acceptable outcome; the project is built so the answer is
trustworthy either way.

## Progress so far (verified on real GSWA data)

- Reading the TSG packages (`pytsg`) works: mineral results, mineral groups,
  error/confidence and **Final Mask** all come through. On a real NVCL hole
  (ETG0187) the Final Mask splits core cleanly (1744 keep / 1091 drop per view),
  and the SWIR-vs-TIR complementarity is as expected — SWIR sees
  KAOLIN/WHITE-MICA/CHLORITE, TIR sees SILICA (quartz) / CARBONATE.
- The DASC HyLogger package is characterised: of 2019 holes, **1958 have TIR**
  and **1124 have TIR + assays + logging**. We pinned a **15-hole gold
  shortlist**, mostly the **Bannockburn (BBDD/BBRD)** deposit plus a few regional
  holes for spread.
- Everything is composited to **5 m depth windows** (matching the GSWA gold
  cut-off convention); assays are overlap-weighted into those windows; SWIR and
  TIR are kept as **separate compositions** (never pooled) via a per-view CLR
  transform.
- Domaining (PCA -> clustering -> down-hole change-point segmentation) and
  boundary-agreement scoring against the logged lithology intervals are built and
  tested, with a random-boundary baseline so "it matches the log" is measured
  against chance.

## How we keep ourselves honest

Success criteria were frozen **before** any results were seen; there are
planted-truth and data-corruption tests (the pipeline must visibly react to e.g.
a x1000 assay unit error or an ignored core mask); and the work is independently
reviewed in separate fresh sessions.

## Where your eye would genuinely change what we do

These are assumptions we have made explicit and would rather confirm than guess.

1. **SWIR-active mineral set (drives the planted-truth test).** We assume SWIR
   detects hydroxyl-bearing minerals, carbonates and sulfates (white mica,
   chlorite, kaolinite, carbonate, sulfate), **not** anhydrous silicates, and
   that **chlorite appears in both SWIR and TIR** (our bridge between the views).
   Is that set right, and is chlorite the best bridge mineral? This drives the
   headline 97% quartz / 3% chlorite case.

2. **Assay below-detection.** In the DASC assay table, below-detection values
   appear to be stored as **negatives** (e.g. -0.01, -5000 ppm Au; ~49,500 of
   ~237,000 Au rows). We read a negative as "below |value|" and substitute half
   the detection limit. Correct convention? Is half-limit acceptable?

3. **Gold outliers.** Some `Au_PPM` values reach ~421,000 ppm (~42% Au). We
   **flag** rather than drop these. Plausible high-grade intercepts, or likely
   unit/entry errors to treat differently?

4. **Boundary scoring.** We score agreement with the **boundaries** between
   logged intervals (within a 2 m tolerance), not the lithology codes (which are
   company-specific). Logging density varies a lot (61-281 intervals/hole). Does
   scoring boundaries — rather than harmonising codes or using `GSWARockName` —
   match how you'd judge whether a domain is "right"?

5. **Processing level / instrument.** TIR results on our holes come from a
   classifier variant (`sjCLST`) and SWIR from `sTSAS`; we ignore the TSAV
   results per the data-quality guidance. We also treat instrument generation
   (HyLogger 3 vs 4) as a possible confounder to control for. Anything to flag?

Even a quick reaction to #1 and #2 would unblock the next step (the simulated
known-answer test).

## Status note

No headline result yet — the four-arm comparison (SWIR / TIR / concat / fused)
runs next, on the shortlisted holes. This update reports data plumbing and method
only, deliberately claiming no result until the evaluation is run.
