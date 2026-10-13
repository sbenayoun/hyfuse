"""synth.py (T3.1): planted-truth simulation of SWIR/TIR mineralogy.

Purpose: a known-answer test. We simulate rocks with KNOWN true mineral mixes
along depth and KNOWN domain boundaries, then apply VIEW-SPECIFIC detectability
to produce synthetic SWIR and TIR observations. The fusion method must recover
the planted truth at least as well as either single view BEFORE we trust it on
real holes (AGENT_INSTRUCTIONS T3.1).

Model (GSWA geologist guidance + Spectral Regions slide; see params.yaml):
- TIR sees essentially all minerals.
- SWIR sees only the SWIR-active set: hydroxyl-bearing minerals, carbonates and
  sulfates (white mica, chlorite, kaolinite, carbonate, sulfate); NOT anhydrous
  silicates (quartz, feldspar).
- CHLORITE is visible in BOTH views (the bridge mineral).
- A view reports only its detectable minerals, RENORMALISED to sum to 1 within
  that view. This reproduces the GSWA case: 97% quartz / 3% chlorite reads
  quartz-dominant in TIR but chlorite-only (100%) in SWIR.
- Noise, misidentification and occasional aspectral/invalid rows are added.

ASSUMPTION: the SWIR-active set is a first guess (params.swir_active_minerals);
VERIFY against the GSWA SKOS vocabulary / a geologist.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# Mineral universe for the simulation. 'views' lists where each is detectable.
# Anhydrous silicates: TIR only. Hydroxyl/carbonate/sulfate: SWIR (+TIR).
# Chlorite: BOTH (bridge).
DEFAULT_MINERALS: dict[str, dict] = {
    "quartz":     {"views": ("tir",),         "group": "SILICA"},
    "feldspar":   {"views": ("tir",),         "group": "FELDSPAR"},
    "white_mica": {"views": ("swir", "tir"),  "group": "WHITE-MICA"},
    "kaolinite":  {"views": ("swir", "tir"),  "group": "KAOLIN"},
    "chlorite":   {"views": ("swir", "tir"),  "group": "CHLORITE"},   # bridge
    "carbonate":  {"views": ("swir", "tir"),  "group": "CARBONATE"},
    "sulfate":    {"views": ("swir", "tir"),  "group": "SULPHATE"},
}

# SWIR-active minerals = those whose 'views' include 'swir'. (A convenience; the
# authoritative set is params.swir_active_minerals, cross-checked in a test.)
SWIR_ACTIVE = tuple(m for m, meta in DEFAULT_MINERALS.items()
                    if "swir" in meta["views"])


@dataclass
class SynthHole:
    """One simulated hole with planted truth + per-view observations."""

    truth: pd.DataFrame        # window x mineral TRUE fractions (sum 1) + domain
    swir: pd.DataFrame         # window x group SWIR observed (renormalised)
    tir: pd.DataFrame          # window x group TIR observed (renormalised)
    boundaries: list[float]    # true domain boundary depths
    minerals: dict


def _domain_profiles(n_domains: int, minerals: list[str],
                     rng: np.random.Generator) -> np.ndarray:
    """One true composition vector per domain (rows sum to 1).

    Domains differ by mineral RATIOS (the quantity CLR is designed for and the
    way real alteration/lithology varies), not by absolute single-mineral bumps.
    The discriminating ratios are split across views so NEITHER single view
    separates all domains, but combining them does:
      - TIR-only ratio axis: quartz : feldspar  (invisible to SWIR)
      - SWIR ratio axis:      white_mica : kaolinite  (weak/absent in TIR unmix)
    Each domain gets a distinct (log-spaced) level on BOTH axes, plus a modest
    shared background and a little chlorite (the both-views bridge). A domain's
    identity therefore lives in cross-view ratio structure.
    """
    k = len(minerals)
    idx = {m: i for i, m in enumerate(minerals)}
    background = rng.dirichlet(np.ones(k) * 1.5)  # smooth shared background

    # log-spaced multipliers so domains differ MULTIPLICATIVELY (ratios).
    levels = np.exp(np.linspace(-1.0, 1.0, n_domains))  # e.g. 0.37 .. 2.72

    profiles = np.tile(background, (n_domains, 1)).astype(float)
    for d in range(n_domains):
        p = profiles[d].copy()
        # TIR-only ratio axis: vary quartz up / feldspar down (and vice versa).
        if "quartz" in idx and "feldspar" in idx:
            p[idx["quartz"]] *= levels[d]
            p[idx["feldspar"]] /= levels[d]
        # SWIR ratio axis: vary white_mica vs kaolinite in a DIFFERENT order so
        # the two axes are not collinear (a single view can't stand in for both).
        if "white_mica" in idx and "kaolinite" in idx:
            lv = levels[(d + n_domains // 2) % n_domains]
            p[idx["white_mica"]] *= lv
            p[idx["kaolinite"]] /= lv
        if "chlorite" in idx:
            p[idx["chlorite"]] = max(p[idx["chlorite"]], 0.03)  # keep the bridge
        p = np.clip(p, 1e-6, None)
        profiles[d] = p / p.sum()
    return profiles


def simulate_hole(hole_id: str = "SYN", *, n_windows: int = 60,
                  n_domains: int = 4, window_m: float = 5.0,
                  noise: float = 0.03, p_misid: float = 0.02,
                  p_aspectral: float = 0.03,
                  minerals: dict | None = None,
                  seed: int = 42,
                  include_quartz_chlorite_case: bool = True) -> SynthHole:
    """Simulate one hole with planted truth and view-specific observations.

    Returns truth (window x mineral), and swir/tir (window x mineral-group,
    renormalised within each view). Depth windows are contiguous of width
    window_m starting at 0.
    """
    minerals = minerals or DEFAULT_MINERALS
    mnames = list(minerals)
    rng = np.random.default_rng(seed)

    # Assign contiguous domains down-hole with known boundaries.
    bounds_idx = sorted(rng.choice(range(2, n_windows - 2),
                                   size=n_domains - 1, replace=False).tolist())
    domain_of = np.zeros(n_windows, dtype=int)
    cur = 0
    for i in range(n_windows):
        if i in bounds_idx:
            cur += 1
        domain_of[i] = cur
    boundaries = [float(i * window_m) for i in bounds_idx]

    profiles = _domain_profiles(n_domains, mnames, rng)

    # True composition per window = its domain profile + small compositional noise.
    true = profiles[domain_of] + rng.normal(0, noise, size=(n_windows, len(mnames)))
    true = np.clip(true, 1e-6, None)
    true /= true.sum(axis=1, keepdims=True)

    # Plant the GSWA 97% quartz / 3% chlorite window (first window of domain 0).
    if include_quartz_chlorite_case and "quartz" in mnames and "chlorite" in mnames:
        qi, ci = mnames.index("quartz"), mnames.index("chlorite")
        true[0] = 1e-6
        true[0, qi] = 0.97
        true[0, ci] = 0.03
        true[0] /= true[0].sum()

    win_from = np.arange(n_windows) * window_m
    win_to = win_from + window_m
    idx = pd.MultiIndex.from_arrays(
        [[hole_id] * n_windows, win_from, win_to],
        names=["hole_id", "win_from", "win_to"],
    )
    truth = pd.DataFrame(true, index=idx, columns=mnames)
    truth["domain"] = domain_of

    swir = _observe_view(true, mnames, minerals, "swir", rng,
                         noise, p_misid, p_aspectral, idx)
    tir = _observe_view(true, mnames, minerals, "tir", rng,
                        noise, p_misid, p_aspectral, idx)
    return SynthHole(truth=truth, swir=swir, tir=tir,
                     boundaries=boundaries, minerals=minerals)


def _observe_view(true: np.ndarray, mnames: list[str], minerals: dict,
                  view: str, rng: np.random.Generator,
                  noise: float, p_misid: float, p_aspectral: float,
                  idx) -> pd.DataFrame:
    """Produce one view's observed mineral-GROUP composition.

    Keep only minerals detectable in this view, renormalise to sum 1 (this is the
    key SWIR/TIR effect), add noise + occasional misidentification, aggregate to
    mineral groups, and mark some windows aspectral (all-zero composition).
    """
    detect = [j for j, m in enumerate(mnames) if view in minerals[m]["views"]]
    groups = [minerals[m]["group"] for m in mnames]
    n = true.shape[0]

    obs = true[:, detect].copy()
    # Relative (multiplicative) observation noise so true-zero minerals stay
    # near zero (additive noise on near-zeros would, after renormalisation,
    # invent minerals that are not there — e.g. breaking the planted 97/3 case).
    obs = obs * (1.0 + rng.normal(0, noise, size=obs.shape))
    obs = np.clip(obs, 0.0, None)
    # a tiny detection floor only where the mineral is genuinely present
    present = true[:, detect] > 1e-4
    obs = np.where(present & (obs <= 0), 1e-9, obs)
    # renormalise within the view's detectable minerals
    sums = obs.sum(axis=1, keepdims=True)
    obs = np.where(sums > 0, obs / sums, 0.0)

    # occasional misidentification: swap two detectable columns in a few rows
    if len(detect) >= 2:
        mis = rng.random(n) < p_misid
        for i in np.where(mis)[0]:
            a, b = rng.choice(len(detect), size=2, replace=False)
            obs[i, [a, b]] = obs[i, [b, a]]

    # aggregate detectable minerals -> their groups
    det_groups = [groups[j] for j in detect]
    df = pd.DataFrame(obs, index=idx, columns=det_groups)
    df = df.T.groupby(level=0).sum().T  # sum minerals sharing a group

    # occasional aspectral windows -> all-zero row (explicit "no result")
    asp = rng.random(n) < p_aspectral
    df.loc[asp, :] = 0.0
    return df
