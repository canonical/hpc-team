# AGENTS.md

Guidance for AI agents working in this repository.

## Repository

- `terraform/` — OpenTofu plans for Charmed HPC infrastructure. Check with
  `just validate` (the justfile lists all recipes).
- `scripts/gen-contrib` — generates per-repository CONTRIBUTING.md files.
- `scripts/bulk-ops/` — the bulk repository operations tool, described below.
- Every new source file gets the Apache-2.0 license header
  ("Copyright <year> Canonical Ltd."). Follow the conventional commit
  subjects configured in `.commitlintrc.yaml`.

## bulk-ops

`scripts/bulk-ops/bulk-ops.py` applies a change, inspects, or merges pull
requests across the repository sets in `scripts/bulk-ops/repos/` (currently
`all`, `charms`, `libs`, `not-team`). The workflow is `clone` (cached clones
under `~/.cache/bulk-ops`, override with `-w`), `exec` (run a command in each
clone), `push` (commit, push to an automatically created fork, open or update
the pull requests), then `status` and `merge`. `scripts/bulk-ops/README.md`
is the user documentation and the contract: update it whenever behavior or
flags change.

### Ground rules

- Standard library only. The script runs as `./bulk-ops.py` with no
  environment setup and should stay that way. No dependencies, no packaging.
- All GitHub access goes through the `gh` CLI and plain git.
- Keep the CLI stable. Flags, output format, and exit codes are relied on by
  the team and encoded in the README examples.

### Easy to break, load-bearing details

- The `exec` command after `--` is split from argv before argparse runs;
  everything after the first `--` is the command. The command runs with the
  terminal inherited, never captured.
- `status` and `merge` find pull requests with
  `gh pr list --search head:<branch>`, not `--head`. Only the search form
  matches pull requests opened from forks (`login:branch` heads).
- Forks are created with `gh api --method POST repos/<repo>/forks`, which
  returns the existing fork's real `full_name`, so forks renamed after
  forking still resolve. Fork remotes are derived from each clone's `origin`
  URL, so ssh setups keep ssh; https is the fallback when the URL cannot be
  parsed.
- Updating an existing pull request body goes through the REST API
  (`gh api repos/<repo>/pulls/<N> -X PATCH -f body=...`). `gh pr edit` uses a
  GraphQL mutation that fails on repositories that still use classic
  Projects.
- `push` pushes when there are staged changes or commits on the branch
  (`origin/<default>..<branch>`). The second condition recovers commits
  stranded by a failed run, for example a fork outage or a dropped network,
  so re-running `push` is the documented fix. Do not gate on staged changes
  alone.
- `exec -b` fetches and re-cuts the branch from `origin/<default>`, so
  re-running it reapplies cleanly. `exec` without `-b` runs on the clone's
  current state. `clone` updates hard-reset clones and discard uncommitted
  changes.
- Pull request bodies default to each repository's own template. `push -e`
  opens the body in the editor once per identical template, editing the
  cached file under `<workdir>/.bodies/<branch>/<owner>/<repo>.md`, which
  later runs reuse. `--body` and `--body-file` bypass the cache;
  `--no-cached-body` ignores it. Only an explicit or edited body rewrites
  the body of an already-open pull request.
- The results summary of every mutating command must handle the `failed`
  bucket in all modes; `push --dry-run` once crashed because the bucket was
  only initialized outside dry runs.

### Output conventions

- Per repository: a `==> owner/repo` header, then messages indented by four
  spaces. Warnings and per-repository failures go to stderr.
- Mutating commands end with a summary block and exit 1 if any repository
  failed, 0 otherwise. `push --dry-run` prints the full `git diff --cached`
  per clone with absolute path prefixes, so files can be opened directly
  from the output, and changes nothing.

### Validating changes

After any edit:

1. `python3 -m py_compile scripts/bulk-ops/bulk-ops.py`
2. `--help` on every subcommand, plus the error paths (unknown set, missing
   command after `--`, invalid choices).
3. Live checks that are safe: `status`, `status --diff`, `push --dry-run`,
   and `exec` against a throwaway branch.

A real `push` opens real pull requests on `canonical/*` repositories. If a
live test is unavoidable, use a one-line set file pointing at one small
repository (`canonical/slurmutils`), then close the pull request and delete
the fork branch (`gh api -X DELETE
repos/<login>/<repo>/git/refs/heads/<branch>`). Never leave test pull
requests or branches behind.

### Environment quirks

- If git commits fail with a pinentry error in a non-interactive shell, the
  local config signs commits. Prefix test runs with
  `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgsign GIT_CONFIG_VALUE_0=false`.
- `Could not resolve host: github.com` on WSL is a transient resolver failure,
  not a configuration problem. Retry the command before debugging anything.
- The `gh` login lacks the `delete_repo` scope, so forks created during
  testing accumulate. Only their branches can be deleted via the API.
