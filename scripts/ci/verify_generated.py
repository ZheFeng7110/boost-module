#!/usr/bin/env python3
"""Verify that the repository's generation steps are idempotent.

The repository commits the outputs of the generation scripts.  CI therefore
runs each step from a clean checkout and uses ``git diff`` as the oracle: a
step is allowed to create ignored caches, but it must not modify tracked
files (or leave non-ignored untracked files behind).

``import_boost.py`` is different from the other steps.  Re-vendoring restores
the upstream files and intentionally removes the project's vendored patches;
``reapply_hand_edits.py`` must be run afterwards.  The workflow runs this
optional pair only once, on the Linux leg, when ``import_boost.py`` changed
relative to the CI base revision.

Usage:
    python scripts/ci/verify_generated.py
    python scripts/ci/verify_generated.py --import-boost-if-changed
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
IMPORT_BOOST = "scripts/import_boost.py"


def git(*args, capture_output=False):
    """Run git in the repository root."""
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=capture_output,
        text=False,
    )


def git_text(*args):
    result = git(*args, capture_output=True)
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", errors="replace")


def assert_clean(step):
    """Fail if *step* changed tracked or non-ignored files."""
    diff = git("diff", "--exit-code", "HEAD", "--")
    status = git_text("status", "--porcelain=v1", "--untracked-files=all")
    if diff.returncode == 0 and not status:
        print("  clean: git diff --exit-code HEAD --")
        return

    print("\n{} left the working tree dirty.".format(step), file=sys.stderr)
    stat = git_text("diff", "--stat", "HEAD", "--")
    if stat:
        print(stat, file=sys.stderr, end="")
    if status:
        print("git status --porcelain:", file=sys.stderr)
        print(status, file=sys.stderr, end="")
    raise SystemExit(1)


def run_step(name, *arguments, check_diff=True):
    command = [sys.executable, str(SCRIPTS / name), *arguments]
    print("\n==> {}".format(" ".join(command)), flush=True)
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(
            "{} failed with exit code {}".format(name, result.returncode)
        )
    if check_diff:
        assert_clean(name)


def _revision_exists(revision):
    return git("rev-parse", "--verify", revision).returncode == 0


def _changed_since_base(path):
    """Return whether *path* changed in the current CI revision range."""
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    revisions = []

    if event == "pull_request":
        base_ref = os.environ.get("GITHUB_BASE_REF")
        if base_ref:
            revisions.extend(["origin/{}".format(base_ref), base_ref])
    elif event == "push":
        before = os.environ.get("GITHUB_EVENT_BEFORE")
        if before and set(before) != {"0"}:
            revisions.append(before)

    for base in revisions:
        if _revision_exists("{}^{{commit}}".format(base)):
            names = git_text("diff", "--name-only", "{}...HEAD".format(base), "--", path)
            if names is not None:
                return bool(names.strip())

    # Local runs and unusual GitHub events do not always provide a base ref.
    # HEAD^ is still a useful and deterministic fallback for the normal case.
    if _revision_exists("HEAD^{commit}"):
        names = git_text("diff", "--name-only", "HEAD^..HEAD", "--", path)
        if names is not None:
            return bool(names.strip())

    # An initial commit has no parent; inspect the complete tree instead.
    names = git_text("diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "HEAD", "--", path)
    return bool(names and names.strip())


def import_boost_changed():
    changed = _changed_since_base(IMPORT_BOOST)
    print(
        "{} changed in the CI revision range: {}".format(
            IMPORT_BOOST, "yes" if changed else "no"
        )
    )
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--import-boost-if-changed",
        action="store_true",
        help="run import_boost.py once when it changed since the CI base",
    )
    args = parser.parse_args()

    assert_clean("initial checkout")

    if args.import_boost_if_changed and import_boost_changed():
        # import_boost intentionally removes the vendored patches, so its
        # intermediate diff is expected.  The following reapply step is the
        # idempotent boundary checked by CI and restores the committed state.
        run_step("import_boost.py", check_diff=False)
        run_step("reapply_hand_edits.py")
    elif args.import_boost_if_changed:
        print("skip scripts/import_boost.py (unchanged)")

    # Keep this order aligned with docs/architecture.md §6 and the documented
    # regeneration flow: provision the pinned target headers, generate the
    # export surface, replay hand edits, then regenerate derived metadata.
    run_step("fetch_mingw_sysroot.py")
    # gen_exports emits drafts before the required hand-edit replay.  Its
    # intermediate diff is therefore expected; the replay below is the
    # idempotent boundary for this generation pair.
    run_step("gen_exports.py", "--emit-cppm", check_diff=False)
    run_step("reapply_hand_edits.py")
    run_step("gen_features.py")
    run_step("gen_features.py", "--check")
    run_step("gen_audit.py")
    run_step("gen_audit.py", "--macros")

    assert_clean("all generation steps")
    print("\nAll generated outputs are up to date and idempotent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
