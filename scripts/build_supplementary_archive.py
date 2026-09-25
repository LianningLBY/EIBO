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
EXPECTED_MAIN_PDF_SHA256 = "de5e4b63e24d830f9606f7783fe37835fe23a25d0b2b4b7a6031b10b1060f15d"


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
        raise ValueError(f"manifest path escapes /efs/workspace: {raw_path}") from exc
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
        if source.suffix in {".tex", ".bib", ".sty"}:
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
            "All included payloads are resolved from local manifest paths under `/efs/workspace`.",
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


def write_deterministic_archive(staging: Path, output: Path) -> tuple[str, int, int]:
    output.parent.mkdir(parents=True, exist_ok=True)
    entries = staged_files(staging)
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as gz:
            with tarfile.open(mode="w", fileobj=gz, format=tarfile.PAX_FORMAT) as tar:
                for rel in entries:
                    source = staging / rel
                    data = source.read_bytes()
                    info = tarfile.TarInfo(rel.as_posix())
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
        help=f"archive path to write; default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--expected-main-pdf-sha256",
        default=EXPECTED_MAIN_PDF_SHA256,
        help="expected sha256 for docs/paper/main.pdf",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and stage membership, but do not write the archive",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    manifest = load_manifest()

    main_pdf = BASE / "docs/paper/main.pdf"
    observed_pdf_sha = sha256_file(main_pdf)
    if observed_pdf_sha != args.expected_main_pdf_sha256:
        print("ERROR: STALE MAIN.PDF HASH MISMATCH", file=sys.stderr)
        print(f"file: {main_pdf}", file=sys.stderr)
        print(f"expected: {args.expected_main_pdf_sha256}", file=sys.stderr)
        print(f"observed: {observed_pdf_sha}", file=sys.stderr)
        return 1

    members, unresolved, mismatches, matched_hashes = build_member_list(
        manifest, args.expected_main_pdf_sha256
    )
    source_errors = assert_sources_exist(members)
    duplicate_errors = assert_unique_archive_paths(members)
    all_preflight_errors = unresolved + mismatches + source_errors + duplicate_errors
    if all_preflight_errors:
        print_errors("ERROR: archive preflight failed", all_preflight_errors)
        return 1

    with tempfile.TemporaryDirectory(prefix="supplementary-build-") as temp_dir:
        staging = Path(temp_dir) / "staging"
        stage_members(staging, members)
        coverage = coverage_errors(manifest, members)
        if coverage:
            print_errors("ERROR: CITED-ID COVERAGE ASSERT FAILED", coverage)
            return 1
        write_readme(staging, manifest)
        forbidden = forbidden_entries(staging)
        if forbidden:
            print_errors("ERROR: FORBIDDEN ARCHIVE ENTRIES", forbidden)
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
