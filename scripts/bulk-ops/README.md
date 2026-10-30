# Bulk repository operations

Scripts for applying a change or merging pull requests across many Charmed HPC
repositories at once. Repository sets live in [`repos/`](repos/): each
file is a set of `owner/repo` lines, `#` comments ignored. A path to a file in
the same format works anywhere a set name does. Single-repository sets are not
codified - use `gh` directly instead.

Sets cover only projects maintained directly as part of Charmed HPC, per the
[underlying projects and dependencies](https://canonical-charmed-hpc.readthedocs-hosted.com/latest/reference/underlying-projects-and-dependencies/)
reference.

## Bulk workflow

**Person A** opens the pull requests. Make the change in one repository,
export it as a patch (`git diff > patches/update-ci.patch`), then:

```shell
# Preview first, then push for real.
scripts/bulk-ops/bulk-push -s charms -b chore/update-ci \
  -m "chore: update CI workflow" \
  --dry-run -- git apply "$PWD/patches/update-ci.patch"

scripts/bulk-ops/bulk-push -s charms -b chore/update-ci \
  -m "chore: update CI workflow" \
  -- git apply "$PWD/patches/update-ci.patch"
```

Repositories where the patch does not apply cleanly are reported as failures
and left untouched. Pass `--interactive` (`-i`) to instead open a shell in the
clone when the command fails, so you can resolve conflicts by hand
(`git apply --3way`, fix markers in your editor, `git add`) and continue with
the resolved changes; exit the shell with no changes to mark the repository as
failed.

**Person B** reviews and merges:

```shell
scripts/bulk-ops/bulk-status -s charms -b chore/update-ci
scripts/bulk-ops/bulk-merge -s charms -b chore/update-ci --auto
```

## Example commands

The command after `--` runs at the root of each cloned repository, so anything
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

See `--help` on each script for all options.
