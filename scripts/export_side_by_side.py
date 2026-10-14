"""Export SWIR|TIR side-by-side figures for the README / pitch deck.

Renders a two-panel (SWIR vs TIR) depth log per hero hole, with detected domain
boundaries (red) and logged lithology boundaries (grey), to standalone HTML
(default) or PNG (--png, needs kaleido). Written to docs/ so they can be
committed and shown in the README / slides.

Usage:
    uv run python scripts/export_side_by_side.py           # HTML -> docs/
    uv run python scripts/export_side_by_side.py --png     # PNG (needs kaleido)
"""

from __future__ import annotations

import argparse
import sys

from hyfuse import viewer_core

# Hero holes for the deck + their WAMEX CollarId (for logged-boundary overlay).
HERO = {
    "16CADD001": 3991008,   # longest hole (1246 m) — the money shot
    "BCMH0070": 5150256,    # a "good" case (F1 0.216)
}
OUT_DIR = "docs"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Export SWIR|TIR side-by-side figures.")
    p.add_argument("--png", action="store_true", help="PNG instead of HTML (needs kaleido)")
    args = p.parse_args(argv)

    available = set(viewer_core.available_holes())
    written = []
    for hole, collar in HERO.items():
        if hole not in available:
            print(f"skip {hole}: no derived Parquet (run make fetch/features)")
            continue
        try:
            path = viewer_core.export_side_by_side(hole, OUT_DIR, collar_id=collar,
                                                   as_png=args.png)
            written.append(path)
            print(f"wrote {path}")
        except Exception as exc:  # noqa: BLE001
            print(f"FAILED {hole}: {exc}", file=sys.stderr)
            if args.png and "kaleido" in str(exc).lower():
                print("  (PNG needs: uv add kaleido; HTML works without it)",
                      file=sys.stderr)
    print(f"\n{len(written)} figures in {OUT_DIR}/")
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
