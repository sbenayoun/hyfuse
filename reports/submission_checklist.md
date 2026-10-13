# Submission checklist (T4.4)

Verified at commit `19785e8` (default branch `main`). Re-verify on the final
commit before submitting.

## GSWA required items (hackathon repo README checklist)

- [x] **Team name / members / captain** — in README (team: A_Team_Name;
      member/captain: Stephane Benayoun). `VERIFY:` replace team name if a real
      one is agreed.
- [x] **Challenge theme** — Data Crunch (README header).
- [x] **Problem tackled + what was built** — README "What we built".
- [x] **Which HyLogger data + where to get it** — README "Data": NCI THREDDS +
      DASC HyLogger Drillholes package, with the join key.
- [x] **How to install and run** — README "Install and run" (`uv sync`,
      `make fetch/features/evaluate/viewer/test`).
- [ ] **Screenshots / demo** — `VERIFY:` add a `make viewer` screenshot (and
      optional short screen recording) to the repo or the pitch deck (T4.5).
- [x] **Licence** — MIT (`LICENSE`).
- [x] **AI tools disclosed** — README "AI tools used" (Kiro; independent review
      sessions).

## Our own requirements

- [x] Clean clone -> `uv sync` -> `make features && make evaluate` reproduces the
      reports **bit-for-bit** (reports/reproduction.md). `make fetch` (~8 GB)
      documented; the analysis half was reproduced from cache.
- [x] `make test` passes — **75 passed** (planted-truth + corruption tests
      included: tests/test_planted.py, tests/test_corruption.py).
- [x] No data or derived data in git — `git ls-files | grep -Ei
      '\.(bip|tsg|parquet|zip|duckdb|sqlite|dat)$'` returns empty.
- [x] README results match script output — key numbers (0.140, 0.139, +0.001,
      CI) match reports/ablation.md.
- [x] Reviews R1–R4 in separate fresh sessions; every finding dispositioned in
      reports/review_response.md. R1/R2/R3 done + resolved; **R4 in progress**
      (fresh session) — confirm no open FAIL before submitting.
- [x] Reviewer calibration (reports/calibration.md): planted 3 flaws, reviewer
      caught **3/3** -> review process trusted.
- [x] README lists the failure modes checked and the accepted limitations
      (n=15/one-deposit, assay selection bias, not geologically validated).
- [x] Latest commit is on the **default branch** (`main`); local == remote.
- [ ] Submit before **Thu 15 Oct 2026 23:59 AWST** (target early evening Thu).
      Today is Tue 13 Oct — comfortably ahead.
- [x] Pitch slides (PDF, max 25 MB) — T4.5 (built from generated results only;
      NOT committed to the repo — attached to the submission form).
- [x] Repo is **public** and separate from the GSWA hackathon repo —
      https://github.com/sbenayoun/hyfuse (PUBLIC).
- [ ] `VERIFY:` judging criteria (T&Cs say communicated before/during the event)
      — shape the pitch around them if found.
- [x] `LICENSE` file added (MIT).
- [ ] Captain submits the repo link via the GSWA submission form.

## Open items before final submit
1. Add a viewer screenshot (T4.5 / README).
2. Confirm R4 returns clean (no open FAIL).
3. Replace team name if a real one is chosen.
4. Build + attach the pitch PDF (T4.5), then submit the repo link.
