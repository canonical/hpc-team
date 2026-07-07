# HPC team agentic skills

A collection of agent skills for Charmed HPC development workflows.

## Skills

| Skill | Description |
|---|---|
| [`create-charm-terraform-module`](create-charm-terraform-module/SKILL.md) | Create or review Terraform modules for individual Juju charms following the CC008 Charm Terraform Standards specification. Use when writing, validating, or restructuring a charm-level Terraform module that uses the Terraform Juju provider. |
| [`create-charmed-hpc-justfile`](create-charmed-hpc-justfile/SKILL.md) | Create or review justfiles for Charmed HPC repositories following the UHPC011 Common justfile format specification. Use when writing, validating, or restructuring a justfile that must conform to the Charmed HPC standard. |
| [`create-juju-integration-interface-readme`](create-interface-readme/SKILL.md) | Create README files for standalone Juju integration interface implementation packages and libraries. Use when writing, reviewing, or generating a README for an interface library package that implements a provider/requirer pattern for Juju charm relations. |
| [`jubilant-bdd-migration`](jubilant-bdd-migration/SKILL.md) | Migrate an existing Juju charm repo's pytest integration tests to Behavior-Driven Development (BDD) by authoring YAML test plans with gherkinator that generate Gherkin feature files backed by pytest-jubilant-bdd's reusable step handlers. Use when asked to "migrate tests to BDD", "convert to Gherkin", "use pytest-jubilant-bdd", or to Gherkin-ize jubilant-based integration tests in a charm repo (e.g. slurm-charms, filesystem-charms, sssd-operator). Do NOT use for the pytest-jubilant-bdd plugin's own unit tests. |
| [`setup-charm-monorepo`](setup-charm-monorepo/SKILL.md) | Set up a charm monorepo with a scripts/repository.py CLI tool and a UHPC011-compliant justfile. Use when scaffolding or reviewing a monorepo repository that uses uv workspaces, repository.py for tooling, and just as the developer entry point. |

---

## create-charm-terraform-module

Creates or reviews Terraform modules for individual Juju charms following the CC008 Charm Terraform Standards specification. A charm module provides a Terraform module for a single charm. It is only required if the charm can be used standalone — if a charm cannot be used standalone, providing a Terraform module is not mandatory.

Refer to [create-charm-terraform-module/SKILL.md](create-charm-terraform-module/SKILL.md) for the full specification, all mandatory and optional inputs and outputs, and the README template.

### When to use

Invoke this skill when you need to write, validate, or restructure a charm-level Terraform module that uses the Terraform Juju provider. Provide a path to a Terraform module directory, or leave blank to review the current directory.

## create-charmed-hpc-justfile

Creates or reviews justfiles for Charmed HPC repositories following the UHPC011 specification. Every Charmed HPC repository must provide a `justfile` with a consistent set of recipes to ensure a uniform contributor experience and facilitate the sharing of GitHub workflows.

Refer to [create-charmed-hpc-justfile/SKILL.md](create-charmed-hpc-justfile/SKILL.md) for the full specification, all recipe signatures, and example justfiles for Python/uv and Terraform projects.

### When to use

Invoke this skill when you need to write, validate, or restructure a justfile that must conform to the Charmed HPC standard. Provide a path to a justfile or repository directory, or leave blank to review the current directory.

## create-juju-integration-interface-readme

Creates README files for standalone Juju integration interface implementation packages and libraries.

Refer to [create-interface-readme/SKILL.md](create-interface-readme/SKILL.md) for the full output format template and reference examples.

### When to use

Invoke this skill when you need to write or generate a README for an interface library package that implements a provider/requirer pattern for Juju charm relations. Ask the user if they do not provide a package name or directory when loading this skill.

## jubilant-bdd-migration

Convert an existing charm repo's existing pytest integration tests (written with `jubilant`) into Gherkin feature files backed by `pytest-jubilant-bdd`. The workflow is driven by `gherkinator`. Test plans are authored once as structured YAML, validated against a strict schema, and transpiled into `.feature` files that the BDD framework executes.

Refer to [jubilant-bdd-migration/SKILL.md](jubilant-bdd-migration/SKILL.md) for the full gherkinator integration details, reusable step reference, and supporting files.

### When to use

Invoke this skill when asked to migrate tests to BDD, convert to Gherkin, use pytest-jubilant-bdd, or Gherkin-ize jubilant-based integration tests in a charm repo (for example, slurm-charms, filesystem-charms, sssd-operator). Do not use for the pytest-jubilant-bdd plugin's own unit tests.

## setup-charm-monorepo

Sets up a charm monorepo following the patterns established by `charmed-hpc/slurm-charms`. The repository uses `uv` workspaces for dependency management, a `scripts/repository.py` CLI tool for build/test/lint orchestration, and a `justfile` (conforming to UHPC011) as the developer-facing entry point.

Refer to [setup-charm-monorepo/SKILL.md](setup-charm-monorepo/SKILL.md) for the full specification, `repository.py` subcommand details, and justfile recipe signatures.

### When to use

Invoke this skill when scaffolding or reviewing a monorepo repository that uses uv workspaces, `repository.py` for tooling, and `just` as the developer entry point. Provide a path to the repository root directory, or leave blank to use the current directory.
