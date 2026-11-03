#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Apply a change, inspect, or merge pull requests across a set of Charmed HPC
repositories.

Repository sets live in repos/: each file is a set of `owner/repo` lines, `#`
comments ignored. A path to a file in the same format works anywhere a set name
does. See README.md for the full workflow.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

PROG = "bulk-ops"
SETS_DIR = Path(__file__).resolve().parent / "repos"


def die(message: str) -> NoReturn:
    print(f"{PROG}: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_repos(set_name: str) -> list[str]:
    """Resolve a repository set to a list of ``owner/repo`` names.

    A set is either a path to a file of ``owner/repo`` lines (``#`` comments
    and blank lines ignored) or the name of a file in ``repos/``.
    """
    set_file = Path(set_name)
    if not set_file.is_file():
        set_file = SETS_DIR / set_name
    if not set_file.is_file():
        die(f"unknown repository set '{set_name}' (looked in {SETS_DIR}/)")

    repos = []
    for line in set_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            repos.append(line)
    if not repos:
        die(f"repository set '{set_name}' is empty")
    return repos


def require_gh() -> None:
    """Ensure the GitHub CLI is installed and authenticated."""
    if shutil.which("gh") is None:
        die("the GitHub CLI (gh) is required")
    auth = subprocess.run(
        ["gh", "auth", "status"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if auth.returncode != 0:
        die("not logged in to the GitHub CLI (run 'gh auth login')")


def list_open_prs(repo: str, branch: str, fields: list[str]) -> list[dict] | None:
    """Return the open pull requests for ``branch`` on ``repo``.

    Returns None if the query itself failed (the error is printed).
    """
    result = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo,
            "--head",
            branch,
            "--state",
            "open",
            "--json",
            ",".join(fields),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            f"gh pr list failed for {repo}: {result.stderr.strip()}",
            file=sys.stderr,
        )
        return None
    return json.loads(result.stdout or "[]")


def print_summary(set_name: str, results: dict[str, list[str]]) -> None:
    """Print the per-outcome summary shared by the push and merge commands."""
    print()
    print(f"Summary for set '{set_name}':")
    for label, repos in results.items():
        names = "".join(f" {repo}" for repo in repos)
        print(f"  {label + ':':<9}{len(repos)}{names}")


def run_git(
    workdir: str, *args: str, check: bool = True
) -> subprocess.CompletedProcess:
    """Run git in the clone at ``workdir``, capturing its output."""
    result = subprocess.run(["git", "-C", workdir, *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def open_pr(repo: str, args: argparse.Namespace, title: str) -> bool:
    """Open a pull request for the pushed branch, or report the existing one.

    Returns True if a pull request exists or was opened.
    """
    prs = list_open_prs(repo, args.branch, ["number"])
    if prs is None:
        print(
            "    pushed branch, but failed to check for existing pull request",
            file=sys.stderr,
        )
        return False
    if prs:
        print("    updated existing pull request")
        return True

    create_cmd = [
        "gh",
        "pr",
        "create",
        "--repo",
        repo,
        "--title",
        title,
        "--body",
        args.body,
        "--head",
        args.branch,
    ]
    if args.draft:
        create_cmd.append("--draft")
    if args.reviewers:
        create_cmd.extend(["--reviewer", args.reviewers])
    created = subprocess.run(create_cmd, capture_output=True, text=True)
    if created.returncode != 0:
        print(
            f"    pushed branch, but failed to open pull request:"
            f" {created.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    print(f"    opened {created.stdout.strip()}")
    return True


def push_repo(repo: str, args: argparse.Namespace, title: str) -> str:
    """Clone ``repo``, run the command in it, then commit, push, and open a PR.

    Returns "pushed", "skipped", "failed", or "dry-run".
    """
    workdir = tempfile.mkdtemp(prefix="bulk-ops-")
    try:
        cloned = subprocess.run(
            ["gh", "repo", "clone", repo, workdir, "--", "--depth", "1", "--quiet"],
            capture_output=True,
            text=True,
        )
        if cloned.returncode != 0:
            print("    failed to clone", file=sys.stderr)
            return "failed"

        env = {**os.environ, "REPO": repo, "REPO_DIR": workdir}
        if subprocess.run(args.command, cwd=workdir, env=env).returncode != 0:
            if not args.interactive:
                print("    command failed", file=sys.stderr)
                return "failed"
            print(f"    command failed: {' '.join(args.command)}", file=sys.stderr)
            print(f"    opening a shell in the clone at {workdir}")
            print("    resolve the issue, then exit the shell to continue.")
            print("    for a failed patch: git apply --3way <patch>, fix conflicts, git add")
            print("    exit with no changes to mark the repository as failed.")
            shell = os.environ.get("SHELL") or "/bin/sh"
            subprocess.run([shell, "-i"], cwd=workdir, env=env)
            run_git(workdir, "add", "-A")
            if run_git(workdir, "diff", "--cached", "--quiet", check=False).returncode == 0:
                print("    no changes after recovery, marking as failed", file=sys.stderr)
                return "failed"
            if run_git(workdir, "grep", "-l", "^<<<<<<< ", "--", ".", check=False).stdout.strip():
                print("    conflict markers remain, marking as failed", file=sys.stderr)
                return "failed"
            print("    recovered, continuing")

        if args.dry_run:
            run_git(workdir, "add", "-A")
            subprocess.run(["git", "-C", workdir, "diff", "--cached", "--stat"])
            return "dry-run"

        try:
            run_git(workdir, "checkout", "--quiet", "-b", args.branch)
            run_git(workdir, "add", "-A")
            if run_git(workdir, "diff", "--cached", "--quiet", check=False).returncode == 0:
                print("    no changes, skipping")
                return "skipped"
            run_git(workdir, "commit", "--quiet", "-m", args.message)
            remote = run_git(
                workdir,
                "ls-remote",
                "--exit-code",
                "origin",
                f"refs/heads/{args.branch}",
                check=False,
            )
            if remote.returncode == 0:
                run_git(workdir, "fetch", "--quiet", "origin", args.branch)
                run_git(workdir, "push", "--quiet", "--force-with-lease", "origin", args.branch)
            else:
                run_git(workdir, "push", "--quiet", "-u", "origin", args.branch)
        except RuntimeError as error:
            print(f"    failed to commit or push: {error}", file=sys.stderr)
            return "failed"

        return "pushed" if open_pr(repo, args, title) else "failed"
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def cmd_push(args: argparse.Namespace) -> int:
    title = args.title or args.message
    repos = load_repos(args.set)
    require_gh()

    results: dict[str, list[str]] = {"pushed": [], "skipped": [], "failed": []}
    for repo in repos:
        print(f"==> {repo}")
        outcome = push_repo(repo, args, title)
        if outcome in results:
            results[outcome].append(repo)

    print_summary(args.set, results)
    return 1 if results["failed"] else 0


def cmd_status(args: argparse.Namespace) -> int:
    repos = load_repos(args.set)
    require_gh()

    errors = 0
    for repo in repos:
        prs = list_open_prs(
            repo, args.branch, ["url", "mergeStateStatus", "reviewDecision"]
        )
        if prs is None:
            errors += 1
            continue
        if not prs:
            print(f"{repo:<40} no open pull request")
            continue
        for pr in prs:
            state = pr.get("mergeStateStatus") or "unknown"
            review = pr.get("reviewDecision") or "no-review"
            print(f"{repo:<40} {pr['url']}\t{state}\t{review}")
    return 1 if errors else 0


def cmd_merge(args: argparse.Namespace) -> int:
    repos = load_repos(args.set)
    require_gh()

    merged: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []

    for repo in repos:
        print(f"==> {repo}")

        prs = list_open_prs(repo, args.branch, ["number", "url", "mergeStateStatus"])
        if prs is None:
            failed.append(repo)
            continue
        if not prs:
            print(f"    no open pull request for branch '{args.branch}', skipping")
            skipped.append(repo)
            continue

        pr = prs[0]
        state = pr.get("mergeStateStatus") or "unknown"

        if args.dry_run:
            print(f"    would merge {pr['url']} (merge state: {state})")
            merged.append(repo)
            continue

        if args.approve:
            review = subprocess.run(
                ["gh", "pr", "review", "--repo", repo, str(pr["number"]), "--approve"],
                capture_output=True,
                text=True,
            )
            if review.returncode != 0:
                print(
                    "    warning: could not approve (already approved, or own pull"
                    " request?)",
                    file=sys.stderr,
                )

        merge_cmd = [
            "gh",
            "pr",
            "merge",
            "--repo",
            repo,
            str(pr["number"]),
            f"--{args.method}",
        ]
        if args.auto:
            merge_cmd.append("--auto")
        if args.delete_branch:
            merge_cmd.append("--delete-branch")

        if subprocess.run(merge_cmd).returncode == 0:
            print(f"    merged {pr['url']}")
            merged.append(repo)
        else:
            print(f"    failed to merge {pr['url']} (merge state: {state})", file=sys.stderr)
            failed.append(repo)

    print_summary(args.set, {"merged": merged, "skipped": skipped, "failed": failed})
    return 1 if failed else 0


def build_parser() -> tuple[argparse.ArgumentParser, argparse.ArgumentParser]:
    """Build the CLI parser; returns the root parser and the push subparser."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-s",
        "--set",
        required=True,
        help=(
            "repository set name from repos/ (e.g. 'charms', 'all') or a path"
            " to a file listing repositories"
        ),
    )
    common.add_argument(
        "-b",
        "--branch",
        required=True,
        help="head branch of the pull requests on each repository",
    )

    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Apply a change, inspect, or merge pull requests across a set of"
            " repositories."
        ),
    )
    sub = parser.add_subparsers(
        dest="action", required=True, metavar="{push,status,merge}"
    )

    push = sub.add_parser(
        "push",
        parents=[common],
        help="apply a change and open (or update) a pull request on each repository",
        description=(
            "Apply a change across a set of repositories, then push a branch and"
            " open (or update) a pull request on each repository."
        ),
        epilog=(
            "The command after '--' runs at the root of each cloned repository with"
            " the REPO (owner/name) and REPO_DIR environment variables set."
            " Repositories where the command produces no changes are skipped."
            " Re-running with the same branch name force-pushes and updates the"
            " existing pull request rather than opening a duplicate.\n\n"
            "example:\n"
            "  bulk-ops push -s charms -b chore/sync-contributing \\\n"
            '    -m "chore: sync CONTRIBUTING.md from hpc-team" \\\n'
            "    -- cp \"$HOME/hpc-team/CONTRIBUTING.md\" CONTRIBUTING.md"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    push.add_argument(
        "-m",
        "--message",
        required=True,
        help="commit message; also used as the default PR title",
    )
    push.add_argument(
        "-t", "--title", help="PR title (defaults to the commit message)"
    )
    push.add_argument("--body", default="", help="PR body")
    push.add_argument(
        "--reviewers",
        help=(
            "comma-separated GitHub users/teams to request review from on each"
            " new PR"
        ),
    )
    push.add_argument(
        "--draft", action="store_true", help="open pull requests as drafts"
    )
    push.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help=(
            "if the command fails on a repository, open a shell in the clone to"
            " resolve the issue manually, then continue with the resolved changes"
        ),
    )
    push.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help=(
            "clone and run the command, show the resulting diff for each"
            " repository, but do not commit or push"
        ),
    )
    push.set_defaults(func=cmd_push)

    status = sub.add_parser(
        "status",
        parents=[common],
        help="show the status of the pull requests opened by push",
        description=(
            "Show the status of the pull requests opened by 'bulk-ops push'"
            " across a set of repositories."
        ),
    )
    status.set_defaults(func=cmd_status)

    merge = sub.add_parser(
        "merge",
        parents=[common],
        help="merge the pull requests opened by push",
        description=(
            "Merge (and optionally approve) the pull requests opened by"
            " 'bulk-ops push' across a set of repositories."
        ),
    )
    merge.add_argument(
        "-m",
        "--method",
        choices=("squash", "merge", "rebase"),
        default="squash",
        help="merge method (default: squash)",
    )
    merge.add_argument(
        "--approve",
        action="store_true",
        help=(
            "approve each pull request before merging; only use this if scripted"
            " approval complies with the repository's branch protection and"
            " review policy"
        ),
    )
    merge.add_argument(
        "--auto",
        action="store_true",
        help=(
            "enable auto-merge so each pull request merges only after its"
            " required checks pass (recommended)"
        ),
    )
    merge.add_argument(
        "--delete-branch",
        action="store_true",
        help="delete each head branch after merging",
    )
    merge.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="show what would be merged without changing anything",
    )
    merge.set_defaults(func=cmd_merge)

    return parser, push


def main() -> int:
    # Split the arguments at '--' so the push command may contain arbitrary options.
    argv = sys.argv[1:]
    command = []
    if "--" in argv:
        split = argv.index("--")
        command, argv = argv[split + 1 :], argv[:split]

    parser, push = build_parser()
    args = parser.parse_args(argv)
    args.command = command
    if args.action == "push" and not command:
        push.error("missing command after '--'")
    return args.func(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
