---
name: jubilant-bdd-migration
description: Migrate an existing Juju charm repo's pytest integration tests to Behavior-Driven Development (BDD) by authoring YAML test plans with gherkinator that generate Gherkin feature files backed by pytest-jubilant-bdd's reusable step handlers. Use when asked to "migrate tests to BDD", "convert to Gherkin", "use pytest-jubilant-bdd", or to Gherkin-ize jubilant-based integration tests in a charm repo (e.g. slurm-charms, filesystem-charms, sssd-operator). Do NOT use for the pytest-jubilant-bdd plugin's own unit tests.
license: Apache-2.0
compatibility: opencode
---

# Jubilant BDD Migration (gherkinator-controlled)

Convert an external charm repo's existing pytest integration tests (written
with `jubilant`) into Gherkin feature files backed by `pytest-jubilant-bdd`.
The workflow is driven by `gherkinator`: test plans are authored once as
structured YAML, validated against a strict schema, and transpiled into
`.feature` files that the BDD framework executes.

## Use this skill when

- The user asks to "migrate", "convert", "Gherkin-ize", or "move to BDD" tests
  in a Juju charm repository.
- The target repo has `tests/integration/*.py` using `jubilant` directly (e.g.
  `jubilant.temp_model()`, `juju.deploy()`, `juju.wait()`) and no feature
  files.
- The repo contains charm markers (`charmcraft.yaml`, `metadata.yaml`,
  `src/charm.py`).

## Do NOT use this skill when

- Working inside the `pytest-jubilant-bdd` plugin repo itself (that repo has
  its own `unit-testing` skill for testing the framework's handlers).
- The user only wants to fix or extend existing BDD tests, not migrate from
  non-BDD tests.
- The target repo does not already use `jubilant`; this is a migration skill,
  not a greenfield authoring guide.

## DOs

- DO install `gherkinator` (snap or from source) before authoring plans.
- DO initialize `test-plan.yaml` via `gherkinator init` and edit it with
  `gherkinator edit` (surfaces schema hints and validates on save).
- DO run `gherkinator validate` after every YAML change.
- DO regenerate `.feature` files with `gherkinator generate --format gh`
  after every YAML change.
- DO start new plans with `status: planned`; flip to `implemented` only
  after the BDD suite is green for that plan.
- DO load each generated `.feature` in its own `test_*.py` via
  `scenarios("features/<name>.feature")`.
- DO use `context.wait()` for polling in custom steps; drop
  `tenacity.Retrying`.
- DO consult the `reusable-step-handler` skill in the pytest-jubilant-bdd
  repo for the canonical `Context` API when authoring custom steps.
- DO keep the original non-BDD tests in place until the BDD suite is fully
  green.

## DO NOTs

- DO NOT hand-edit generated `.feature` files — they are overwritten on
  every `gherkinator generate`.
- DO NOT import step handlers from `pytest_jubilant_bdd._main`; the
  plugin auto-registers them via the `pytest11` entry point, and they are
  not part of the public API.
- DO NOT define a `juju` fixture in `conftest.py` — the plugin provides
  `context`.
- DO NOT invent `type`, `status`, or `risk` values outside the enums
  enforced by `gherkinator validate`.
- DO NOT modify production charm code in the target repo to make a test
  pass — pause and ask the user.
- DO NOT bypass `gherkinator validate` by editing the generated
  `.feature` file to silence schema errors.

## Framework facts (source of truth)

These are verified against the installed `pytest-jubilant-bdd` package.

- **Auto-registration.** The plugin registers via the `pytest11` entry point
  (`pyproject.toml` → `pytest_jubilant_bdd._main`). Installing the package
  makes all built-in `@given`/`@when`/`@then` handlers available to
  pytest-bdd. Consumers **never import the step handlers**.
- **Public API** (`from pytest_jubilant_bdd import ...`): `Context`,
  `assertions`, `flexible`, `make_dict`, `make_list`. Only these are
  importable. `Context` is the fixture type; the rest are for authoring
  custom steps.
- **The `context` fixture** (session-scoped, provided by the plugin) yields
  a `Context` object. It replaces a hand-rolled `juju` fixture. Do **not**
  define a `juju` fixture in the charm repo's `conftest.py`.
- **CLI options** registered by the plugin: `--juju-bdd-no-teardown` (skip
  model teardown) and `--juju-bdd-wait-timeout <sec>` (default 180s).
- **Dependencies** (the plugin pulls these in): `jubilant ~= 1.0`,
  `pytest-bdd ~= 8.0`. Requires Python `>=3.12`.

### Authoritative reference: the `context` fixture API

The full `Context` API — `context.get_juju()`, `context.get_app()` /
`get_apps()` / `get_unit()`, the `action_results` / `exec_results` stacks,
`context.wait()` polling semantics, and the `assertions.app` / `.model` /
`.unit` namespaces — is documented authoritatively in the
**`reusable-step-handler`** skill in the pytest-jubilant-bdd repo:

- Repo path: `.agents/skills/reusable-step-handler/SKILL.md`
- Web: https://github.com/canonical/pytest-jubilant-bdd/blob/main/.agents/skills/reusable-step-handler/SKILL.md

That skill is the source of truth for the `context` fixture and for how
reusable handlers integrate with it. Consult it whenever you need the exact
signature, return type, or error class for a `Context` method, or when
authoring custom steps. The migration skill only restates the high-level
patterns needed to map existing jubilant code onto built-in steps (see
[reference.md](reference.md)).

## Reusable step reference

Exact Gherkin phrasing (single quotes; `[...]` marks optional, reorderable
clauses; `%...%` blocks are raw-regex units handled by the `flexible`
parser).

**Given (setup):**

| Step phrasing | Handler | Notes |
|---|---|---|
| `Given I add model '{model}'` | `add_model` | Creates a model with a random suffix. |
| `Given I add '{n}' units to app '{app}' [in model '{model}']` | `add_unit` | `unit`/`units` both accepted. |
| `Given I deploy '{app}' [in model '{model}'] [from channel '{channel}'] [on base '{base}'] [with '{n}' units]` | `deploy` | Charmhub deploy. |
| `Given I deploy '{app}' from a local charm [located at '{path}'] [in model '{model}'] [on base '{base}'] [with '{n}' units]` | `deploy_local` | If `located at` omitted, reads `<APP>_CHARM_PATH` env var. |
| `Given I integrate '{app_one}' with '{app_two}'` | `integrate` | |
| `Given model '{model}' exists` | `model_exists` | Asserts presence. |
| `Given '{app_one}' is integrated with '{app_two}'` | `is_integrated` | Asserts relation. |
| `Given '{app}' is deployed [in model '{model}']` | `is_deployed` | Asserts deployment. |
| `Given I reset '{option}' for app '{app}' [in model '{model}']` | `reset_app_config` | |
| `Given I set '{option}' for app '{app}' to '{value}' [in model '{model}']` | `set_app_config` | |

**When (actions):**

| Step phrasing | Handler | Notes |
|---|---|---|
| `When I run action '{action}' on unit '{u}' [with parameters '{k=v ...}'] [in model '{model}']` | `run_action` | `unit`/`units` accepted; multiple targets as `'a/0', 'a/1', and 'a/2'`; params like `'debug=true key=val'`. Results pushed to `context.action_results`. |
| `When I execute '{command}' on machine '{m}' [in model '{model}']` | `run_exec` | `machine`/`machines` and `unit`/`units` accepted. Results pushed to `context.exec_results`. |

**Then (attestation):**

| Step phrasing | Handler | Notes |
|---|---|---|
| `Then all agents are '{status}' [in models 'm1', 'm2', and 'm3']` | `assert_all_agent_status` | `status` ∈ `allocating`, `executing`, `error`, `idle`, `lost`. Polls via `context.wait()`. |
| `Then the workload status for app '{app}' is '{status}'` | `assert_workload_status` | `status` ∈ `active`, `blocked`, `error`, `maintenance`, `waiting`. Use `app` or `unit` as the type. |
| `Then the workload status message for app '{app}' is '{message}'` | `assert_workload_status_message` | Use `app` or `unit`. |

Status values are fixed by the framework; do not invent new ones in feature
files.

## Gherkinator integration (controller for test plans)

The migration is driven by `gherkinator`, a CLI that treats YAML test plans
as the single source of truth and generates `.feature` files from them.
Authors edit YAML; `.feature` files are generated artifacts (regenerate them
whenever the YAML changes — never hand-edit them).

### Why gherkinator

- **Schema validation.** `gherkinator validate` enforces required fields and
  allowed enum values (`type`, `status`, `risk`) before any `.feature` file is
  generated.
- **Syntax-correct output.** `gherkinator generate --format gh` runs the
  generated text through the official Cucumber Gherkin parser, so the
  emitted `.feature` files are always syntactically valid.
- **Structured metadata.** The `type`, `status`, and `risk` fields of each
  `TestPlan` become Gherkin tags (`@functional`, `@planned`, `@stable`) and
  support `--risk` / `--status` filtering for incremental migration.
- **Single source of truth.** One `test-plan.yaml` can contain many features
  separated by `---`. Each generates one `<feature>.feature` file.

### Install gherkinator

```bash
# Snap (recommended)
sudo snap install gherkinator --classic

# From source
git clone https://github.com/canonical/gherkinator.git
cd gherkinator && go build -o gherkinator .
```

### Commands used in this skill

| Command | Purpose |
|---|---|
| `gherkinator init <dir> --name <file>` | Create the YAML test plan directory and skeleton file. |
| `gherkinator edit <file>` | Open the YAML in `$EDITOR`/`$VISUAL` with a schema-hinted leading comment. Validates on save. |
| `gherkinator validate <file>` | Check the YAML against the schema (per document). |
| `gherkinator generate --format gh <file>` | Transpile to `.feature` files (default output dir: `.`). |
| `gherkinator generate --format md <file>` | Transpile to Markdown documentation. |
| `gherkinator delete -i <file> "<feature>"` | Remove a plan by feature name (case-insensitive). |
| `gherkinator clean -d <dir>` | Remove all generated `.feature`, `.md`, and `.gherkindocs/`. |

### YAML field mapping (TestPlan → BDD)

The `TestPlan` schema (full reference in [reference.md](reference.md)) maps
to Gherkin like this:

| YAML field | BDD meaning |
|---|---|
| `feature` | Feature name (`Feature: <feature>` line). |
| `type` | First Gherkin tag (`@functional`, `@reliability`, etc.). Always one of: `functional`, `solution`, `performance`, `reliability`, `security`. For most charm tests, use `functional`. Use `reliability` for HA/multi-unit and `performance` for benchmarks. |
| `status` | Second Gherkin tag (`@planned`, `@implemented`, `@deprecated`). Always one of: `planned`, `implemented`, `deprecated`. **Use `planned` for newly migrated tests.** Flip to `implemented` only after the feature file is generated and the BDD suite is green for that plan. |
| `risk` | Third Gherkin tag (`@edge`, `@beta`, `@candidate`, `@stable`). Always one of: `edge`, `beta`, `candidate`, `stable`. Use `stable` for core charm features, `candidate` for secondary features, `beta`/`edge` for less critical paths. |
| `description` | Free-form text rendered under `Feature:`. |
| `issues` | Issue tracker URL (documentation only; not emitted in `.feature`). |
| `docs` | Docs URL (documentation only; not emitted in `.feature`). |
| `background` | Multi-line string of Given/When/Then steps that run before every scenario in the feature. |
| `scenarios` | List of multi-line strings. First line of each entry = scenario title; subsequent lines = Given/When/Then steps. Use `<param>` tokens to reference example columns. |
| `examples` | List of lists. When present, the corresponding scenario becomes a `Scenario Outline:` with an `Examples:` table. Column headers are derived from `<param>` tokens in the scenario text. |

A scenario is rendered as `Scenario: <title>` when it has no `examples`
row, or as `Scenario Outline: <title>` with `Examples:` when it does.

## Migration workflow

1. **Inspect the target repo.** Locate `tests/integration/**/*.py`,
   `conftest.py`, `charmcraft.yaml`, `metadata.yaml`. Identify which tests
   use `jubilant` directly. Reference the pattern-mapping table in
   [reference.md](reference.md).

2. **Map each test to a scenario.** For every `def test_*(...)`:
   - Setup (deploys, models, config, integrations) → **Given** steps.
   - Actions (`juju.run`, `juju.exec`, config changes) → **When** steps.
   - Assertions (status, messages, command output, action results) →
     **Then** steps.
   - Note any test that does NOT map to a built-in step — that becomes a
     custom step.
   - Group tests into logical features (one `.feature` file per group:
     deployment, integration, operations, actions).

3. **Initialize gherkinator.** Run from the repo root:

   ```bash
   gherkinator init tests/integration/features --name test-plan
   ```

   This creates `tests/integration/features/test-plan.yaml` as an empty
   multi-document file. It is the single source of truth for every
   migration scenario in this repo.

4. **Create YAML test plans.** Author one `TestPlan` document per logical
   feature in `tests/integration/features/test-plan.yaml`. Open it with:

   ```bash
   gherkinator edit tests/integration/features/test-plan.yaml
   ```

   The editor opens with a leading comment that documents the schema. For
   each plan document:

   - `feature`: human-readable name (e.g. `"Slurmctld deployment"`).
   - `type`: `functional` for typical charm tests; `reliability` for HA /
     multi-unit; `performance` for benchmarks; `solution` for end-to-end
     user workflows.
   - `status`: `planned` for newly migrated tests.
   - `risk`: choose based on criticality (see field-mapping table above).
   - `description`: 1–3 sentences explaining what the feature covers.
   - `background`: shared Given steps (typically `Given I add model 'test'`).
   - `scenarios`: one entry per original test. First line is the scenario
     title; subsequent lines are Given/When/Then steps using the exact
     phrasing from the step reference table.

   See [examples.md](examples.md) for full YAML test plan examples.

5. **Validate and generate.** Run gherkinator to confirm the YAML is
   schema-compliant, then produce `.feature` files:

   ```bash
   gherkinator validate tests/integration/features/test-plan.yaml
   gherkinator generate --format gh tests/integration/features/test-plan.yaml \
     --output-dir tests/integration/features
   ```

   The generated files (`<feature>.feature`) live alongside the YAML.
   Fix any `validate` errors in the YAML and re-run; do not hand-edit
   `.feature` files — they will be overwritten on the next `generate`.

   Tip: during incremental migration, generate only a subset using
   `--status planned --risk edge` and commit plan-by-plan.

6. **Write custom step definitions** (only for domain logic with no
   built-in equivalent) in `tests/integration/test_<feature>.py`. Each
   module loads its scenarios with `scenarios("features/<name>.feature")`
   and defines any custom steps the framework doesn't already provide. Use
   the `context` fixture and `context.wait()` for polling. Templates are in
   [examples.md](examples.md).

7. **Configure the repo.** Add `pytest-jubilant-bdd` to the integration
   test dependencies. Do **not** redefine a `juju` fixture — the plugin
   provides `context`. Do **not** import step handlers. See
   [reference.md](reference.md) for `pyproject.toml` and `conftest.py`
   snippets.

8. **Run the BDD suite** and confirm scenarios pass:

   ```bash
   just integration
   ```

   Fix-and-rerun until green. After the suite is green for a given plan,
   flip the corresponding YAML `status` field from `planned` to
   `implemented` and re-run `gherkinator generate` so the regenerated
   `.feature` file carries the `@implemented` tag.

## Stop and report if

- `gherkinator validate` reports a schema error — fix the YAML field, not
  the `.feature` output.
- A built-in step's phrasing doesn't match the Gherkin you wrote — re-read
  the reference table; built-in patterns are fixed.
- You're tempted to edit production code in the *target* charm repo to
  make a test pass — pause and ask the user.
- The target repo's `jubilant` API differs materially from the patterns in
  [reference.md](reference.md) — confirm the jubilant version and adjust
  custom-step guidance accordingly.
- A test needs a step the framework genuinely doesn't provide — propose a
  custom step to the user rather than forcing a built-in to fit.

## Evaluation prompts

Use these to check skill routing and behavior.

**Positive (should trigger):**
- "Migrate the integration tests in `tests/integration/test_charm.py` to BDD
  with pytest-jubilant-bdd."
- "Convert this repo's jubilant tests to Gherkin feature files using
  gherkinator."
- "Use gherkinator to scaffold BDD feature files for this charm."

**Near-miss (should NOT trigger):**
- "Write a unit test for the `add_model` step handler in pytest-jubilant-bdd."
- "Explain how `Context.wait()` polls."

**Edge case:**
- "Migrate these tests, but preserve `@pytest.mark.order` across feature
  files and keep the action-result assertions."

## Supporting files

- [reference.md](reference.md) — gherkinator TestPlan schema, command
  reference, pattern-mapping table, `conftest.py`/`pyproject.toml`
  snippets, CLI options, ordering, verification checklist, troubleshooting.
- [examples.md](examples.md) — full before/after migrations showing the
  YAML → gherkinator → `.feature` pipeline and custom-step templates.

## Related resources

- gherkinator: https://github.com/canonical/gherkinator
- pytest-jubilant-bdd: https://github.com/canonical/pytest-jubilant-bdd
- jubilant: https://github.com/canonical/jubilant
- pytest-bdd: https://pytest-bdd.readthedocs.io/
- Gherkin reference: https://cucumber.io/docs/gherkin/reference/
