#!/usr/bin/env python3
"""Emit Track 5 signed-deviation moments at nested replicate prefixes."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import scipy
import sklearn


PROJECT_ROOT = Path(
    "/efs/workspace/projects/"
    "epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-recognition-certification-grade"
)
HARNESS_PATH = PROJECT_ROOT / "artifacts/_project/intermediate/coverage_calibration_ladder.py"
DIAGNOSIS_PATH = PROJECT_ROOT / "artifacts/_project/intermediate/track5_between_block_diagnosis.py"
SRC_ROOT = PROJECT_ROOT / "src"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts"
JSON_PATH = ARTIFACT_DIR / "track5_skewness_prefixes.json"
MD_PATH = ARTIFACT_DIR / "track5_skewness_prefixes.md"
D_JSON_PATH = ARTIFACT_DIR / "track5_skewness_prefixes_D.json"

ALPHABET_SIZE = 32
ALPHA_UPPER = 0.025
TRUE_TV = 0.4
BLOCK_SIZE = 64
CONCENTRATION = 0.1
N = 60000
OUTER_DRAWS = 5000
SEED = 20260919
INNER_REDRAWS = 32
PREFIXES = (200, 500, 1000, 2000, 3000, 5000)

EXPECTED_SD = {
    200: 0.0169715358,
    500: 0.0167711400,
    1000: 0.0162722914,
    2000: 0.0161860482,
    3000: 0.0159308502,
    5000: 0.0160786624,
}
EXPECTED_SKEWNESS = {
    200: -0.139556,
    500: -0.103819,
    1000: 0.055349,
    2000: 0.036285,
    3000: 0.025623,
    5000: -0.008893,
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def skewness(values: np.ndarray) -> float:
    centered = values - float(np.mean(values))
    m2 = float(np.mean(centered**2))
    m3 = float(np.mean(centered**3))
    return float(m3 / m2**1.5)


def summarize_prefixes(deviations: np.ndarray) -> tuple[dict[str, float], dict[str, float]]:
    sd_values: dict[str, float] = {}
    skew_values: dict[str, float] = {}
    for prefix in PREFIXES:
        values = deviations[:prefix]
        sd_values[str(prefix)] = float(np.std(values, ddof=1))
        skew_values[str(prefix)] = skewness(values)
    return sd_values, skew_values


def compare_expected(
    sd_values: dict[str, float], skew_values: dict[str, float]
) -> dict[str, object]:
    mismatches: list[dict[str, object]] = []
    for prefix in PREFIXES:
        key = str(prefix)
        sd_delta = float(sd_values[key] - EXPECTED_SD[prefix])
        if abs(sd_delta) > 1e-10:
            mismatches.append(
                {
                    "series": "sd",
                    "replicate_count": prefix,
                    "generated": sd_values[key],
                    "expected": EXPECTED_SD[prefix],
                    "delta": sd_delta,
                }
            )
        skew_delta = float(skew_values[key] - EXPECTED_SKEWNESS[prefix])
        if abs(skew_delta) > 5e-7:
            mismatches.append(
                {
                    "series": "skewness",
                    "replicate_count": prefix,
                    "generated": skew_values[key],
                    "expected": EXPECTED_SKEWNESS[prefix],
                    "delta": skew_delta,
                }
            )
    return {
        "sd": not any(item["series"] == "sd" for item in mismatches),
        "skewness": not any(item["series"] == "skewness" for item in mismatches),
        "mismatches": mismatches,
    }


def write_summary(payload: dict[str, object], json_sha256: str) -> None:
    sd_values = payload["sd_by_replicate_count"]
    skew_values = payload["skewness_by_replicate_count"]
    matches = payload["matches_expected"]
    lines = [
        "# Track 5 skewness prefix provenance",
        "",
        "## Pre-registered control",
        "",
        f"- SD control matches expected: `{matches['sd']}`.",
        f"- Skewness control matches expected: `{matches['skewness']}`.",
        "",
        "| Replicates | Generated SD | Expected SD | Generated skewness | Expected skewness |",
        "|---:|---:|---:|---:|---:|",
    ]
    for prefix in PREFIXES:
        key = str(prefix)
        lines.append(
            f"| {prefix} | {sd_values[key]:.10f} | {EXPECTED_SD[prefix]:.10f} | "
            f"{skew_values[key]:+.6f} | {EXPECTED_SKEWNESS[prefix]:+.6f} |"
        )

    lines.extend(
        [
            "",
            "## Mismatches",
            "",
        ]
    )
    if matches["mismatches"]:
        for item in matches["mismatches"]:
            lines.append(
                f"- MISMATCH `{item['series']}` at n={item['replicate_count']}: "
                f"generated `{item['generated']:.12f}`, expected `{item['expected']:.12f}`, "
                f"delta `{item['delta']:+.12f}`."
            )
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Stream",
            "",
            "- One shared `numpy.random.Generator` seeded with `20260919` is used for all 5000 outer replicates.",
            "- Each outer replicate consumes A, B, then 32 inner `rng.multinomial(lengths, theta)` pairs.",
            "- `lengths` is derived from A block slices and the latent `theta` arrays are captured by `TracingRNG`.",
            "- The TV estimate calls `eibo.statcore.tv_upper_bound(a, b, alphabet_size=32, alpha=0.025)`.",
            "",
            "Boundary: this is the modelled block law at this design only, never real traffic.",
            "",
            f"content_sha256: {json_sha256}",
            "",
        ]
    )
    MD_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_deviations(deviations: np.ndarray, lengths: np.ndarray) -> None:
    payload = {
        "design": {
            "n": N,
            "B": BLOCK_SIZE,
            "concentration": CONCENTRATION,
            "true_tv": TRUE_TV,
            "outer_draws": OUTER_DRAWS,
        },
        "environment": {
            "sys_executable": sys.executable,
            "sys_version": sys.version,
            "numpy": {"version": np.__version__, "path": np.__file__},
            "scipy": {"version": scipy.__version__, "path": scipy.__file__},
            "sklearn": {"version": sklearn.__version__, "path": sklearn.__file__},
        },
        "seed": SEED,
        "lengths": lengths.tolist(),
        "lengths_note": "explicit vector, not a prose description",
        "D": deviations.tolist(),
        "provenance": "produced by a single re-run of track5_skewness_prefixes.py after no saved D stream was found",
        "notes": (
            "One-time recovery run using the unchanged registered measurement loop: one shared Generator, "
            "draw A, draw B, then consume 32 inner rng.multinomial(lengths, theta) pairs per outer replicate. "
            "The resulting D array is the producer's own recorded stream; no corpus data or network was used."
        ),
    }
    D_JSON_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    sys.path.insert(0, str(SRC_ROOT))
    from eibo import statcore

    harness = load_module("coverage_calibration_ladder_prefixes", HARNESS_PATH)
    diagnosis = load_module("track5_between_block_diagnosis_prefixes", DIAGNOSIS_PATH)
    p, q = harness.make_truth(TRUE_TV)
    rng = np.random.default_rng(SEED)
    deviations = np.empty(OUTER_DRAWS, dtype=float)
    expected_blocks = (N + BLOCK_SIZE - 1) // BLOCK_SIZE

    for rep in range(OUTER_DRAWS):
        trace_a = diagnosis.TracingRNG(rng)
        a = harness.draw_dependent(N, p, BLOCK_SIZE, CONCENTRATION, trace_a)
        theta_a = np.asarray(trace_a.thetas, dtype=float)
        trace_b = diagnosis.TracingRNG(rng)
        b = harness.draw_dependent(N, q, BLOCK_SIZE, CONCENTRATION, trace_b)
        theta_b = np.asarray(trace_b.thetas, dtype=float)
        if theta_a.shape != (expected_blocks, ALPHABET_SIZE) or theta_b.shape != (expected_blocks, ALPHABET_SIZE):
            raise RuntimeError(f"unexpected theta shapes: {theta_a.shape}, {theta_b.shape}")

        result = statcore.tv_upper_bound(a, b, alphabet_size=ALPHABET_SIZE, alpha=ALPHA_UPPER)
        deviations[rep] = float(result.tv_hat) - TRUE_TV

        blocks = [a[start : start + BLOCK_SIZE] for start in range(0, len(a), BLOCK_SIZE)]
        lengths = np.asarray([len(block) for block in blocks], dtype=np.int64)
        if not np.array_equal(lengths, np.asarray([64] * 937 + [32], dtype=np.int64)):
            raise RuntimeError(f"unexpected block lengths: {lengths.tolist()}")
        for _ in range(INNER_REDRAWS):
            rng.multinomial(lengths, theta_a)
            rng.multinomial(lengths, theta_b)

        if (rep + 1) % 500 == 0:
            print(f"outer_replicates={rep + 1}/{OUTER_DRAWS}", flush=True)

    sd_values, skew_values = summarize_prefixes(deviations)
    lengths = np.asarray([BLOCK_SIZE] * 937 + [N - BLOCK_SIZE * 937], dtype=np.int64)
    matches = compare_expected(sd_values, skew_values)
    print("PRE-REGISTERED CONTROL", flush=True)
    print(json.dumps(matches, indent=2, sort_keys=True), flush=True)
    for item in matches["mismatches"]:
        print(
            f"MISMATCH {item['series']} prefix={item['replicate_count']} "
            f"delta={item['delta']:+.12f}",
            flush=True,
        )

    payload = {
        "design": {
            "n": N,
            "B": BLOCK_SIZE,
            "concentration": CONCENTRATION,
            "true_tv": TRUE_TV,
            "seed": SEED,
            "outer_draws": OUTER_DRAWS,
        },
        "sd_by_replicate_count": sd_values,
        "skewness_by_replicate_count": skew_values,
        "expected_values": {
            "sd_by_replicate_count": {str(k): v for k, v in EXPECTED_SD.items()},
            "skewness_by_replicate_count": {str(k): v for k, v in EXPECTED_SKEWNESS.items()},
        },
        "matches_expected": matches,
        "stream": {
            "method": (
                "single shared-generator pass: draw A, draw B, then consume 32 "
                "inner rng.multinomial(lengths, theta) pairs per outer replicate"
            ),
            "reused_diagnosis_loop": True,
            "inner_redraws_per_outer": INNER_REDRAWS,
            "lengths_construction": (
                "np.asarray([len(x) for x in [a[s:s+64] for s in range(0,len(a),64)]])"
            ),
        },
        "generator_script": "artifacts/_project/intermediate/track5_skewness_prefixes.py",
        "notes": (
            "The six prefix values are computed from the same 5000 D_i stream, with no restart or "
            "alternate seed. Boundary: modelled block law at this design only, never real traffic."
        ),
    }
    JSON_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_deviations(deviations, lengths)
    json_sha256 = sha256_file(JSON_PATH)
    write_summary(payload, json_sha256)
    print(
        json.dumps(
            {
                "json": str(JSON_PATH),
                "md": str(MD_PATH),
                "json_sha256": json_sha256,
                "matches_expected": matches,
            },
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
