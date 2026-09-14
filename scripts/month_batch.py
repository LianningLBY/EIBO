#!/usr/bin/env python3
"""Run one bounded, resumable batch of direct-content range requests."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import os
import threading
import time
import urllib.request


ROOT = Path("/root/autodl-tmp/eibo/data/raw")
DATA = ROOT.parent
ARTIFACTS = Path("/root/eibo/artifacts")
STATE_PATH = ARTIFACTS / "month_fetch_state.json"
REPORT_PATH = ARTIFACTS / "month_fetch_report.json"
SUMS_PATH = DATA / "SHA256SUMS.txt"
URL = "https://zenodo.org/api/records/17249078/files/{name}/content"
CHUNK = 16 * 1024 * 1024
RETRIES = 6
STALL = 180
KNOWN = {
    "2024-07.zip": 1492444177,
    "2024-08.zip": 1522431507,
    "2024-09.zip": 2818547704,
    "2024-10.zip": 3389907136,
}
MONTHS = [
    "2024-06.zip", "2024-07.zip", "2024-08.zip", "2024-09.zip",
    "2024-10.zip", "2024-11.zip", "2024-12.zip", "2025-01.zip",
    "2025-02.zip", "2025-03.zip", "2025-04.zip", "2025-05.zip",
]


def timestamp():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"events": [], "growth": [], "stalls": [], "sizes": {}, "probe": [], "concurrency": None}


def save_state(state):
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")


def event(state, text):
    line = f"{timestamp()} {text}"
    print(line, flush=True)
    state["events"].append(line)


def discover(name):
    if name in KNOWN:
        return KNOWN[name]
    for attempt in range(1, 11):
        try:
            req = urllib.request.Request(
                URL.format(name=name),
                headers={"Range": "bytes=0-0", "Connection": "close"},
            )
            with urllib.request.urlopen(req, timeout=90) as response:
                cr = response.headers.get("Content-Range", "")
                if "/" not in cr:
                    raise RuntimeError(f"status={response.status} content-range={cr!r}")
                return int(cr.rsplit("/", 1)[1])
        except Exception as exc:
            print(f"{timestamp()} size_retry name={name} attempt={attempt} error={exc!r}", flush=True)
            time.sleep(min(20, attempt * 2))
    raise RuntimeError(f"size discovery failed for {name}")


def probe(name, state):
    probe_size = 1024 * 1024
    results = []
    for workers in (1, 2, 4, 8, 12, 16, 24, 32):
        def one(i):
            start = i * probe_size
            end = start + probe_size - 1
            req = urllib.request.Request(
                URL.format(name=name),
                headers={"Range": f"bytes={start}-{end}", "Connection": "close"},
            )
            with urllib.request.urlopen(req, timeout=90) as response:
                data = response.read()
                cr = response.headers.get("Content-Range", "")
                if response.status != 206 or not cr.startswith(f"bytes {start}-{end}/") or len(data) != probe_size:
                    raise RuntimeError(f"status={response.status} range={cr!r} bytes={len(data)}")

        failures = []
        t0 = time.monotonic()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(one, i) for i in range(workers)]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    failures.append(repr(exc))
        result = {"workers": workers, "successes": workers - len(failures), "failures": failures, "seconds": time.monotonic() - t0}
        results.append(result)
        event(state, f"concurrency workers={workers} successes={result['successes']} failures={len(failures)} seconds={result['seconds']:.2f}")
        if failures:
            break
    state["probe"] = results
    state["concurrency"] = max((r["workers"] for r in results if not r["failures"]), default=4)
    save_state(state)


def fetch_one(name, path, start, end):
    expected = end - start + 1
    if path.exists() and path.stat().st_size == expected:
        return expected
    tmp = path.with_suffix(path.suffix + ".tmp")
    for attempt in range(1, RETRIES + 1):
        if tmp.exists():
            tmp.unlink()
        try:
            req = urllib.request.Request(
                URL.format(name=name),
                headers={"Range": f"bytes={start}-{end}", "Connection": "close", "Accept-Encoding": "identity"},
            )
            with urllib.request.urlopen(req, timeout=120) as response, tmp.open("wb") as out:
                cr = response.headers.get("Content-Range", "")
                if response.status != 206 or not cr.startswith(f"bytes {start}-{end}/"):
                    raise RuntimeError(f"status={response.status} content-range={cr!r}")
                while block := response.read(2 * 1024 * 1024):
                    out.write(block)
            if tmp.stat().st_size != expected:
                raise RuntimeError(f"expected={expected} got={tmp.stat().st_size}")
            os.replace(tmp, path)
            return expected
        except Exception:
            if tmp.exists():
                tmp.unlink()
            if attempt == RETRIES:
                raise
            time.sleep(min(20, attempt * 2))
    raise AssertionError("unreachable")


def hash_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(8 * 1024 * 1024):
            h.update(block)
    return h.hexdigest()


def assemble(name, expected, offset):
    target = ROOT / (".2024-08.zip.download" if name == "2024-08.zip" else name)
    parts = ROOT / f".{name}.parts"
    assembling = ROOT / f".{name}.assembling"
    total_parts = (expected - offset + CHUNK - 1) // CHUNK
    if total_parts and all((parts / f"part-{i:05d}").exists() and (parts / f"part-{i:05d}").stat().st_size == min(CHUNK, expected - offset - i * CHUNK) for i in range(total_parts)):
        if assembling.exists():
            assembling.unlink()
        with assembling.open("wb") as out:
            if offset:
                with target.open("rb") as prefix:
                    while block := prefix.read(8 * 1024 * 1024):
                        out.write(block)
            for i in range(total_parts):
                with (parts / f"part-{i:05d}").open("rb") as part:
                    while block := part.read(8 * 1024 * 1024):
                        out.write(block)
        if assembling.stat().st_size == expected:
            os.replace(assembling, target)
            return True
    return False


def write_report(state):
    sizes = state["sizes"]
    files = []
    for name in MONTHS:
        path = ROOT / name
        expected = sizes.get(name)
        actual = path.stat().st_size if path.exists() else 0
        valid = expected is not None and actual == expected
        files.append({"name": name, "bytes": actual, "expected": expected, "sha256": hash_file(path) if valid else None, "valid": valid})
    sums = SUMS_PATH.read_text() if SUMS_PATH.exists() else ""
    xs = DATA / "CESNET-QUICEXT-25-XS.h5"
    xs_bytes = xs.stat().st_size if xs.exists() else 0
    xs_complete = xs_bytes == 3544625537
    xs_hash = hash_file(xs) if xs_complete else None
    report = {
        "python_path_verified": "/root/miniconda3/bin/python3 --version => Python 3.12.3",
        "xs_status": {"bytes": xs_bytes, "hash": xs_hash, "complete": xs_complete},
        "deleted_08": state.get("deleted_08", False),
        "resume_07": {"starting_offset": state.get("resume_07", 0), "growth_log": state.get("growth", []), "stalls": state.get("stalls", [])},
        "mechanism": {"how_launched": "managed ssh_execute foreground bounded batches", "concurrency_used": state.get("concurrency"), "observed_limit": state.get("concurrency"), "probe": state.get("probe", []), "refusal_text": state.get("refusal_text")},
        "throughput_window": state.get("throughput_window", {"duration_minutes": 0, "bytes_transferred": 0, "aggregate_mb_s": 0}),
        "projected_hours_one_month": state.get("projected_hours_one_month"),
        "projected_hours_all_months": state.get("projected_hours_all_months"),
        "full_corpus_practical": state.get("full_corpus_practical"),
        "files_completed": files,
        "sha256sums_file_contents": sums,
        "data_disk_avail_gb": state.get("data_disk_avail_gb"),
        "blockers": state.get("blockers", []),
        "events": state.get("events", []),
        "expected_sizes": sizes,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", choices=MONTHS)
    parser.add_argument("--max-ranges", type=int, default=1)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    state = load_state()
    if "2024-06.zip" not in state["sizes"] and (ROOT / "2024-06.zip").exists():
        state["sizes"]["2024-06.zip"] = (ROOT / "2024-06.zip").stat().st_size
    if (ROOT / "2024-08.zip").exists() and (ROOT / "2024-08.zip").stat().st_size == 0:
        state["deleted_08"] = False
        state["refusal_text"] = "Remote deletion is only available through cleanup_remote_paths; arbitrary Worker SSH deletion was blocked: rm -f /root/autodl-tmp/eibo/data/raw/2024-08.zip"
        blocker = "2024-08.zip remains a zero-byte 504 leftover because cleanup_remote_paths was unavailable; it was not overwritten."
        if blocker not in state.setdefault("blockers", []):
            state["blockers"].append(blocker)
        event(state, "delete_08_blocked existing_zero_byte_preserved=true")
    if args.name and args.name not in state["sizes"]:
        state["sizes"][args.name] = KNOWN.get(args.name) or discover(args.name)
        event(state, f"size name={args.name} bytes={state['sizes'][args.name]}")
    requested = [args.name] if args.name else MONTHS[1:]
    for name in requested:
        if name not in state["sizes"]:
            state["sizes"][name] = discover(name)
            event(state, f"size name={name} bytes={state['sizes'][name]}")
    if (ROOT / "2024-06.zip").exists():
        state["sizes"]["2024-06.zip"] = (ROOT / "2024-06.zip").stat().st_size
    if args.probe:
        probe("2024-09.zip", state)
    save_state(state)
    if args.name:
        name = args.name
        expected = state["sizes"][name]
        target = ROOT / (".2024-08.zip.download" if name == "2024-08.zip" else name)
        offset = target.stat().st_size if name == "2024-07.zip" and target.exists() else 0
        if name == "2024-07.zip" and "resume_07" not in state:
            state["resume_07"] = offset
        parts = ROOT / f".{name}.parts"
        parts.mkdir(parents=True, exist_ok=True)
        total = (expected - offset + CHUNK - 1) // CHUNK
        pending = []
        for i in range(total):
            start = offset + i * CHUNK
            end = min(expected - 1, start + CHUNK - 1)
            path = parts / f"part-{i:05d}"
            if not (path.exists() and path.stat().st_size == end - start + 1):
                pending.append((i, start, end, path))
        pending = pending[:args.max_ranges]
        event(state, f"batch_start name={name} offset={offset} pending={len(pending)} concurrency={state.get('concurrency') or 8}")
        t0 = time.monotonic()
        before = time.monotonic()
        with ThreadPoolExecutor(max_workers=state.get("concurrency") or 8) as pool:
            futures = {pool.submit(fetch_one, name, path, start, end): (i, start, end) for i, start, end, path in pending}
            for future in as_completed(futures):
                i, start, end = futures[future]
                n = future.result()
                event(state, f"range_done name={name} index={i} bytes={n}")
                state["growth"].append({"timestamp": timestamp(), "name": name, "bytes": start + n})
                save_state(state)
        elapsed = time.monotonic() - t0
        fetched = sum(end - start + 1 for _, start, end, _ in pending)
        state["throughput_window"] = {"duration_minutes": elapsed / 60, "bytes_transferred": fetched, "aggregate_mb_s": fetched / elapsed / 1e6}
        event(state, f"batch_done name={name} ranges={len(pending)} bytes={fetched} seconds={elapsed:.2f}")
        if assemble(name, expected, offset):
            event(state, f"file_done name={name} bytes={expected}")
        save_state(state)
    if args.finalize:
        for name, expected in state["sizes"].items():
            if name == "2024-06.zip":
                continue
            assemble(name, expected, ROOT.joinpath(name).stat().st_size if name == "2024-07.zip" else 0)
        valid_lines = []
        for name in MONTHS:
            path = ROOT / name
            if name in state["sizes"] and path.exists() and path.stat().st_size == state["sizes"][name]:
                valid_lines.append(f"{hash_file(path)}  {name}")
        old = SUMS_PATH.read_text().splitlines() if SUMS_PATH.exists() else []
        for line in valid_lines:
            if line not in old:
                old.append(line)
        SUMS_PATH.write_text("\n".join(old) + ("\n" if old else ""))
    write_report(state)


if __name__ == "__main__":
    main()
