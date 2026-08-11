---
name: migrate-charm-to-26-04
description: Migrate a Juju charm (or monorepo of charms) from an Ubuntu 24.04 base to the Ubuntu 26.04 (Resolute) base. Use this when the user wants to upgrade a charm's charmcraft.yaml base, Python version, CI workflows, test dependencies, and documentation, and verify the juju snap/controller versions required for 26.04.
---

# Migrate a Juju Charm to Ubuntu 26.04 (Resolute)

Apply this skill when the user asks to migrate a charm (or a monorepo of charms) to the Ubuntu 26.04 base, also known as "Resolute".

## Prerequisites — Juju snap and controller version

Before starting, verify both the **juju snap** and the **Juju controller** are recent enough. There are two distinct version-gate issues on 26.04. If either check fails, **ask the user whether they want the upgrade performed automatically or whether they will do it manually** before proceeding.

### 1. Juju snap must contain the `/sbin` fix (>= 3.6/edge)

The `3.6/stable` juju snap (revision **3.6.25**, snap rev 35378, as of 2026-07-16) has a bug where it incorrectly unlinks the `/sbin` -> `/usr/sbin` merged-usr symlink on Ubuntu 26.04 (Resolute). This breaks `snapd`, which looks for mount helpers (`mount.fuse`, `mount.fuse3`) in `/sbin`, and therefore breaks any charm that installs snaps at runtime. The fix is in `3.6/edge` (revision **3.6.26-14dcb65**, snap rev 35559) and later.

Tracked at https://github.com/juju/juju/issues/22713

**Check:** run `snap info juju` and compare the `installed:` line against `3.6/edge`. The installed snap must be at least as new as the current `3.6/edge` revision. If the installed version is `3.6.25` (stable) or older, it has the bug.

```bash
snap info juju | grep -E "installed:|3\.6/edge:|3\.6/stable:"
```

### 2. Controller must recognize `ubuntu@26.04` as a base (> 3.6.25)

Controllers running **3.6.25** or older (e.g. 3.6.4) do not recognize `ubuntu@26.04` as a valid base string when deploying charms resolved from Charmhub, and fail with:

```
ERROR the charm defined bases "ubuntu@26.04" not supported
ERROR failed to deploy charm "ubuntu"
```

This only affects **Charmhub-resolved** charm deploys with `--base ubuntu@26.04`. Local charm deploys (e.g. `juju deploy ./my.charm --base ubuntu@26.04`) bypass the base-validation path and work even on older controllers, which can mask the problem during development.

The issue typically surfaces in integration tests that deploy a Charmhub principal (such as the `ubuntu` charm) alongside the charm under test on 26.04.

**Check:** run `juju controllers --refresh` and confirm every controller that will run 26.04 workloads reports a `Version` newer than 3.6.25 (i.e. >= 3.6.26).

```bash
juju controllers --refresh
```

### Upgrading — ask the user first

If either check fails, the juju snap and controller must be upgraded **in lockstep**: refresh the snap first, then upgrade the controller to the version bundled in that snap — not an arbitrary upstream controller version. **Ask the user whether they want this done automatically or manually** before running any upgrade commands:

- **Automatic** (if the user consents):
  ```bash
  sudo snap refresh juju --channel 3.6/edge   # or 3.6/stable once the fix promotes
  juju upgrade-controller
  ```
  Then re-run both checks above to confirm.

- **Manual** (if the user prefers): tell the user the two commands to run and wait for their confirmation before continuing with the migration.

## Decide: principal vs. subordinate

The migration differs depending on whether the charm is a **principal** charm or a **subordinate** charm. Check the `charmcraft.yaml` for the `subordinate: true` key (or ask the user).

- **Principal charms** (the common case): replace the 24.04 base with 26.04 and bump Python to 3.14. This is a clean cut-over.
- **Subordinate charms**: ask the user which strategy they prefer:
  - **Multi-base (keep both 24.04 and 26.04)**: add 26.04 as an **additional** base using charmcraft's multi-base notation, while keeping 24.04. Keep Python compatible with both bases (`>=3.12`). This avoids maintaining two charm revisions — a single multi-base subordinate can serve principals on either base. This is the default if the user has no preference.
  - **Full migration to 26.04**: drop 24.04 entirely and treat the subordinate like a principal — replace the base with 26.04 and bump Python to `==3.14.*`. Use this when the subordinate only needs to serve 26.04 principals.

  The chosen strategy determines which Part 1 and Part 2 sub-sections to follow below.

Reference: charmcraft supports multi-base notation where each `platforms` entry specifies a `base:arch` pair, and the top-level `base`/`build-base` keys are omitted. See https://canonical.com/juju/docs/charmcraft/4.3/reference/platforms/.

The migration has eight parts. Parts 1–2 differ by charm type. Parts 3–8 apply to both.

## Part 1 — `charmcraft.yaml`: the base

### Principal charms and subordinate charms (full migration) — replace the base

Change the `base` key from `ubuntu@24.04` to `ubuntu@26.04`:

```yaml
# before
base: ubuntu@24.04

# after
base: ubuntu@26.04
```

Leave `platforms`, `build-snaps`, `build-packages`, `override-build`, and `build-environment` untouched — those are charm-specific and unrelated to the base bump. Do **not** leave `parts` untouched if the charm uses the `charm` or `reactive` plugin — see Part 3.

### Subordinate charms (multi-base) — convert to multi-base

Remove the top-level `base` key and convert `platforms` to multi-base shorthand notation, adding a 26.04 entry alongside the existing 24.04 one. For example, if the charm currently has:

```yaml
base: ubuntu@24.04
platforms:
  amd64:
```

Change it to:

```yaml
platforms:
  ubuntu@24.04:amd64:
  ubuntu@26.04:amd64:
```

The multi-base shorthand `<base>:<arch>:` is a YAML dict entry with a null value; it means "build on and build for that base and architecture". Repeat for any other architectures the charm supports (e.g. `ubuntu@24.04:arm64:` / `ubuntu@26.04:arm64:`).

Do **not** keep the top-level `base` key — charmcraft rejects `base` when `platforms` contains multi-base entries.

## Part 2 — `pyproject.toml`: `requires-python`

### Principal charms and subordinate charms (full migration) — bump to 3.14

Ubuntu 26.04 ships Python 3.14 as the default interpreter. Bump `requires-python` in **every** `pyproject.toml` in the repo:

- **Charm `pyproject.toml` files** (e.g. `charms/<name>/pyproject.toml`): change `requires-python = "==3.12.*"` (or similar) to `requires-python = "==3.14.*"`.
- **Library/package `pyproject.toml` files** (e.g. `internal/<name>/pyproject.toml`, `pkg/<name>/pyproject.toml`): change `requires-python = ">=3.12"` (or similar) to `requires-python = ">=3.14"`.
- **Root `pyproject.toml`** (monorepo only): change `requires-python = "==3.12.*"` to `requires-python = "==3.14.*"`.

### Subordinate charms (multi-base) — widen to support both bases

To keep a single charm revision working on both 24.04 (Python 3.12) and 26.04 (Python 3.14), widen `requires-python` instead of bumping it:

- **Charm `pyproject.toml`**: change `requires-python = "==3.12.*"` to `requires-python = ">=3.12"`.
- **Library/package `pyproject.toml` files**: ensure `requires-python` is `>=3.12` (it usually already is — leave it alone unless it's pinned tighter).
- **Root `pyproject.toml`** (monorepo only): if the subordinate lives in a monorepo whose root pins `==3.12.*`, that pin applies to the whole workspace. You cannot widen just the subordinate while the root stays pinned — in that case, coordinate with the user: either the whole workspace moves to `>=3.12` (preferred for a multi-base subordinate), or the subordinate must be split out of the workspace.

### Both paths

After changing `requires-python`, regenerate the lockfile (`uv lock` in a monorepo, or whatever the project uses).

## Part 3 — Verify the charmcraft `uv` plugin is in use

### Why this is needed

Charmcraft 4.3+ rejects the deprecated `charm` and `reactive` plugins when the base is `ubuntu@26.04`:

```
charmcraft internal error: 1 validation error for PlatformCharm
parts
  Value error, Cannot use 'charm' or 'reactive' plugins with base 'ubuntu@26.04'
```

Only the `uv` plugin (and other modern plugins) are supported on 26.04. This skill assumes the `uv` plugin — it was developed against charms that already use it. Charms still on the `charm` plugin need a plugin migration first, which is out of scope for this skill.

### What to do

For **every** `charmcraft.yaml` in the repo, check the `parts` block. The charm uses the `uv` plugin if its `parts` block looks like:

```yaml
parts:
  charm:
    plugin: uv
    source: .
    build-snaps:
      - astral-uv
```

The charm uses the deprecated `charm` plugin if its `parts` block is:

```yaml
parts:
  charm: {}
```

or explicitly sets `plugin: charm` / `plugin: reactive`.

**If any charm uses the `charm` or `reactive` plugin, stop and ask the user how to proceed.** Migrating from the `charm` plugin to the `uv` plugin is not a mechanical change — it depends on how the charm's build tooling works (e.g. `requirements.txt` export, `charm-binary-python-packages` injection, custom staging scripts) and must be coordinated with the user. Do not attempt the migration until every charm is on the `uv` plugin.

If all charms already use the `uv` plugin, this part is a no-op — continue to Part 4.

## Part 4 — Multi-base command runner adjustments (multi-base charms only)

**Skip this part for single-base charms** (principal charms, and subordinate charms that did a full migration to 26.04) — `charmcraft pack` produces one `.charm` file and existing recipes work unchanged.

This applies to **any multi-base charm** (typically subordinates, but also any charm that keeps both 24.04 and 26.04 platforms) whose integration test recipe packs the charm and then deploys a single local `.charm` file.

### Why this is needed

When a charm has multiple platforms, `charmcraft pack` produces **one `.charm` file per platform**, named `<charm>_<base>-<arch>.charm`:

```
<charm>_ubuntu@24.04-amd64.charm
<charm>_ubuntu@26.04-amd64.charm
```

Recipes written for a single-base charm typically glob and rename into a single path, e.g.:

```make
charmcraft -v pack
mv <charm>_*.charm <charm>.charm   # breaks: multiple sources, non-directory target
```

This fails because `mv` treats the last argument as a destination directory, but `<charm>.charm` is not a directory. Even if it didn't fail, the recipe would non-deterministically pick one of the two artifacts.

### What to do

If the command runner used in the repo (e.g. `just`, `tox`, `make`, a custom script) requires any change to support multiple bases, adjust it accordingly. The fix is to select the packed artifact matching the `--base` passed to the integration tests instead of globbing. For a justfile recipe using the `*args` variadic parameter, this looks like:

```make
# Run integration tests
[group("test")]
integration *args: lock
    #!/usr/bin/env bash
    set -euxo pipefail

    charmcraft -v pack

    # `charmcraft pack` produces one charm file per platform (e.g.
    # `<charm>_ubuntu@24.04-amd64.charm` and `<charm>_ubuntu@26.04-amd64.charm`).
    # Select the charm matching the `--base` passed to the integration tests so
    # that `LOCAL_<CHARM>` points at the correct multi-base artifact.
    base="ubuntu@24.04"
    # Parse `--base <value>` or `--base=<value>` out of the captured args.
    set -- {{args}}
    while [ $# -gt 0 ]; do
        case "$1" in
            --base=*) base="${1#--base=}"; shift ;;
            --base) base="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    charm_name="<charm>_${base}-amd64.charm"
    if [ ! -f "$charm_name" ]; then
        echo "error: packed charm '$charm_name' not found for base '$base'" >&2
        exit 1
    fi
    mv "$charm_name" <charm>.charm
    export LOCAL_<CHARM>={{project_dir / "<charm>.charm"}}
    {{uv_run}} pytest \
        -v \
        --tb native \
        -s \
        --log-cli-level=INFO \
        {{args}} \
        {{tests_dir / "integration"}}
```

Notes:
- The packed filename format is `<charm>_<base>-<arch>.charm` where `<base>` already includes the `ubuntu@` prefix (e.g. `ubuntu@24.04`). Do **not** prepend `ubuntu@` again when constructing `charm_name`.
- If the integration test conftest defaults `--base` to `ubuntu@24.04`, the recipe default above matches.
- For architectures other than amd64, adjust the `-amd64` suffix accordingly, or derive it from the platform list in `charmcraft.yaml`.
- For repos using `tox`, `make`, or a custom script instead of `just`, apply the same logic — parse the base from the test args and select the matching artifact.

## Part 5 — `pyproject.toml`: tool configuration

In addition to `requires-python` (Part 2), check every `pyproject.toml` for Python-version-pinned tool configuration and bump it to match the new interpreter:

- **`[tool.black]` `target-version`**: change `target-version = ["py312"]` to `target-version = ["py314"]`.
- **`[tool.ruff]` `target-version`** (if present): change `target-version = "py312"` to `target-version = "py314"`.
- Any other tool that pins a Python target version (e.g. `[tool.mypy]` `python_version`): bump accordingly.

These don't affect runtime behavior but keep static analysis and formatting consistent with the new interpreter.

## Part 6 — Test dependencies: `pyfakefs`

### Why this is needed

`pyfakefs` versions before **6.0.0** (December 2025) are incompatible with Python 3.14's rewritten `shutil.rmtree`. Python 3.14 rewrote `rmtree` to use `_rmtree_safe_fd`, which contains `assert func is os.lstat`. When pyfakefs patches `os.lstat`, this assertion fails:

```
AssertionError
    assert func is os.lstat
```

This surfaces in any test that calls `shutil.rmtree(...)` on a fake filesystem path — for example, tests covering cert removal, config cleanup, or any "delete this directory" logic.

### What to do

Search `pyproject.toml` files for a `pyfakefs` pin. If it's pinned to `< 6.0` (e.g. `pyfakefs == 5.7.4`, which was the last 5.x release in January 2025), bump it to `pyfakefs ~= 6.2` (or later). `pyfakefs` 6.x declares `Programming Language :: Python :: 3.14` support.

```toml
# before
"pyfakefs == 5.7.4",

# after
"pyfakefs ~= 6.2",
```

If `pyfakefs` is already at `>= 6.0` or not used, this part is a no-op.

After bumping, regenerate the lockfile (`uv lock`).

## Part 7 — CI workflows

### GitHub Actions runners

Every CI workflow job that runs on Ubuntu should be bumped from `ubuntu-24.04` to `ubuntu-26.04`. Search `.github/workflows/` for `runs-on: ubuntu-24.04`:

```yaml
# before
runs-on: ubuntu-24.04

# after
runs-on: ubuntu-26.04
```

This applies to all jobs: unit tests, integration tests, release/publish, lint, etc.

### Juju channel in CI

If the CI workflow sets up a Juju operator environment (e.g. via `charmed-kubernetes/actions-operator`) and pins `juju-channel: 3.6/stable`, this will hit the `/sbin` unlinking bug on the 26.04 runner (see Prerequisites). Change it to `3.6/edge` until the fix promotes to stable:

```yaml
# before
with:
  juju-channel: 3.6/stable

# after
with:
  juju-channel: 3.6/edge
```

Coordinate with the user if this is a shared/reusable workflow that other repos depend on.

## Part 8 — Documentation and integration test plans

Search the repo for remaining `ubuntu@24.04` / `24.04` references and update them to `26.04`. Common locations:

- **`README.md`**: deploy examples (`juju deploy ubuntu --base ubuntu@24.04`).
- **`terraform/variables.tf`** and **`terraform/README.md`**: variable descriptions and examples that reference the base.
- **Integration test scenarios**: any test file that deploys a principal or peer charm on a specific base. Common forms:
  - BDD/gherkin-style plan files (e.g. `tests/integration/plans/*.yaml`) and any generated feature files (e.g. `tests/integration/features/*.feature`) containing steps like `I deploy 'ubuntu' on base 'ubuntu@24.04'`. If feature files are generated from plan files by a tool (e.g. `gherkinator`, `behave`), update the plan files and regenerate; otherwise update both.
  - pytest integration tests that deploy principals via `juju deploy ... --base ubuntu@24.04` directly in Python.
- **Integration test conftest defaults**: pytest fixtures or `addoption` calls that default `--base` to `ubuntu@24.04` (e.g. `tests/integration/conftest.py`). Update the default to `ubuntu@26.04` so tests run against the new base unless overridden.

Use a grep sweep to find any remaining references:

```bash
grep -rn "24\.04\|ubuntu-24\.04\|ubuntu@24" --include="*.yaml" --include="*.yml" --include="*.md" --include="*.tf" --include="*.feature" --include="*.toml" --include="*.py" .
```

## Validation

After applying all applicable parts:

1. **Verify the juju snap and controller versions** (see Prerequisites). The juju snap must be at least as new as the current `3.6/edge` revision (3.6.26-14dcb65, snap rev 35559 as of 2026-07-16) to contain the `/sbin` fix, and every controller that will run 26.04 workloads must report a version newer than 3.6.25. If either check fails, ask the user whether to upgrade automatically or manually before proceeding. Without this, 26.04 integration tests that deploy Charmhub charms will fail with `the charm defined bases "ubuntu@26.04" not supported`, and snap-installing charms will hit the `/sbin` unlinking bug.
2. **Verify every charm uses the `uv` plugin** (see Part 3). If any charm uses the `charm` or `reactive` plugin, stop and ask the user how to proceed before continuing.
3. Regenerate the lockfile (`uv lock`).
4. Run unit tests if available.
5. Build the charm (`charmcraft pack`) to confirm the base bump and `requires-python` change don't break the build.
6. For multi-base charms (subordinate charms that chose the multi-base strategy), build **both** platforms to confirm both bases pack successfully:
   ```
   charmcraft pack --platform ubuntu@24.04:amd64
   charmcraft pack --platform ubuntu@26.04:amd64
   ```
7. For multi-base charms, if the command runner was updated (Part 4), run integration tests against **both** bases to confirm the artifact selection works:
   ```
   just integration --base ubuntu@24.04
   just integration --base ubuntu@26.04
   ```
   Confirm that `test_deploy` (or the equivalent deploy-and-wait-for-active test) passes on both bases. A failure in a workload-execution test (e.g. `apptainer exec ...`) that is identical on both bases is likely an upstream workload bug, not a migration regression — compare the 24.04 result to distinguish migration issues from pre-existing workload issues.
8. **Sweep for remaining references**: grep the repo for any `24.04`, `ubuntu-24.04`, `ubuntu@24.04`, `py312`, `>=3.12`, or `==3.12` references that were missed. Exclude `uv.lock` package wheel filenames (e.g. `graalpy312` in upstream package URLs) — those are upstream artifacts, not migration targets.
