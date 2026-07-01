---
name: create-charm-terraform-module
description: 'Create or review Terraform modules for individual Juju charms following the CC008 Charm Terraform Standards specification. Use when writing, validating, or restructuring a charm-level Terraform module that uses the Terraform Juju provider.'
argument-hint: 'Path to a Terraform module directory, or leave blank to review the current directory.'
allowed-tools: terraform, tofu
---

# Charm Terraform Standards

Creates or reviews Terraform modules for individual Juju charms following the CC008 Charm Terraform Standards specification. A charm module provides a Terraform module for a single charm. It is only required if the charm can be used standalone — if a charm cannot be used standalone, providing a Terraform module is not mandatory.

The specification assumes the Terraform Juju provider version is pessimistically held to ~> 1.0.

## Process

1. **Read the module directory** — Read all `.tf` files and `README.md` in the target directory to understand the current state. If creating a new module, check the charm's `metadata.yaml` or `charmcraft.yaml` to identify the charm name, endpoints (`provides`/`requires`), and whether it is subordinate. Also, add Terraform specific metadata files to the .gitignore file (see below).
2. **Apply the file structure** — Ensure the module provides the required file layout (see below).
4. **Define inputs** — Add all mandatory input variables to `variables.tf` with the correct names, types, and defaults. Add optional inputs as needed. Entries must be in alphabetical order.
5. **Define outputs** — Add all mandatory outputs to `outputs.tf`. Add `provides` and `requires` outputs if the charm defines those endpoints. Entries must be in alphabetical order.
6. **Write main module code** — In `main.tf`, define the `juju_application` resource using the input variables. If the module is large, split into `applications.tf`, `integrations.tf`, `offers.tf`, etc.
7. **Write provider and version blocks** — Ensure `providers.tf` contains the Juju provider block and `terraform.tf` contains a `terraform` block with `required_version` and `required_providers` (Juju provider ~> 1.0).
8. **Document the module** — Write `README.md` following the structure defined in the README Structure section below. Use the `uuid` output of the `juju_model` model resource in the README's `Usage` section.
9. **Validate** — Check that all mandatory inputs and outputs are present with correct names and types, and that files are in alphabetical order where required. Use `terraform fmt` and `terraform validate` to validate that the module is correct.

## Required file structure

Every charm module must provide these files:

- `README.md` — Documentation. Must clarify inputs and outputs at minimum.
- `providers.tf` — All provider blocks and configurations.
- `terraform.tf` — A single `terraform` block defining `required_version` and `required_providers`. Minimum Juju provider version is >1.0.0.
- `main.tf` — Main module code defining the `juju_application` resource. May be split into `applications.tf`, `integrations.tf`, `offers.tf`, etc. if the module is large.
- `variables.tf` — Input variables, in alphabetical order.
- `outputs.tf` — Outputs, in alphabetical order.
- `locals.tf` — Local variables, in alphabetical order. Not requried if the charm module does not need local variables defined.

## README Structure

The `README.md` must follow this structure:

### Title and description

```markdown
# Terraform module for <charm-name>

This is a Terraform module facilitating the deployment of the <charm-name> charm using
the [Juju Terraform provider](https://github.com/juju/terraform-provider-juju).
For more information, refer to the
[documentation](https://registry.terraform.io/providers/juju/juju/latest/docs)
for the Juju Terraform provider.
```

### Requirements section

List the minimum versions and prerequisites:

```markdown
## Requirements

- Terraform >= 1.0
- Juju Terraform provider >= 1.0.0, < 2.0.0
- An existing Juju model
```

### API section

Document all inputs and outputs under an `## API` heading.

#### Inputs table

Use a `### Inputs` sub-heading with a table containing these columns: Name, Type, Description, Default, Required. Mark required inputs (those with no default) with `Y` in the Required column. Leave the Required column empty for optional inputs. List entries in alphabetical order.

```markdown
### Inputs

| Name          | Type        | Description                                                        | Default         | Required |
|---------------|-------------|--------------------------------------------------------------------|-----------------|:--------:|
| `app_name`    | string      | The Juju application name                                          | `"<charm>"`    |          |
| `channel`     | string      | Charm channel to deploy from                                       | `"latest/edge"` |          |
| `config`      | map(string) | Map of charm configuration options                                 | `{}`            |          |
| `model_uuid`  | string      | UUID of the Juju model to deploy the charm into                    |                 |    Y     |
| `revision`    | number      | Charm revision to deploy. Null deploys the latest on given channel | `null`          |          |
| `units`       | number      | Number of application units to deploy                              | `1`             |          |
```

#### Outputs table

Use a `### Outputs` sub-heading with a table containing these columns: Name, Description.

```markdown
### Outputs

| Name          | Description                              |
|---------------|------------------------------------------|
| `application` | The deployed `juju_application` resource |
| `provides`    | Map of `provides` endpoint names         |
| `requires`    | Map of `requires` endpoint names         |
```

If the module exposes `provides` or `requires` outputs, add a follow-up paragraph and table listing the keys and endpoint names for each:

```markdown
The `requires` output exposes the following endpoint names:

| Key               | Endpoint name     |
|-------------------|-------------------|
| `<key>`           | `<endpoint>`      |
```

### Usage section

Show a minimal usage example that references `juju_model.<model>.uuid` for the `model_uuid` input, followed by a `terraform apply` command:

```markdown
## Usage

Ensure that Terraform is aware of the Juju model dependency of the charm module.

\```hcl
module "<charm>" {
  source     = "git::https://github.com/canonical/<charm-repo>//terraform"
  model_uuid = juju_model.my_model.uuid
}
\```

To deploy this module with its required dependency, you can run the following
command:

\```shell
terraform apply -var="model_uuid=<MODEL_UUID>" -auto-approve
\```
```

## Files and directories to add to .gitignore

- `.terraform`
- `.terraform.lock.hcl`
- `*.tfstate*`

## Mandatory inputs

The following variables must be present in `variables.tf`:

| Name | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `app_name` | `string` | Charm-specific, non-null | Name for the deployed application |
| `channel` | `string` | Charm-specific, non-null | Charm channel. Must not be nullable if default is null |
| `config` | `map(string)` | `{}` | Map of config options |
| `constraints` | `string` | `null` | Constraints string. **Must not** be provided for subordinate charms |
| `model_uuid` | `string` | — | Existing model UUID. **Not nullable** |
| `revision` | `number` | `null` | Charm revision. Null deploys the latest on a given channel |
| `units` | `number` | `1` | Unit count/scale. **Must not** be provided for subordinate charms |

## Optional inputs

The following variables may be added to `variables.tf`. If present, they must use the names and types listed here:

| Name | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `base` | `string` | `null` | Operating system (e.g. `ubuntu@22.04`) |
| `endpoint_bindings` | Attribute Set | `{}` | Endpoint binding map |
| `expose` | Block List | `{}` | Expose block per provider docs |
| `machines` | `set(string)` | `[]` | List of `juju_machine` resources for deployment |
| `offered_endpoints` | `list(string)` | `[]` | Endpoints exposed as offers |
| `resources` | `map(string)` | `{}` | Resources to use |
| `storage_directives` | `map(string)` | `{}` | Storage map |

Other inputs beyond this list are also allowed.

## Mandatory outputs

The following output must be present in `outputs.tf`:

| Name | Type | Description |
| :--- | :--- | :--- |
| `application` | `object` | The deployed `juju_application` resource object |

## Optional outputs

The following outputs may be added to `outputs.tf`. If present, they must use the names and types listed here:

| Name | Type | Description |
| :--- | :--- | :--- |
| `offers` | `map(string)` | Offers exposed by the charm. Keys should be compatible with endpoint names |
| `provides` | `map(string)` | Provides endpoints. **Mandatory if the charm has `provides` defined** |
| `requires` | `map(string)` | Requires endpoints. **Mandatory if the charm has `requires` defined** |

Other outputs beyond this list are also allowed.

## Example outputs

```hcl
output "application" {
  value = juju_application.<charm>
}

output "provides" {
  value = {
    metrics = "prometheus-metrics"
  }
}

output "requires" {
  value = {
    mimir_cluster = "mimir-cluster"
  }
}

output "offers" {
  value = {
    metrics = <offer-url>
  }
}
```

## Versioning

Tags and versions use `{major}.{minor}.{patch}` with no metadata, pre-release info, or additional suffixes.

- **Major** — Non-backward-compatible changes: renaming resources (triggers destroy/recreate), changing default config values (e.g. channel upgrades), renaming variables or outputs.
- **Minor** — New features: adding optional config options, adding new outputs.
- **Patch** — Trivial fixes: updating descriptions, non-breaking bug fixes.

### Tagging conventions by repository layout

- Charm module co-located with charm code: `tf-X.Y.Z`
- Multiple modules in a single repository: `<product>-X.Y.Z` (e.g. `prometheus-k8s-1.1.2`)
- Dedicated repository per module: `vX.Y.Z`

## Constraints

- DO NOT include the `units` variable for subordinate charms.
- DO NOT add metadata, pre-release info, or additional suffixes to version tags.
- DO NOT create the `locals.tf` file if local, non-input variables are not required.
- DO NOT use Latin words or phrases in documentation or descriptions. DO USE plain English.
- DO ensure `variables.tf`, `outputs.tf`, and `locals.tf` entries are in alphabetical order.
- DO ensure the minimum Juju provider version is ~> 1.0.
- DO ensure every module includes the required file structure (`README.md`, `providers.tf`, `terraform.tf`, `main.tf`, `variables.tf`, `outputs.tf`, `locals.tf`).
- DO include `provides` and `requires` outputs when the charm defines those endpoints.
