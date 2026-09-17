import hashlib
import json
import math
import os
import tempfile


PATH = "/root/eibo/artifacts/x12_detector_validation_k5.json"
EXPECTED = {
    ("lightgbm", "0.05"): 8,
    ("lightgbm", "0.1"): 8,
    ("lightgbm", "0.2"): 10,
    ("prototype", "0.05"): 3,
    ("prototype", "0.1"): 4,
    ("prototype", "0.2"): 4,
    ("ronetc", "0.05"): 3,
    ("ronetc", "0.1"): 3,
    ("ronetc", "0.2"): 2,
}


def binomial_sf(k, n, p):
    total = 0.0
    for i in range(k, n + 1):
        total += math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i))
    return total


with open(PATH) as handle:
    artifact = json.load(handle)

verified = []
for detector, detail in artifact["floor_violation_test"]["per_detector"].items():
    for holdout, row in detail["holdouts"].items():
        test = row.get("binomial_test")
        if not isinstance(test, dict):
            continue
        p_value = float(test["p_value"])
        n = int(row["informative_pair_count"])
        candidates = [
            k for k in range(n + 1)
            if abs(binomial_sf(k, n, float(test["null_violation_rate"])) - p_value) <= 1e-12
        ]
        if len(candidates) != 1:
            raise AssertionError(
                f"{detector}/{holdout}: expected one p-value count, got {candidates}"
            )
        violations = candidates[0]
        if row["floor_violation_count"] != violations:
            raise AssertionError(
                f"{detector}/{holdout}: floor count {row['floor_violation_count']} != {violations}"
            )
        if n != 340:
            raise AssertionError(f"{detector}/{holdout}: trials {n} != 340")
        if EXPECTED[(detector, holdout)] != violations:
            raise AssertionError(
                f"{detector}/{holdout}: expected map disagrees with p-value: {violations}"
            )
        test["violations"] = violations
        test["trials"] = n
        verified.append({
            "detector": detector,
            "holdout": holdout,
            "violations": violations,
            "trials": n,
            "reported_p": p_value,
            "recomputed_p": binomial_sf(violations, n, float(test["null_violation_rate"])),
            "reject_null": test["reject_null"],
        })

fd, temp_path = tempfile.mkstemp(prefix="x12_detector_validation_k5.", suffix=".tmp", dir=os.path.dirname(PATH))
try:
    with os.fdopen(fd, "w") as handle:
        json.dump(artifact, handle, indent=2, sort_keys=False)
        handle.write("\n")
    os.replace(temp_path, PATH)
finally:
    if os.path.exists(temp_path):
        os.unlink(temp_path)

with open(PATH, "rb") as handle:
    digest = hashlib.sha256(handle.read()).hexdigest()

print(json.dumps({"verified": verified, "sha256": digest}, sort_keys=True))
