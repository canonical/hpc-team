#!/usr/bin/env python3
"""Atomic mutation-testing harness for Phase 4 of `write-charm-unit-tests`.

Copy this template into the target repo (or a scratch dir), adapt CONFIG,
define mutations in MUTATIONS, and run:

    python3 mutate.py M1 M2 ...

Each mutation is applied to the STAGED copy, the full unit suite runs, and
the file is restored — all inside one process. Verdicts (KILLED/SURVIVED and
the killing tests) are parsed from junit XML.

Why this exact shape — every constraint below was learned from a real failure:

- Apply -> run -> restore must be atomic (one process). A mutation left
  applied across tool invocations can silently vanish from the staged copy,
  and the next run then reports a false SURVIVED that condemns a sound test.
- The harness asserts the staged file is pristine before each mutation and
  verifies the restore afterward, so a campaign can never end with mutated
  source or run against a half-mutated tree.
- Verdicts come from junit XML, with pytest invoked as
  `--tb=no -rN -p no:warnings --junitxml=<path>`. pytest's terminal failure
  rendering can itself crash (pytest 9 + pyfakefs: ValueError in bestrelpath
  on identical paths), and a crashed run reports nothing.
- In repos that stage charms into a build directory, STAGED must point at
  the staged copy and PRISTINE at the source tree. Re-sync the staging
  before the campaign: a stale staged copy silently tests old code.

This file is a template, not a tool. It is meant to be copied, adapted, and
deleted from the target repo when the campaign is finished.
"""

import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# --- ADAPT FOR THE TARGET REPO -------------------------------------------------
# Worked example: a repo that stages charms into a build directory (_build/).
# For a repo whose tests import src/ directly, point STAGED and PRISTINE at the
# same src tree and keep a pristine backup copy elsewhere instead.
ROOT = Path("/path/to/target-repo").resolve()  # repo root
STAGED = ROOT / "_build" / "<charm>" / "src"  # code under test (staged copy)
PRISTINE = ROOT / "charms" / "<charm>" / "src"  # pristine source used to restore
TESTS = ROOT / "_build" / "<charm>" / "tests" / "unit"  # test dir passed to pytest
PYTEST = ROOT / ".venv" / "bin" / "pytest"  # pytest executable
PYTHONPATH = [  # import path for the charm under test (staged src first, then lib)
    str(STAGED),
    str(ROOT / "_build" / "<charm>" / "lib"),
]
XML = ROOT / "_build" / ".mutation-results.xml"  # writable scratch location
# --------------------------------------------------------------------------------

# id -> (file relative to the src dir, exact old text, replacement text)
# Keep mutations small and plausible: the bug a real contributor would write.
# The old text must occur exactly once in the file — the harness asserts it.
MUTATIONS = {
    # Drop a keyword argument so the callee applies a different default.
    "M1": (
        "config.py",
        "_initialize_config_file(config_path, force=True)",
        "_initialize_config_file(config_path)",
    ),
    # Turn an unconditional assignment into a first-write-only setdefault.
    "M2": (
        "config.py",
        'config.options["example_enabled"] = True',
        'config.options.setdefault("example_enabled", True)',
    ),
    # "M3": ("charm.py", "        self.helper.delete_stale_state()\n", ""),  # delete a cleanup call
}


def run_suite() -> tuple[dict, list[str]]:
    """Run the full unit suite; return (junit suite attrs, failing test names)."""
    subprocess.run(
        [
            str(PYTEST),
            str(TESTS),
            "-q",
            "--tb=no",
            "-rN",
            "-p",
            "no:warnings",
            f"--junitxml={XML}",
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": ":".join(PYTHONPATH)},
    )
    root = ET.parse(XML).getroot()
    suite = root.find("testsuite")
    attrib = suite.attrib if suite is not None else {}
    failed = []
    for tc in root.iter("testcase"):
        if tc.find("failure") is not None or tc.find("error") is not None:
            failed.append(tc.attrib["classname"].split(".")[-1] + "::" + tc.attrib["name"])
    return attrib, failed


def main() -> None:
    if not sys.argv[1:]:
        sys.exit(f"usage: {sys.argv[0]} M1 [M2 ...]  (defined: {', '.join(MUTATIONS)})")

    for mid in sys.argv[1:]:
        rel, old, new = MUTATIONS[mid]
        staged_file = STAGED / rel
        pristine_file = PRISTINE / rel
        pristine = pristine_file.read_text()
        original = staged_file.read_text()
        assert original == pristine, f"{mid}: staged {rel} is not pristine before mutation"
        count = original.count(old)
        assert count == 1, f"{mid}: expected exactly 1 match, got {count}"
        staged_file.write_text(original.replace(old, new))

        try:
            attrib, failed = run_suite()
        finally:
            staged_file.write_text(pristine)
            assert staged_file.read_text() == pristine_file.read_text(), f"{mid}: restore failed"

        verdict = "KILLED" if failed else "SURVIVED"
        print(f"=== {mid} ({rel}): {verdict} ===")
        print(
            f"    {attrib.get('tests')} tests | {attrib.get('failures', 0)} failures | "
            f"{attrib.get('errors', 0)} errors"
        )
        for f in failed:
            print(f"    KILLED_BY: {f}")


if __name__ == "__main__":
    main()
