"""fetch.py (T1.4): sequential, cached NVCL/THREDDS downloads.

Downloads per-hole TSG packages from the NCI THREDDS WA catalogue.

Design (per AGENT_INSTRUCTIONS.md T1.4 + hard rules):
- Sequential requests only (be polite to NVCL/NCI).
- Exponential backoff on 5xx / network errors (tenacity).
- On-disk cache keyed by hole id; re-running is a no-op for cached holes.
- A --max-holes guard so a stray run cannot bulk-download.
- Logs to logs/fetch.log.
- Extracts only the TSG files (.tsg/.bip, incl. tir/mir) + optional hires;
  skips the big raw cras imagery unless --with-cras is given, to save disk.

THREDDS download URL pattern (verified against the WA catalogue):
    https://thredds.nci.org.au/thredds/fileServer/rs07/WA/<HOLE>.zip
The catalogue index page uses `catalog.html?dataset=rs07/<HOLE>.zip`.
"""

from __future__ import annotations

import argparse
import logging
import sys
import zipfile
from pathlib import Path

import httpx
import yaml
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

THREDDS_FILESERVER = "https://thredds.nci.org.au/thredds/fileServer/rs07/WA"

# Project paths (…/hyfuse/).
ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = ROOT / "data" / "raw" / "holes"
CACHE_DIR = ROOT / "cache" / "zips"
LOG_DIR = ROOT / "logs"
HOLES_YAML = ROOT / "config" / "holes.yaml"

# File suffixes that make up the small, useful TSG package (skip raw cras).
# pytsg.read_tsg needs the .tsg headers + .bip spectra; the .tsg header
# references .cal/.ini sidecars, so keep those too. Skip the big _tsg_cras.bip
# imagery and per-tray .jpg photos unless explicitly requested.
TSG_KEEP_SUFFIXES = (
    "_tsg.tsg", "_tsg.bip", "_tsg.cal", "_tsg.ini", "_tsg_1.ini",
    "_tsg_tir.tsg", "_tsg_tir.bip",
    "_tsg_mir.tsg", "_tsg_mir.bip",
    "_tsg_hires.dat",
)
RETRY_STATUS = {500, 502, 503, 504}


log = logging.getLogger("hyfuse.fetch")


def _setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_DIR / "fetch.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )


class RetryableHTTP(Exception):
    """Raised on a retryable HTTP status so tenacity backs off."""


@retry(
    retry=retry_if_exception_type((RetryableHTTP, httpx.TransportError)),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _download(url: str, dest: Path) -> None:
    """Stream a URL to dest, retrying on 5xx / transport errors."""
    tmp = dest.with_suffix(dest.suffix + ".part")
    with httpx.stream("GET", url, timeout=60.0, follow_redirects=True) as r:
        if r.status_code in RETRY_STATUS:
            raise RetryableHTTP(f"{r.status_code} for {url}")
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_bytes(chunk_size=1 << 16):
                f.write(chunk)
    tmp.replace(dest)


def _extract_tsg(zip_path: Path, out_dir: Path, with_cras: bool) -> list[str]:
    """Extract only the TSG package files (skip raw cras unless requested)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[str] = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            low = name.lower()
            keep = low.endswith(TSG_KEEP_SUFFIXES)
            if with_cras and low.endswith("_tsg_cras.bip"):
                keep = True
            if not keep:
                continue
            # Zip entries may use Windows backslash separators; normalise
            # before taking the basename so files flatten correctly on Linux.
            basename = name.replace("\\", "/").rsplit("/", 1)[-1]
            target = out_dir / basename
            with zf.open(name) as src, target.open("wb") as dst:
                dst.write(src.read())
            extracted.append(target.name)
    return extracted


def fetch_hole(hole: str, *, with_cras: bool = False, force: bool = False) -> Path:
    """Fetch and extract one hole. Returns the per-hole output dir.

    Cached: if the output dir already has TSG files and not `force`, skip.
    """
    out_dir = RAW_DIR / hole
    if not force and out_dir.exists() and any(out_dir.glob("*_tsg*.tsg")):
        log.info("cache hit: %s (skipping)", hole)
        return out_dir

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = CACHE_DIR / f"{hole}.zip"
    url = f"{THREDDS_FILESERVER}/{hole}.zip"

    if not zip_path.exists() or force:
        log.info("downloading %s -> %s", url, zip_path)
        _download(url, zip_path)
        log.info("downloaded %s (%.1f MB)", hole, zip_path.stat().st_size / 1e6)
    else:
        log.info("zip cache hit: %s", zip_path.name)

    names = _extract_tsg(zip_path, out_dir, with_cras)
    log.info("extracted %d TSG files for %s: %s", len(names), hole, names)
    if not names:
        log.warning("no TSG files found in %s; package layout may differ", hole)
    return out_dir


def _load_holes() -> list[str]:
    if not HOLES_YAML.exists():
        return []
    data = yaml.safe_load(HOLES_YAML.read_text()) or {}
    return list(data.get("holes") or [])


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    p = argparse.ArgumentParser(description="Fetch TSG packages from NCI THREDDS.")
    p.add_argument("holes", nargs="*", help="hole ids (default: config/holes.yaml)")
    p.add_argument("--max-holes", type=int, default=5,
                   help="hard guard against bulk download (default 5)")
    p.add_argument("--with-cras", action="store_true",
                   help="also extract the large raw cras imagery")
    p.add_argument("--force", action="store_true", help="ignore cache")
    args = p.parse_args(argv)

    holes = args.holes or _load_holes()
    if not holes:
        log.error("no holes given and config/holes.yaml is empty")
        return 2
    if len(holes) > args.max_holes:
        log.error("refusing: %d holes > --max-holes=%d (raise it deliberately)",
                  len(holes), args.max_holes)
        return 2

    for hole in holes:
        try:
            fetch_hole(hole, with_cras=args.with_cras, force=args.force)
        except Exception as exc:  # noqa: BLE001 - log and continue to next hole
            log.error("FAILED %s: %s", hole, exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
