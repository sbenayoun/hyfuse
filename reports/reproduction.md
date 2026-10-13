# Clean-clone reproduction (T4.3) — verified

Addresses R3 finding F2 ("clean-clone reproduction not demonstrated").

## Procedure (what a judge can repeat)

```bash
git clone https://github.com/sbenayoun/hyfuse.git
cd hyfuse
uv sync
# provide the data: either `make fetch` (~8 GB from NCI THREDDS, see README),
# or point data/raw at an existing cache.
make features        # rebuild tidy per-hole Parquet + coverage audit from raw
make evaluate        # four-arm ablation -> reports/ablation.md + confounders.md
make test            # 75 passed
make doctor          # DOCTOR OK
```

## Result (2026-10-13, clone of commit c449c87)

Reproduced in a fresh temp clone of the PUBLIC GitHub repo, env built from
`uv.lock`, data provided from the existing fetch cache (so the ~8 GB download was
not repeated; `make fetch` would do it on a truly cold clone):

- `uv sync`  → OK (Python 3.12.12)
- `make doctor`  → DOCTOR OK
- `make test`  → **75 passed**
- `make features && make evaluate`  → regenerated reports are **BIT-FOR-BIT
  IDENTICAL** to the committed versions:
  - `reports/ablation.md`     IDENTICAL
  - `reports/confounders.md`  IDENTICAL
  - `reports/coverage.md`     IDENTICAL

Deterministic (seed 42 threaded through PCA/HDBSCAN/KMeans/CV/bootstrap/
permutation). Reproducibility ≠ correctness, but the committed numbers are
exactly what the pipeline produces from the raw data.

## Caveat
The cold-clone `make fetch` step (~8 GB sequential download from NCI THREDDS) was
NOT re-run here; only the analysis half (`features`/`evaluate`) was reproduced
from cached raw data. Budget ~15 GB disk and a sequential download for a true
from-scratch run.
