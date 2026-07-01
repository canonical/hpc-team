---
name: create-charmed-hpc-justfile
description: 'Create or review justfiles for Charmed HPC repositories following the UHPC011 Common justfile format specification. Use when writing, validating, or restructuring a justfile that must conform to the Charmed HPC standard.'
argument-hint: 'Path to a justfile or repository directory, or leave blank to review the current directory.'
---

# Common justfile format for Charmed HPC repositories

Creates or reviews justfiles for Charmed HPC repositories following the UHPC011 specification. Every Charmed HPC repository must provide a `justfile` with a consistent set of recipes to ensure a uniform contributor experience and facilitate the sharing of GitHub workflows.

The justfile must run with `just` version 1.48.1. Use of unstable features is permitted.

## Process

1. **Read the repository** — Read the existing `justfile` (if any) and examine the repository structure to understand the project type (e.g. Python/uv project, Terraform modules, monorepo). Check for tooling such as `pyproject.toml`, `repository.py`, `uv.lock`, or Terraform configuration files.
2. **Identify required tooling** — Determine which tools the justfile will delegate to (e.g. `uv`, `tofu`, `repository.py`). Add `require()` calls for any external tools the recipes depend on.
3. **Add required recipes** — Ensure all required recipes are present with the correct names and signatures (see Required recipes below). If a recipe is not applicable to the repository, implement it as a no-op, but it must still be present.
4. **Add recommended recipes** — Add any recommended recipes that are applicable to the repository (see Recommended recipes below). Use exactly the recipe names specified.
5. **Implement the `test` recipe** — Follow the suggested implementation pattern for the `test` recipe if the repository uses a `bash`-compatible environment (see Suggested `test` implementation below).
6. **Add the license header** — Add the Apache 2.0 license header as a comment at the top of the justfile.
7. **Validate** — Verify that all required recipes are present, no recipe groups are used, and recipe names match the specification. Run `just --list` to confirm the justfile parses correctly.

## Required recipes

Every Charmed HPC justfile must implement these recipes. The implementation may be a no-op if not appropriate for the repository, but the recipe must still be present.

```just
# Performed if no recipes are specified. Must have this exact implementation.
[private]
default:
    @just help

# Show available recipes
help:

# Prepare the local environment
setup:

# Clean project directory
clean:

# Apply static checks
# Implementation expected to be composed of recommended recipes: fmt, lint, and typecheck.
check:

# Run specified target test suites, or all test suites if none specified
test *targets:
```

### Recipe details

- **`default`** — Must be private (`[private]`). Must delegate to `just help`. This is the only recipe with a prescribed implementation.
- **`help`** — Typically implemented as `@just --list --unsorted`.
- **`setup`** — Prepares the local development environment. For uv projects, this typically delegates to the `env` recipe. For Terraform projects, this typically delegates to `init`.
- **`clean`** — Removes build artifacts, caches, and generated files.
- **`check`** — Runs all static analysis. Typically composed of `fmt`, `lint`, and `typecheck`.
- **`test *targets`** — Runs specified test suites by name, or all test suites if no targets are given.

## Recommended recipes

Repositories may implement the following recipes as needed. If implemented, they must use these exact names:

```just
# Apply formatting standards
fmt:

# Check against style standards
lint:

# Perform type checking
typecheck:

# Run all test suites
# Implementation expected to be composed of unit, integration, and other test type recipes.
test-all:

# Run unit tests for specified artifacts, or all artifacts if none specified
unit *args:

# Run integration tests for specified artifacts, or all artifacts if none specified
integration *args:

# Build specified artifacts, or all artifacts if none specified
build *args:

# Regenerate uv.lock
lock:

# Create a uv development environment
env:

# Upgrade uv.lock with the latest dependencies
upgrade:
```

## Suggested `test` implementation

Given the relative complexity of the required `test` recipe, use this implementation pattern when the environment has `bash` available:

```just
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

When no targets are provided, all test suites run via `test-all`. When specific targets are given, each is dispatched to a matching recipe if one exists.

## License header

Every justfile must include the Apache 2.0 license header at the top:

```
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
```

## Example justfile — Python/uv project

```just
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

uv := require("uv")

export PY_COLORS := "1"
export PYTHONBREAKPOINT := "pdb.set_trace"

uv_run := "uv run --frozen --extra dev"

[private]
default:
    @just help

# Prepare the local environment
setup: env

# Clean project directory
clean:
    {{uv_run}} repository.py clean

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

# Run all test suites
test-all: unit integration

# Run unit tests
unit *args: lock
    {{uv_run}} repository.py unit {{args}}

# Run integration tests
integration *args: lock
    {{uv_run}} repository.py integration {{args}}

# Regenerate uv.lock
lock:
    uv lock

# Create a uv development environment
env: lock
    uv sync --extra dev

# Upgrade uv.lock with the latest dependencies
upgrade:
    uv lock --upgrade

# Apply formatting standards
fmt: lock
    {{uv_run}} repository.py fmt

# Check files against style standards
lint: lock
    {{uv_run}} repository.py lint

# Perform type checking
typecheck:
    {{uv_run}} repository.py typecheck

# Show available recipes
help:
    @just --list --unsorted
```

## Example justfile — Terraform project

```just
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
# limitations under the License.\
# Necessary to use `||` logical operator.

set unstable := true

project_dir := justfile_directory()
modules_dir := project_dir / "modules"
default_module_list := shell("ls -d -- $1/*", modules_dir)
uv := require("tofu")

[private]
default:
    @just help

# Prepare the local environment
setup: init

# Clean project directory
clean:
    find . -name .terraform -type d | xargs rm -rf
    find . -name .terraform.lock.hcl -type f | xargs rm -rf
    find . -name "terraform.tfstate*" -type f | xargs rm -rf

# Apply static checks
check: fmt validate

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

# Run all test suites
test-all: integration

# Run integration tests
integration *args:
    tofu apply -auto-approve

# Apply formatting standards to project
fmt:
    just --fmt --unstable
    tofu fmt -recursive

# Initialize Terraform modules
init *modules:
    #!/usr/bin/env bash
    set -euxo pipefail
    modules=({{ prepend(modules_dir, modules) || default_module_list }})
    for module in ${modules}; do
        tofu -chdir=${module} init
    done

# Validate Terraform modules
validate *modules: (init modules)
    #!/usr/bin/env bash
    set -euxo pipefail
    modules=({{ prepend(modules_dir, modules) || default_module_list }})
    for module in ${modules}; do
        tofu -chdir=${module} fmt -check
        tofu -chdir=${module} validate
    done

# Show available recipes
help:
    @just --list --unsorted
```

## Constraints

- DO NOT use recipe groups. All recipes must be ungrouped.
- DO NOT omit any required recipe. If a recipe is not applicable, implement it as a no-op.
- DO NOT rename required or recommended recipes. Use the exact names specified.
- DO NOT change the implementation of the `default` recipe. It must always be `@just help`.
- DO NOT change the signature of the `test` recipe. It must accept `*targets`.
- DO ensure the `default` recipe has the `[private]` attribute.
- DO ensure the justfile is compatible with `just` version 1.48.1.
- DO use `require()` for any external tools the recipes depend on (e.g. `uv`, `tofu`).
- DO include the Apache 2.0 license header at the top of the justfile.
- DO include a comment above each recipe describing what it does.
