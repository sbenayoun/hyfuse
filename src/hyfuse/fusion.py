"""fusion.py (T3.2): the four ablation arms, each -> a per-window feature matrix.

Arms (all consume per-view mineral-GROUP composition matrices, indexed by
(hole_id, win_from, win_to), one column per group):

  1. swir_only : per-view compositional transform of the SWIR composition.
  2. tir_only  : per-view compositional transform of the TIR composition.
  3. concat    : naive concatenation of RAW swir+tir abundances (straw man;
                 shows whether a fancy fusion is actually needed).
  4. fused     : per-view compositional transform (SEPARATELY per view) then
                 concatenate the transformed blocks. SWIR and TIR are never
                 pooled into one composition.

Transform choice (`transform`): "hellinger" (default) or "clr" (ablation).
The planted-truth study (reports/data_notes.md, reports/planted_truth.md) found
CLR's geometric-mean centring destroys domain signal when many mineral groups
are near-zero; the Hellinger (sqrt) transform preserves it, so it is the default.
It also found naive `concat` is a strong baseline — reported honestly.

All arms are aligned to the SAME windows (inner join on the window index) so the
ablation scores every arm on an identical window/hole set (checklist item C2).
"""

from __future__ import annotations

import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from hyfuse.features import view_features


def align(swir: pd.DataFrame, tir: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Inner-join two per-view frames on the window index (identical windows)."""
    common = swir.index.intersection(tir.index)
    return swir.loc[common], tir.loc[common]


def arm_swir_only(swir_mat: pd.DataFrame, *, transform: str = "hellinger",
                  delta: float = 1e-6) -> pd.DataFrame:
    return view_features(swir_mat, "swir", transform=transform, delta=delta)


def arm_tir_only(tir_mat: pd.DataFrame, *, transform: str = "hellinger",
                 delta: float = 1e-6) -> pd.DataFrame:
    return view_features(tir_mat, "tir", transform=transform, delta=delta)


def arm_concat(swir_mat: pd.DataFrame, tir_mat: pd.DataFrame) -> pd.DataFrame:
    """Naive concatenation of RAW abundances (the straw man)."""
    s, t = align(swir_mat.add_prefix("swir_"), tir_mat.add_prefix("tir_"))
    return pd.concat([s, t], axis=1)


def arm_fused(swir_mat: pd.DataFrame, tir_mat: pd.DataFrame, *,
              transform: str = "hellinger", delta: float = 1e-6,
              pca_components: int | None = None, seed: int = 42) -> pd.DataFrame:
    """Fused: per-view compositional transform (separately), then concatenate.

    SWIR and TIR are transformed independently (never pooled) and only their
    resulting feature blocks are concatenated. Both transforms land on a common
    bounded scale (Hellinger in [0,1]; CLR log-ratio), so no block rescaling is
    applied by default. Optional per-view PCA (pca_components) is available as an
    ablation; None keeps the full transformed features.
    """
    sw = view_features(swir_mat, "swir", transform=transform, delta=delta)
    ti = view_features(tir_mat, "tir", transform=transform, delta=delta)
    sw, ti = align(sw, ti)
    if sw.empty or ti.empty:
        return pd.DataFrame(index=sw.index)
    if pca_components:
        sw = _pca_block(sw, pca_components, seed, "swir")
        ti = _pca_block(ti, pca_components, seed, "tir")
    return pd.concat([sw, ti], axis=1)


def _pca_block(features: pd.DataFrame, n_components: int, seed: int,
               tag: str) -> pd.DataFrame:
    n_comp = max(1, min(n_components, features.shape[1], features.shape[0]))
    xs = StandardScaler().fit_transform(features.to_numpy(dtype=float))
    scores = PCA(n_components=n_comp, random_state=seed).fit_transform(xs)
    return pd.DataFrame(scores, index=features.index,
                        columns=[f"{tag}_pc{i + 1}" for i in range(n_comp)])


def all_arms(swir_mat: pd.DataFrame, tir_mat: pd.DataFrame, *,
             transform: str = "hellinger", delta: float = 1e-6,
             pca_components: int | None = None,
             seed: int = 42) -> dict[str, pd.DataFrame]:
    """Build all four arms aligned to the SAME windows (identical set, item C2)."""
    sw, ti = align(swir_mat, tir_mat)
    return {
        "swir_only": arm_swir_only(sw, transform=transform, delta=delta),
        "tir_only": arm_tir_only(ti, transform=transform, delta=delta),
        "concat": arm_concat(sw, ti),
        "fused": arm_fused(sw, ti, transform=transform, delta=delta,
                           pca_components=pca_components, seed=seed),
    }
