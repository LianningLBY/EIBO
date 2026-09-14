#!/usr/bin/env python3
import concurrent.futures
import datetime as dt
import hashlib
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request


DATA_DIR = "/root/autodl-tmp/eibo/data"
NAME = "CESNET-QUICEXT-25-XS.h5"
TARGET = os.path.join(DATA_DIR, NAME)
CHUNK_DIR = os.path.join(DATA_DIR, NAME.replace(".h5", ".chunks"))
URL = f"https://zenodo.org/api/records/17249078/files/{NAME}/content"
FALLBACK_URL = "https://s3.cl4.du.cesnet.cz/cesnet-quicext-25/CESNET-QUICEXT-25-XS.h5?AWSAccessKeyId=ALPSWBOXLLA5GKEAX561&Signature=z79fK%2BqBZQ7kgVnJnAECMLnij%2BU%3D&Expires=1789392395"
EXPECTED_BYTES = 3_544_625_537
EXPECTED_SHA256 = "6b323c4c53b7c9d0ec9011f895b3c5ba6b35247576e41ef19fe84ab8632810ab"
CHUNK_SIZE = 64 * 1024 * 1024
WORKERS = 8
READ_SIZE = 1024 * 1024
HTTP_TIMEOUT = 45
STALL_SECONDS = 120


def utc_now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def chunk_path(index):
    return os.path.join(CHUNK_DIR, f"part-{index:04d}")


def expected_chunk_size(index, total):
    start = index * CHUNK_SIZE
    end = min(start + CHUNK_SIZE, total)
    return max(0, end - start)


def content_length_for(url):
    errors = []
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                return int(resp.headers["Content-Length"])
        except Exception as e:
            errors.append(f"HEAD attempt {attempt}: {repr(e)}")
            time.sleep(3 * attempt)
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(
                url,
                headers={"Range": "bytes=0-0", "User-Agent": "eibo-xs-resume/1.0"},
            )
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                content_range = resp.headers.get("Content-Range", "")
                if "/" in content_range:
                    return int(content_range.rsplit("/", 1)[1])
                if resp.headers.get("Content-Length"):
                    return int(resp.headers["Content-Length"])
                raise RuntimeError(f"missing Content-Range in range response: {dict(resp.headers)}")
        except Exception as e:
            errors.append(f"RANGE attempt {attempt}: {repr(e)}")
            time.sleep(3 * attempt)
    raise RuntimeError("could not obtain content length: " + " | ".join(errors))


def choose_source_url():
    attempts = []
    for label, url in [("zenodo_api_content", URL), ("cesnet_s3_fallback", FALLBACK_URL)]:
        try:
            length = content_length_for(url)
            attempts.append({"label": label, "url": url, "content_length": length, "ok": True})
            return url, length, attempts
        except Exception as e:
            attempts.append({"label": label, "url": url, "ok": False, "error": repr(e)})
    raise RuntimeError("all source URLs failed: " + json.dumps(attempts, sort_keys=True))


def current_chunk_bytes(total, n_parts):
    out = 0
    for i in range(n_parts):
        p = chunk_path(i)
        if os.path.exists(p):
            out += min(os.path.getsize(p), expected_chunk_size(i, total))
    return out


def missing_or_short(total, n_parts):
    todo = []
    for i in range(n_parts):
        p = chunk_path(i)
        want = expected_chunk_size(i, total)
        have = os.path.getsize(p) if os.path.exists(p) else 0
        if have < want:
            todo.append((i, have, want))
    return todo


def download_chunk(index, total, cancel, source_url):
    p = chunk_path(index)
    want = expected_chunk_size(index, total)
    os.makedirs(CHUNK_DIR, exist_ok=True)
    have = os.path.getsize(p) if os.path.exists(p) else 0
    if have > want:
        raise RuntimeError(f"{os.path.basename(p)} has {have} bytes, expected at most {want}")
    if have == want:
        return {"index": index, "status": "already_complete", "bytes": have}

    start = index * CHUNK_SIZE + have
    end = index * CHUNK_SIZE + want - 1
    headers = {"Range": f"bytes={start}-{end}", "User-Agent": "eibo-xs-resume/1.0"}
    req = urllib.request.Request(source_url, headers=headers)

    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        content_range = resp.headers.get("Content-Range", "")
        if resp.status != 206 or not content_range.startswith(f"bytes {start}-{end}/"):
            raise RuntimeError(f"unexpected range response for part {index}: status={resp.status} content_range={content_range!r}")
        mode = "ab" if have else "wb"
        with open(p, mode) as f:
            while not cancel["stop"]:
                block = resp.read(READ_SIZE)
                if not block:
                    break
                f.write(block)
                cancel["last_progress"] = time.time()
                cancel["downloaded_this_cycle"] += len(block)

    have2 = os.path.getsize(p)
    if have2 != want:
        raise RuntimeError(f"part {index} incomplete after request: have {have2}, want {want}")
    return {"index": index, "status": "downloaded", "bytes": have2}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def assemble_and_verify(total, n_parts):
    tmp = TARGET + ".assembling"
    with open(tmp, "wb") as out:
        for i in range(n_parts):
            p = chunk_path(i)
            want = expected_chunk_size(i, total)
            have = os.path.getsize(p)
            if have != want:
                raise RuntimeError(f"cannot assemble: {os.path.basename(p)} has {have}, want {want}")
            with open(p, "rb") as f:
                remaining = want
                while remaining:
                    block = f.read(min(8 * 1024 * 1024, remaining))
                    if not block:
                        raise RuntimeError(f"short read while assembling {p}")
                    out.write(block)
                    remaining -= len(block)
    size = os.path.getsize(tmp)
    sha = sha256_file(tmp)
    if size != total:
        raise RuntimeError(f"assembled size mismatch: {size} != {total}")
    if sha != EXPECTED_SHA256:
        raise RuntimeError(f"assembled sha256 mismatch: {sha} != {EXPECTED_SHA256}")
    os.replace(tmp, TARGET)
    return {"path": TARGET, "bytes": size, "sha256": sha}


def main():
    print("COMMAND: /root/miniconda3/bin/python3 /root/eibo/scripts/resume_xs_h5.py")
    print("START_UTC:", utc_now())
    print("URL:", URL)
    print("FALLBACK_URL:", FALLBACK_URL)
    source_url, remote_length, source_attempts = choose_source_url()
    print("SOURCE_ATTEMPTS:", json.dumps(source_attempts, sort_keys=True))
    print("ACTIVE_SOURCE_URL:", source_url)
    print("CONTENT_LENGTH:", remote_length)
    if remote_length != EXPECTED_BYTES:
        raise RuntimeError(f"authoritative Content-Length {remote_length} != expected {EXPECTED_BYTES}")

    total = remote_length
    n_parts = math.ceil(total / CHUNK_SIZE)
    initial_target_size = os.path.getsize(TARGET) if os.path.exists(TARGET) else 0
    initial_chunk_bytes = current_chunk_bytes(total, n_parts)
    print("INITIAL_TARGET_BYTES:", initial_target_size)
    print("INITIAL_CHUNK_BYTES:", initial_chunk_bytes)
    print("INITIAL_MISSING_CHUNK_BYTES:", total - initial_chunk_bytes)

    stall_log = []
    was_resumed = False
    cycle = 0
    while True:
        todo = missing_or_short(total, n_parts)
        if not todo:
            break
        was_resumed = True
        cycle += 1
        print("CYCLE:", cycle, "TODO_PARTS:", json.dumps(todo))
        cancel = {"stop": False, "last_progress": time.time(), "downloaded_this_cycle": 0}
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futures = [ex.submit(download_chunk, i, total, cancel, source_url) for i, _, _ in todo]
            pending = set(futures)
            while pending:
                done, pending = concurrent.futures.wait(pending, timeout=5, return_when=concurrent.futures.FIRST_COMPLETED)
                for fut in done:
                    try:
                        print("PART_RESULT:", json.dumps(fut.result(), sort_keys=True))
                    except Exception as e:
                        print("PART_ERROR:", repr(e))
                if pending and (time.time() - cancel["last_progress"] > STALL_SECONDS):
                    before = current_chunk_bytes(total, n_parts)
                    ts = utc_now()
                    cancel["stop"] = True
                    stall_log.append({"timestamp_utc": ts, "cycle": cycle, "chunk_bytes": before, "reason": f"no byte growth for {STALL_SECONDS}s"})
                    print("STALL:", json.dumps(stall_log[-1], sort_keys=True))
                    break
        time.sleep(2)

    final_chunk_bytes = current_chunk_bytes(total, n_parts)
    print("FINAL_CHUNK_BYTES:", final_chunk_bytes)
    if final_chunk_bytes != total:
        raise RuntimeError(f"chunk tree still incomplete: {final_chunk_bytes} != {total}")
    result = assemble_and_verify(total, n_parts)
    result["was_resumed"] = was_resumed
    result["stall_log"] = stall_log
    result["completed_utc"] = utc_now()
    print("RESULT:", json.dumps(result, sort_keys=True))
    print("END_UTC:", utc_now())


if __name__ == "__main__":
    main()
