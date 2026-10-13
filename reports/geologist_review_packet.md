# HyFuse — geologist review packet (results round)

*For a GSWA / project geologist. This is the round our software + statistics
review cannot do: judging whether the detected domains are geologically real.
Backed by `reports/ablation.md`. Written for a geologist — the data engineer who
built this explicitly defers the geology to you.*

## The one-line context

We tested whether fusing SWIR + TIR HyLogger mineral results recovers geological
domains better than one view, on 15 gold holes. The statistical answer was
**inconclusive** (fusion ≈ TIR alone; no gold prediction across holes). Before we
trust even that, we need a geologist to sanity-check whether the *domains the
method draws* correspond to real geology — or to something else (e.g. weathering).

## How to read the table

For each hole we report, from the fused arm:
- **detected** = number of domain boundaries the method placed down-hole,
- **logged** = number of logged-lithology interval boundaries (company logging),
- **F1** = agreement of detected vs logged boundaries within a 2 m tolerance,
- **perm p** = how often *random* boundaries match the log at least as well
  (high p ⇒ the detected boundaries are no better than random).

Boundaries are compared at our 5 m window resolution (company logging is finer).

## Intervals to eyeball (pull core photo + logged unit at the detected depths)

| # | Hole | WAMEX CollarId | detected | logged | F1 | perm p | why we picked it |
|---|---|---|---:|---:|---:|---:|---|
| 1 | BCMH0070 | 5150256 | 4 | 33 | 0.216 | 0.332 | a relatively "good" hole |
| 2 | BBDD0005 | 4125327 | 3 | 14 | 0.235 | 0.553 | highest F1, but high p (maybe coincidental) |
| 3 | BBRD0056 | 4125322 | 0 | 12 | 0.000 | 1.000 | a clear miss — the one RC hole |
| 4 | 16CADD001 | 3991008 | 8 | 88 | 0.104 | 0.421 | very fine company logging vs 5 m windows |

### Questions, per interval
1. **BCMH0070** — do the 4 detected domain boundaries land on real lithological
   contacts, or on the weathering / regolith transition near the top of hole?
2. **BBDD0005** — the method's "best" hole, but random boundaries do about as well
   (p 0.55). Are these 3 boundaries geologically meaningful, or coincidental at
   5 m resolution?
3. **BBRD0056** — the method found **no** domains here. This is the only
   reverse-circulation (RC) hole in the set. Is the spectral/mineral signal
   genuinely weaker/degraded in RC vs diamond core — i.e. is a null result
   expected here?
4. **16CADD001** — 88 logged intervals vs ~135 windows. Is 5 m simply too coarse
   to recover this hole's boundaries, or is the method missing real structure?

## The big question (our main untested alternative explanation)

**Do the detected domain boundaries systematically coincide with the
regolith / fresh-rock (weathering) transition rather than with lithological
contacts?** If they do, then what we are calling "geological domains" is partly a
weathering signal, and we need to say so plainly. This is the single most
important thing a software review cannot settle — your read on a few holes would
tell us.

## Two method assumptions we'd like confirmed

1. **Below-detection convention.** In the DASC assay table, below-detection Au
   appears as **negative values** (e.g. −0.01, −5000 ppm; ~49,500 of ~237,000
   rows). We read a negative as "below |value|" and impute half the detection
   limit. Is that the correct convention, and is half-limit acceptable?
2. **TIR processing level as a confounder.** Our 15 holes use two TIR processing
   variants (sjCLST ×13, sTSAT ×2). Our test did **not** flag processing level as
   driving the domains — but with only 2 holes on the minority variant it may be
   under-powered. Does sjCLST vs sTSAT carry geological information we should
   worry about?

## What we are NOT asking you to vouch for

- The statistics / code (independently reviewed four times; see
  `reports/review_R*.md`).
- Any claim of mineralisation — we make none.
We only need your geological eye on: are the domains real, and do they track
lithology or weathering?

## How to pull the data for a hole
- Core photos / logs: via the NVCL hole (THREDDS) and the DASC package, keyed by
  the WAMEX CollarId above (`hylogger_dataset_index` → `wamex_dh_geology`).
- Or ask us for the per-hole viewer screenshot (`make viewer`, select the hole):
  it shows the mineral stacks, detected domains, and logged boundaries together.
