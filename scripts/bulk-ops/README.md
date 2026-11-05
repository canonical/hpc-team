# Bulk repository operations

[`bulk-ops.py`](bulk-ops.py) applies a change or merges pull requests across many Charmed HPC
repositories at once. Repository sets live in [`repos/`](repos/): each
file is a set of `owner/repo` lines, `#` comments ignored. A path to a file in
the same format works anywhere a set name does. Single-repository sets are not
codified - use `gh` directly instead.

The tool works on a local cache of clones (default `~/.cache/bulk-ops`,
override with `-w/--workdir`), so each step is split and fast to re-run:

- `clone` clones (or updates) every repository in a set.
- `exec` runs a command at the root of each clone, optionally on a fresh branch.
- `push` commits each clone's changes, pushes the branch to a fork (created
  automatically), and opens or updates the pull requests - in one bulk step at
  the end, after you've reviewed everything.
- `status` and `merge` inspect and merge the pull requests via the GitHub API.

Sets cover only projects maintained directly as part of Charmed HPC, per the
[underlying projects and dependencies](https://canonical-charmed-hpc.readthedocs-hosted.com/latest/reference/underlying-projects-and-dependencies/)
reference.

## Bulk workflow

**Person A** opens the pull requests. Make the change in one repository,
export it as a patch (`git diff > patches/update-ci.patch`), then:

```shell
# 1. Clone (or update) every repository in the set. Done once; re-run
#    whenever you want the clones refreshed.
scripts/bulk-ops/bulk-ops.py clone -s charms

# 2. Apply the change on a branch in each clone. Fix-ups afterwards are
#    just edits in ~/.cache/bulk-ops - nothing is pushed yet.
scripts/bulk-ops/bulk-ops.py exec -s charms -b chore/update-ci \
  -- git apply "$PWD/patches/update-ci.patch"

#    Preview the full diff of every repository before anything happens:
scripts/bulk-ops/bulk-ops.py push -s charms -b chore/update-ci \
  -m "chore: update CI workflow" --dry-run

# 3. Commit, push each branch to a fork, and open or update the pull
#    requests - all at once, at the end.
scripts/bulk-ops/bulk-ops.py push -s charms -b chore/update-ci \
  -m "chore: update CI workflow"
```

Branches are pushed to a fork of each repository, so no permissions on the
target repositories are required. Pull request bodies default to each
repository's own pull request template. Pass `-e`/`--edit-body` to `push` to
open the body in your editor before anything is pushed: repositories that
share the same template are edited in a single session and the result is
applied to every pull request of the set (distinct templates get one session
each, and `--body`/`--body-file` set the starting text without a template).
Re-running `push` with the same branch force-pushes and updates the existing
pull requests rather than opening duplicates - and with an explicit or edited
body, updates their bodies too, even when there is nothing new to push.

Edited bodies are cached under the workdir
(`.bodies/<branch>/<owner>/<repo>.md`) and reused by later `push` runs, so you
can draft the body with `push --dry-run -e`, review the diffs, and open the
pull requests with a plain `push` afterwards. With `-e` the editor opens the
cached file itself, and each session names the repositories it covers, so
you always know which repository you are editing. Pass `--no-cached-body` to
start over from the template.

If the `exec` command fails on a repository, pass `--interactive` (`-i`) to
open a shell in the clone instead (`git apply --3way`, fix markers in your
editor, `git add`), then exit the shell to continue. Exit with no changes to
mark the repository as failed. Without `-b`, `exec` runs on the current state
of each clone rather than resetting a branch first.

**Person B** reviews and merges:

```shell
scripts/bulk-ops/bulk-ops.py status -s charms -b chore/update-ci
scripts/bulk-ops/bulk-ops.py merge -s charms -b chore/update-ci --auto
```

## Example commands

The command after `--` runs at the root of each clone, so anything
that modifies the working tree works:

```shell
# In-place edit of an existing file
-- sed -i 's/ubuntu-24.04/ubuntu-26.04/' charmcraft.yaml

# Edit only matching files
-- sh -c 'sed -i "s/24.04/26.04/" charms/*/charmcraft.yaml'

# Delete a file everywhere
-- rm .github/workflows/stale.yaml

# Apply a prepared patch
-- git apply "$PWD/patches/update-ci.patch"

# Copy a whole directory of shared workflows
-- cp -r "$PWD/shared-workflows/." .github/workflows/

# Generate the file per repository
-- "$PWD/scripts/gen-contrib" --repo "$REPO" --license apache-2.0 -o CONTRIBUTING.md

# Run a formatter or linter autofix
-- sh -c 'tofu fmt -recursive && ruff check --fix . || true'
```

Use `sh -c '...'` when you need shell features such as globbing, pipes, `&&`,
or `$REPO` expansion - otherwise globs are expanded by your shell in the wrong
directory. `$REPO` and `$REPO_DIR` are set inside each clone, so per-repository
customization can key off the repository name.

See `scripts/bulk-ops/bulk-ops.py <command> --help` for all options.