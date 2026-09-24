#!/usr/bin/env python3
"""Local known-truth coverage calibration for the finite-alphabet TV upper side."""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy.stats import beta


PROJECT_ROOT = Path(
    "/efs/workspace/projects/"
    "epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-recognition-certification-grade"
)
SRC_ROOT = PROJECT_ROOT / "src"
COUNTS_PATH = PROJECT_ROOT / "artifacts/_project/data/q1_lower_side_full_n.json"
JSON_PATH = PROJECT_ROOT / "artifacts/coverage_calibration_v2.json"
NOTE_PATH = PROJECT_ROOT / "artifacts/coverage_calibration_v2.md"

ALPHABET_SIZE = 32
ALPHA_UPPER = 0.025
NOMINAL_COVERAGE = 1.0 - ALPHA_UPPER
TV_LEVELS = (0.05, 0.10, 0.20, 0.30, 0.40)
SELECTED_SERVICE_IDS = (49, 10, 50, 6)
REPLICATES = 200
SEED = 20260917
DEPENDENCE_CONCENTRATION = 0.1
DEPENDENCE_BLOCKS = (1, 8, 64)
KNOWN_CONTROL_N = 2791
KNOWN_CONTROL_TV = 0.05
KNOWN_CONTROL_EXPECTED_RADIUS = 0.16311342728653244
CORPUS_PATH = "/efs/workspace/_corpus/CESNET-QUICEXT-25-XS.h5"
CORPUS_SIZE = 3544625537
CORPUS_SHA256 = "6b323c4c53b7c9d0ec9011f895b3c5ba6b35247576e41ef19fe84ab8632810ab"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def cp_interval(successes: int, trials: int) -> list[float]:
    """Exact two-sided 95% Clopper-Pearson interval (alpha/2 per tail)."""
    tail = 0.05 / 2.0
    lower = 0.0 if successes == 0 else float(beta.ppf(tail, successes, trials - successes + 1))
    upper = 1.0 if successes == trials else float(beta.ppf(1.0 - tail, successes + 1, trials - successes))
    return [lower, upper]


def make_distributions(tv: float) -> tuple[np.ndarray, np.ndarray, float]:
    p = np.full(ALPHABET_SIZE, 1.0 / ALPHABET_SIZE, dtype=np.float64)
    delta = tv * ALPHABET_SIZE / (ALPHABET_SIZE - 1)
    q = (1.0 - delta) * p
    q[0] += delta
    direct_tv = float(0.5 * np.abs(p - q).sum())
    return p, q, direct_tv


def draw_iid(n: int, probabilities: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    return rng.choice(ALPHABET_SIZE, size=n, p=probabilities).astype(np.int16, copy=False)


def draw_dependent(
    n: int,
    probabilities: np.ndarray,
    block_size: int,
    concentration: float,
    rng: np.random.Generator,
) -> np.ndarray:
    if block_size < 1 or block_size > n:
        raise ValueError(f"invalid block_size={block_size} for n={n}")
    if block_size == 1:
        return draw_iid(n, probabilities, rng)
    output = np.empty(n, dtype=np.int16)
    position = 0
    parameters = concentration * probabilities
    while position < n:
        stop = min(position + block_size, n)
        theta = rng.dirichlet(parameters)
        output[position:stop] = rng.choice(ALPHABET_SIZE, size=stop - position, p=theta)
        position = stop
    return output


def reference_radius(n_a: int, n_b: int, statcore: Any) -> float:
    zeros_a = np.zeros(n_a, dtype=np.int16)
    zeros_b = np.zeros(n_b, dtype=np.int16)
    result = statcore.tv_upper_bound(
        zeros_a,
        zeros_b,
        alphabet_size=ALPHABET_SIZE,
        alpha=ALPHA_UPPER,
    )
    return float(result.radius_1 + result.radius_2)


def summarize_cell(
    *,
    arm: str,
    tv: float,
    n: int,
    replicates: int,
    rng: np.random.Generator,
    statcore: Any,
    draw_pair: Callable[[np.ndarray, np.ndarray, np.random.Generator], tuple[np.ndarray, np.ndarray]],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    p, q, direct_tv = make_distributions(tv)
    upper_values: list[float] = []
    estimates: list[float] = []
    covered = 0
    cap_hit_count = 0
    for replicate in range(replicates):
        sample_a, sample_b = draw_pair(p, q, rng)
        result = statcore.tv_upper_bound(
            sample_a,
            sample_b,
            alphabet_size=ALPHABET_SIZE,
            alpha=ALPHA_UPPER,
        )
        tv_hat = float(result.tv_hat)
        # Re-apply the cap explicitly after the reference call.
        eps_hi = min(float(result.eps_hi), 1.0)
        if eps_hi + 1e-15 < tv_hat:
            raise AssertionError(
                f"eps_hi < tv_hat at arm={arm} TV={tv} n={n} replicate={replicate}: "
                f"{eps_hi} < {tv_hat}"
            )
        if not 0.0 <= eps_hi <= 1.0:
            raise AssertionError(f"invalid eps_hi={eps_hi}")
        capped = eps_hi >= 1.0 - 1e-15
        cap_hit_count += int(capped)
        estimates.append(tv_hat)
        upper_values.append(eps_hi)
        covered += int(eps_hi >= tv)

    radius = reference_radius(n, n, statcore)
    row = {
        "arm": arm,
        "true_tv": float(tv),
        "direct_true_tv": direct_tv,
        "n": int(n),
        "n_a": int(n),
        "n_b": int(n),
        "replicates": int(replicates),
        "radius": radius,
        "ratio_true_tv_over_radius": float(tv / radius),
        "coverage": float(covered / replicates),
        "covered_replicates": int(covered),
        "coverage_ci95": cp_interval(covered, replicates),
        "coverage_ci_method": (
            "Clopper-Pearson exact, two-sided 95%; total alpha=0.05, "
            "alpha/2=0.025 per tail"
        ),
        "informative": bool(tv / radius > 1.0),
        "capped": bool(cap_hit_count > 0),
        "cap_hit_count": int(cap_hit_count),
        "cap_definition": "at least one replicate returned eps_hi at the explicit <=1 cap",
        "median_tv_hat": float(np.median(np.asarray(estimates))),
        "median_eps_hi": float(np.median(np.asarray(upper_values))),
        "guarantee_scope": (
            "finite-sample finite-alphabet upper certificate under iid sampling"
            if arm == "iid"
            else "empirical dependence stress test; iid certificate assumptions do not apply"
        ),
    }
    if extra:
        row.update(extra)
    return row


def load_selected_counts() -> tuple[dict[str, Any], list[int]]:
    with COUNTS_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    counts = payload["per_service_full_n_counts"]
    selected: list[int] = []
    sources: dict[str, Any] = {}
    for service_id in SELECTED_SERVICE_IDS:
        key = str(service_id)
        if key not in counts:
            raise KeyError(f"selected service {service_id} missing from {COUNTS_PATH}")
        n = int(counts[key]["eligible_n"])
        selected.append(n)
        sources[key] = {
            "eligible_n": n,
            "total_app_rows": int(counts[key]["total_app_rows"]),
        }
    if selected != [2791, 10988, 50953, 107065]:
        raise AssertionError(f"selected n values changed: {selected}")
    return sources, selected


def block_sizes(n: int) -> list[int]:
    return sorted({min(n, max(1, int(value))) for value in DEPENDENCE_BLOCKS})


def evaluate_verdict(iid_rows: list[dict[str, Any]], dependent_rows: list[dict[str, Any]]) -> str:
    informative_iid = [row for row in iid_rows if row["informative"]]
    if not informative_iid:
        return "STILL NOT ESTABLISHED"
    iid_supported = all(row["coverage_ci95"][0] >= NOMINAL_COVERAGE for row in informative_iid)
    if not iid_supported:
        return "STILL NOT ESTABLISHED"
    informative_dependent = [row for row in dependent_rows if row["informative"]]
    dependent_supported = all(
        row["coverage_ci95"][0] >= NOMINAL_COVERAGE for row in informative_dependent
    )
    return "SUPPORTED" if dependent_supported else "PARTIALLY SUPPORTED"


def make_note(payload: dict[str, Any]) -> str:
    iid = payload["iid_arm"]
    dep = payload["dependent_arm"]
    iid_inf = [row for row in iid if row["informative"]]
    iid_trivial = [row for row in iid if not row["informative"]]
    dep_inf = [row for row in dep if row["informative"]]
    dep_trivial = [row for row in dep if not row["informative"]]
    verdict = payload["coverage_verdict"]
    cap_cells = [row for row in iid + dep if row["capped"]]
    lines = [
        "# Coverage Calibration v2",
        "",
        f"- Verdict: **{verdict}**.",
        f"- Upper-side nominal coverage: `{NOMINAL_COVERAGE}`; the upper side is a "
        "finite-sample finite-alphabet certificate only under iid sampling.",
        f"- Replicates per cell: `{REPLICATES}`; coverage intervals are exact two-sided "
        "95% Clopper-Pearson intervals with total alpha=0.05 and alpha/2 per tail.",
        "",
        "## What the calibration shows",
        "",
        f"- Arm 1 has `{len(iid_inf)}` informative cells (ratio > 1) and "
        f"`{len(iid_trivial)}` trivially-guaranteed cells (ratio <= 1).",
        f"- Arm 2 has `{len(dep_inf)}` informative cells and `{len(dep_trivial)}` "
        "trivially-guaranteed cells across the fixed block-size stress ladder.",
        "- Informative means the reported nominal radius is smaller than the known true "
        "TV, so coverage is not guaranteed merely by radius size. Trivially-guaranteed "
        "means the radius alone already reaches or exceeds the true TV.",
        "",
        "## Informative cells",
        "",
        "Arm 1:",
    ]
    if iid_inf:
        lines.extend(
            f"- TV={row['true_tv']:.2f}, n={row['n']}, ratio={row['ratio_true_tv_over_radius']:.6f}, "
            f"coverage={row['coverage']:.3f}, CP CI=[{row['coverage_ci95'][0]:.6f}, "
            f"{row['coverage_ci95'][1]:.6f}]"
            for row in iid_inf
        )
    else:
        lines.append("- None.")
    lines.append("Arm 2:")
    if dep_inf:
        lines.extend(
            f"- TV={row['true_tv']:.2f}, n={row['n']}, B={row['B']}, conc={row['conc']}, "
            f"ratio={row['ratio_true_tv_over_radius']:.6f}, coverage={row['coverage']:.3f}, "
            f"CP CI=[{row['coverage_ci95'][0]:.6f}, {row['coverage_ci95'][1]:.6f}]"
            for row in dep_inf
        )
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The informative Arm 1 cells are the evidence relevant to the iid "
            "finite-sample upper-side claim. The small-n cells are reported separately "
            "because their radius is already at least the known TV.",
            "- Arm 2 is a dependence stress test, not a finite-sample theorem claim. "
            "Coverage degradation there would show sensitivity to dependence rather than "
            "invalidate the iid certificate.",
            f"- Final classification is **{verdict}** because the informative Arm 1 "
            "cells are evaluated against the nominal coverage using their CP lower "
            "interval endpoints, while the dependence arm is reported as an empirical "
            "out-of-scope stress test.",
            "",
            "## Cap",
            "",
            f"- Any cell hit the explicit `eps_hi <= 1` cap: **{'yes' if cap_cells else 'no'}**.",
        ]
    )
    if cap_cells:
        lines.append(
            "- Capped cells: "
            + ", ".join(
                f"{row['arm']}(TV={row['true_tv']},n={row['n']}"
                + (f",B={row['B']}" if "B" in row else "")
                + ")"
                for row in cap_cells
            )
            + "."
        )
    lines.extend(
        [
            "",
            "## Provenance",
            "",
            f"- Runner SHA-256: `{payload['runner']['sha256']}`; seed: `{payload['seed']}`.",
            f"- Effective sample sizes came from `{COUNTS_PATH}` for services "
            f"{', '.join(map(str, SELECTED_SERVICE_IDS))}; the HDF5 corpus was not read "
            "for this calibration.",
            "- Deviations from the earlier calibration: replaced the fixed n ladder with "
            "verified per-service effective n values; expanded the TV sweep through 0.40; "
            "marked informative versus trivially-guaranteed cells; added explicit cap "
            "tracking; added the seed and CP alpha convention; and added the fixed "
            "dependence stress ladder.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    sys.path.insert(0, str(SRC_ROOT))
    from eibo import statcore

    runner_path = Path(__file__).resolve()
    runner_sha = sha256_file(runner_path)
    sources, selected_ns = load_selected_counts()

    # Required control runs before any new cell is generated.
    control_p, control_q, control_direct_tv = make_distributions(KNOWN_CONTROL_TV)
    control = statcore.tv_upper_bound(
        np.zeros(KNOWN_CONTROL_N, dtype=np.int16),
        np.zeros(KNOWN_CONTROL_N, dtype=np.int16),
        alphabet_size=ALPHABET_SIZE,
        alpha=ALPHA_UPPER,
    )
    control_got = float(control.eps_hi)
    control_status = "MATCH" if math.isclose(
        control_got,
        KNOWN_CONTROL_EXPECTED_RADIUS,
        rel_tol=0.0,
        abs_tol=1e-12,
    ) else "MISMATCH"
    print(
        "CONTROL REPRODUCED: TV=0.05, n=2791, expected="
        f"{KNOWN_CONTROL_EXPECTED_RADIUS:.17g}, got={control_got:.17g} => {control_status}",
        flush=True,
    )
    if control_status != "MATCH":
        raise RuntimeError(
            "control mismatch; stopping before new cells: "
            f"expected={KNOWN_CONTROL_EXPECTED_RADIUS!r} got={control_got!r}"
        )

    radii = {str(n): reference_radius(n, n, statcore) for n in selected_ns}
    for n, radius in radii.items():
        print(f"radius n={n}: {radius:.12f}", flush=True)

    rng = np.random.default_rng(SEED)
    failures: list[dict[str, Any]] = []
    iid_rows: list[dict[str, Any]] = []
    dependent_rows: list[dict[str, Any]] = []

    for tv in TV_LEVELS:
        for n in selected_ns:
            try:
                row = summarize_cell(
                    arm="iid",
                    tv=tv,
                    n=n,
                    replicates=REPLICATES,
                    rng=rng,
                    statcore=statcore,
                    draw_pair=lambda p, q, local_rng, size=n: (
                        draw_iid(size, p, local_rng),
                        draw_iid(size, q, local_rng),
                    ),
                )
                iid_rows.append(row)
                print(
                    f"iid TV={tv:.2f} n={n} ratio={row['ratio_true_tv_over_radius']:.4f} "
                    f"coverage={row['coverage']:.3f} capped={row['capped']}",
                    flush=True,
                )
            except Exception as exc:
                failures.append(
                    {
                        "arm": "iid",
                        "true_tv": tv,
                        "n": n,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "traceback": traceback.format_exc(),
                    }
                )
                print(f"FAILED iid TV={tv:.2f} n={n}: {type(exc).__name__}: {exc}", flush=True)

    for tv in TV_LEVELS:
        for n in selected_ns:
            for block_size in block_sizes(n):
                try:
                    row = summarize_cell(
                        arm="dependent",
                        tv=tv,
                        n=n,
                        replicates=REPLICATES,
                        rng=rng,
                        statcore=statcore,
                        draw_pair=lambda p, q, local_rng, size=n, b=block_size: (
                            draw_dependent(
                                size,
                                p,
                                b,
                                DEPENDENCE_CONCENTRATION,
                                local_rng,
                            ),
                            draw_dependent(
                                size,
                                q,
                                b,
                                DEPENDENCE_CONCENTRATION,
                                local_rng,
                            ),
                        ),
                        extra={"B": int(block_size), "conc": DEPENDENCE_CONCENTRATION},
                    )
                    dependent_rows.append(row)
                    print(
                        f"dep TV={tv:.2f} n={n} B={block_size} "
                        f"ratio={row['ratio_true_tv_over_radius']:.4f} "
                        f"coverage={row['coverage']:.3f} capped={row['capped']}",
                        flush=True,
                    )
                except Exception as exc:
                    failures.append(
                        {
                            "arm": "dependent",
                            "true_tv": tv,
                            "n": n,
                            "B": block_size,
                            "conc": DEPENDENCE_CONCENTRATION,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "traceback": traceback.format_exc(),
                        }
                    )
                    print(
                        f"FAILED dep TV={tv:.2f} n={n} B={block_size}: "
                        f"{type(exc).__name__}: {exc}",
                        flush=True,
                    )

    deviations = [
        "Replaced the prior fixed n ladder with verified per-service effective n values.",
        "Expanded the true-TV sweep through 0.40 and selected cells by reference radii.",
        "Added informative/trivially-guaranteed labels and per-cell true-TV/radius ratios.",
        "Added explicit eps_hi cap re-application and per-cell cap tracking.",
        "Added seed, runner hash, CP alpha convention, and exact failed-cell reporting.",
        "Used a fixed B={1,8,64} dependence ladder at concentration 0.1.",
    ]
    payload: dict[str, Any] = {
        "experiment": "coverage_calibration_v2",
        "timestamp_utc": "2026-09-17T17:06:20Z",
        "seed": SEED,
        "method": {
            "upper_call": "eibo.statcore.tv_upper_bound",
            "alphabet_size": ALPHABET_SIZE,
            "alpha_upper": ALPHA_UPPER,
            "nominal_coverage": NOMINAL_COVERAGE,
            "guarantee": (
                "finite-sample finite-alphabet upper certificate under iid sampling; "
                "dependent arm is empirical stress testing only"
            ),
            "coverage_ci": (
                "exact two-sided 95% Clopper-Pearson; total alpha=0.05, "
                "alpha/2=0.025 per tail"
            ),
            "cap_rule": "explicitly re-apply eps_hi=min(returned_eps_hi,1.0) for every replicate",
            "informative_rule": "true_tv / radius > 1",
            "trivial_rule": "true_tv / radius <= 1",
        },
        "control": {
            "cell": {"true_tv": KNOWN_CONTROL_TV, "n_a": KNOWN_CONTROL_N, "n_b": KNOWN_CONTROL_N},
            "expected_eps_hi": KNOWN_CONTROL_EXPECTED_RADIUS,
            "got_eps_hi": control_got,
            "status": control_status,
            "direct_true_tv_from_generator": control_direct_tv,
            "source": "artifacts/coverage_calibration.json known TV=0.05,n=2791 radius",
        },
        "inputs": {
            "effective_n_path": str(COUNTS_PATH),
            "selected_service_ids": list(SELECTED_SERVICE_IDS),
            "selected_services": sources,
            "corpus_path": CORPUS_PATH,
            "corpus_size": CORPUS_SIZE,
            "corpus_sha256_existing_record": CORPUS_SHA256,
            "corpus_read_for_calibration": False,
        },
        "generator": {
            "P": "uniform32",
            "Q": "(1-delta)P+delta*point_mass_at_symbol_0",
            "direct_tv_check": "0.5*sum(abs(P-Q))",
            "tv_levels": list(TV_LEVELS),
        },
        "iid_arm": iid_rows,
        "dependent_arm": dependent_rows,
        "dependence": {
            "structure": "shared-Dirichlet block law, one theta per block then categorical emissions",
            "concentration": DEPENDENCE_CONCENTRATION,
            "block_sizes_by_n": {str(n): block_sizes(n) for n in selected_ns},
        },
        "radii_by_n": radii,
        "failures": failures,
        "coverage_verdict": evaluate_verdict(iid_rows, dependent_rows),
        "verdict_basis": (
            "Informative iid cells require CP lower endpoint >= nominal 0.975. "
            "The dependent arm is reported as an empirical stress test and does not "
            "change the scope of the iid finite-sample theorem."
        ),
        "deviations": deviations,
        "runner": {
            "path": str(runner_path),
            "sha256": runner_sha,
            "interpreter": "python3",
            "gpu_used": False,
            "ssh_used": False,
        },
    }
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_json = JSON_PATH.with_suffix(".json.tmp")
    with tmp_json.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_json, JSON_PATH)

    note = make_note(payload)
    tmp_note = NOTE_PATH.with_suffix(".md.tmp")
    with tmp_note.open("w", encoding="utf-8") as handle:
        handle.write(note)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_note, NOTE_PATH)

    print(
        json.dumps(
            {
                "json": str(JSON_PATH),
                "note": str(NOTE_PATH),
                "runner_sha256": runner_sha,
                "seed": SEED,
                "iid_cells": len(iid_rows),
                "dependent_cells": len(dependent_rows),
                "failures": len(failures),
                "coverage_verdict": payload["coverage_verdict"],
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
