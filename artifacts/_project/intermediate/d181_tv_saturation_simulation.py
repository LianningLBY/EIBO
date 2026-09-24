#!/usr/bin/env python3
"""Known-truth simulation for TV-estimator saturation versus upward bias.

The experiment uses iid samples from the specified P/Q pair.  The plug-in
estimate and Eq. (6) are obtained from the repository reference implementation
(`eibo.statcore.tv_upper_bound`).  Eq. (9) is evaluated from the same returned
plug-in estimate with its m-free radius.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time
import argparse
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(
    "/efs/workspace/projects/"
    "epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-recognition-certification-grade"
)
OUTPUT_PATH = PROJECT_ROOT / "artifacts/d181_tv_saturation_simulation.json"

TRUE_TVS = (0.2, 0.4, 0.6, 0.8)
ALPHABET_SIZES = (32, 1024, 32768, 1048576)
SAMPLE_SIZES = (2791, 20000)
REPLICATES = 1000
ALPHA = 0.025
SEED = 20260922
LARGE_M_THRESHOLD = 32768
MAX_M = max(ALPHABET_SIZES)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def make_truth(true_tv: float, m: int) -> tuple[float, float]:
    """Return the mixture weight and direct TV for the specified construction."""
    delta = true_tv * m / (m - 1)
    direct_tv = delta * (1.0 - 1.0 / m)
    return delta, direct_tv


def draw_pair(
    n: int,
    true_tv: float,
    m: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Draw P=Unif(m), Q=(1-delta)Unif(m)+delta*e_1 without dense arrays."""
    delta, _ = make_truth(true_tv, m)
    sample_a = rng.integers(0, m, size=n, dtype=np.int64)
    special = rng.random(n) < delta
    sample_b = rng.integers(0, m, size=n, dtype=np.int64)
    sample_b[special] = 0
    return sample_a, sample_b


def eq9_upper(tv_hat: float, n_a: int, n_b: int) -> float:
    """Eq. (9), with the same alpha=0.025 per-law convention as Eq. (6)."""
    radius_a = math.sqrt(math.log(2.0 / ALPHA) / (2.0 * n_a))
    radius_b = math.sqrt(math.log(2.0 / ALPHA) / (2.0 * n_b))
    return min(1.0, max(0.0, tv_hat + radius_a + radius_b))


def summarize_cell(
    *,
    true_tv: float,
    m: int,
    n: int,
    rng: np.random.Generator,
    tv_upper_bound,
    cell_index: int,
    total_cells: int,
) -> dict[str, object]:
    estimates: list[float] = []
    eq6_values: list[float] = []
    eq9_values: list[float] = []
    started = time.perf_counter()
    reference_reconciliations: list[dict[str, float]] = []

    for replicate in range(REPLICATES):
        sample_a, sample_b = draw_pair(n, true_tv, m, rng)
        reference = tv_upper_bound(
            sample_a,
            sample_b,
            alphabet_size=m,
            alpha=ALPHA,
        )
        tv_hat = float(reference.tv_hat)
        eps_hi_eq6 = min(1.0, float(reference.eps_hi))
        eps_hi_eq9 = eq9_upper(tv_hat, n, n)

        # The sparse calculation is an independent implementation of the
        # plug-in TV used to confirm the repository reference on real rows.
        if replicate == 0:
            values_a, counts_a = np.unique(sample_a, return_counts=True)
            values_b, counts_b = np.unique(sample_b, return_counts=True)
            common, index_a, index_b = np.intersect1d(
                values_a, values_b, return_indices=True
            )
            overlap = int(np.minimum(counts_a[index_a], counts_b[index_b]).sum())
            sparse_tv_hat = 1.0 - overlap / n
            reference_reconciliations.append(
                {
                    "reference_tv_hat": tv_hat,
                    "sparse_tv_hat": float(sparse_tv_hat),
                    "absolute_difference": abs(tv_hat - sparse_tv_hat),
                    "reference_eps_hi_eq6": eps_hi_eq6,
                }
            )
            if not math.isclose(tv_hat, sparse_tv_hat, rel_tol=0.0, abs_tol=1e-15):
                raise AssertionError(
                    f"plug-in reconciliation failed at true_tv={true_tv}, m={m}, n={n}: "
                    f"reference={tv_hat}, sparse={sparse_tv_hat}"
                )

        estimates.append(tv_hat)
        eq6_values.append(eps_hi_eq6)
        eq9_values.append(eps_hi_eq9)

    elapsed = time.perf_counter() - started
    estimate_array = np.asarray(estimates, dtype=np.float64)
    eq6_array = np.asarray(eq6_values, dtype=np.float64)
    eq9_array = np.asarray(eq9_values, dtype=np.float64)
    mean_tv_hat = float(np.mean(estimate_array))
    median_tv_hat = float(np.median(estimate_array))
    bias = mean_tv_hat - true_tv
    row = {
        "true_tv": float(true_tv),
        "m": int(m),
        "n": int(n),
        "replicates": REPLICATES,
        "delta": make_truth(true_tv, m)[0],
        "direct_true_tv": make_truth(true_tv, m)[1],
        "median_tv_hat": median_tv_hat,
        "mean_tv_hat": mean_tv_hat,
        "bias": float(bias),
        "relative_bias": float(bias / true_tv),
        "median_relative_error": float((median_tv_hat - true_tv) / true_tv),
        "eq6_certify_fraction": float(np.mean(eq6_array < 0.5)),
        "eq9_certify_fraction": float(np.mean(eq9_array < 0.5)),
        "eq6_cap_fraction": float(np.mean(eq6_array >= 1.0 - 1e-15)),
        "eq9_cap_fraction": float(np.mean(eq9_array >= 1.0 - 1e-15)),
        "elapsed_seconds": float(elapsed),
        "reference_implementation": "eibo.statcore.tv_upper_bound",
        "reference_reconciliation": reference_reconciliations,
    }
    print(
        f"CELL {cell_index:02d}/{total_cells}: true_tv={true_tv:.1f} m={m} n={n} "
        f"median={median_tv_hat:.6f} mean={mean_tv_hat:.6f} "
        f"rel_bias={bias / true_tv:.4f} "
        f"eq6={row['eq6_certify_fraction']:.4f} "
        f"eq9={row['eq9_certify_fraction']:.4f} "
        f"elapsed={elapsed:.2f}s",
        flush=True,
    )
    return row


def classify_falsifier(rows: list[dict[str, object]]) -> dict[str, object]:
    max_m_rows = [row for row in rows if row["m"] == MAX_M]
    if not max_m_rows:
        raise AssertionError("no maximum-m rows were produced")
    no_upward_bias = all(
        abs(float(row["median_relative_error"])) <= 0.01 for row in max_m_rows
    )
    large_upward_bias = all(
        float(row["relative_bias"]) > 0.10 for row in max_m_rows
    )
    if no_upward_bias:
        outcome = "NO_UPWARD_BIAS_AT_LARGE_M_TRUE_TV_NEAR_1"
    elif large_upward_bias:
        outcome = "LARGE_UPWARD_BIAS_AT_LARGE_M_SATURATION_NEEDS_BIAS_QUALIFIER"
    else:
        outcome = "MIXED_OR_INCONCLUSIVE_LARGE_M_RESULT"
    return {
        "large_m_threshold": LARGE_M_THRESHOLD,
        "falsifier_max_m": MAX_M,
        "no_upward_bias_condition": (
            "all max-m rows have abs(median_tv_hat - true_tv) / true_tv <= 0.01"
        ),
        "large_upward_bias_condition": (
            "all max-m rows have (mean_tv_hat - true_tv) / true_tv > 0.10"
        ),
        "no_upward_bias_condition_met": no_upward_bias,
        "large_upward_bias_condition_met": large_upward_bias,
        "outcome": outcome,
        "max_m_rows": [
            {
                "true_tv": row["true_tv"],
                "n": row["n"],
                "median_tv_hat": row["median_tv_hat"],
                "mean_tv_hat": row["mean_tv_hat"],
                "median_relative_error": row["median_relative_error"],
                "relative_bias": row["relative_bias"],
            }
            for row in max_m_rows
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pilot",
        action="store_true",
        help="run only the first cell and report the projected full-grid time",
    )
    args = parser.parse_args()
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from eibo.statcore import tv_upper_bound

    total_cells = len(TRUE_TVS) * len(ALPHABET_SIZES) * len(SAMPLE_SIZES)
    rng = np.random.default_rng(SEED)
    rows: list[dict[str, object]] = []
    cell_index = 0
    first_cell_elapsed = None

    for n in SAMPLE_SIZES:
        for true_tv in TRUE_TVS:
            for m in ALPHABET_SIZES:
                cell_index += 1
                row = summarize_cell(
                    true_tv=true_tv,
                    m=m,
                    n=n,
                    rng=rng,
                    tv_upper_bound=tv_upper_bound,
                    cell_index=cell_index,
                    total_cells=total_cells,
                )
                rows.append(row)
                if cell_index == 1:
                    first_cell_elapsed = float(row["elapsed_seconds"])
                    projected = first_cell_elapsed * total_cells
                    print(
                        f"TIMING first_cell_seconds={first_cell_elapsed:.2f} "
                        f"projected_total_seconds={projected:.2f} "
                        f"projected_total_minutes={projected / 60.0:.2f}",
                        flush=True,
                    )
                if args.pilot:
                    print("PILOT complete; full grid not run", flush=True)
                    return

    payload = {
        "experiment": "d181_tv_saturation_simulation",
        "description": (
            "Known-truth iid simulation distinguishing true-TV-near-1 from sparse-sample "
            "upward bias in the plug-in TV estimator."
        ),
        "seed": SEED,
        "replicates": REPLICATES,
        "true_tv_values": list(TRUE_TVS),
        "alphabet_sizes": list(ALPHABET_SIZES),
        "sample_sizes": list(SAMPLE_SIZES),
        "alpha": ALPHA,
        "alpha_convention": "alpha=0.025 per law, as passed to Eq. (6) reference",
        "construction": (
            "P=uniform(m), Q=(1-delta)*uniform(m)+delta*e_1, "
            "delta=true_tv*m/(m-1)"
        ),
        "sampling": "iid draws from P and Q",
        "eq6": (
            "eibo.statcore.tv_upper_bound(sample_a, sample_b, alphabet_size=m, "
            "alpha=0.025); returned eps_hi, explicitly capped at 1"
        ),
        "eq9": (
            "min(1, tv_hat + sqrt(ln(2/alpha)/(2*n_a)) + "
            "sqrt(ln(2/alpha)/(2*n_b)))"
        ),
        "guarantee_scope": (
            "This is a finite-sample iid simulation of estimator behavior; it is not "
            "itself a finite-sample certificate for the synthetic estimates."
        ),
        "timing": {
            "first_cell_seconds": first_cell_elapsed,
            "total_elapsed_seconds": float(sum(float(row["elapsed_seconds"]) for row in rows)),
            "total_elapsed_minutes": float(
                sum(float(row["elapsed_seconds"]) for row in rows) / 60.0
            ),
        },
        "rows": rows,
        "falsifier": classify_falsifier(rows),
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"OUTPUT json={OUTPUT_PATH}", flush=True)
    print(f"SHA256 script={sha256_file(Path(__file__).resolve())}", flush=True)
    print(f"SHA256 json={sha256_file(OUTPUT_PATH)}", flush=True)


if __name__ == "__main__":
    main()
