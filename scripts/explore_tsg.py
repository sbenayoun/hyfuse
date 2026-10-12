"""T1.2/T1.3 exploration: read example TSG and scout scalars/classes.

Offline validation against the pytsg example data (no NVCL download).
Prints what loaded, lists scalar column names, searches for likely
Final Mask / mineral-result / error columns, and dumps the `classes`
(mineral code -> label) definitions. Read-only; writes nothing.
"""

from __future__ import annotations

import sys

import pandas as pd
import pytsg

pd.set_option("display.max_columns", 20)
pd.set_option("display.width", 160)


def summarise_spectra(name: str, s) -> None:
    if s is None:
        print(f"\n### {name.upper()}: absent")
        return
    print(f"\n### {name.upper()}")
    print(f"  spectra shape   : {s.spectra.shape}")
    print(f"  wavelength range: {s.wavelength.min():.1f} .. {s.wavelength.max():.1f} nm "
          f"({s.wavelength.shape[0]} bands)")
    print(f"  scalars shape   : {s.scalars.shape}")
    cols = list(s.scalars.columns)
    print(f"  scalar columns ({len(cols)}):")
    for c in cols:
        print(f"    - {c}")

    # Hunt for columns of interest (T1.3).
    low = {c: str(c).lower() for c in cols}
    def match(*keys):
        return [c for c, lc in low.items() if any(k in lc for k in keys)]
    print("  --- candidate columns ---")
    print(f"  final-mask?     : {match('mask', 'final')}")
    print(f"  mineral/result? : {match('min', 'tsa', 'result', 'species', 'group')}")
    print(f"  error/weight?   : {match('err', 'wt', 'weight', 'conf')}")

    # classes = mineral code -> label definitions (candidate code lookup).
    print(f"  classes type    : {type(s.classes).__name__}, len={len(s.classes)}")
    items = s.classes.items() if isinstance(s.classes, dict) else enumerate(s.classes)
    for i, (k, cls) in enumerate(items):
        if i >= 5:
            break
        if isinstance(cls, dict):
            keys = list(cls.keys())
            print(f"    class[{k}] dict keys: {keys}")
            for kk in keys[:1]:
                print(f"       {kk} -> {cls[kk]!r}")
        else:
            print(f"    class[{k}] = {cls!r}")


def main() -> None:
    folder = sys.argv[1] if len(sys.argv) > 1 else "../pytsg/example_data/PE257D"
    print(f"pytsg version: {pytsg.__version__}")
    print(f"reading: {folder}")
    data = pytsg.read_tsg(folder)
    print("\n=== TSG summary ===")
    print(f"available: {data.available}")
    for name in ("nir", "tir", "mir"):
        summarise_spectra(name, getattr(data, name))


if __name__ == "__main__":
    main()
