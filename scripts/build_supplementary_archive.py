#!/usr/bin/env python3
"""Build the supplementary archive from explicit, verified membership."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import re
import shutil
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml


BASE = Path(
    "/efs/workspace/projects/"
    "epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-recognition-certification-grade"
)
WORKSPACE_ROOT = Path("/efs/workspace")
DEFAULT_OUTPUT = BASE / "artifacts" / "supplementary.tar.gz"
# The path the manifest cites for art_20260924_2d151d. Registration copied the
# built archive here once; re-running the build without mirroring would leave this
# copy stale while every other assert still passed.
REGISTERED_OUTPUT = BASE / "artifacts" / "_project" / "data" / "supplementary.tar.gz"
# Manifest id for this archive; the build compares its own output hash against the
# recorded one so a rebuild cannot silently leave the record stale.
REGISTERED_ARTIFACT_ID = "art_20260924_2d151d"
EXPECTED_MAIN_PDF_SHA256 = "3877e12747d608a741a5cd09fd2db4a3d6356e6901d5cbc6d007aee0ad4a315f"


CODE_MEMBERS = (
    BASE / "src/eibo/statcore.py",
    BASE / "src/eibo/divisibility.py",
    BASE / "src/eibo/__init__.py",
    BASE / "tests/test_statcore.py",
    BASE / "tests/test_divisibility.py",
    BASE / "scripts/xs_compression_early_readout.py",
)

GENERATOR_MEMBERS = (
    BASE / "figures/paper/_generators/build_data.py",
    BASE / "figures/paper/_generators/render_figs.py",
    BASE / "figures/paper/_generators/render_fig1.py",
    BASE / "figures/paper/_generators/DATA_PROVENANCE.json",
)

CITED_DATA_IDS = (
    "art_20260913_e5ebac",
    "art_20260914_443901",
    "art_20260915_27333a",
    "art_20260918_17c1b0",
    "art_20260918_4b3dc7",
    "art_20260918_9821af",
    "art_20260918_a408c2",
    "art_20260918_a73525",
    "art_20260918_b5a5cd",
    "art_20260918_f27ba9",
    "art_20260918_fd1598",
    "art_20260919_17d7d3",
    "art_20260919_b84113",
    "art_20260919_fc043c",
    "art_20260920_0e4cdb",
    "art_20260922_764458",
    "art_20260922_f7853e",
)

ADDED_DATA_IDS = (
    "art_20260914_082a7f",
    "art_20260916_c212ed",
    "art_20260914_104088",
    "art_20260916_0780aa",
    "art_20260914_3dff66",
    "art_20260914_b4d6db",
    "art_20260914_1bdf63",
    "art_20260914_e21c94",
    "art_20260914_7986d6",
    "art_20260914_023753",
    "art_20260914_9fb96b",
    "art_20260915_75134b",
    "art_20260915_240634",
    "art_20260913_e5ebac",
    "art_20260914_443901",
    "art_20260915_27333a",
    "art_20260918_a408c2",
    "art_20260918_17c1b0",
    "art_20260918_4b3dc7",
    "art_20260918_9821af",
    "art_20260918_fd1598",
    "art_20260918_f27ba9",
    "art_20260918_a73525",
    "art_20260918_b5a5cd",
    "art_20260919_17d7d3",
    "art_20260919_b84113",
    "art_20260919_fc043c",
    "art_20260920_0e4cdb",
    "art_20260922_f7853e",
    "art_20260922_764458",
)

GENERATOR_PROVENANCE_DATA_IDS = (
    "art_20260913_dd5823",
    "art_20260914_c2a33e",
    "art_20260914_fc478a",
    "art_20260914_0e48a1",
    "art_20260914_24c7ab",
)

CURRENT_ARCHIVE_PAYLOAD_IDS = (
    "art_20260915_70f9a1",
    "art_20260915_ci_main_table_pairbootstrap",
    "art_20260922_d0bf02",
    "art_20260922_91028b",
    "art_20260922_a6078a",
    "art_20260913_3f762c",
    "art_20260913_6addd0",
    "art_20260913_ea99d2",
    "art_20260913_1f0edb",
    "art_20260915_883c41",
    "art_20260915_4ddfb9",
    "art_20260913_613998",
    "art_20260919_30a7b4",
    "art_20260919_fa717f",
    "art_20260920_f5c06b",
    "art_20260920_5beddf",
    "art_20260920_f18204",
    "art_20260920_3d6096",
    "art_20260920_7376cc",
)

FORBIDDEN_ENTRY_RE = re.compile(
    r"RETIRED|do_not_cite|31cbed|c962b4|camera_ready_plan|references\.bib\.prev",
    re.IGNORECASE,
)
ARTIFACT_ID_RE = re.compile(r"art_[0-9]{8}_[0-9a-f]{6}")
PROJECT_SLUG = "epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-recognition-certification-grade"
# The slug is also spelled across Python string-concatenation boundaries in the
# figure generators, where the contiguous full slug never occurs (it is split as
# "...-open-set-encrypted-traffic-" + "recognition-certification-grade"). Matching
# only the full slug misses those files, and the miss is in the hiding direction.
PROJECT_SLUG_PREFIX = "epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-"
CONTENT_CENSUS_PATTERNS = {
    "root": "/root/",
    "efs": "/efs/",
    "home": "/home/",
    "usr": "/usr/local/",
    "autodl": "autodl",
    "eibo": "eibo",
    "slug": PROJECT_SLUG,
    "slug_prefix": PROJECT_SLUG_PREFIX,
}
EXPECTED_LEAK_BASELINE = {
    "root": 17,
    "efs": 12,
    "home": 1,
    "usr": 1,
    "autodl": 11,
    "eibo": 33,
    "slug": 9,
    "slug_prefix": 11,
}
# PDF metadata values that indicate a toolchain or the paper's own title, not a
# person or institution. The project's own main.pdf carries empty-string
# Author/Title/Subject/Keywords under plain LaTeX, so "" must be treated as
# absent rather than as a hit.
#
# The acmart template populates Title and Creator where the previous USENIX
# build left them empty, so the allowlist has to cover those too or EVERY
# rebuild fails on a clean artifact — the guard would be reporting the
# template's own behaviour as a leak. Values are decoded before comparison
# (see decode_pdf_literal), so these are matched as real text.
PDF_METADATA_ALLOWED_PREFIXES = (
    "pdfTeX-",
    "pdfTeX,",
    "LaTeX with hyperref",
    "LaTeX with acmart",
    "Matplotlib",
    "GPL Ghostscript",
    # The paper's own title. It is public (it is on the PDF's title page), so
    # its presence in metadata identifies nothing the submission does not
    # already disclose.
    "Certification-Grade",
)
EXPECTED_LEAK_BASELINE_FILES = (
    "supplementary/code/__init__.py",
    "supplementary/code/statcore.py",
    "supplementary/code/test_divisibility.py",
    "supplementary/code/test_statcore.py",
    "supplementary/code/xs_compression_early_readout.py",
    "supplementary/data/ci_k_ladder.json",
    "supplementary/data/coverage_calibration_ladder.json",
    "supplementary/data/coverage_calibration_v2.json",
    "supplementary/data/coverage_calibration_v2.md",
    "supplementary/data/d181_balanced_accuracy_risk_interval.json",
    "supplementary/data/d181_same_channel_classifier.json",
    "supplementary/data/d181_tv_saturation_simulation.json",
    "supplementary/data/masking_regime_sweep.json",
    "supplementary/data/q1_absolute_counts.meta.json",
    "supplementary/data/q1_absolute_counts_k10.meta.json",
    "supplementary/data/q1_gate_five_pairs_full_n.json",
    "supplementary/data/q1_lower_side_full_n.json",
    "supplementary/data/track5_armE_design.json",
    "supplementary/data/track5_diagnosis_between_block.json",
    "supplementary/data/track5_radius_form_coverage.json",
    "supplementary/data/track5_skewness_prefixes_D.json",
    "supplementary/data/x11_full_bracket.json",
    "supplementary/data/x12_detector_validation_k5.json",
    "supplementary/data/x12_k5_containment_corrected_342.json",
    "supplementary/data/x12_label_space_check.json",
    "supplementary/data/x1_headline_table.json",
    "supplementary/data/x3_chain_rule_divergence.json",
    "supplementary/data/x3_control_heterogeneous_iid.json",
    "supplementary/data/x3_control_known_truth.json",
    "supplementary/data/x3_control_occupancy_dose_response.json",
    "supplementary/data/x3_fixed_population_and_occupancy.json",
    "supplementary/data/x3_variant_a_estimator_family.json",
    "supplementary/data/x3_variant_c_nested_lr.json",
    "supplementary/data/x5_estimator_ground_truth.json",
    "supplementary/data/x9_dose_response_channels.json",
    "supplementary/generators/DATA_PROVENANCE.json",
    "supplementary/generators/build_data.py",
    "supplementary/generators/render_fig1.py",
    "supplementary/generators/render_figs.py",
    "supplementary/latex/main.tex",
)
TEXT_SUFFIXES = {".json", ".md", ".py", ".csv", ".tex", ".txt", ".sty", ".bib", ".bst", ".cls"}
BINARY_SUFFIXES = {".pdf", ".png", ".npz", ".h5", ".pyc"}
PDF_METADATA_KEYS = ("Author", "Producer", "Title", "Creator", "Subject", "Keywords")
PDF_METADATA_REGEX = (
    r"/(Author|Producer|Title|Creator|Subject|Keywords)\s*"
    r"(?:\(([^()]*)\)|<([0-9A-Fa-f\s]+)>)"
)


@dataclass(frozen=True)
class Member:
    category: str
    source: Path
    archive_path: Path
    artifact_id: str | None = None
    expected_sha256: str | None = None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest() -> dict[str, dict]:
    with (BASE / "artifacts/manifest.yaml").open("r", encoding="utf-8") as fh:
        entries = yaml.safe_load(fh)
    if not isinstance(entries, list):
        raise ValueError("artifacts/manifest.yaml is not a YAML list")
    return {str(entry["id"]): entry for entry in entries}


def unique_ids(groups: tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for artifact_id in groups:
        if artifact_id not in seen:
            seen.add(artifact_id)
            result.append(artifact_id)
    return result


def resolve_manifest_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        resolved = path
    else:
        resolved = WORKSPACE_ROOT / path
    try:
        resolved.resolve().relative_to(WORKSPACE_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"manifest path escapes workspace root: {raw_path}") from exc
    return resolved


def data_ids() -> list[str]:
    return unique_ids(
        CITED_DATA_IDS
        + ADDED_DATA_IDS
        + GENERATOR_PROVENANCE_DATA_IDS
        + CURRENT_ARCHIVE_PAYLOAD_IDS
    )


def extract_cited_ids_from_tex() -> list[str]:
    text = (BASE / "docs/paper/main.tex").read_text(encoding="utf-8").replace(r"\_", "_")
    return sorted(set(ARTIFACT_ID_RE.findall(text)))


def latex_members(expected_main_pdf_sha256: str) -> list[Member]:
    root = BASE / "docs/paper"
    members: list[Member] = []
    for source in sorted(root.iterdir()):
        if not source.is_file():
            continue
        if source.name == "main.pdf":
            observed = sha256_file(source)
            if observed != expected_main_pdf_sha256:
                print("ERROR: STALE MAIN.PDF HASH MISMATCH", file=sys.stderr)
                print(f"expected: {expected_main_pdf_sha256}", file=sys.stderr)
                print(f"observed: {observed}", file=sys.stderr)
                return []
            members.append(Member("latex", source, Path("supplementary/latex/main.pdf")))
            continue
        if source.name == "camera_ready_plan.md":
            continue
        if source.name == "references.bib.prev" or source.name.endswith(".prev"):
            continue
        # The copyright badge is a hard dependency of popets.sty, which does
        # \includegraphics{cc-by-4.pdf}. The PoPETs style bundle is NOT on CTAN,
        # so the badge must travel with the archive or a fresh unpack cannot
        # compile the paper at all. Collected explicitly rather than by adding
        # ".pdf" to the suffix set, which would sweep in other root-level PDFs
        # and entangle the binary-content metadata guard.
        if source.name == "cc-by-4.pdf":
            members.append(Member("latex", source, Path("supplementary/latex") / source.name))
            continue
        # ".bst" carries the bibliography style. Under the PoPETs/ACM template
        # that style (ACM-Reference-Format) is a LOCAL file, not the TeX Live
        # builtin plainnat used previously, so without it the archive ships a
        # paper whose bibliography cannot be rebuilt.
        #
        # ".cls" is equally load-bearing and was missed on the first pass: the
        # paper is `\documentclass{acmart}`, and acmart is NOT present in this
        # image's TeX Live (verified: `kpsewhich acmart.cls` finds nothing), so
        # the class file exists only as a local copy in docs/paper/. Without it
        # the shipped sources cannot be compiled at all. Verified by rebuilding
        # from exactly the collected set: with .cls present the build produces
        # the 24-page PDF with 0 errors; without it, `File acmart.cls not found`.
        if source.suffix in {".tex", ".bib", ".sty", ".bst", ".cls"}:
            members.append(Member("latex", source, Path("supplementary/latex") / source.name))

    figure_root = root / "figures/paper"
    for source in sorted(figure_root.iterdir()):
        if source.is_file() and source.suffix in {".pdf", ".png"}:
            rel = source.relative_to(root)
            members.append(Member("latex", source, Path("supplementary/latex") / rel))
    return members


def build_member_list(manifest: dict[str, dict], expected_main_pdf_sha256: str) -> tuple[list[Member], list[str], list[str], int]:
    members: list[Member] = []
    unresolved: list[str] = []
    mismatches: list[str] = []
    matched_hashes = 0

    for source in CODE_MEMBERS:
        members.append(Member("code", source, Path("supplementary/code") / source.name))

    for artifact_id in data_ids():
        entry = manifest.get(artifact_id)
        if entry is None:
            unresolved.append(f"{artifact_id}: not present in manifest")
            continue
        raw_path = entry.get("path")
        expected_sha = entry.get("content_sha256")
        if not raw_path:
            unresolved.append(f"{artifact_id}: missing path")
            continue
        if not expected_sha:
            unresolved.append(f"{artifact_id}: missing content_sha256")
            continue
        source = resolve_manifest_path(str(raw_path))
        if not source.is_file():
            unresolved.append(f"{artifact_id}: file not found at {source}")
            continue
        observed_sha = sha256_file(source)
        if observed_sha != expected_sha:
            mismatches.append(
                f"{artifact_id}: {source} expected {expected_sha} observed {observed_sha}"
            )
        else:
            matched_hashes += 1
        members.append(
            Member(
                "data",
                source,
                Path("supplementary/data") / source.name,
                artifact_id=artifact_id,
                expected_sha256=str(expected_sha),
            )
        )

    for source in GENERATOR_MEMBERS:
        members.append(Member("generators", source, Path("supplementary/generators") / source.name))

    pdf_members = latex_members(expected_main_pdf_sha256)
    if not pdf_members:
        mismatches.append("main.pdf: expected PDF hash did not match")
    members.extend(pdf_members)

    return members, unresolved, mismatches, matched_hashes


def assert_sources_exist(members: list[Member]) -> list[str]:
    missing: list[str] = []
    for member in members:
        if not member.source.is_file():
            missing.append(f"{member.archive_path}: source not found at {member.source}")
    return missing


def assert_unique_archive_paths(members: list[Member]) -> list[str]:
    seen: dict[Path, Member] = {}
    duplicates: list[str] = []
    for member in members:
        prior = seen.get(member.archive_path)
        if prior is not None:
            duplicates.append(
                f"{member.archive_path}: {prior.source} and {member.source}"
            )
        else:
            seen[member.archive_path] = member
    return duplicates


def stage_members(staging: Path, members: list[Member]) -> None:
    for member in members:
        target = staging / member.archive_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(member.source, target)
        os.chmod(target, 0o644)


def staged_files(staging: Path) -> list[Path]:
    return sorted(path.relative_to(staging) for path in staging.rglob("*") if path.is_file())


def assert_root_only(staging: Path) -> list[str]:
    errors: list[str] = []
    for rel in staged_files(staging):
        if not rel.parts or rel.parts[0] != "supplementary":
            errors.append(f"{rel.as_posix()}: staged file is outside supplementary/")
    return errors


def category_counts_from_staging(staging: Path) -> dict[str, int]:
    counts = {"code": 0, "data": 0, "generators": 0, "latex": 0}
    for rel in staged_files(staging):
        parts = rel.parts
        if len(parts) >= 3 and parts[0] == "supplementary" and parts[1] in counts:
            counts[parts[1]] += 1
    return counts


def write_readme(staging: Path, manifest: dict[str, dict]) -> None:
    counts = category_counts_from_staging(staging)
    total_with_readme = len(staged_files(staging)) + 1
    cited_ids = extract_cited_ids_from_tex()
    provenance_rows = []
    for artifact_id in cited_ids:
        entry = manifest[artifact_id]
        filename = resolve_manifest_path(str(entry["path"])).name
        provenance_rows.append((artifact_id, filename, str(entry["content_sha256"])))

    lines = [
        "# Supplementary Archive",
        "",
        "## Contents",
        "",
        "| Category | File count |",
        "|---|---:|",
    ]
    for category in ("code", "data", "generators", "latex"):
        lines.append(f"| `{category}/` | {counts[category]} |")
    lines.append(f"| Total archived files, including this README | {total_with_readme} |")
    lines.extend(
        [
            "",
            "## Reproduction Requirements",
            "",
            "- Python 3.12 or later.",
            "- Standard-library Python plus PyYAML for the archive builder.",
            "- LaTeX tooling is required only to rebuild the paper PDF from `latex/`.",
            "- Artifact payload membership is resolved from `artifacts/manifest.yaml` and verified by SHA-256 before packaging.",
            "",
            "## Server-Only Payloads",
            "",
            "No payload is copied directly from a server-only path by this archive builder. "
            "All included payloads are resolved from the project artifact manifest.",
            "",
            "## Provenance Metadata",
            "",
            "Some artifacts in this archive are provenance records written by the tools that produced them. "
            "Those records include local execution paths and environment details of the machine that ran the analysis, "
            "such as a project directory name, a container path, a Python environment path, and, in two analysis files, "
            "a private cloud hostname and region string recorded by a non-canonical analysis run. "
            "The artifacts are shipped byte-identical and unedited so that the content hashes printed in the paper remain valid. "
            "The recorded paths are provenance metadata, not results.",
            "",
            "## Cited Artifact Provenance",
            "",
            "| Artifact id | Filename | SHA-256 |",
            "|---|---|---|",
        ]
    )
    for artifact_id, filename, digest in provenance_rows:
        lines.append(f"| `{artifact_id}` | `{filename}` | `{digest}` |")
    lines.extend(
        [
            "",
            "## Exclusions",
            "",
            "Superseded, retired, do-not-cite, stale plan, previous-reference, and `*.prev` files are excluded. "
            "`data_validation.json` from an older archive root is not included because it has no manifest entry.",
            "",
        ]
    )

    readme = staging / "supplementary/README.md"
    readme.parent.mkdir(parents=True, exist_ok=True)
    readme.write_text("\n".join(lines), encoding="utf-8")
    os.chmod(readme, 0o644)


def coverage_errors(manifest: dict[str, dict], members: list[Member]) -> list[str]:
    member_basenames = {member.archive_path.name for member in members}
    errors: list[str] = []
    for artifact_id in extract_cited_ids_from_tex():
        entry = manifest.get(artifact_id)
        if entry is None:
            errors.append(f"{artifact_id}: not present in manifest")
            continue
        raw_path = entry.get("path")
        if not raw_path:
            errors.append(f"{artifact_id}: missing path")
            continue
        filename = resolve_manifest_path(str(raw_path)).name
        if filename not in member_basenames:
            errors.append(f"{artifact_id}: {filename} is not in archive member set")
    return errors


def forbidden_entries(staging: Path) -> list[str]:
    offenders = []
    for rel in staged_files(staging):
        entry = rel.as_posix()
        if FORBIDDEN_ENTRY_RE.search(entry):
            offenders.append(entry)
    return offenders


def content_census(staging: Path) -> tuple[dict[str, int], dict[str, list[str]], set[str]]:
    per_pattern: dict[str, int] = {label: 0 for label in CONTENT_CENSUS_PATTERNS}
    per_file: dict[str, list[str]] = {}
    for rel in staged_files(staging):
        suffix = rel.suffix.lower()
        if suffix in BINARY_SUFFIXES:
            continue
        if suffix not in TEXT_SUFFIXES:
            continue
        text = (staging / rel).read_bytes().decode("utf-8", errors="replace")
        text_lower = text.lower()
        matches: list[str] = []
        for label, pattern in CONTENT_CENSUS_PATTERNS.items():
            if pattern.lower() in text_lower:
                per_pattern[label] += 1
                matches.append(label)
        if matches:
            per_file[rel.as_posix()] = matches
    return per_pattern, per_file, set(per_file)


def decode_pdf_hex_value(hex_value: str) -> str:
    compact = re.sub(r"\s+", "", hex_value)
    if len(compact) % 2:
        compact += "0"
    try:
        return bytes.fromhex(compact).decode("utf-8", errors="replace")
    except ValueError:
        return hex_value


def decode_pdf_literal(literal: str) -> str:
    """Decode a PDF literal string's escapes so the guard compares REAL text.

    PDF literals encode non-ASCII bytes as `\\ooo` octal escapes, so a UTF-16BE
    title arrives as `\\376\\377\\000C\\000e...`. Comparing that raw form against
    a prefix allowlist is meaningless in both directions: a benign string never
    matches, and a leaking one is compared as gibberish. Decoding first makes the
    check strict about what it claims to check.
    """
    out = bytearray()
    i = 0
    while i < len(literal):
        ch = literal[i]
        if ch == "\\" and i + 1 < len(literal):
            nxt = literal[i + 1]
            if nxt.isdigit():                      # 1-3 octal digits
                j = i + 1
                digits = ""
                while j < len(literal) and len(digits) < 3 and literal[j].isdigit():
                    digits += literal[j]
                    j += 1
                out.append(int(digits, 8) & 0xFF)
                i = j
                continue
            mapped = {"n": 10, "r": 13, "t": 9, "b": 8, "f": 12}
            if nxt in mapped:                      # named escapes
                out.append(mapped[nxt])
                i += 2
                continue
            if nxt in "()\\":
                out.append(ord(nxt))
                i += 2
                continue
        out.extend(ch.encode("latin-1", errors="replace"))
        i += 1
    raw = bytes(out)
    # UTF-16 with a BOM is what most TeX engines write for non-ASCII metadata.
    if raw[:2] in (b"\xfe\xff", b"\xff\xfe"):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8", errors="replace")


def pdf_metadata(decoded: str) -> dict[str, str | None]:
    metadata: dict[str, str | None] = {key: None for key in PDF_METADATA_KEYS}
    for match in re.finditer(PDF_METADATA_REGEX, decoded):
        key = match.group(1)
        literal = match.group(2)
        hex_value = match.group(3)
        if literal is not None:
            metadata[key] = decode_pdf_literal(literal)
        elif hex_value is not None:
            metadata[key] = decode_pdf_hex_value(hex_value)
    return metadata


def binary_content_census(staging: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for rel in staged_files(staging):
        suffix = rel.suffix.lower()
        if suffix not in BINARY_SUFFIXES:
            continue
        data = (staging / rel).read_bytes()
        decoded = data.decode("latin-1", errors="replace")
        decoded_lower = decoded.lower()
        matches = [
            label
            for label, pattern in CONTENT_CENSUS_PATTERNS.items()
            if pattern.lower() in decoded_lower
        ]
        metadata = pdf_metadata(decoded) if suffix == ".pdf" else None
        records.append(
            {
                "path": rel.as_posix(),
                "matched_tokens": matches,
                "pdf_metadata": metadata,
            }
        )
    return records


def print_content_census(per_pattern: dict[str, int], union_files: set[str]) -> None:
    print("content_census_text:")
    print("  per_pattern_counts:")
    for label in CONTENT_CENSUS_PATTERNS:
        print(f"    {label}: {per_pattern[label]}")
    print(f"  union_count: {len(union_files)}")
    print("  union_files:")
    for filename in sorted(union_files):
        print(f"    - {filename}")


def print_binary_content_census(records: list[dict[str, object]]) -> None:
    print("content_census_binary:")
    print(f"  files_scanned: {len(records)}")
    print("  token_scan: latin-1 decode with errors=\"replace\"; case-insensitive substring match")
    print(f"  pdf_metadata_regex: {PDF_METADATA_REGEX}")
    for record in records:
        print(f"  - path: {record['path']}")
        matches = record["matched_tokens"]
        if matches:
            print("    matched_tokens:")
            for label in matches:
                print(f"      - {label}")
        else:
            print("    matched_tokens: none")
        metadata = record["pdf_metadata"]
        if metadata is None:
            continue
        found = {key: value for key, value in metadata.items() if value is not None}
        if not found:
            print("    pdf_metadata: none")
        else:
            print("    pdf_metadata:")
            for key in PDF_METADATA_KEYS:
                value = found.get(key)
                if value is not None:
                    print(f"      {key}: {value}")


def assert_render_not_older_than_sources() -> list[str]:
    """Fail if the compiled PDF predates any shipped paper source.

    A matching embedded-PDF hash proves which render ships; it says nothing about
    whether the sources beside it moved afterwards. A stale PDF next to a newer
    .bib or .tex is exactly how a fabricated bibliography entry reached a shipped
    archive while the hash assert passed on every run.
    """
    paper_dir = BASE / "docs/paper"
    main_pdf = paper_dir / "main.pdf"
    if not main_pdf.exists():
        return [f"missing render: {main_pdf}"]
    pdf_mtime = main_pdf.stat().st_mtime
    newer: list[str] = []
    for pattern in ("*.tex", "*.bib", "*.sty", "*.bst", "*.cls"):
        for source in sorted(paper_dir.glob(pattern)):
            if source.stat().st_mtime > pdf_mtime:
                newer.append(f"{source.name} (source is newer than main.pdf)")
    return newer


def content_census_guard(
    per_pattern: dict[str, int], union_files: set[str]
) -> list[str]:
    errors: list[str] = []
    baseline_files = set(EXPECTED_LEAK_BASELINE_FILES)
    new_files = sorted(union_files - baseline_files)
    if new_files:
        errors.append("files not in EXPECTED_LEAK_BASELINE_FILES:")
        errors.extend(f"  {filename}" for filename in new_files)
    for label in CONTENT_CENSUS_PATTERNS:
        baseline = EXPECTED_LEAK_BASELINE[label]
        observed = per_pattern[label]
        if observed > baseline:
            errors.append(
                f"{label}: observed count {observed} exceeds baseline {baseline}"
            )
    return errors


def binary_content_guard(records: list[dict[str, object]]) -> list[str]:
    """Fail on any leaking token or unexpected PDF metadata in a binary member.

    The binary census previously computed and printed these records without any
    consumer, so a figure PDF carrying an author name or a leak token would be
    detected and accepted. This gives the records a failure path.
    """
    errors: list[str] = []
    for record in records:
        path = str(record.get("path", "?"))
        tokens = record.get("matched_tokens") or []
        if tokens:
            errors.append(f"{path}: matched leak tokens {tokens}")
        metadata = record.get("pdf_metadata") or {}
        for key, value in metadata.items():
            # Empty string means the field is present but unset (the project's own
            # main.pdf carries "" for Author/Title/Subject/Keywords). Treat it as
            # absent, or every build would fail on a clean artifact.
            if value is None or str(value).strip() == "":
                continue
            if str(value).startswith(PDF_METADATA_ALLOWED_PREFIXES):
                continue
            errors.append(f"{path}: unexpected PDF metadata {key}={value!r}")
    return errors


def write_deterministic_archive(staging: Path, output: Path) -> tuple[str, int, int]:
    output.parent.mkdir(parents=True, exist_ok=True)
    entries = staged_files(staging)
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as gz:
            with tarfile.open(mode="w", fileobj=gz, format=tarfile.PAX_FORMAT) as tar:
                for rel in entries:
                    source = staging / rel
                    data = source.read_bytes()
                    info = tarfile.TarInfo(f"./{rel.as_posix()}")
                    info.size = len(data)
                    info.mtime = 0
                    info.mode = 0o644
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    with source.open("rb") as fh:
                        tar.addfile(info, fh)
    return sha256_file(output), output.stat().st_size, len(entries)


def print_errors(title: str, errors: list[str]) -> None:
    if not errors:
        return
    print(title, file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)


def print_summary(
    *,
    output: Path,
    archive_sha256: str,
    byte_size: int,
    entry_count: int,
    counts: dict[str, int],
    matched_hashes: int,
    mismatched_hashes: int,
    unresolved_ids: int,
    dry_run: bool,
) -> None:
    if dry_run:
        print("DRY RUN: archive not written")
    print(f"output_path: {output}")
    print(f"sha256: {archive_sha256}")
    print(f"byte_size: {byte_size}")
    print(f"entry_count: {entry_count}")
    print("per_category_counts:")
    for category in ("code", "data", "generators", "latex"):
        print(f"  {category}: {counts[category]}")
    print(f"matched_hash_count: {matched_hashes}")
    print(f"mismatched_hash_count: {mismatched_hashes}")
    print(f"unresolved_id_count: {unresolved_ids}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="archive path to write",
    )
    parser.add_argument(
        "--expected-main-pdf-sha256",
        default=EXPECTED_MAIN_PDF_SHA256,
        help="expected sha256 for docs/paper/main.pdf",
    )
    parser.add_argument(
        "--mirror-to",
        type=Path,
        default=REGISTERED_OUTPUT,
        help=(
            "path the manifest cites for this artifact; the built archive is copied "
            "there and verified byte-for-byte. Pass an empty value to skip."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and stage membership, but do not write the archive",
    )
    return parser.parse_args(argv)


def assert_matches_registered_hash(
    manifest: dict[str, dict], built_sha256: str, artifact_id: str
) -> list[str]:
    """Fail if the freshly built archive differs from the manifest's recorded hash.

    The mirror asserts built == registered, which catches a stale cited copy. It
    does not catch the next case up: if a rebuild produces different bytes, both
    paths agree with each other while the manifest's recorded hash goes stale, so
    the cited artifact diverges from what shipped with every other assert green.
    Re-pinning the manifest hash when the archive legitimately changes is the
    intended behaviour — that is exactly when the record needs updating.
    """
    entry = manifest.get(artifact_id)
    if entry is None:
        return []  # not yet registered; nothing to compare against
    recorded = entry.get("content_sha256")
    if not recorded:
        return [
            f"{artifact_id}: manifest entry carries no content_sha256",
            f"  set it to: {built_sha256}",
        ]
    if recorded != built_sha256:
        return [
            f"{artifact_id}: manifest hash does not match the built archive",
            f"  manifest: {recorded}",
            f"  built:    {built_sha256}",
            "  (re-pin the manifest if the archive change is intended)",
        ]
    return []


def mirror_to_registered_path(built: Path, registered: Path | None) -> list[str]:
    """Copy the built archive to the path the manifest cites, and verify by bytes.

    The script's default output and the registered artifact live at different
    paths. Re-running the build rewrites one and leaves the other at its old
    bytes, so the cited artifact silently goes stale while every other assert
    still passes (they check the paper PDF, not the cited tarball). This closes
    that gap by making the build write both and verify they agree.
    """
    # Path("") normalises to Path("."), so an empty string cannot be tested with
    # `is None` — it would fall through and copy onto the current directory.
    if registered is None or str(registered).strip() in ("", "."):
        return []
    if not built.exists():
        return [f"built archive missing: {built}"]
    if registered.is_dir():
        return [f"mirror target is a directory, not a file: {registered}"]
    registered.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(built, registered)
    built_sha = sha256_file(built)
    registered_sha = sha256_file(registered)
    if built_sha != registered_sha:
        return [
            "registered copy does not match the built archive:",
            f"  built:      {built_sha}  ({built})",
            f"  registered: {registered_sha}  ({registered})",
        ]
    os.chmod(registered, 0o644)
    print(f"mirrored to registered path: {registered}", file=sys.stderr)
    print(f"  sha256: {registered_sha}", file=sys.stderr)
    return []


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    manifest = load_manifest()

    main_pdf = BASE / "docs/paper/main.pdf"
    observed_pdf_sha = sha256_file(main_pdf)
    if observed_pdf_sha != args.expected_main_pdf_sha256:
        print("ERROR: STALE MAIN.PDF HASH MISMATCH", file=sys.stderr)
        print("file: docs/paper/main.pdf", file=sys.stderr)
        print(f"expected: {args.expected_main_pdf_sha256}", file=sys.stderr)
        print(f"observed: {observed_pdf_sha}", file=sys.stderr)
        return 1

    members, unresolved, mismatches, matched_hashes = build_member_list(
        manifest, args.expected_main_pdf_sha256
    )
    source_errors = assert_sources_exist(members)
    duplicate_errors = assert_unique_archive_paths(members)
    freshness_errors = assert_render_not_older_than_sources()
    # A user-supplied output that is a directory would otherwise raise a raw
    # IsADirectoryError from .open("wb") at write time. Pointing a build at a
    # directory is a natural way to test without touching the deliverable, so it
    # must fail here with a named message rather than a traceback.
    output_errors = []
    if args.output.is_dir():
        output_errors.append(f"--output is a directory, not a file: {args.output}")
    if str(args.mirror_to).strip() not in ("", ".") and args.mirror_to.is_dir():
        output_errors.append(
            f"--mirror-to is a directory, not a file: {args.mirror_to}"
        )
    all_preflight_errors = (
        unresolved
        + mismatches
        + source_errors
        + duplicate_errors
        + freshness_errors
        + output_errors
    )
    if all_preflight_errors:
        print_errors("ERROR: archive preflight failed", all_preflight_errors)
        return 1

    with tempfile.TemporaryDirectory(prefix="supplementary-build-") as temp_dir:
        staging = Path(temp_dir) / "staging"
        stage_members(staging, members)
        root_errors = assert_root_only(staging)
        if root_errors:
            print_errors("ERROR: STAGING ROOT ASSERT FAILED", root_errors)
            return 1
        coverage = coverage_errors(manifest, members)
        if coverage:
            print_errors("ERROR: CITED-ID COVERAGE ASSERT FAILED", coverage)
            return 1
        write_readme(staging, manifest)
        forbidden = forbidden_entries(staging)
        per_pattern, _per_file, union_files = content_census(staging)
        binary_records = binary_content_census(staging)
        print_content_census(per_pattern, union_files)
        print_binary_content_census(binary_records)
        content_errors = content_census_guard(per_pattern, union_files)
        binary_errors = binary_content_guard(binary_records)
        if forbidden:
            print_errors("ERROR: FORBIDDEN ARCHIVE ENTRIES", forbidden)
            return 1
        if content_errors:
            print_errors("ERROR: CONTENT CENSUS BASELINE GUARD FAILED", content_errors)
            return 1
        if binary_errors:
            print_errors("ERROR: BINARY CONTENT GUARD FAILED", binary_errors)
            return 1

        entries = staged_files(staging)
        counts = category_counts_from_staging(staging)
        if args.dry_run:
            print_summary(
                output=args.output,
                archive_sha256="not_written",
                byte_size=0,
                entry_count=len(entries),
                counts=counts,
                matched_hashes=matched_hashes,
                mismatched_hashes=len(mismatches),
                unresolved_ids=len(unresolved),
                dry_run=True,
            )
            return 0

        archive_sha, byte_size, entry_count = write_deterministic_archive(staging, args.output)
        hash_errors = assert_matches_registered_hash(
            manifest, archive_sha, REGISTERED_ARTIFACT_ID
        )
        if hash_errors:
            print_errors("ERROR: MANIFEST HASH MISMATCH", hash_errors)
            return 1
        mirror_errors = mirror_to_registered_path(args.output, args.mirror_to)
        if mirror_errors:
            print_errors("ERROR: MIRROR TO REGISTERED PATH FAILED", mirror_errors)
            return 1
        print_summary(
            output=args.output,
            archive_sha256=archive_sha,
            byte_size=byte_size,
            entry_count=entry_count,
            counts=counts,
            matched_hashes=matched_hashes,
            mismatched_hashes=len(mismatches),
            unresolved_ids=len(unresolved),
            dry_run=False,
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
