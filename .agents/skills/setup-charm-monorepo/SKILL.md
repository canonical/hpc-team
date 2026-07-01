---
name: setup-charm-monorepo
description: 'Set up a charm monorepo with a scripts/repository.py CLI tool and a UHPC011-compliant justfile. Use when scaffolding or reviewing a monorepo repository that uses uv workspaces, repository.py for tooling, and just as the developer entry point.'
argument-hint: 'Path to the repository root directory, or leave blank to use the current directory.'
---

# Set up a charm monorepo

Sets up a charm monorepo following the patterns established by `charmed-hpc/slurm-charms`. The repository uses `uv` workspaces for dependency management, a `scripts/repository.py` CLI tool for build/test/lint orchestration, and a `justfile` (conforming to UHPC011) as the developer-facing entry point.

`repository.py` must never be called directly by developers. All interaction goes through the justfile, which delegates to `repository.py` via `uv run`.

## Process

1. **Read the repository** -- Examine the existing directory structure. Identify charm directories (e.g. `charms/`), internal packages (`internal/`), public packages (`pkg/`), shared integration tests (`tests/integration/`), and configuration files (`pyproject.toml`, `uv.lock`).
2. **Create `scripts/repository.py`** -- Place the monorepo CLI tool at `scripts/repository.py`. Follow the structure and subcommands described in the `repository.py` specification below. Adapt paths and tool configuration to match the target repository.
3. **Create the justfile** -- Create a UHPC011-compliant justfile at the repository root that delegates to `scripts/repository.py`. Follow the justfile specification below.
4. **Configure `pyproject.toml`** -- Ensure the root `pyproject.toml` has the necessary `[tool.repository]` section for external libraries and binary packages, plus tool configuration for `ruff`, `black`, `codespell`, `pyright`, `coverage`, and `pytest`.
5. **Verify** -- Run `just help` to confirm the justfile parses. Run `just test unit` and `just lint` to confirm that the justfile correctly delegates to `scripts/repository.py`. Fix any issues.

## Repository structure

The target repository layout should follow this pattern:

```
.
├── justfile                    # UHPC011-compliant, delegates to scripts/repository.py
├── pyproject.toml              # Root project config (deps, uv workspace, tool configs)
├── uv.lock
├── scripts/
│   └── repository.py           # Monorepo CLI tool (never called directly)
├── charms/                     # Individual Juju charms (uv workspace members)
│   └── <charm-name>/
│       ├── charmcraft.yaml
│       ├── pyproject.toml
│       ├── src/
│       ├── tests/unit/
│       └── terraform/
├── internal/                   # Private packages (uv workspace members)
│   └── <package-name>/
├── pkg/                        # Public packages (uv workspace members)
│   └── <package-name>/
└── tests/
    └── integration/            # Shared cross-charm integration tests
```

## `scripts/repository.py` specification

The `repository.py` file is a Python CLI tool that orchestrates all build, test, lint, and formatting operations across the monorepo. It must not be executed directly by developers; the justfile is the only entry point.

### Required subcommands

| Subcommand    | Description                                                                 |
|---------------|-----------------------------------------------------------------------------|
| `fmt`         | Apply formatting standards. Runs `black` and `ruff check --fix`.            |
| `lint`        | Check code style. Runs `codespell` and `ruff check`.                        |
| `typecheck`   | Stage charms, then run `pyright` against charm and package source.          |
| `unit`        | Stage charms, then run `pytest` with `coverage` for each charm and package. |
| `integration` | Build all charms, then run `pytest` against `tests/integration/`.           |
| `stage`       | Copy charm source, libraries, and requirements into `_build/`.              |
| `build`       | Stage charms, then run `charmcraft pack` for each charm.                    |
| `clean`       | Remove the `_build/` directory and all build artifacts.                     |

All subcommands accept optional positional `target` arguments (charm or package names). When no targets are given, the command operates on all charms and packages.

### Key design patterns

- **`BuildTool` wrapper** -- A dataclass that locates a binary on `PATH` via `shutil.which` and provides a `run_command` method that streams stdout/stderr in real time using threads.
- **`Repository` class** -- Loads monorepo metadata from `pyproject.toml` and `uv.lock` on initialization. Discovers charms, internal/external libraries, and packages. Resolves binary package versions from the lock file.
- **`Charm` and `Package` dataclasses** -- Hold metadata, paths, library dependencies, and package dependencies for each charm/package.
- **`CharmLibrary` dataclass** -- Represents a charm library with charm name, library name, and major/minor version. Handles conversion to/from `charmcraft.yaml` format.
- **Staging** -- Before running unit tests or type checks, charms are staged into `_build/<charm-name>/` with their libraries copied in, `charmcraft.yaml` rewritten (to inject `charm-binary-python-packages`), and `requirements.txt` exported via `uv export`.
- **Coverage** -- Unit tests run under `coverage run` per charm/package, then results are combined into a single report with `coverage combine`, `coverage report`, and `coverage xml`.
- **uv runner** -- Commands are run through `uv run --frozen --extra dev` to use the development virtual environment.

### Path constants

```python
ROOT_DIR = Path(__file__).parent.parent.resolve()  # repository root (one level up from scripts/)
BUILD_PATH = ROOT_DIR / "_build"
CHARMS_PATH = ROOT_DIR / "charms"
PUBLIC_PKGS_PATH = ROOT_DIR / "pkg"
PRIVATE_PKGS_PATH = ROOT_DIR / "internal"
LIBS_CHARM_PATH = BUILD_PATH / "libs"
```

Note: since `repository.py` lives in `scripts/`, `ROOT_DIR` must resolve to the parent of `scripts/` (i.e. the repository root).

### Configuration in `pyproject.toml`

The `repository.py` script reads configuration from the root `pyproject.toml`:

```toml
[tool.repository]
external-libraries = [
    { lib = "<charm>.<library>", version = "<major>.<minor>" },
]
binary-packages = [
    "<package-name>",
]
```

Per-charm `pyproject.toml` files may declare library dependencies:

```toml
[tool.repository]
libraries = [
    "<charm>.<library>",
]
```

## Justfile specification

The justfile must conform to UHPC011 (Common justfile format for Charmed HPC repositories). It delegates all substantial work to `scripts/repository.py` via `uv run`.

### Required variables and settings

```just
uv := require("uv")

export PY_COLORS := "1"
export PYTHONBREAKPOINT := "pdb.set_trace"

uv_run := "uv run --frozen --extra dev"
```

### Required recipes

All UHPC011 required recipes must be present:

```just
[private]
default:
    @just help

# Show available recipes
help:
    @just --list --unsorted

# Prepare the local environment
setup: env

# Clean project directory
clean:
    {{uv_run}} scripts/repository.py clean

# Apply static checks
check: fmt lint typecheck

# Run tests for specified targets, or all tests if none specified
test *targets:
    #!/usr/bin/env bash
    if [ "{{targets}}" = "" ]; then
        just test-all
        exit 0
    fi

    for target in {{targets}}; do
        if just --show $target > /dev/null 2>&1; then
            echo "Running $target tests..."
            just $target
        else
            echo "$target tests not found, skipping."
            exit 1
        fi
    done
```

### Recommended recipes (delegating to `scripts/repository.py`)

```just
# Run all test suites
test-all: unit integration

# Run unit tests
unit *args: lock
    {{uv_run}} scripts/repository.py unit {{args}}

# Run integration tests
integration *args: lock
    {{uv_run}} scripts/repository.py integration {{args}}

# Apply formatting standards
fmt: lock
    {{uv_run}} scripts/repository.py fmt

# Check files against style standards
lint: lock
    {{uv_run}} scripts/repository.py lint

# Perform type checking
typecheck: lock
    {{uv_run}} scripts/repository.py typecheck

# Build specified charms, or all charms if none specified
build *args: lock
    {{uv_run}} scripts/repository.py build {{args}}

# Regenerate uv.lock
lock:
    uv lock

# Create a uv development environment
env: lock
    uv sync --extra dev

# Upgrade uv.lock with the latest dependencies
upgrade:
    uv lock --upgrade
```

### License header

The justfile must include the Apache 2.0 license header at the top. Update the year to the current year:

```
# Copyright 2025 Canonical Ltd.
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
```

## Verification

After setting up both files, verify that the justfile correctly delegates to `scripts/repository.py`:

1. **Parse check** -- Run `just --list` and confirm all required and recommended recipes appear without errors.
2. **Unit tests** -- Run `just test unit` and confirm it dispatches to the `unit` recipe, which calls `scripts/repository.py unit`.
3. **Lint** -- Run `just lint` and confirm it calls `scripts/repository.py lint`.
4. **Format** -- Run `just fmt` and confirm it calls `scripts/repository.py fmt`.
5. **Type check** -- Run `just typecheck` and confirm it calls `scripts/repository.py typecheck`.
6. **Clean** -- Run `just clean` and confirm it calls `scripts/repository.py clean`.
7. **Test dispatch** -- Run `just test unit integration` and confirm both the `unit` and `integration` recipes are invoked sequentially.
8. **Test fallback** -- Run `just test` with no arguments and confirm it delegates to `test-all`, which runs all test suites.

If any command fails, check that:
- `scripts/repository.py` is importable (no syntax errors, correct Python version).
- The `uv` development environment is set up (`just setup`).
- The `pyproject.toml` has the correct `[tool.repository]` configuration.
- Charm directories exist under `charms/` with valid `pyproject.toml` and `charmcraft.yaml` files.

## Constraints

- DO NOT allow `scripts/repository.py` to be called directly. It must always be invoked through the justfile via `uv run`.
- DO NOT place `repository.py` at the repository root. It must live in `scripts/`.
- DO NOT omit any UHPC011 required recipe from the justfile.
- DO NOT rename required or recommended recipes. Use the exact names specified by UHPC011.
- DO NOT use recipe groups in the justfile. All recipes must be ungrouped.
- DO NOT change the implementation of the `default` recipe. It must always be `@just help`.
- DO NOT change the signature of the `test` recipe. It must accept `*targets`.
- DO ensure the `default` recipe has the `[private]` attribute.
- DO ensure the justfile is compatible with `just` version 1.48.1.
- DO use `require()` for any external tools the recipes depend on (e.g. `uv`).
- DO include the Apache 2.0 license header at the top of the justfile.
- DO include a comment above each recipe describing what it does.
- DO set `ROOT_DIR` in `repository.py` to `Path(__file__).parent.parent.resolve()` to account for the `scripts/` subdirectory.
