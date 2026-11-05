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

The workflow is split into steps that operate on a cached set of clones
(default ~/.cache/bulk-ops), so each step is fast to re-run: `clone` clones or
updates the repositories of a set, `exec` runs a command in each clone, and
`push` commits each clone's changes, pushes the branch to a fork (created
automatically), and opens or updates the pull requests in one bulk step.
"""

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

PROG = "bulk-ops"
SETS_DIR = Path(__file__).resolve().parent / "repos"
DEFAULT_WORKDIR = Path.home() / ".cache" / "bulk-ops"


def die(message: str) -> NoReturn:
    print(f"{PROG}: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run ``cmd`` and capture its output."""
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def git(workdir: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run git in ``workdir`` and capture its output."""
    result = run(["git", "-C", str(workdir), *args])
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result


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


def gh_login() -> str:
    """Return the login of the authenticated GitHub user."""
    result = run(["gh", "api", "user", "--jq", ".login"])
    if result.returncode != 0:
        die(f"could not determine GitHub login: {result.stderr.strip()}")
    return result.stdout.strip()


def repo_dir(workdir: Path, repo: str) -> Path:
    """Return the cache directory of ``repo`` (``owner/name``) in ``workdir``."""
    if "/" not in repo:
        die(f"invalid repository '{repo}', expected 'owner/name'")
    owner, name = repo.split("/", 1)
    return workdir / owner / name


def default_branch(workdir: Path) -> str:
    """Return the default branch of the repository cloned at ``workdir``."""
    head = git(workdir, "rev-parse", "--abbrev-ref", "origin/HEAD", check=False)
    if head.returncode == 0 and head.stdout.strip().startswith("origin/"):
        return head.stdout.strip()[len("origin/") :]
    symref = git(workdir, "ls-remote", "--symref", "origin", "HEAD", check=False)
    for line in symref.stdout.splitlines():
        if line.startswith("ref: refs/heads/"):
            return line[len("ref: refs/heads/") :].split()[0]
    raise RuntimeError("could not determine the default branch")


def search_open_prs(repo: str, branch: str, fields: list[str]) -> list[dict] | None:
    """Return the open pull requests on ``repo`` whose head branch is ``branch``.

    Matches pull requests opened from forks too, which have ``login:branch``
    heads. Returns None if the query itself failed (the error is printed).
    """
    result = run(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo,
            "--search",
            f"head:{branch}",
            "--state",
            "open",
            "--json",
            ",".join(fields),
        ]
    )
    if result.returncode != 0:
        print(
            f"gh pr list failed for {repo}: {result.stderr.strip()}",
            file=sys.stderr,
        )
        return None
    return json.loads(result.stdout or "[]")


def find_pr_template(workdir: Path) -> Path | None:
    """Return the pull request template of the repository at ``workdir``, if any."""
    for base in (workdir / ".github", workdir / "docs", workdir):
        if not base.is_dir():
            continue
        for entry in sorted(base.iterdir()):
            if entry.is_file() and entry.name.lower() in (
                "pull_request_template.md",
                "pull_request_template.txt",
            ):
                return entry
        for entry in sorted(base.iterdir()):
            if entry.is_dir() and entry.name.lower() == "pull_request_template":
                templates = sorted(entry.glob("*.md"))
                if templates:
                    return templates[0]
    return None


def template_text(target: Path) -> str | None:
    """Return the pull request template of ``target`` as text, if any."""
    template = find_pr_template(target)
    if template is None:
        return None
    try:
        return template.read_text()
    except OSError as error:
        print(f"warning: could not read {template}: {error}", file=sys.stderr)
        return None


def edit_text(base: str, path: Path | None = None) -> str:
    """Open the user's editor on ``base``; return the edited text.

    With ``path``, the text is edited in that file (kept afterwards, so the
    editor shows its real location); without, a throwaway temp file is used.
    """
    editor = (
        os.environ.get("GH_EDITOR")
        or os.environ.get("VISUAL")
        or os.environ.get("EDITOR")
        or "vi"
    )
    tmp = path is None
    if tmp:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", prefix=f"{PROG}-body-", delete=False
        ) as file:
            file.write(base)
            path = Path(file.name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(base)
    try:
        # The editor inherits the terminal so interactive editing works.
        if subprocess.run(shlex.split(editor) + [str(path)]).returncode != 0:
            die(f"editor '{editor}' exited with an error")
        return path.read_text()
    finally:
        if tmp:
            path.unlink(missing_ok=True)


def derive_fork_url(origin_url: str, fork: str) -> str | None:
    """Return ``origin_url`` rewritten to point at ``fork`` (``owner/name``).

    Keeps the protocol and host of ``origin_url`` so https and ssh (both
    scp-like and ssh:// forms) remotes keep working. The fork name is taken
    as-is, so forks that exist under a different name than their upstream
    (e.g. the upstream was renamed after forking) resolve correctly:

        https://github.com/canonical/a.git  ->  https://github.com/<fork>.git
        git@github.com:canonical/a.git     ->  git@github.com:<fork>.git
        ssh://git@github.com/canonical/a   ->  ssh://git@github.com/<fork>.git

    Returns None if ``origin_url`` does not look like a GitHub remote.
    """
    url = origin_url.strip()
    # scp-like syntax: git@host:owner/name.git (no scheme separator)
    if "@" in url.split("/", 1)[0] and ("://" not in url):
        host = url.split(":", 1)[0]
        return f"{host}:{fork}.git"
    # scheme syntax: https://github.com/owner/name.git
    if "://" in url:
        scheme, rest = url.split("://", 1)
        host = rest.split("/", 1)[0]
        return f"{scheme}://{host}/{fork}.git"
    return None


def cached_body_path(workdir: Path, branch: str, repo: str) -> Path:
    """Return the cached pull request body file of ``repo`` for ``branch``."""
    return workdir / ".bodies" / branch / f"{repo}.md"


def read_cached_body(workdir: Path, branch: str, repo: str) -> str | None:
    """Return the cached pull request body of ``repo`` for ``branch``, if any."""
    try:
        return cached_body_path(workdir, branch, repo).read_text()
    except OSError:
        return None


def save_cached_bodies(
    workdir: Path, branch: str, bodies: dict[str, str | None]
) -> Path:
    """Cache ``bodies`` under the workdir for ``branch``; return the cache dir."""
    for repo, body in bodies.items():
        path = cached_body_path(workdir, branch, repo)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body or "")
    return workdir / ".bodies" / branch


def print_summary(set_name: str, results: dict[str, list[str]]) -> None:
    """Print the per-outcome summary shared by the commands."""
    print()
    print(f"Summary for set '{set_name}':")
    for label, repos in results.items():
        names = "".join(f" {repo}" for repo in repos)
        print(f"  {label + ':':<10}{len(repos)}{names}")


def cmd_clone(args: argparse.Namespace) -> int:
    repos = load_repos(args.set)
    require_gh()

    cloned: list[str] = []
    updated: list[str] = []
    failed: list[str] = []

    for repo in repos:
        print(f"==> {repo}")
        target = repo_dir(args.workdir, repo)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            if (target / ".git").exists():
                branch = default_branch(target)
                git(target, "fetch", "--quiet", "--prune", "origin")
                git(target, "checkout", "--quiet", "--force", branch)
                git(target, "reset", "--quiet", "--hard", f"origin/{branch}")
                git(target, "clean", "-fdq")
                print("    updated")
                updated.append(repo)
            else:
                result = run(
                    ["gh", "repo", "clone", repo, str(target), "--", "--quiet"]
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        result.stderr.strip() or "gh repo clone failed"
                    )
                print(f"    cloned to {target}")
                cloned.append(repo)
        except RuntimeError as error:
            print(f"    failed: {error}", file=sys.stderr)
            failed.append(repo)

    print_summary(
        args.set, {"cloned": cloned, "updated": updated, "failed": failed}
    )
    return 1 if failed else 0


def cmd_exec(args: argparse.Namespace) -> int:
    repos = load_repos(args.set)
    require_gh()

    ok: list[str] = []
    failed: list[str] = []

    for repo in repos:
        print(f"==> {repo}")
        target = repo_dir(args.workdir, repo)
        if not (target / ".git").exists():
            print(
                "    not in the workdir; run 'bulk-ops.py clone -s <set>' first",
                file=sys.stderr,
            )
            failed.append(repo)
            continue

        if args.branch:
            try:
                base = default_branch(target)
                git(target, "fetch", "--quiet", "--prune", "origin")
                git(
                    target,
                    "checkout",
                    "--quiet",
                    "--force",
                    "-B",
                    args.branch,
                    f"origin/{base}",
                )
                git(target, "clean", "-fdq")
            except RuntimeError as error:
                print(f"    failed to prepare branch: {error}", file=sys.stderr)
                failed.append(repo)
                continue

        env = {**os.environ, "REPO": repo, "REPO_DIR": str(target)}
        # The command inherits the terminal so its output is shown as-is.
        if subprocess.run(args.command, cwd=str(target), env=env).returncode == 0:
            ok.append(repo)
            continue

        if not args.interactive:
            print("    command failed", file=sys.stderr)
            failed.append(repo)
            continue
        print(f"    command failed: {' '.join(args.command)}", file=sys.stderr)
        print(f"    opening a shell in {target}")
        print("    resolve the issue, then exit the shell to continue.")
        print("    for a failed patch: git apply --3way <patch>, fix conflicts, git add")
        print("    exit with no changes to mark the repository as failed.")
        shell = os.environ.get("SHELL") or "/bin/sh"
        subprocess.run([shell, "-i"], cwd=str(target), env=env)
        git(target, "add", "-A")
        if git(target, "diff", "--cached", "--quiet", check=False).returncode == 0:
            print("    no changes after recovery, marking as failed", file=sys.stderr)
            failed.append(repo)
            continue
        if git(target, "grep", "-l", "^<<<<<<< ", "--", ".", check=False).stdout.strip():
            print("    conflict markers remain, marking as failed", file=sys.stderr)
            failed.append(repo)
            continue
        print("    recovered")
        ok.append(repo)

    print_summary(args.set, {"ok": ok, "failed": failed})
    return 1 if failed else 0


def cmd_push(args: argparse.Namespace) -> int:
    repos = load_repos(args.set)
    require_gh()
    title = args.title or args.message
    login: str | None = None

    # Determine the pull request body of each repository: an explicit --body
    # or --body-file wins, otherwise each repository defaults to its own
    # pull request template. With --edit-body the body is opened in the
    # editor before anything is pushed - once per distinct template, so a
    # set of identical templates is a single editor session.
    explicit = None
    if args.body is not None:
        explicit = args.body
    elif args.body_file is not None:
        try:
            explicit = args.body_file.expanduser().read_text()
        except OSError as error:
            die(f"could not read --body-file: {error}")

    bodies: dict[str, str | None] = {}
    from_cache: set[str] = set()
    if args.edit_body:
        # Open the body in the editor before anything is pushed, one session
        # per distinct base text: an explicit --body/--body-file, a body
        # cached by a previous run, or the repository's template. The edited
        # bodies are cached in the workdir and reused by later push runs.
        groups: dict[str, list[str]] = {}
        for repo in repos:
            target = repo_dir(args.workdir, repo)
            if not (target / ".git").exists():
                continue  # reported as a failure in the loop below
            base = explicit
            if base is None and not args.no_cached_body:
                base = read_cached_body(args.workdir, args.branch, repo)
            if base is None:
                base = template_text(target)
            groups.setdefault(base or "", []).append(repo)
        if len(groups) > 1:
            print(
                f"note: the set has {len(groups)} distinct pull request"
                " bodies to edit; opening one editor session for each"
            )
        for text, group in groups.items():
            print(
                "==> editing the pull request body for"
                f" {', '.join(group)}"
            )
            # Edit the cached file of the first member of the group, so the
            # editor shows which repository the body belongs to; the result
            # is copied to every member below.
            anchor = cached_body_path(args.workdir, args.branch, group[0])
            edited = edit_text(text, anchor)
            for repo in group:
                bodies[repo] = edited
        cache_dir = save_cached_bodies(args.workdir, args.branch, bodies)
        print(f"    saved {len(bodies)} edited bodies to {cache_dir}")
    elif explicit is not None:
        bodies = {repo: explicit for repo in repos}
    else:
        for repo in repos:
            target = repo_dir(args.workdir, repo)
            if not (target / ".git").exists():
                continue
            if not args.no_cached_body:
                cached = read_cached_body(args.workdir, args.branch, repo)
                if cached is not None:
                    bodies[repo] = cached
                    from_cache.add(repo)
            if bodies.get(repo) is None:
                bodies[repo] = template_text(target)

    update_bodies = args.edit_body or explicit is not None

    results: dict[str, list[str]] = {
        "previewed": [],
        "pushed": [],
        "skipped": [],
        "failed": [],
    }

    for repo in repos:
        print(f"==> {repo}")
        target = repo_dir(args.workdir, repo)
        if not (target / ".git").exists():
            print(
                "    not in the workdir; run 'bulk-ops.py clone -s <set>' first",
                file=sys.stderr,
            )
            results["failed"].append(repo)
            continue

        try:
            git(target, "checkout", "--quiet", args.branch)
        except RuntimeError:
            print(
                f"    branch '{args.branch}' not found;"
                " run exec -b first",
                file=sys.stderr,
            )
            results["failed"].append(repo)
            continue

        git(target, "add", "-A")

        if args.dry_run:
            # Show the full diff that would be committed and pushed, with
            # absolute paths so files can be opened directly from the output.
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(target),
                    "diff",
                    "--cached",
                    f"--src-prefix={target}/a/",
                    f"--dst-prefix={target}/b/",
                ]
            )
            if repo in from_cache:
                print(
                    "    body: cached"
                    f" ({cached_body_path(args.workdir, args.branch, repo)})"
                )
            results["previewed"].append(repo)
            continue

        update_body = update_bodies and bool(bodies.get(repo))
        has_changes = (
            git(target, "diff", "--cached", "--quiet", check=False).returncode != 0
        )

        # Commits already on the branch from a previous run that failed
        # during the fork creation or the push: they still need pushing
        # and a pull request.
        local_commits = 0
        try:
            base = default_branch(target)
            local_commits = int(
                git(
                    target,
                    "rev-list",
                    "--count",
                    f"origin/{base}..{args.branch}",
                    check=False,
                ).stdout.strip()
                or 0
            )
        except (RuntimeError, ValueError):
            local_commits = 0
        should_push = has_changes or local_commits > 0

        if not should_push and not update_body:
            print("    no changes, skipping")
            results["skipped"].append(repo)
            continue

        if has_changes:
            if git(target, "grep", "-l", "^<<<<<<< ", "--", ".", check=False).stdout.strip():
                print("    conflict markers remain, marking as failed", file=sys.stderr)
                results["failed"].append(repo)
                continue

        try:
            if has_changes:
                git(target, "commit", "--quiet", "-m", args.message)

            if should_push:
                owner = repo.split("/", 1)[0]
                if login is None:
                    login = gh_login()
                if owner == login:
                    # Own repository: no fork needed.
                    remote, head = "origin", args.branch
                else:
                    # POST /forks returns the existing fork object (with its
                    # real full_name) when a fork already exists, so forks
                    # named differently from their upstream still resolve.
                    forked = run(
                        [
                            "gh",
                            "api",
                            "--method",
                            "POST",
                            f"repos/{repo}/forks",
                            "-q",
                            ".full_name",
                        ]
                    )
                    if forked.returncode != 0:
                        raise RuntimeError(
                            f"could not create fork: {forked.stderr.strip()}"
                        )
                    fork = forked.stdout.strip()
                    remote, head = "fork", f"{login}:{args.branch}"
                    # Match the protocol of the clone's origin remote, so
                    # ssh users get an ssh fork remote instead of https.
                    origin_url = git(
                        target, "remote", "get-url", "origin", check=False
                    ).stdout.strip()
                    fork_url = derive_fork_url(origin_url, fork) or (
                        f"https://github.com/{fork}.git"
                    )
                    if git(target, "remote", "get-url", "fork", check=False).returncode == 0:
                        git(target, "remote", "set-url", "fork", fork_url)
                    else:
                        git(target, "remote", "add", "fork", fork_url)
                    print(f"    pushing to fork {fork}")

                if (
                    git(
                        target,
                        "ls-remote",
                        "--exit-code",
                        remote,
                        f"refs/heads/{args.branch}",
                        check=False,
                    ).returncode
                    == 0
                ):
                    git(target, "fetch", "--quiet", remote, args.branch)
                    git(
                        target,
                        "push",
                        "--quiet",
                        "--force-with-lease",
                        remote,
                        args.branch,
                    )
                else:
                    git(target, "push", "--quiet", "-u", remote, args.branch)
        except RuntimeError as error:
            print(f"    failed to commit or push: {error}", file=sys.stderr)
            results["failed"].append(repo)
            continue

        if not should_push:
            # Nothing new to push, but there may be a body to update.
            print("    no new changes")

        prs = search_open_prs(repo, args.branch, ["number", "url"])
        if prs is None:
            print(
                "    failed to check for existing pull request",
                file=sys.stderr,
            )
            results["failed"].append(repo)
        elif prs:
            if update_body:
                # An explicit or edited body also updates existing pull
                # requests. Go through the REST API: 'gh pr edit' uses a
                # GraphQL mutation that fails on repositories that still use
                # classic Projects.
                edited = run(
                    [
                        "gh",
                        "api",
                        f"repos/{repo}/pulls/{prs[0]['number']}",
                        "-X",
                        "PATCH",
                        "-f",
                        f"body={bodies[repo]}",
                    ]
                )
                if edited.returncode == 0:
                    print("    updated existing pull request (body)")
                else:
                    print(
                        "    updated existing pull request, but could not update"
                        f" its body: {edited.stderr.strip()}",
                        file=sys.stderr,
                    )
            else:
                print("    updated existing pull request")
            results["pushed"].append(repo)
        elif should_push:
            create_cmd = [
                "gh",
                "pr",
                "create",
                "--repo",
                repo,
                "--title",
                title,
                "--head",
                head,
            ]
            if bodies.get(repo):
                create_cmd += ["--body", bodies[repo]]
            if args.draft:
                create_cmd.append("--draft")
            if args.reviewers:
                create_cmd += ["--reviewer", args.reviewers]
            created = run(create_cmd)
            if created.returncode == 0:
                print(f"    opened {created.stdout.strip()}")
                results["pushed"].append(repo)
            else:
                print(
                    "    pushed branch, but failed to open pull request:"
                    f" {created.stderr.strip()}",
                    file=sys.stderr,
                )
                results["failed"].append(repo)
        else:
            print("    no changes and no pull request to update, skipping")
            results["skipped"].append(repo)

    if args.dry_run:
        print_summary(
            args.set, {"previewed": results["previewed"], "failed": results["failed"]}
        )
    else:
        print_summary(
            args.set,
            {
                "pushed": results["pushed"],
                "skipped": results["skipped"],
                "failed": results["failed"],
            },
        )
    return 1 if results["failed"] else 0


def cmd_status(args: argparse.Namespace) -> int:
    repos = load_repos(args.set)
    require_gh()

    errors = 0
    for repo in repos:
        prs = search_open_prs(
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

        prs = search_open_prs(repo, args.branch, ["number", "url", "mergeStateStatus"])
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
            review = run(
                ["gh", "pr", "review", "--repo", repo, str(pr["number"]), "--approve"]
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


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-s",
        "--set",
        required=True,
        help=(
            "repository set name from repos/ (e.g. 'charms', 'all') or a path to a"
            " file listing repositories"
        ),
    )

    work = argparse.ArgumentParser(add_help=False)
    work.add_argument(
        "-w",
        "--workdir",
        type=Path,
        default=DEFAULT_WORKDIR,
        help=f"directory holding the cached clones (default: {DEFAULT_WORKDIR})",
    )

    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Apply a change, inspect, or merge pull requests across a set of"
            " repositories."
        ),
    )
    sub = parser.add_subparsers(
        dest="action", required=True, metavar="{clone,exec,push,status,merge}"
    )

    clone = sub.add_parser(
        "clone",
        parents=[common, work],
        help="clone or update every repository in a set",
        description=(
            "Clone every repository in a set into the workdir, or update the"
            " existing clones to the latest default branch. Updating resets each"
            " clone, discarding uncommitted changes and stale branches."
        ),
    )
    clone.set_defaults(func=cmd_clone)

    exec_cmd = sub.add_parser(
        "exec",
        parents=[common, work],
        help="run a command in each clone of a set",
        description="Run a command at the root of each clone of a set.",
        epilog=(
            "The command after '--' runs at the root of each clone with the REPO"
            " (owner/name) and REPO_DIR (absolute path) environment variables"
            " set.\n\n"
            "With -b, the branch is created (or reset) from the default branch"
            " before the command runs; without it, the command runs on the current"
            " state of each clone.\n\n"
            "example:\n"
            "  bulk-ops.py exec -s charms -b chore/update-ci \\\n"
            '    -- git apply "$PWD/patches/update-ci.patch"'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    exec_cmd.add_argument(
        "-b",
        "--branch",
        help="create (or reset) this branch from the default branch before running",
    )
    exec_cmd.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help=(
            "if the command fails on a repository, open a shell in the clone to"
            " resolve the issue manually, then continue with the resolved changes"
        ),
    )
    exec_cmd.set_defaults(func=cmd_exec)

    push = sub.add_parser(
        "push",
        parents=[common, work],
        help="commit each clone, push to a fork, and open the pull requests",
        description=(
            "Commit the changes of each clone of a set on a branch, push the"
            " branch to a fork of the repository (created automatically), and"
            " open or update a pull request."
        ),
        epilog=(
            "The pull request body defaults to the repository's pull request"
            " template. With --edit-body the body is opened in your editor"
            " before anything is pushed: one session per distinct template, so"
            " identical templates are edited once and applied to every pull"
            " request. Edited bodies are cached under the workdir"
            " (.bodies/<branch>/) and reused by later push runs, so"
            " 'push --dry-run -e' drafts the body while reviewing the diffs"
            " and the next push opens the pull requests with that draft;"
            " --no-cached-body starts over from the template. Re-running"
            " push with the same branch force-pushes and updates the"
            " existing pull request rather than opening a duplicate, and an"
            " explicit or edited body also updates the bodies of the"
            " existing pull requests. Run with --dry-run first to review"
            " the full diff of every repository before anything is committed"
            " or pushed.\n\n"
            "example:\n"
            "  bulk-ops.py push -s charms -b chore/update-ci \\\n"
            '    -m "chore: update CI workflow"'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    push.add_argument(
        "-b",
        "--branch",
        required=True,
        help="branch to commit and push in each clone",
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
    body = push.add_mutually_exclusive_group()
    body.add_argument(
        "--body", help="PR body (defaults to the PR template)"
    )
    body.add_argument(
        "--body-file",
        type=Path,
        help="PR body from a file (defaults to the PR template)",
    )
    push.add_argument(
        "-e",
        "--edit-body",
        action="store_true",
        help=(
            "open the pull request body in your editor before anything is"
            " pushed, once per distinct template (a set of identical templates"
            " is a single session)"
        ),
    )
    push.add_argument(
        "--no-cached-body",
        action="store_true",
        help=(
            "ignore pull request bodies cached by a previous --edit-body"
            " run; with --edit-body, start from the template again and"
            " overwrite the cache"
        ),
    )
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
        "-n",
        "--dry-run",
        action="store_true",
        help="show the diff of each clone without committing, pushing, or opening PRs",
    )
    push.set_defaults(func=cmd_push)

    status = sub.add_parser(
        "status",
        parents=[common],
        help="show the status of the pull requests opened by push",
        description=(
            "Show the status of the pull requests opened by 'bulk-ops.py push'"
            " across a set of repositories."
        ),
    )
    status.add_argument(
        "-b",
        "--branch",
        required=True,
        help="head branch of the pull requests to inspect",
    )
    status.set_defaults(func=cmd_status)

    merge = sub.add_parser(
        "merge",
        parents=[common],
        help="merge the pull requests opened by push",
        description=(
            "Merge (and optionally approve) the pull requests opened by"
            " 'bulk-ops.py push' across a set of repositories."
        ),
    )
    merge.add_argument(
        "-b",
        "--branch",
        required=True,
        help="head branch of the pull requests to merge",
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

    return parser


def main() -> int:
    # Split the arguments at '--' so the exec command may contain arbitrary
    # options.
    argv = sys.argv[1:]
    command = []
    if "--" in argv:
        split = argv.index("--")
        command, argv = argv[split + 1 :], argv[:split]

    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "workdir"):
        args.workdir = args.workdir.expanduser().resolve()
    args.command = command
    if args.action == "exec" and not command:
        parser.error("exec requires a command after '--'")
    if args.action != "exec" and command:
        parser.error(f"the '{args.action}' command does not take a command after '--'")
    return args.func(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
