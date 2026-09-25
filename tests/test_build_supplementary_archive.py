# Argument-surface and consumer coverage for the supplementary archive builder.
#
# Three defects in this script shared one shape: new code that was correct on the
# line that runs, with the defect one step off it — a flag whose skip-branch had
# never executed (--mirror-to ""), a path argument with no directory guard
# (--output /tmp), and a scan whose return value nothing consumed
# (binary_content_census was printed and dropped). Each was found by review, not
# by the test suite.
#
# So these tests are written as MECHANISMS, not as cases: they enumerate the
# script's own argument surface and its own validation functions, and fail when
# one is added without a demonstrated non-firing branch and a named consumer.
# A new argument or guard is covered automatically; there is no list to forget
# to update.
#
# Convention follows tests/test_q1_thresholds.py: unittest, importlib for the
# standalone script, no pytest dependency.

from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Overridable so the suite's own ability to fail can be demonstrated against a
# deliberately-mutated copy, without touching the real script.
SCRIPT = Path(
    os.environ.get("BSA_SCRIPT", str(ROOT / "scripts" / "build_supplementary_archive.py"))
)

_spec = importlib.util.spec_from_file_location("build_supplementary_archive", SCRIPT)
bsa = importlib.util.module_from_spec(_spec)
sys.modules["build_supplementary_archive"] = bsa
_spec.loader.exec_module(bsa)

SOURCE = SCRIPT.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


def _main_node() -> ast.FunctionDef:
    for node in TREE.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            return node
    raise AssertionError("main() not found")


def _path_arguments() -> list[str]:
    """CLI options whose argparse type is Path (from bsa's own parser)."""
    parser = bsa.parse_args.__globals__
    import argparse

    prog = argparse.ArgumentParser()
    # Rebuild the parser by calling parse_args with --help suppressed is fragile;
    # instead introspect the function's source for add_argument pairs.
    found: list[str] = []
    for node in ast.walk(TREE):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "add_argument":
            continue
        flag = node.args[0].value if node.args and isinstance(node.args[0], ast.Constant) else None
        is_path = any(
            kw.arg == "type" and isinstance(kw.value, ast.Name) and kw.value.id == "Path"
            for kw in node.keywords
        )
        if flag and is_path:
            found.append(flag)
    return sorted(found)


def _error_returning_functions() -> list[str]:
    """Top-level functions whose annotation is exactly list[str] (error-list shaped)."""
    names: list[str] = []
    for node in TREE.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        rendered = ast.unparse(node.returns) if node.returns is not None else ""
        if rendered.replace(" ", "") == "list[str]":
            names.append(node.name)
    return sorted(names)


# Functions that produce data rather than validate it. They are error-list shaped
# (they return a list of strings) but they are inputs to guards, not guards: an
# empty result is a legitimate answer, not a failure. Listed explicitly so the
# distinction is visible rather than implied by a naming convention.
DATA_PRODUCERS = frozenset({"unique_ids", "data_ids", "extract_cited_ids_from_tex"})


def _guard_functions() -> list[str]:
    return sorted(set(_error_returning_functions()) - DATA_PRODUCERS)


def _call_assignments_in_main() -> dict[str, str]:
    """Map function name -> variable it is assigned to inside main()."""
    assigned: dict[str, str] = {}
    main = _main_node()
    for node in ast.walk(main):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        value = node.value
        if not isinstance(target, ast.Name) or not isinstance(value, ast.Call):
            continue
        fn = value.func
        fname = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", None)
        if fname:
            assigned[fname] = target.id
    return assigned


def _names_tested_in_main() -> set[str]:
    """Variable names whose truthy branch causes main() to return non-zero.

    Reaching a conditional is NOT sufficient. binary_content_census originally
    had its records printed inside an ``if`` and the branch simply fell through,
    so the build succeeded — the defect was *detected and displayed, not
    enforced*. This walks only into ``if`` bodies that actually contain a
    non-zero return, which is the property that can fail a build.
    """
    main = _main_node()
    tested: set[str] = set()

    def branch_fails(body: list[ast.stmt]) -> bool:
        for stmt in body:
            if isinstance(stmt, ast.Return):
                v = stmt.value
                if isinstance(v, ast.Constant) and isinstance(v.value, int) and v.value != 0:
                    return True
            # sys.exit / raise also fail the build
            if isinstance(stmt, ast.Raise):
                return True
            for sub in ast.walk(stmt):
                if isinstance(sub, ast.Call):
                    fn = sub.func
                    if isinstance(fn, ast.Attribute) and fn.attr in ("exit", "system_exit"):
                        return True
        return False

    for node in ast.walk(main):
        if isinstance(node, ast.If) and branch_fails(node.body):
            for sub in ast.walk(node.test):
                if isinstance(sub, ast.Name):
                    tested.add(sub.id)
    # propagate: names summed into a tested aggregate
    changed = True
    while changed:
        changed = False
        for node in ast.walk(main):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name) or target.id not in tested:
                continue
            for sub in ast.walk(node.value):
                if isinstance(sub, ast.Name) and sub.id not in tested:
                    tested.add(sub.id)
                    changed = True
    return tested


def _consumed_guards() -> dict[str, bool]:
    """For each guard, whether main() tests the result of calling it.

    Checking that a guard *exists* is not enough — binary_content_census existed
    and was printed while its records were dropped. The property that matters is
    that the returned error list reaches a conditional, which is the only thing
    that can fail a build.
    """
    assigned = _call_assignments_in_main()
    tested = _names_tested_in_main()
    result: dict[str, bool] = {}
    for name in _guard_functions():
        var = assigned.get(name)
        result[name] = var is not None and var in tested
    return result


class TestArgumentSurface(unittest.TestCase):
    """MECHANISM: every Path-typed CLI argument must reject a directory cleanly.

    The defect this encodes: --output /tmp raised a raw IsADirectoryError from
    .open("wb") because only the mirror path had been hardened. A test written
    against that one flag would not have caught the sibling. This enumerates the
    parser's own Path arguments, so a newly added path option is covered the
    moment it exists.
    """

    def test_there_is_at_least_one_path_argument(self):
        # guards against the introspection silently returning nothing
        self.assertTrue(_path_arguments(), "no Path-typed arguments discovered")

    def test_each_path_argument_rejects_a_directory(self):
        args = _path_arguments()
        sha = bsa.sha256_file(ROOT / "docs" / "paper" / "main.pdf")
        for flag in args:
            with self.subTest(flag=flag), tempfile.TemporaryDirectory() as tmp:
                argv = [
                    sys.executable,
                    str(SCRIPT),
                    "--expected-main-pdf-sha256",
                    sha,
                    flag,
                    tmp,  # a directory, the natural "test without touching it" value
                ]
                # neutralise the other path argument so only this one is under test
                for other in args:
                    if other != flag:
                        argv += [other, ""]
                proc = subprocess.run(argv, capture_output=True, text=True)
                self.assertEqual(proc.returncode, 1, f"{flag}: expected exit 1")
                combined = proc.stdout + proc.stderr
                self.assertNotIn(
                    "Traceback", combined, f"{flag}: raised a traceback instead of an error"
                )
                self.assertIn(
                    "is a directory", combined, f"{flag}: no named directory error"
                )

    def test_empty_value_skips_the_mirror(self):
        """The documented off-switch: --mirror-to "" must skip, not crash."""
        self.assertEqual(bsa.mirror_to_registered_path(Path("x"), Path("")), [])
        self.assertEqual(bsa.mirror_to_registered_path(Path("x"), Path(".")), [])
        self.assertEqual(bsa.mirror_to_registered_path(Path("x"), None), [])


class TestGuardConsumers(unittest.TestCase):
    """MECHANISM: every validation function must be called AND its result tested.

    The defect this encodes: binary_content_census computed leak records, printed
    them, and dropped them — the guard that would consume them did not exist, so
    a leaking figure PDF was detected and accepted. Checking only that a function
    exists would have passed. This asserts the result reaches a conditional in
    main(), so a new guard that is written but not wired fails here.
    """

    def test_guard_functions_are_discovered(self):
        self.assertTrue(
            _guard_functions(), "no list[str]-returning guards discovered"
        )

    def test_every_guard_is_called_and_its_result_tested_in_main(self):
        consumed = _consumed_guards()
        unwired = sorted(n for n, ok in consumed.items() if not ok)
        self.assertEqual(
            unwired,
            [],
            "these validation functions are not both called and tested in main(): "
            f"{unwired} — a guard whose result is unused cannot fail a build",
        )


class TestGuardFailurePaths(unittest.TestCase):
    """MECHANISM: every guard must be shown to fire, with a negative case.

    Registry keyed by guard name. The coverage test below fails if a guard is
    added to the script without a registered bad-input case, so the suite cannot
    silently fall behind the script.
    """

    def _bad_input_cases(self) -> dict[str, object]:
        return {
            "assert_root_only": lambda: bsa.assert_root_only(self._staging_with_stray()),
            "assert_sources_exist": lambda: bsa.assert_sources_exist([self._ghost_member()]),
            "assert_unique_archive_paths": lambda: bsa.assert_unique_archive_paths(
                [self._dup_member(), self._dup_member()]
            ),
            "assert_render_not_older_than_sources": lambda: self._freshness_with_newer_source(),
            "coverage_errors": lambda: bsa.coverage_errors(
                {}, [self._ghost_member()]
            ),
            "forbidden_entries": lambda: bsa.forbidden_entries(self._staging_with_forbidden()),
            "content_census_guard": lambda: bsa.content_census_guard(self._grown_census(), set()),
            "binary_content_guard": lambda: bsa.binary_content_guard(self._leaking_binary()),
            "assert_matches_registered_hash": lambda: bsa.assert_matches_registered_hash(
                {bsa.REGISTERED_ARTIFACT_ID: {"content_sha256": "0" * 64}},
                "1" * 64,
                bsa.REGISTERED_ARTIFACT_ID,
            ),
            "mirror_to_registered_path": lambda: bsa.mirror_to_registered_path(
                Path("/nonexistent/absent.tar.gz"), Path(tempfile.mkdtemp()) / "x.tar.gz"
            ),
        }

    @staticmethod
    def _ghost_member():
        return bsa.Member(
            category="data",
            source=Path("/nonexistent/absent_payload.json"),
            archive_path=Path("supplementary/data/absent_payload.json"),
        )

    @staticmethod
    def _dup_member():
        return bsa.Member(
            category="data",
            source=ROOT / "docs/paper/main.pdf",
            archive_path=Path("supplementary/data/same.json"),
        )

    @staticmethod
    def _staging_with_forbidden() -> Path:
        tmp = Path(tempfile.mkdtemp())
        (tmp / "supplementary" / "data").mkdir(parents=True)
        (tmp / "supplementary" / "data" / "x.RETIRED_do_not_cite.json").write_text("{}")
        return tmp

    @staticmethod
    def _freshness_with_newer_source() -> list[str]:
        """Exercise the freshness guard against a temp tree, never the real one."""
        tmp = Path(tempfile.mkdtemp())
        paper = tmp / "docs" / "paper"
        paper.mkdir(parents=True)
        pdf = paper / "main.pdf"
        src = paper / "references.bib"
        pdf.write_bytes(b"%PDF-1.4\n")
        src.write_text("@article{x,}\n")
        # make the source strictly newer than the render
        future = pdf.stat().st_mtime + 300
        import os

        os.utime(src, (future, future))
        original_base = bsa.BASE
        try:
            bsa.BASE = tmp
            return bsa.assert_render_not_older_than_sources()
        finally:
            bsa.BASE = original_base

    @staticmethod
    def _staging_with_stray() -> Path:
        tmp = Path(tempfile.mkdtemp())
        (tmp / "supplementary" / "data").mkdir(parents=True)
        (tmp / "supplementary" / "data" / "ok.txt").write_text("x")
        (tmp / "stray.txt").write_text("x")
        return tmp

    @staticmethod
    def _grown_census() -> dict[str, int]:
        census = {k: 0 for k in bsa.CONTENT_CENSUS_PATTERNS}
        census.update(dict(bsa.EXPECTED_LEAK_BASELINE))
        first = next(iter(bsa.EXPECTED_LEAK_BASELINE))
        census[first] = bsa.EXPECTED_LEAK_BASELINE[first] + 1
        return census

    @staticmethod
    def _leaking_binary() -> list[dict[str, object]]:
        return [
            {
                "path": "supplementary/latex/fig.pdf",
                "matched_tokens": ["eibo"],
                "pdf_metadata": {"Author": "Jane Doe, Example University"},
            }
        ]

    def test_guard_registry_covers_every_guard_in_the_script(self):
        known = set(self._bad_input_cases())
        actual = set(_guard_functions())
        missing = sorted(actual - known)
        self.assertEqual(
            missing,
            [],
            "guards present in the script but with no registered bad-input case: "
            f"{missing} — add one so the guard is proven able to fail",
        )
        stale = sorted(known - actual)
        self.assertEqual(
            stale,
            [],
            f"registry names functions that are no longer guards: {stale}",
        )

    def test_each_guard_fires_on_its_bad_input(self):
        for name, make in self._bad_input_cases().items():
            with self.subTest(guard=name):
                result = make()
                self.assertIsInstance(result, list, f"{name}: not an error list")
                self.assertTrue(result, f"{name}: did not fire on bad input")


class TestGoodInputIsSilent(unittest.TestCase):
    """A guard that fires on correct input is worse than none — pair each with a pass."""

    def test_clean_binary_records_do_not_fire(self):
        clean = [
            {
                "path": "supplementary/latex/main.pdf",
                "matched_tokens": [],
                "pdf_metadata": {
                    "Author": "",
                    "Producer": "pdfTeX-1.40.26",
                    "Title": "",
                    "Creator": "LaTeX with hyperref",
                    "Subject": "",
                    "Keywords": "",
                },
            }
        ]
        self.assertEqual(bsa.binary_content_guard(clean), [])

    def test_census_at_baseline_does_not_fire(self):
        census = {k: 0 for k in bsa.CONTENT_CENSUS_PATTERNS}
        census.update(dict(bsa.EXPECTED_LEAK_BASELINE))
        self.assertEqual(bsa.content_census_guard(census, set()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
