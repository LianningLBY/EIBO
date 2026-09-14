from pathlib import Path


TARGET = Path("/root/eibo/x12_detector_validation.py")


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return source.replace(old, new)


def main() -> None:
    source = TARGET.read_text(encoding="utf-8")

    old = '''def preregistration_payload(args: argparse.Namespace, output_json: Path) -> dict[str, Any]:
'''
    new = '''def score_matrix_path(output_json: Path, detector: str) -> Path:
    return output_json.with_name(
        f"{output_json.stem}__per_class_scores__{detector}.npz"
    )


def persist_score_matrix(
    output_json: Path,
    detector: str,
    result: dict[str, Any],
    test: dict[str, Any],
    classes: list[int],
) -> dict[str, Any]:
    import numpy as np

    matrix = result.pop("score_matrix", None)
    score_kind = str(result.get("score_kind", "class_score"))
    if matrix is None:
        return {
            "status": "not_written",
            "reason": result.get("error", "detector did not provide a class score matrix"),
            "score_kind": score_kind,
        }
    scores = np.asarray(matrix, dtype=np.float32)
    flow_tokens = np.asarray(test["flow_tokens"], dtype=np.uint64)
    row_ids = np.asarray(test["ids"], dtype=np.uint64)
    dates = np.asarray(test["date"], dtype="U")
    true_labels = np.asarray(test["y_original"], dtype=np.int64)
    class_labels = np.asarray(classes, dtype=np.int64)
    expected_shape = (len(true_labels), len(class_labels))
    if scores.shape != expected_shape:
        raise ValueError(
            f"{detector} score matrix shape {scores.shape} != held-out shape {expected_shape}"
        )
    if len(np.unique(flow_tokens)) != len(flow_tokens):
        raise ValueError(f"{detector} score payload has duplicate flow_token keys")
    path = score_matrix_path(output_json, detector)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as handle:
        np.savez(
            handle,
            scores=scores,
            flow_tokens=flow_tokens,
            row_ids=row_ids,
            dates=dates,
            true_labels=true_labels,
            class_labels=class_labels,
            alignment_key=np.asarray("flow_token"),
            score_kind=np.asarray(score_kind),
        )
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    return {
        "status": "written",
        "path": str(path),
        "rows": int(scores.shape[0]),
        "classes": int(scores.shape[1]),
        "dtype": str(scores.dtype),
        "alignment_key": "flow_token",
        "score_kind": score_kind,
    }


def preregistration_payload(args: argparse.Namespace, output_json: Path) -> dict[str, Any]:
'''
    source = replace_once(source, old, new, "score persistence helper insertion")

    old = '''    return {
        "pred": pred,
        "score": score,
        "accepted": np.ones(len(pred), dtype=bool),
'''
    new = '''    return {
        "pred": pred,
        "score": score,
        "score_matrix": probabilities,
        "score_kind": "predict_proba",
        "accepted": np.ones(len(pred), dtype=bool),
'''
    source = replace_once(source, old, new, "LightGBM score matrix return")

    old = '''    radius_array = np.asarray(radii, dtype=np.float32)[nearest]
    accepted = nearest_distance <= radius_array
    score = (1.0 / (1.0 + nearest_distance)).astype(np.float32)
    return {
        "pred": nearest,
        "score": score,
        "accepted": accepted,
'''
    new = '''    radius_array = np.asarray(radii, dtype=np.float32)[nearest]
    accepted = nearest_distance <= radius_array
    score = (1.0 / (1.0 + nearest_distance)).astype(np.float32)
    class_scores = (1.0 / (1.0 + distances_test)).astype(np.float32)
    return {
        "pred": nearest,
        "score": score,
        "score_matrix": class_scores,
        "score_kind": "inverse_distance_class_score",
        "accepted": accepted,
'''
    source = replace_once(source, old, new, "prototype score matrix return")

    old = '''    return {
        "pred": pred,
        "score": score,
        "accepted": accepted,
        "device": str(device),
'''
    new = '''    return {
        "pred": pred,
        "score": score,
        "score_matrix": mean_probabilities.astype(np.float32),
        "score_kind": "mean_predict_proba",
        "accepted": accepted,
        "device": str(device),
'''
    source = replace_once(source, old, new, "RoNeTC score matrix return")

    old = '''        state["detectors"] = {}
        results: dict[str, dict[str, Any]] = {}

        log("DETECTOR_START lightgbm")
        results["lightgbm"] = run_lightgbm(train["X"], train["y"], test["X"], args)
        state["detectors"]["lightgbm"] = {
            key: value
            for key, value in results["lightgbm"].items()
            if key not in {"pred", "score", "accepted"}
        }
'''
    new = '''        state["detectors"] = {}
        state["score_matrices"] = {}
        results: dict[str, dict[str, Any]] = {}

        log("DETECTOR_START lightgbm")
        results["lightgbm"] = run_lightgbm(train["X"], train["y"], test["X"], args)
        state["score_matrices"]["lightgbm"] = persist_score_matrix(
            output_json, "lightgbm", results["lightgbm"], test, classes
        )
        state["detectors"]["lightgbm"] = {
            key: value
            for key, value in results["lightgbm"].items()
            if key not in {"pred", "score", "accepted", "score_matrix"}
        }
'''
    source = replace_once(source, old, new, "LightGBM persistence call")

    old = '''        log("DETECTOR_START prototype")
        results["prototype"] = run_prototype(train["X"], train["y"], test["X"], args)
        state["detectors"]["prototype"] = {
            key: value
            for key, value in results["prototype"].items()
            if key not in {"pred", "score", "accepted"}
        }
'''
    new = '''        log("DETECTOR_START prototype")
        results["prototype"] = run_prototype(train["X"], train["y"], test["X"], args)
        state["score_matrices"]["prototype"] = persist_score_matrix(
            output_json, "prototype", results["prototype"], test, classes
        )
        state["detectors"]["prototype"] = {
            key: value
            for key, value in results["prototype"].items()
            if key not in {"pred", "score", "accepted", "score_matrix"}
        }
'''
    source = replace_once(source, old, new, "prototype persistence call")

    old = '''        log("DETECTOR_START ronetc")
        results["ronetc"] = run_ronetc(train["X"], train["y"], test["X"], args)
        state["detectors"]["ronetc"] = {
            key: value
            for key, value in results["ronetc"].items()
            if key not in {"pred", "score", "accepted"}
        }
'''
    new = '''        log("DETECTOR_START ronetc")
        results["ronetc"] = run_ronetc(train["X"], train["y"], test["X"], args)
        state["score_matrices"]["ronetc"] = persist_score_matrix(
            output_json, "ronetc", results["ronetc"], test, classes
        )
        state["detectors"]["ronetc"] = {
            key: value
            for key, value in results["ronetc"].items()
            if key not in {"pred", "score", "accepted", "score_matrix"}
        }
'''
    source = replace_once(source, old, new, "RoNeTC persistence call")

    old = '''        log("DETECTOR_START pcap_encoder")
        results["pcap_encoder"] = run_pcap_encoder_probe(args)
        state["detectors"]["pcap_encoder"] = {
            key: value
            for key, value in results["pcap_encoder"].items()
            if key not in {"pred", "score", "accepted"}
        }
'''
    new = '''        log("DETECTOR_START pcap_encoder")
        results["pcap_encoder"] = run_pcap_encoder_probe(args)
        state["score_matrices"]["pcap_encoder"] = persist_score_matrix(
            output_json, "pcap_encoder", results["pcap_encoder"], test, classes
        )
        state["detectors"]["pcap_encoder"] = {
            key: value
            for key, value in results["pcap_encoder"].items()
            if key not in {"pred", "score", "accepted", "score_matrix"}
        }
'''
    source = replace_once(source, old, new, "pcap persistence call")

    TARGET.write_text(source, encoding="utf-8")
    print("PATCHED", TARGET)
    print("SCORE_MATRIX_PATH", "output_json.stem + '__per_class_scores__' + detector + '.npz'")
    print("ALIGNMENT_KEY", "flow_token")


if __name__ == "__main__":
    main()
