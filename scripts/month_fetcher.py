#!/root/miniconda3/bin/python3
"""Resumable direct-content range fetcher for the QUICEXT monthly archives."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import threading
import time
import urllib.error
import urllib.request


ROOT = Path("/root/autodl-tmp/eibo/data/raw")
REPORT = Path("/root/eibo/artifacts/month_fetch_report.json")
SUMS = ROOT.parent / "SHA256SUMS.txt"
BASE = "https://zenodo.org/api/records/17249078/files/{name}/content"
CHUNK_BYTES = 16 * 1024 * 1024
DISCOVERY_RETRIES = 10
RANGE_RETRIES = 6
STALL_SECONDS = 180
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

lock = threading.Lock()
events = []
growth = []
stalls = []


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log(message):
    line = f"{now()} {message}"
    print(line, flush=True)
    with lock:
        events.append(line)


def request_headers(name, start=0, end=0):
    req = urllib.request.Request(
        BASE.format(name=name),
        headers={"Range": f"bytes={start}-{end}", "Connection": "close"},
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        status = getattr(response, "status", None)
        content_range = response.headers.get("Content-Range", "")
        content_length = response.headers.get("Content-Length")
        total = None
        if "/" in content_range:
            total = int(content_range.rsplit("/", 1)[1])
        elif content_length and status == 200:
            total = int(content_length)
        if total is None:
            raise RuntimeError(
                f"header status={status} content-range={content_range!r} "
                f"content-length={content_length!r}"
            )
        return total, status, content_range


def discover_size(name):
    if name in KNOWN:
        return KNOWN[name]
    last = None
    for attempt in range(1, DISCOVERY_RETRIES + 1):
        try:
            total, status, content_range = request_headers(name)
            log(f"size name={name} bytes={total} status={status} range={content_range!r}")
            return total
        except Exception as exc:
            last = repr(exc)
            log(f"size_retry name={name} attempt={attempt}/{DISCOVERY_RETRIES} error={last}")
            time.sleep(min(30, 2 * attempt))
    raise RuntimeError(f"could not discover size for {name}: {last}")


def fetch_range(name, path, start, end):
    expected = end - start + 1
    if path.exists() and path.stat().st_size == expected:
        return expected
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    for attempt in range(1, RANGE_RETRIES + 1):
        if tmp.exists():
            tmp.unlink()
        try:
            req = urllib.request.Request(
                BASE.format(name=name),
                headers={
                    "Range": f"bytes={start}-{end}",
                    "Connection": "close",
                    "Accept-Encoding": "identity",
                },
            )
            with urllib.request.urlopen(req, timeout=120) as response, tmp.open("wb") as out:
                status = getattr(response, "status", None)
                content_range = response.headers.get("Content-Range", "")
                if status != 206 or not content_range.startswith(f"bytes {start}-{end}/"):
                    raise RuntimeError(f"status={status} content-range={content_range!r}")
                while True:
                    block = response.read(2 * 1024 * 1024)
                    if not block:
                        break
                    out.write(block)
            if tmp.stat().st_size != expected:
                raise RuntimeError(f"expected={expected} got={tmp.stat().st_size}")
            os.replace(tmp, path)
            return expected
        except Exception as exc:
            if tmp.exists():
                tmp.unlink()
            if attempt == RANGE_RETRIES:
                raise RuntimeError(f"range {name} {start}-{end}: {exc!r}")
            time.sleep(min(20, attempt * 2))
    raise AssertionError("unreachable")


def probe_concurrency(name):
    results = []
    probe_bytes = 1024 * 1024
    for workers in (1, 2, 4, 8, 12, 16, 24, 32):
        starts = [i * probe_bytes for i in range(workers)]
        t0 = time.monotonic()

        def one(start):
            req = urllib.request.Request(
                BASE.format(name=name),
                headers={"Range": f"bytes={start}-{start + probe_bytes - 1}", "Connection": "close"},
            )
            with urllib.request.urlopen(req, timeout=90) as response:
                data = response.read()
                cr = response.headers.get("Content-Range", "")
                if response.status != 206 or not cr.startswith(f"bytes {start}-{start + probe_bytes - 1}/"):
                    raise RuntimeError(f"status={response.status} content-range={cr!r}")
                if len(data) != probe_bytes:
                    raise RuntimeError(f"probe bytes={len(data)}")
            return len(data)

        failures = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(one, start) for start in starts]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    failures.append(repr(exc))
        elapsed = time.monotonic() - t0
        result = {"workers": workers, "successes": workers - len(failures), "failures": failures, "seconds": elapsed}
        results.append(result)
        log(f"concurrency workers={workers} successes={result['successes']} failures={len(failures)} seconds={elapsed:.2f}")
        if failures:
            break
    valid = [r["workers"] for r in results if not r["failures"]]
    return results, max(valid) if valid else 0


def assemble(name, expected, start_offset=0):
    target = ROOT / name
    part_dir = ROOT / f".{name}.parts"
    part_dir.mkdir(parents=True, exist_ok=True)
    ranges = []
    start = start_offset
    index = 0
    while start < expected:
        end = min(expected - 1, start + CHUNK_BYTES - 1)
        ranges.append((index, start, end))
        index += 1
        start = end + 1
    t0 = time.monotonic()
    completed_bytes = 0
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = {
            pool.submit(fetch_range, name, part_dir / f"part-{i:05d}", s, e): (i, s, e)
            for i, s, e in ranges
        }
        for future in as_completed(futures):
            i, s, e = futures[future]
            n = future.result()
            completed_bytes += n
            log(f"range_done name={name} index={i} bytes={n} completed={completed_bytes}/{expected - start_offset}")
    assembling = target.with_suffix(target.suffix + ".assembling")
    if assembling.exists():
        assembling.unlink()
    with assembling.open("wb") as out:
        if start_offset:
            with target.open("rb") as prefix:
                shutil.copyfileobj(prefix, out, length=2 * 1024 * 1024)
        for i, _, _ in ranges:
            with (part_dir / f"part-{i:05d}").open("rb") as part:
                shutil.copyfileobj(part, out, length=2 * 1024 * 1024)
    if assembling.stat().st_size != expected:
        raise RuntimeError(f"assembled {name}: expected={expected} got={assembling.stat().st_size}")
    os.replace(assembling, target)
    elapsed = time.monotonic() - t0
    return target, elapsed, completed_bytes


def hash_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def record_growth(name, start_offset):
    target = ROOT / name
    part_dir = ROOT / f".{name}.parts"
    previous = None
    last_change = time.monotonic()
    while True:
        prefix = target.stat().st_size if target.exists() else start_offset
        parts = sum(path.stat().st_size for path in part_dir.glob("part-*.tmp") if path.exists())
        parts += sum(path.stat().st_size for path in part_dir.glob("part-*") if path.is_file() and not path.name.endswith(".tmp"))
        current = min(prefix + parts, expected_sizes[name])
        stamp = now()
        growth.append({"timestamp": stamp, "name": name, "bytes": current})
        changed = current != previous
        if changed:
            last_change = time.monotonic()
        elif time.monotonic() - last_change >= STALL_SECONDS:
            event = {"timestamp": stamp, "name": name, "bytes": current, "stall_seconds": STALL_SECONDS}
            stalls.append(event)
            log(f"WATCHDOG_DEAD name={name} bytes={current} stall_seconds={STALL_SECONDS}")
            last_change = time.monotonic()
        previous = current
        if target.exists() and target.stat().st_size >= expected_sizes[name]:
            return
        time.sleep(30)


def verify(name, expected):
    path = ROOT / name
    actual = path.stat().st_size if path.exists() else 0
    digest = hash_file(path) if path.exists() and actual == expected else None
    valid = actual == expected and digest is not None
    return {"name": name, "bytes": actual, "expected": expected, "sha256": digest, "valid": valid}


expected_sizes = {}
CONCURRENCY = 8


def main():
    global expected_sizes, CONCURRENCY
    ROOT.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    deleted_08 = False
    eight = ROOT / "2024-08.zip"
    if eight.exists() and eight.stat().st_size == 0:
        log("delete_08_blocked path=/root/autodl-tmp/eibo/data/raw/2024-08.zip reason=cleanup_remote_paths tool unavailable")

    june = ROOT / "2024-06.zip"
    if not june.exists():
        raise RuntimeError("2024-06.zip is absent; refusing to infer its size")
    expected_sizes = {"2024-06.zip": june.stat().st_size}
    expected_sizes.update({name: discover_size(name) for name in MONTHS[1:]})
    probe_results, limit = probe_concurrency("2024-09.zip")
    CONCURRENCY = limit or 4
    log(f"selected_concurrency={CONCURRENCY} observed_limit={limit}")

    existing_07 = ROOT / "2024-07.zip"
    resume_offset = existing_07.stat().st_size if existing_07.exists() else 0
    log(f"resume_07 starting_offset={resume_offset}")
    jobs = []
    for name in MONTHS[1:]:
        path = ROOT / name
        if name == "2024-07.zip":
            if path.exists() and path.stat().st_size == expected_sizes[name]:
                continue
            jobs.append((name, resume_offset))
        elif path.exists() and path.stat().st_size == expected_sizes[name]:
            continue
        else:
            jobs.append((name, 0))

    started = time.monotonic()
    for name, offset in jobs:
        watchdog = threading.Thread(target=record_growth, args=(name, offset), daemon=True)
        watchdog.start()
        target, elapsed, transferred = assemble(name, expected_sizes[name], offset)
        log(f"file_done name={name} bytes={target.stat().st_size} resumed_offset={offset} seconds={elapsed:.2f} transferred={transferred}")
        growth.append({"timestamp": now(), "name": name, "bytes": target.stat().st_size})

    files = [verify(name, expected_sizes[name]) for name in MONTHS]
    lines = []
    existing = SUMS.read_text() if SUMS.exists() else ""
    for item in files:
        if item["valid"]:
            lines.append(f"{item['sha256']}  {item['name']}")
    merged = existing.splitlines()
    for line in lines:
        if line not in merged:
            merged.append(line)
    SUMS.write_text("\n".join(merged) + ("\n" if merged else ""))
    duration = max(time.monotonic() - started, 1e-9)
    total_expected = sum(expected_sizes.values())
    transferred = sum(expected_sizes[name] - offset for name, offset in jobs if expected_sizes[name] > offset)
    rate = transferred / duration
    average_month = sum(expected_sizes.values()) / len(MONTHS)
    projected_one = average_month / rate / 3600 if rate else None
    projected_all = sum(expected_sizes.values()) / rate / 3600 if rate else None
    report = {
        "python_path_verified": "/root/miniconda3/bin/python3 --version => Python 3.12.3",
        "xs_status": {"bytes": (ROOT.parent / "CESNET-QUICEXT-25-XS.h5").stat().st_size if (ROOT.parent / "CESNET-QUICEXT-25-XS.h5").exists() else 0, "hash": hash_file(ROOT.parent / "CESNET-QUICEXT-25-XS.h5") if (ROOT.parent / "CESNET-QUICEXT-25-XS.h5").exists() and (ROOT.parent / "CESNET-QUICEXT-25-XS.h5").stat().st_size == 3544625537 else None, "complete": (ROOT.parent / "CESNET-QUICEXT-25-XS.h5").exists() and (ROOT.parent / "CESNET-QUICEXT-25-XS.h5").stat().st_size == 3544625537},
        "deleted_08": deleted_08,
        "resume_07": {"starting_offset": resume_offset, "growth_log": growth, "stalls": stalls},
        "mechanism": {"launched": "managed ssh_execute -> background /root/miniconda3/bin/python3", "concurrency_probe": probe_results, "concurrency_used": CONCURRENCY, "observed_limit": limit, "refusal_text": None},
        "throughput_window": {"duration_minutes": duration / 60.0, "bytes_transferred": transferred, "aggregate_mb_s": rate / 1e6, "window_note": "Measured from bytes fetched during this run."},
        "projected_hours_one_month": projected_one,
        "projected_hours_all_months": projected_all,
        "full_corpus_practical": bool(duration >= 300 and rate > 0),
        "files_completed": files,
        "sha256sums_file_contents": SUMS.read_text(),
        "data_disk_avail_gb": None,
        "blockers": ["2024-08.zip deletion was not performed because cleanup_remote_paths was not mounted; the existing zero-byte path was left untouched." if not deleted_08 else ""],
        "events": events,
        "expected_sizes": expected_sizes,
        "total_expected_bytes": total_expected,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log(f"FATAL {exc!r}")
        raise
