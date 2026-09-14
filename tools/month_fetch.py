#!/usr/bin/env python3
"""Resumable parallel range downloader for the monthly Zenodo archives."""

import argparse
import concurrent.futures
import datetime as dt
import os
import re
import shutil
import sys
import threading
import time
import urllib.error
import urllib.request


RAW = "/root/autodl-tmp/eibo/data/raw/"
BASE = "https://zenodo.org/api/records/17249078/files/"
DEFAULT_NAMES = [
    "2024-07.zip",
    "2024-08.zip",
    "2024-09.zip",
    "2024-10.zip",
    "2024-11.zip",
    "2024-12.zip",
    "2025-01.zip",
    "2025-02.zip",
    "2025-03.zip",
    "2025-04.zip",
    "2025-05.zip",
]
KNOWN = {
    "2024-07.zip": 1492444177,
    "2024-08.zip": 1522431507,
    "2024-09.zip": 2818547704,
    "2024-10.zip": 3389907136,
}
CHUNK = 16 * 1024 * 1024
REQUEST_TIMEOUT = 90
RETRIES = 6
LOG_LOCK = threading.Lock()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def log(message):
    with LOG_LOCK:
        line = f"{now()} {message}"
        print(line, flush=True)
        os.makedirs("/root/autodl-tmp/eibo/tools", exist_ok=True)
        with open("/root/autodl-tmp/eibo/tools/month_fetch.log", "a", encoding="ascii") as handle:
            handle.write(line + "\n")


def headers_request(name, method="HEAD", range_header=None):
    request = urllib.request.Request(BASE + name + "/content", method=method)
    request.add_header("Accept-Encoding", "identity")
    if range_header:
        request.add_header("Range", range_header)
    return urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT)


def content_length(name):
    if name in KNOWN:
        return KNOWN[name], "authoritative prompt size"

    try:
        with headers_request(name, method="HEAD") as response:
            value = response.headers.get("Content-Length")
            if response.status == 200 and value and int(value) > 1024 * 1024:
                return int(value), "HEAD Content-Length"
    except Exception as exc:
        log(f"CONTENT_LENGTH_HEAD_ERROR name={name} error={type(exc).__name__}:{exc}")

    with headers_request(name, method="GET", range_header="bytes=0-0") as response:
        if response.status != 206:
            raise RuntimeError(f"range discovery status {response.status}, expected 206")
        content_range = response.headers.get("Content-Range", "")
        match = re.search(r"/([0-9]+)$", content_range)
        if not match:
            raise RuntimeError(f"missing Content-Range for {name}: {content_range!r}")
        return int(match.group(1)), "GET Range Content-Range"


def part_path(parts_dir, start, end):
    return os.path.join(parts_dir, f"part_{start:016d}_{end:016d}")


def valid_part(path, expected):
    try:
        return os.path.getsize(path) == expected
    except FileNotFoundError:
        return False


def fetch_part(name, start, end, path):
    expected = end - start + 1
    if valid_part(path, expected):
        return "existing", expected
    temp = path + f".tmp.{os.getpid()}.{threading.get_ident()}"
    for attempt in range(1, RETRIES + 1):
        try:
            with headers_request(name, method="GET", range_header=f"bytes={start}-{end}") as response:
                if response.status != 206:
                    raise RuntimeError(f"status {response.status}, expected 206")
                content_range = response.headers.get("Content-Range", "")
                if not content_range.startswith(f"bytes {start}-{end}/"):
                    raise RuntimeError(f"unexpected Content-Range {content_range!r}")
                remaining = expected
                with open(temp, "wb") as handle:
                    while remaining:
                        block = response.read(min(1024 * 1024, remaining))
                        if not block:
                            raise RuntimeError(f"short body with {remaining} bytes remaining")
                        handle.write(block)
                        remaining -= len(block)
            if os.path.getsize(temp) != expected:
                raise RuntimeError("temporary part size mismatch")
            os.replace(temp, path)
            return "downloaded", expected
        except Exception as exc:
            try:
                os.unlink(temp)
            except FileNotFoundError:
                pass
            if attempt == RETRIES:
                raise
            delay = min(30, 2 ** (attempt - 1))
            log(f"PART_RETRY name={name} range={start}-{end} attempt={attempt} sleep_s={delay} error={type(exc).__name__}:{exc}")
            time.sleep(delay)


def assemble(name, expected, prefix_len, parts):
    target = os.path.join(RAW, name)
    temp = target + f".assembling.{os.getpid()}"
    with open(temp, "wb") as output:
        if prefix_len:
            with open(target, "rb") as prefix:
                shutil.copyfileobj(prefix, output, length=1024 * 1024)
        for start, end, path in parts:
            with open(path, "rb") as handle:
                shutil.copyfileobj(handle, output, length=1024 * 1024)
    if os.path.getsize(temp) != expected:
        raise RuntimeError(f"assembled size mismatch for {name}")
    os.replace(temp, target)


def download_one(name, workers):
    target = os.path.join(RAW, name)
    parts_dir = os.path.join(RAW, "." + name + ".parts")
    expected, source = content_length(name)
    os.makedirs(parts_dir, exist_ok=True)
    current = os.path.getsize(target) if os.path.exists(target) else 0
    if current > expected:
        raise RuntimeError(f"existing file is larger than Content-Length: {current}>{expected}")
    log(f"FILE_START name={name} expected={expected} current={current} offset={current} source={source}")
    if current == expected:
        log(f"FILE_COMPLETE name={name} bytes={expected} action=already_complete")
        return name, expected, True

    ranges = []
    start = current
    while start < expected:
        end = min(expected - 1, start + CHUNK - 1)
        path = part_path(parts_dir, start, end)
        ranges.append((start, end, path))
        start = end + 1

    missing = [(start, end, path) for start, end, path in ranges if not valid_part(path, end - start + 1)]
    log(f"FILE_PLAN name={name} ranges={len(ranges)} missing={len(missing)} part_dir={parts_dir}")
    done_bytes = expected - current
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(fetch_part, name, start, end, path): (start, end, path)
            for start, end, path in missing
        }
        for future in concurrent.futures.as_completed(futures):
            start, end, path = futures[future]
            action, size = future.result()
            done_bytes += size
            log(f"PART_DONE name={name} range={start}-{end} action={action} file_bytes={current} downloaded_or_present={done_bytes}/{expected}")
    assemble(name, expected, current, ranges)
    log(f"FILE_COMPLETE name={name} bytes={expected} action=assembled")
    return name, expected, True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--file-workers", type=int, default=3)
    parser.add_argument("names", nargs="*", default=DEFAULT_NAMES)
    args = parser.parse_args()
    os.makedirs(RAW, exist_ok=True)
    log(f"JOB_START endpoint={BASE} raw={RAW} workers={args.workers} file_workers={args.file_workers}")
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.file_workers) as pool:
        futures = {pool.submit(download_one, name, args.workers): name for name in args.names}
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                future.result()
            except Exception as exc:
                failures.append(name)
                log(f"FILE_FAILED name={name} error={type(exc).__name__}:{exc}")
    if failures:
        log(f"JOB_END status=partial failures={','.join(sorted(failures))}")
        return 2
    log("JOB_END status=complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
