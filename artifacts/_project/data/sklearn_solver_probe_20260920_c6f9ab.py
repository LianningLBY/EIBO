import json
import platform
import sys
import warnings
from datetime import datetime, timezone

import numpy as np
import scipy
import sklearn
from sklearn.linear_model import LogisticRegression


def readable_attr(obj, name):
    try:
        value = getattr(obj, name)
    except Exception as exc:  # pragma: no cover - provenance capture only
        return {"readable": False, "error": repr(exc)}
    return {"readable": True, "value": value}


def normalize_value(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


output_path = "/root/eibo/artifacts/_project/intermediate/sklearn_solver_probe_20260920.json"

X = np.array(
    [
        [0.0, 0.0],
        [0.0, 1.0],
        [1.0, 0.0],
        [1.0, 1.0],
        [3.0, 3.0],
        [3.0, 4.0],
        [4.0, 3.0],
        [4.0, 4.0],
    ],
    dtype=float,
)
y = np.array([0, 0, 0, 0, 1, 1, 1, 1], dtype=int)

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    clf = LogisticRegression(max_iter=1000, random_state=0)
    solver_prefit_info = readable_attr(clf, "solver")
    penalty_prefit_info = readable_attr(clf, "penalty")
    clf.fit(X, y)

post_solver = getattr(clf, "solver")
post_penalty = getattr(clf, "penalty")
l1_ratio = getattr(clf, "l1_ratio", None)

result = {
    "sklearn_version": sklearn.__version__,
    "resolved_solver": str(post_solver),
    "resolved_penalty": str(post_penalty),
    "l1_ratio": normalize_value(l1_ratio),
    "solver_prefit": normalize_value(solver_prefit_info.get("value"))
    if solver_prefit_info.get("readable")
    else solver_prefit_info,
    "penalty_prefit": normalize_value(penalty_prefit_info.get("value"))
    if penalty_prefit_info.get("readable")
    else penalty_prefit_info,
    "deprecation_warnings": [str(w.message) for w in caught],
    "interpreter": sys.executable,
    "python_version": sys.version,
    "numpy_version": np.__version__,
    "scipy_version": scipy.__version__,
    "sklearn_file": sklearn.__file__,
    "numpy_file": np.__file__,
    "scipy_file": scipy.__file__,
    "hostname": platform.node(),
    "utc_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "toy_fit_note": "Fitted LogisticRegression(max_iter=1000, random_state=0) with no solver or penalty argument on an 8-row, 2-class toy array before reading post-fit attributes.",
    "notes": "Warnings were captured with warnings.catch_warnings(record=True) and simplefilter('always') around construction and fit. Prefit values were read from the same estimator before fit when readable.",
}

with open(output_path, "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2, sort_keys=True)
    handle.write("\n")

print(json.dumps(result, indent=2, sort_keys=True))
