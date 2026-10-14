# HyFuse — speaker notes

Spoken notes to accompany `reports/pitch.md`. Written for the presenter (a **data
engineer, not a geoscientist**) — lean into that: it is the reason the project is
built around verification rather than geological intuition. Each slide has a
one-line goal, what to say, and the number(s) to land. Target ~5-6 minutes;
timings in brackets.

**Opening line (before slide 1):**
"Quick context on me — I'm a data engineer, not a geoscientist. So I couldn't
rely on looking at core and judging what's right. I had to build a method that
proves itself. That constraint shaped the whole project."

---

## Slide 1 — The problem  [~45s]

Goal: make the judges feel the problem in one concrete image.

Say:
- "GSWA says combining SWIR and TIR HyLogger results is an unsolved problem — and
  a good solution would be a powerful tool."
- "Here's why it's hard, in one example: a rock that's 97% quartz and 3% chlorite
  reads as **quartz** in the TIR view and as **chlorite** in the SWIR view. Same
  rock, two different stories, because each sensor only sees some minerals."
- (point at the SWIR|TIR side-by-side figure) "This is one real hole, both views.
  Look — silica, feldspars, pyroxenes show up on the TIR side and are simply
  **absent** on the SWIR side. The two instruments literally see different rock.
  That gap is the whole problem."
- "So the question I set out to answer: **does combining the two views actually
  recover geology better than using one view — tested on drillholes the method
  has never seen?**"

Land: "unsolved problem", the 97/3 example, the visible SWIR/TIR gap,
"held-out holes".

---

## Slide 2 — What we built  [~60s]

Goal: show it's a real, end-to-end pipeline, and show the viewer.

Say:
- "I built a reproducible pipeline: it fetches the HyLogger data, applies GSWA's
  own quality rules — the core mask, unit checks, below-detection handling —
  composites everything to 5-metre windows, and turns it into features."
- "Then it compares **four options on identical windows**: SWIR alone, TIR alone,
  a naive mash-up of both, and a proper *view-aware* fusion. And it scores them on
  **held-out holes** — holes left completely out of training."
- (point at screenshot) "This is the viewer — pick a hole, see the mineral
  stacks, the domains the method found, and the geologist's logged boundaries,
  side by side."

Land: "four arms, identical windows, held-out holes." Don't rush the screenshot —
it's your proof it actually runs on real data.

---

## Slide 3 — How we tested it  [~75s] — THIS IS YOUR SLIDE

Goal: this is where "data engineer" pays off. Spend time here.

Say:
- "Because I can't judge the geology by eye, I made the method accountable to data
  instead. Four things:"
- "**One — pre-registration.** I froze what counts as success — the tolerance, the
  scoring, the cross-validation — in version control *before* I ran anything. You
  can check the git timestamps. No moving the goalposts."
- "**Two — honest validation.** Leave-holes-out cross-validation, a random
  baseline to compare against, and uncertainty from resampling *holes*, not data
  points."
- "**Three — tests that try to break it.** A simulation where I know the true
  answer, plus corruption tests — I deliberately scale an assay by a thousand,
  shift depths, ignore the core mask — and the pipeline has to *notice*."
- "**Four — independent review.** Four separate blind reviews of the code and
  stats. And to check the *reviewer*, I planted three bugs on a throwaway branch —
  it caught all three."

Land: "pre-registered, held-out, tests that fail loudly, reviewed — and the review
itself was calibrated." This is the trust story; say it with confidence.

---

## Slide 4 — The result  [~55s] — THE MONEY SLIDE

Goal: deliver the honest answer plainly. Do not dress it up.

Say:
- "Here's the result on 15 gold holes, at our pre-registered 5-metre window. And
  it's **inconclusive** — in a specific, honest way."
- "Fusion scores 0.140 on boundary recovery; the best single view, TIR, scores
  0.139. The difference is **plus 0.001**, and the confidence interval crosses
  zero. So: **fusion is no better than just using TIR.**"
- "And separately — **no** version predicts gold grade on held-out holes."
- "That's a negative result. I'm presenting it exactly as plainly as I'd present
  a positive one — the point of all that rigor was to *trust* whatever came out."

Land: "+0.001, CI crosses zero → no better than one view" and "no gold skill."
Pause. (Then go to 4b.)

---

## Slide 4b — Sensitivity (why we didn't move the goalposts)  [~40s]

Goal: turn "did you try other settings?" into a demonstration of integrity.

Say:
- "A geologist reviewing our work asked: why 5 metres — would finer windows help?
  Good question. So I ran it — as a *declared sensitivity analysis*, with the
  5-metre headline left frozen."
- "At 1 metre, fusion actually *does* beat the single view — the interval excludes
  zero. But at half a metre it flips back to inconclusive."
- "So the honest statement is: **any fusion benefit is not robust — it only shows
  up near 1 metre.** I'm reporting the favourable slice as a sensitivity, not
  promoting it to the headline. Moving the goalposts after seeing the result is
  exactly the kind of thing my planted-flaw test was built to catch."
- "Whether that 1-metre signal is real geology or just finer windows matching
  dense logging — that's the open question I've handed back to the geologist."

Land: "fusion helps at 1 m, but not robust — and we did NOT move the headline."
This is your integrity story made concrete; deliver it with a bit of pride.

---

## Slide 5 — What we checked, and the limits  [~45s]

Goal: pre-empt the obvious challenges; show you know the weaknesses.

Say:
- "Two things I checked so the result is defensible: the domains are **not** just
  tracking a processing-level artifact — I tested for that. And my known-answer
  simulation *agreed* — even there, TIR alone was as good as fusion."
- "The honest limits: it's **15 holes, and 11 are one deposit**. That's a weak test
  of generality — this result is really about one geological setting. The assays
  are biased toward where companies expected mineralisation. And a geoscientist
  hasn't eyeballed the domains yet."

Land: "11 of 15 one deposit — not general" and "a geologist still needs to look."
This is you being honest about scope — judges respect it.

---

## Slide 6 — What GSWA gets, and next steps  [~45s]

Goal: leave them with something usable and a path forward.

Say:
- "What GSWA can take away today: a public, MIT-licensed pipeline that runs from
  two commands and reproduces these exact numbers bit-for-bit — plus the viewer."
- "The method finding: for these holes, a simple TIR view is as good as fusion,
  and mineralogy alone doesn't predict gold across holes."
- "Where I'd go next: more holes across **different** deposits; get a geologist to
  label domains; and specifically test fusion where SWIR and TIR genuinely
  disagree — the chlorite that both views can see is a natural bridge."

Land: "reproducible pipeline you can adopt", "honest method result", "clear next
steps." Close: "Everything's in the repo — thank you."

---

## If asked (Q&A backup — appendix slides)

- **"Did you try finer / different windows?"** "Yes — a geologist asked, so I ran
  a sensitivity sweep. At 1 metre fusion edges ahead; at half a metre it's
  inconclusive again. It's not robust, so I kept the pre-registered 5-metre result
  as the headline and reported the rest as a sensitivity. Native data spacing is
  ~8 mm, so even finer is possible — that's a next step, with a geologist deciding
  whether the 1-metre signal is real."
- **"Why didn't fusion win?"** "On my known-answer simulation, these domains were
  already very separable in TIR, so there was little for the second view to add.
  Whether fusion helps probably depends on finding holes where the two views
  genuinely disagree — that's the next experiment."
- **"What's this CLR/Hellinger thing?"** "A detail: the standard compositional
  transform (CLR) actually destroyed the signal on my known-answer test, so I
  switched to a square-root transform that preserved it. It's documented in the
  repo — an example of the simulation catching a method bug before it hit real
  data."
- **"Isn't a negative result a failure?"** "Not here. GSWA asked whether fusion
  helps; the honest answer on this data is 'not measurably, and here's the
  evidence.' A trustworthy no is more useful than an overstated yes."
- **"You're not a geologist — how do we trust the geology?"** "You shouldn't trust
  *me* on the geology — that's the point. I handed a geologist a short list of
  specific intervals to eyeball, and the README lists exactly which failure modes
  I did and didn't check. The software/stats are verified; the geological call is
  explicitly left to an expert."
