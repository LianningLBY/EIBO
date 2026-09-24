#!/usr/bin/env python3
"""Track 5 signed-deviation skewness measurement on the diagnosis RNG stream."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(
    "/efs/workspace/projects/"
    "epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-recognition-certification-grade"
)
HARNESS_PATH = PROJECT_ROOT / "artifacts/_project/intermediate/coverage_calibration_ladder.py"
DIAGNOSIS_PATH = PROJECT_ROOT / "artifacts/_project/intermediate/track5_between_block_diagnosis.py"
SRC_ROOT = PROJECT_ROOT / "src"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts"
JSON_PATH = ARTIFACT_DIR / "track5_skewness_n5000.json"
MD_PATH = ARTIFACT_DIR / "track5_skewness_n5000.md"

ALPHABET_SIZE = 32
ALPHA_UPPER = 0.025
TRUE_TV = 0.4
BLOCK_SIZE = 64
CONCENTRATION = 0.1
N = 60000
OUTER_DRAWS = 5000
SEED = 20260919
BOOTSTRAP_SEED = 20260920
BOOTSTRAP_RESAMPLES = 20000
WITHIN_REDRAWS = 32
SD_CONTROL_EXPECTED = 0.0169715358


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


def bootstrap_ci(values: np.ndarray) -> list[float]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    boot = np.empty(BOOTSTRAP_RESAMPLES, dtype=float)
    batch_size = 100
    for start in range(0, BOOTSTRAP_RESAMPLES, batch_size):
        stop = min(start + batch_size, BOOTSTRAP_RESAMPLES)
        indices = rng.integers(0, len(values), size=(stop - start, len(values)))
        samples = values[indices]
        means = samples.mean(axis=1)
        centered = samples - means[:, None]
        m2 = np.mean(centered**2, axis=1)
        m3 = np.mean(centered**3, axis=1)
        boot[start:stop] = m3 / np.power(m2, 1.5)
    return [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))]


def main() -> None:
    sys.path.insert(0, str(SRC_ROOT))
    from eibo import statcore

    harness = load_module("coverage_calibration_ladder", HARNESS_PATH)
    diagnosis = load_module("track5_between_block_diagnosis", DIAGNOSIS_PATH)
    p, q = harness.make_truth(TRUE_TV)
    rng = np.random.default_rng(SEED)
    deviations = np.empty(OUTER_DRAWS, dtype=float)
    expected_blocks = (N + BLOCK_SIZE - 1) // BLOCK_SIZE

    for rep in range(OUTER_DRAWS):
        # Exact diagnosis-of-record outer draw order.
        trace_a = diagnosis.TracingRNG(rng)
        a = harness.draw_dependent(N, p, BLOCK_SIZE, CONCENTRATION, trace_a)
        theta_a = np.asarray(trace_a.thetas)
        trace_b = diagnosis.TracingRNG(rng)
        b = harness.draw_dependent(N, q, BLOCK_SIZE, CONCENTRATION, trace_b)
        theta_b = np.asarray(trace_b.thetas)
        if theta_a.shape != (expected_blocks, ALPHABET_SIZE) or theta_b.shape != (expected_blocks, ALPHABET_SIZE):
            raise RuntimeError(f"unexpected theta shapes: {theta_a.shape}, {theta_b.shape}")

        result = statcore.tv_upper_bound(a, b, alphabet_size=ALPHABET_SIZE, alpha=ALPHA_UPPER)
        deviations[rep] = float(result.tv_hat) - TRUE_TV

        # Consume the diagnosis-of-record inner redraws on the shared generator.
        lengths = np.full(expected_blocks, BLOCK_SIZE, dtype=np.int64)
        lengths[-1] = N - BLOCK_SIZE * (expected_blocks - 1)
        for _ in range(WITHIN_REDRAWS):
            rng.multinomial(lengths, theta_a)
            rng.multinomial(lengths, theta_b)

        if (rep + 1) % 500 == 0:
            print(f"outer_replicates={rep + 1}/{OUTER_DRAWS}", flush=True)

    sd_d = float(np.std(deviations, ddof=1))
    mean_d = float(np.mean(deviations))
    skew_d = skewness(deviations)
    se = math.sqrt(
        6.0 * OUTER_DRAWS * (OUTER_DRAWS - 1)
        / ((OUTER_DRAWS - 2) * (OUTER_DRAWS + 1) * (OUTER_DRAWS + 3))
    )
    ci = [float(skew_d - 1.96 * se), float(skew_d + 1.96 * se)]
    z = float(skew_d / se)
    ci_contains_zero = bool(ci[0] <= 0.0 <= ci[1])
    bootstrap = bootstrap_ci(deviations)
    sd_ok = bool(0.0168 <= sd_d <= 0.0171)

    notes = (
        "Outer replicates reuse the diagnosis-of-record loop structure from "
        "track5_between_block_diagnosis.py: shared Generator, A draw, B draw, "
        "then 32 inner multinomial redraw pairs consumed before the next outer replicate. "
        f"Outer seed {SEED} matches DIAGNOSIS_SEED=20260919. Bootstrap percentile CI uses "
        f"{BOOTSTRAP_RESAMPLES} resamples with bootstrap seed {BOOTSTRAP_SEED}. "
        "Conclusion is about the modelled block law at this design, never about real traffic."
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
        "stream_reproduced": {
            "used": "inner redraws consumed",
            "method": "reused track5_between_block_diagnosis.py loop order with 32 rng.multinomial redraw pairs per outer replicate",
            "reused_diagnosis_loop": True,
        },
        "sd_D": sd_d,
        "sd_control_expected": SD_CONTROL_EXPECTED,
        "sd_control_ok": sd_ok,
        "mean_D": mean_d,
        "skewness_D": skew_d,
        "skewness_formula": "g1 = m3 / m2**1.5, with m2=mean((D-mean(D))**2) and m3=mean((D-mean(D))**3) using 1/n central moments",
        "se_skewness": se,
        "ci95_skewness": ci,
        "z_skewness": z,
        "ci_contains_zero": ci_contains_zero,
        "bootstrap_ci95_skewness": bootstrap,
        "proposition_tested": "the signed deviation D = tv_hat - TRUE_TV is negatively skewed",
        "falsifier_fired": ci_contains_zero,
        "notes": notes,
    }
    JSON_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    json_sha = sha256_file(JSON_PATH)
    md = "\n".join(
        [
            "# Track 5 signed-deviation skewness",
            "",
            f"- Design: n={N}, B={BLOCK_SIZE}, concentration={CONCENTRATION}, TRUE_TV={TRUE_TV}, outer replicates={OUTER_DRAWS}.",
            f"- Seed: `{SEED}`; matches diagnosis-of-record seed `20260919`: yes.",
            "- Stream: `inner redraws consumed`; reused the diagnosis-of-record loop structure with 32 inner redraw pairs per outer replicate.",
            f"- Stream control: sd(D) = `{sd_d:.12f}` vs expected `0.0169715358`; matches the 0.01697 stream: `{sd_ok}`; not the wrong ~0.0151 stream.",
            f"- Mean(D): `{mean_d:.12f}`.",
            f"- Skewness(D): `{skew_d:.12f}` using `g1 = m3 / m2**1.5` with 1/n central moments.",
            f"- Analytic SE: `{se:.12f}`; 95% CI: `[{ci[0]:.12f}, {ci[1]:.12f}]`; z = `{z:.6f}`.",
            f"- CI contains zero: `{ci_contains_zero}`.",
            f"- Bootstrap percentile 95% CI ({BOOTSTRAP_RESAMPLES} resamples): `[{bootstrap[0]:.12f}, {bootstrap[1]:.12f}]`.",
            "",
            "## Pre-committed falsifier",
            "",
            '- Proposition tested: **"the signed deviation D = tv_hat - TRUE_TV is negatively skewed."**',
            f"- Falsifier fired: `{ci_contains_zero}`. The falsifier fires if the n=5000 analytic 95% CI contains zero.",
            "",
            "Boundary: this conclusion is about the modelled block law at this design, never about real traffic.",
            "",
            f"content_sha256: {json_sha}",
            "",
        ]
    )
    MD_PATH.write_text(md, encoding="utf-8")
    print(json.dumps({"json": str(JSON_PATH), "md": str(MD_PATH), "json_sha256": json_sha, **payload}, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
