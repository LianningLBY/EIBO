#!/usr/bin/env python3
"""Repair a small set of CESNET H5 byte-range chunks on the data disk."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import os
import shutil
import sys
import urllib.request


URL = "https://s3.cl4.du.cesnet.cz/cesnet-quicext-25/CESNET-QUICEXT-25-XS.h5?AWSAccessKeyId=ALPSWBOXLLA5GKEAX561&Signature=z79fK%2BqBZQ7kgVnJnAECMLnij%2BU%3D&Expires=1789392395"
CHUNK_DIR = Path("/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.chunks")
CHUNK_BYTES = 64 * 1024 * 1024
SUB_BYTES = 8 * 1024 * 1024
REPAIR = (15, 30, 35)


def fetch_subpart(index, start, end):
    path = CHUNK_DIR / f"repair-{index:04d}-{start:012d}"
    expected = end - start + 1
    if path.exists() and path.stat().st_size == expected:
        return path
    if path.exists():
        path.unlink()
    request = urllib.request.Request(URL, headers={"Range": f"bytes={start}-{end}"})
    with urllib.request.urlopen(request, timeout=120) as response, path.open("wb") as handle:
        if getattr(response, "status", None) != 206:
            raise RuntimeError(f"unexpected status for {start}-{end}: {response.status}")
        if not response.headers.get("Content-Range", "").startswith(f"bytes {start}-{end}/"):
            raise RuntimeError(f"unexpected range for {start}-{end}")
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            handle.write(block)
    if path.stat().st_size != expected:
        raise RuntimeError(f"short subpart {start}-{end}: {path.stat().st_size}")
    return path


def main():
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    jobs = []
    for chunk_index in REPAIR:
        base = chunk_index * CHUNK_BYTES
        for offset in range(0, CHUNK_BYTES, SUB_BYTES):
            start = base + offset
            end = start + SUB_BYTES - 1
            jobs.append((chunk_index, start, end))
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(fetch_subpart, *job) for job in jobs]
        for n, future in enumerate(as_completed(futures), 1):
            print(f"subpart {n}/{len(jobs)} ready: {future.result()}", flush=True)
    for chunk_index in REPAIR:
        output = CHUNK_DIR / f"part-{chunk_index:04d}.repaired"
        if output.exists():
            output.unlink()
        with output.open("wb") as handle:
            base = chunk_index * CHUNK_BYTES
            for offset in range(0, CHUNK_BYTES, SUB_BYTES):
                part = CHUNK_DIR / f"repair-{chunk_index:04d}-{base + offset:012d}"
                with part.open("rb") as source:
                    shutil.copyfileobj(source, handle)
        if output.stat().st_size != CHUNK_BYTES:
            raise RuntimeError(f"repaired chunk {chunk_index} has bad size")
        os.replace(output, CHUNK_DIR / f"part-{chunk_index:04d}")
        print(f"chunk {chunk_index} repaired", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
