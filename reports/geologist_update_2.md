# HyFuse — geologist update #2 (follow-up to the first note)

*Short follow-up since the first update. One new finding and one question that
would directly shape how we read the upcoming results. Backed by
`reports/planted_truth.md`.*

## What's new since the last note

We ran a **known-answer (planted-truth) test** before touching the real holes:
simulate rocks with KNOWN mineral mixes and KNOWN domain boundaries, apply
SWIR/TIR detectability, and check the method recovers the truth.

Two outcomes worth telling you:

1. **The core SWIR/TIR effect reproduces exactly.** A simulated 97% quartz /
   3% chlorite rock reads **chlorite-dominant in SWIR** (quartz invisible to
   SWIR) and **silica/quartz-dominant in TIR** — the phenomenon the whole
   project is built on.

2. **We changed our compositional transform.** We were going to use the standard
   centred-log-ratio (CLR). On the known-answer data CLR actually **destroyed**
   the domain signal (it over-weights near-absent minerals when most windows
   contain only a few mineral groups). We switched to a square-root (Hellinger)
   transform, which recovers the signal cleanly and handles "not detected in
   this view" zeros naturally. This is a methods detail, flagged for the record.

3. **On our simulated domains, TIR alone was as good as any fusion.** Because we
   happened to design the synthetic domains to be strongly TIR-separable, TIR by
   itself recovered them as well as combining both views, and a naive
   "use both views" did not beat TIR alone. We are **reporting this honestly**
   rather than tuning the simulation to make fusion look good — a negative or
   "fusion doesn't help" result is an acceptable outcome for us.

## The one question that would most help us right now

Our simulated domains being TIR-dominated is an artefact of how we built them —
it tells us nothing about real rocks. So:

> **In real HyLogger holes, do geological domains tend to be separable mainly by
> TIR minerals (quartz/feldspar/silicates), mainly by SWIR minerals
> (white mica / chlorite / clays / carbonates), or genuinely only when both are
> combined? And do domains differ more in mineral RATIOS or in which minerals
> are present at all?**

Your sense of this would tell us whether a combined SWIR+TIR representation
should be *expected* to beat a single view, or whether one view usually
dominates — which is exactly how we'll interpret the real results we're about to
generate.

## What's coming next (for a later, results-based round)

Once the real-hole run is done we'll send a handful of specific intervals (one
the method got right, one wrong, one flagged unusual) with hole, depth, predicted
domain, logged unit, key minerals and the **core-photo reference**, so you can
eyeball whether the detected domains make geological sense. No action needed on
that yet.
