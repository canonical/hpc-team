# hpc-team-gitgud agentic skills

A collection of GitHub Copilot agent skills for Charmed HPC development workflows.

## Skills

| Skill | Description |
|---|---|
| [`create-charm-terraform-module`](create-charm-terraform-module/SKILL.md) | Create or review Terraform modules for individual Juju charms following the CC008 Charm Terraform Standards specification |
| [`create-charmed-hpc-justfile`](create-charmed-hpc-justfile/SKILL.md) | Create or review justfiles for Charmed HPC repositories following the UHPC011 Common justfile format specification |
| [`create-juju-integration-interface-readme`](create-interface-readme/SKILL.md) | Create README files for standalone Juju integration interface implementation packages and libraries |
| [`setup-charm-monorepo`](setup-charm-monorepo/SKILL.md) | Set up a charm monorepo with a `scripts/repository.py` CLI tool and a UHPC011-compliant justfile |

---

## create-charm-terraform-module

Creates or reviews Terraform modules for individual Juju charms following the CC008 specification. A charm module is only required if the charm can be used standalone.

### When to use

Invoke this skill when you need to write, validate, or restructure a charm-level Terraform module that uses the Terraform Juju provider (pessimistically held to ~> 1.0).

### Summary

1. Read all `.tf` files in the module directory (or scan the charm's `metadata.yaml`/`charmcraft.yaml` for a new module).
2. Ensure the required file structure: `README.md`, `providers.tf`, `terraform.tf`, `main.tf`, `variables.tf`, `outputs.tf`, and optionally `locals.tf`.
3. Define mandatory inputs (`app_name`, `channel`, `config`, `model_uuid`, `revision`, `units`) and optional inputs (`base`, `endpoint_bindings`, `expose`, `machines`, `offered_endpoints`, `resources`, `storage_directives`) in `variables.tf`.
4. Define mandatory outputs (`application`) and optional outputs (`provides`, `requires`, `offers`) in `outputs.tf`.
5. Document the module in `README.md` with an API section (inputs/outputs tables) and a usage example.
6. Validate with `terraform fmt` and `terraform validate`.

### Key constraints

- Do not include the `units` or `constraints` variables for subordinate charms.
- Keep `variables.tf`, `outputs.tf`, and `locals.tf` entries in alphabetical order.
- Use plain English; do not use Latin words or phrases.
- Require the minimum Juju provider version at ~> 1.0.

See [create-charm-terraform-module/SKILL.md](create-charm-terraform-module/SKILL.md) for the full workflow, all mandatory/optional inputs and outputs, and the README template.

---

## create-charmed-hpc-justfile

Creates or reviews justfiles for Charmed HPC repositories following the UHPC011 specification. Every Charmed HPC repository must provide a `justfile` with a consistent set of recipes.

### When to use

Invoke this skill when you need to write, validate, or restructure a justfile that must conform to the Charmed HPC standard. The justfile must be compatible with `just` version 1.48.1.

### Summary

1. Read the repository to understand the project type (Python/uv, Terraform, monorepo) and identify tooling (`uv`, `tofu`, `repository.py`).
2. Add `require()` calls for any external tools the recipes depend on.
3. Implement all required recipes (`default`, `help`, `setup`, `clean`, `check`, `test`) with the correct names and signatures.
4. Add recommended recipes (`fmt`, `lint`, `typecheck`, `test-all`, `unit`, `integration`, `build`, `lock`, `env`, `upgrade`) as applicable.
5. Include the Apache 2.0 license header at the top.
6. Validate by running `just --list`.

### Key constraints

- Do not use recipe groups. All recipes must be ungrouped.
- Do not rename required or recommended recipes.
- The `default` recipe must be `[private]` and delegate to `just help`.
- The `test` recipe must accept `*targets`.
- Every required recipe must be present (implement as a no-op if not applicable).

See [create-charmed-hpc-justfile/SKILL.md](create-charmed-hpc-justfile/SKILL.md) for the full specification, all recipe signatures, and example justfiles.

---

## create-juju-integration-interface-readme

Creates README files for standalone Juju integration interface implementation packages and libraries.

### When to use

Invoke this skill when you need to write or generate a README for an interface library package that implements a provider/requirer pattern for Juju charm relations.

### Summary

1. Identify the interface package directory (`src/` with `__init__.py` defining provider/requirer classes, data models, and custom events).
2. Read the source code to extract the package name, Provider/Requirer class names, custom events, and data models.
3. Determine data flow direction: which fields the Requirer sends to the Provider, and which the Provider sends to the Requirer.
4. Generate the README with the required sections: Usage, Direction (with mermaid diagram), Behavior, Integration data (with YAML example), and Examples (requirer and provider charm code).
5. Verify accuracy against the source code.

### Key constraints

- Do not use Latin terms (for example, use "for example" instead of "e.g.", and "that is" instead of "i.e.").
- Do not invent data fields, events, or behaviors not present in the source code.
- Use bullet lists for Provider and Requirer behavior expectations.
- Use fenced code blocks with language identifiers (`python`, `yaml`, `mermaid`).

See [create-interface-readme/SKILL.md](create-interface-readme/SKILL.md) for the full output format template and reference examples.

---

## setup-charm-monorepo

Sets up a charm monorepo following the patterns established by `charmed-hpc/slurm-charms`. Uses `uv` workspaces, a `scripts/repository.py` CLI tool, and a UHPC011-compliant justfile.

### When to use

Invoke this skill when scaffolding or reviewing a monorepo repository that uses uv workspaces, `repository.py` for build/test/lint orchestration, and `just` as the developer entry point.

### Summary

1. Read the repository structure to identify charm directories, internal/public packages, integration tests, and configuration files.
2. Create `scripts/repository.py` with the required subcommands: `fmt`, `lint`, `typecheck`, `unit`, `integration`, `stage`, `build`, `clean`.
3. Create the UHPC011-compliant justfile that delegates all work to `scripts/repository.py` via `uv run`.
4. Configure `pyproject.toml` with the `[tool.repository]` section, tool settings, and workspace members.
5. Verify with `just --list`, `just test unit`, and `just lint`.

### Key constraints

- Do not call `scripts/repository.py` directly. All interaction goes through the justfile.
- Do not place `repository.py` at the repository root. It must live in `scripts/`.
- Do not omit any UHPC011 required recipe from the justfile.
- Do not rename required or recommended recipes.

See [setup-charm-monorepo/SKILL.md](setup-charm-monorepo/SKILL.md) for the full specification, `repository.py` subcommand details, and justfile recipe signatures.
