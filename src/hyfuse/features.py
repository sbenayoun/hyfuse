"""features.py (T1.6, T1.7): tidy depth-aligned Parquet + coverage audit.

T1.6: for each hole in config/holes.yaml, read the TSG package, build the tidy
long table (read.py), and write one Parquet per hole to data/derived/holes/.
Final Mask is recorded as a column (not pre-filtered) so downstream QC and the
corruption tests can exercise masking explicitly; qc.apply_final_mask does the
keep==1 filtering where needed.

T1.7 coverage audit is a separate entry point (coverage.py / make features).
Compositional CLR features (T2.3) are added later.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml

from hyfuse import qc, read

log = logging.getLogger("hyfuse.features")

ROOT = Path(__file__).resolve().parent.parent.parent
RAW_HOLES = ROOT / "data" / "raw" / "holes"
DERIVED_HOLES = ROOT / "data" / "derived" / "holes"
HOLES_YAML = ROOT / "config" / "holes.yaml"


def build_hole(hole_id: str, instrument_gen: str = "unknown") -> Path | None:
    """Read one fetched TSG hole -> tidy Parquet. Returns the Parquet path."""
    folder = RAW_HOLES / hole_id
    if not folder.exists():
        log.error("hole folder missing (fetch first): %s", folder)
        return None
    df = read.read_hole(str(folder), hole_id=hole_id, instrument_gen=instrument_gen)
    if df.empty:
        log.error("no tidy rows produced for %s", hole_id)
        return None

    DERIVED_HOLES.mkdir(parents=True, exist_ok=True)
    out = DERIVED_HOLES / f"{hole_id}.parquet"
    df.to_parquet(out, index=False)

    summ = qc.mask_summary(df)
    metres = qc.metres_after_mask(df)
    log.info("%s: %d rows -> %s | mask=%s | kept_metres=%.1f",
             hole_id, len(df), out.name, summ, metres)
    return out


def _load_holes() -> list[str]:
    if not HOLES_YAML.exists():
        return []
    data = yaml.safe_load(HOLES_YAML.read_text()) or {}
    return list(data.get("holes") or [])


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s",
                        stream=sys.stdout)
    p = argparse.ArgumentParser(description="Build tidy per-hole Parquet (T1.6).")
    p.add_argument("holes", nargs="*", help="hole ids (default: config/holes.yaml)")
    args = p.parse_args(argv)

    holes = args.holes or _load_holes()
    if not holes:
        log.error("no holes given and config/holes.yaml is empty")
        return 2
    ok = 0
    for h in holes:
        if build_hole(h) is not None:
            ok += 1
    log.info("built %d/%d holes", ok, len(holes))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
