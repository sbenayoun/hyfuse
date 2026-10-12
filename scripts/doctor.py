"""doctor.py (T1.1, AGENT_INSTRUCTIONS section 2A step 6).

Smoke test: print key library versions, confirm the working directory is not
under /mnt/c, confirm sys.executable is inside the project's .venv (fail
loudly otherwise), and run one duckdb query.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _fail(msg: str) -> None:
    print(f"DOCTOR FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    print(f"python     : {sys.version.split()[0]}")
    print(f"executable : {sys.executable}")
    print(f"prefix     : {sys.prefix}")

    # 1. Must run inside the project's .venv, not a stray system Python.
    #    sys.executable may resolve through a symlink into uv's Python store,
    #    so check sys.prefix (the active environment) against the project .venv.
    project_venv = (Path(__file__).resolve().parent.parent / ".venv").resolve()
    if Path(sys.prefix).resolve() != project_venv:
        _fail(
            f"not running inside the project .venv.\n"
            f"  sys.prefix = {sys.prefix}\n"
            f"  expected   = {project_venv}\n"
            f"  (run via `uv run` / `make`, not a bare python)"
        )

    # 2. Must not be under /mnt/c (WSL2 Windows mount is slow + case-insensitive).
    cwd = Path.cwd().resolve()
    if str(cwd).startswith("/mnt/c"):
        _fail(f"working directory is under /mnt/c: {cwd}")
    print(f"cwd        : {cwd}  (not under /mnt/c: OK)")

    # 3. Key library versions.
    import duckdb
    import pytsg
    import ruptures
    import sklearn

    print(f"duckdb     : {duckdb.__version__}")
    print(f"pytsg      : {getattr(pytsg, '__version__', 'n/a')}")
    print(f"scikit-learn: {sklearn.__version__}")
    print(f"ruptures   : {ruptures.__version__}")

    # 4. One DuckDB query.
    (answer,) = duckdb.sql("select 42").fetchone()
    if answer != 42:
        _fail(f"duckdb returned {answer}, expected 42")
    print("duckdb query: 42  (OK)")

    print("DOCTOR OK")


if __name__ == "__main__":
    main()
