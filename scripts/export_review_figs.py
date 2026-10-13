"""Export standalone per-hole figures for the geologist review packet.

Renders the four holes flagged in reports/geologist_review_packet.md to
self-contained HTML (default) or PNG (--png, needs kaleido) under review_figs/.
These open in any browser with no server and no THREDDS/DASC access — ideal to
email to a geologist alongside reports/geologist_review_packet.md.

Usage:
    uv run python scripts/export_review_figs.py            # HTML, TIR + SWIR
    uv run python scripts/export_review_figs.py --png      # PNG (needs kaleido)
"""

from __future__ import annotations

import argparse
import sys

from hyfuse import viewer_core

# Hole -> WAMEX CollarId for the flagged review intervals (geologist packet).
REVIEW_HOLES = {
    "BCMH0070": 5150256,
    "BBDD0005": 4125327,
    "BBRD0056": 4125322,
    "16CADD001": 3991008,
}
OUT_DIR = "review_figs"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Export per-hole review figures.")
    p.add_argument("--png", action="store_true", help="PNG instead of HTML (needs kaleido)")
    p.add_argument("--views", nargs="+", default=["tir", "swir"],
                   help="views to export (default: tir swir)")
    args = p.parse_args(argv)

    available = set(viewer_core.available_holes())
    written = []
    for hole, collar in REVIEW_HOLES.items():
        if hole not in available:
            print(f"skip {hole}: no derived Parquet (run make fetch/features)")
            continue
        for view in args.views:
            try:
                path = viewer_core.export_hole(hole, OUT_DIR, view=view,
                                               collar_id=collar, as_png=args.png)
                written.append(path)
                print(f"wrote {path}")
            except Exception as exc:  # noqa: BLE001
                print(f"FAILED {hole}/{view}: {exc}", file=sys.stderr)
                if args.png and "kaleido" in str(exc).lower():
                    print("  (PNG needs: uv add kaleido; HTML works without it)",
                          file=sys.stderr)
    print(f"\n{len(written)} figures in {OUT_DIR}/ — "
          "share with reports/geologist_review_packet.md")
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
