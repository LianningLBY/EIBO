#!/usr/bin/env python3
"""Download CESNET-QUICEXT-25 XS H5 by concurrent HTTP byte ranges.

The script keeps all temporary chunks on the data disk, resumes completed
chunks, verifies Content-Range for each response, then assembles one exact
H5 file. It uses only the Python standard library.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import os
import shutil
import sys
import time
import urllib.request


URL = "https://s3.cl4.du.cesnet.cz/cesnet-quicext-25/CESNET-QUICEXT-25-XS.h5?AWSAccessKeyId=ALPSWBOXLLA5GKEAX561&Signature=z79fK%2BqBZQ7kgVnJnAECMLnij%2BU%3D&Expires=1789392395"
TOTAL = 3_544_625_537
OUT = Path("/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.h5")
CHUNK_DIR = OUT.with_suffix(".chunks")
WORKERS = 4
CHUNK_BYTES = 64 * 1024 * 1024


def fetch_one(index: int, start: int, end: int) -> tuple[int, int]:
    path = CHUNK_DIR / f"part-{index:04d}"
    expected = end - start + 1
    if path.exists() and path.stat().st_size == expected:
        return index, expected
    if path.exists():
        path.unlink()
    request = urllib.request.Request(URL, headers={"Range": f"bytes={start}-{end}"})
    with urllib.request.urlopen(request, timeout=120) as response, path.open("wb") as handle:
        status = getattr(response, "status", None)
        content_range = response.headers.get("Content-Range", "")
        if status != 206 or not content_range.startswith(f"bytes {start}-{end}/"):
            raise RuntimeError(f"part {index}: status={status} content-range={content_range!r}")
        while True:
            block = response.read(8 * 1024 * 1024)
            if not block:
                break
            handle.write(block)
    actual = path.stat().st_size
    if actual != expected:
        raise RuntimeError(f"part {index}: expected {expected} bytes, got {actual}")
    return index, actual


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    ranges = []
    start = 0
    index = 0
    while start < TOTAL:
        end = min(TOTAL - 1, start + CHUNK_BYTES - 1)
        ranges.append((index, start, end))
        index += 1
        start = end + 1
    print(f"target={OUT}")
    print(f"total_bytes={TOTAL} chunks={len(ranges)} workers={WORKERS}", flush=True)
    completed = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(fetch_one, i, s, e) for i, s, e in ranges]
        for future in as_completed(futures):
            i, n = future.result()
            completed += 1
            print(f"chunk={i} bytes={n} completed={completed}/{len(ranges)}", flush=True)
    tmp = OUT.with_suffix(".assembling")
    if tmp.exists():
        tmp.unlink()
    with tmp.open("wb") as output:
        for i, _, _ in ranges:
            part = CHUNK_DIR / f"part-{i:04d}"
            with part.open("rb") as source:
                shutil.copyfileobj(source, output, length=8 * 1024 * 1024)
    actual = tmp.stat().st_size
    if actual != TOTAL:
        raise RuntimeError(f"assembled size mismatch: expected {TOTAL}, got {actual}")
    os.replace(tmp, OUT)
    print(f"assembled_bytes={OUT.stat().st_size}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
