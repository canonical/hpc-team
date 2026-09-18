# Examples

Concrete before/after migrations and custom-step templates. See
`SKILL.md` for the step reference and `reference.md` for configuration
and schema.

## Full before/after pipeline

### Before (traditional pytest + jubilant)

```python
# tests/integration/test_charm.py
import pytest
import jubilant
import tenacity


@pytest.mark.order(3)
def test_deploy_and_check(juju):
    juju.deploy("slurmctld", "slurmctld", channel="latest/edge")
    juju.wait(lambda s: s.apps["slurmctld"].status == "active")

    result = juju.run("slurmctld/0", "get-password")

    for attempt in tenacity.Retrying(stop=tenacity.stop_after_attempt(5)):
        with attempt:
            assert result.return_code == 0
            assert result.status == "completed"
```

### After (gherkinator-controlled BDD)

**1. Initialize the test plan:**

```bash
gherkinator init tests/integration/features --name test-plan
```

**2. Author the YAML** in `tests/integration/features/test-plan.yaml`.
   Write the YAML directly — do not use `gherkinator edit` (it is an
   interactive editor for humans, not agents). Then validate in a loop
   until clean:

   ```bash
   gherkinator validate tests/integration/features/test-plan.yaml
   # iterate on the YAML until: "All N test plan(s) are valid."
   ```

```yaml
feature: "Slurmctld deployment"
type: functional
status: planned
risk: stable
description: "End-to-end deployment check for slurmctld."
background: |-
  Given I add model 'test'
scenarios:
  - |-
    Deploy slurmctld and run get-password
    Given I deploy 'slurmctld' from channel 'latest/edge'
    When I run action 'get-password' on unit 'slurmctld/0'
    Then the workload status for app 'slurmctld' is 'active'
```

**3. Validate the schema:**

```bash
gherkinator validate tests/integration/features/test-plan.yaml
```

Expected output:

```
All 1 test plan(s) are valid.
```

**4. Generate the `.feature` file:**

```bash
gherkinator generate --format gh tests/integration/features/test-plan.yaml \
  --output-dir tests/integration/features
```

Generated `slurmctld_deployment.feature`:

```gherkin
@functional @planned @stable
Feature: Slurmctld deployment

  End-to-end deployment check for slurmctld.

  Background:
    Given I add model 'test'

  Scenario: Deploy slurmctld and run get-password
    Given I deploy 'slurmctld' from channel 'latest/edge'
    When I run action 'get-password' on unit 'slurmctld/0'
    Then the workload status for app 'slurmctld' is 'active'
```

**5. Load the scenarios** in `tests/integration/test_deployment.py`:

```python
"""BDD step definitions for slurmctld deployment."""
from pytest_bdd import scenarios

scenarios("features/slurmctld_deployment.feature")

# No custom steps needed — every step above is provided by
# pytest-jubilant-bdd. Action results are available on the `context`
# fixture (context.action_results) if a later scenario needs to inspect
# them.
```

**6. Run the suite:**

```bash
pytest tests/integration/ -v
```

**7. Flip `status` to `implemented` once green** — edit the YAML,
change `status: planned` to `status: implemented`, then re-run
`gherkinator generate` so the regenerated `.feature` carries the
`@implemented` tag.

## Local-charm deploy example

The YAML input:

```yaml
feature: "Local charm deployment"
type: functional
status: planned
risk: stable
description: "Deploy a locally built charm and configure it."
background: |-
  Given I add model 'test'
scenarios:
  - |-
    Deploy a locally built charm with config
    Given I deploy 'slurmctld' from a local charm located at '/tmp/slurmctld.charm' with '3' units
    Given I set 'debug' for app 'slurmctld' to 'true'
    Then the workload status for app 'slurmctld' is 'active'
```

Generated `.feature`:

```gherkin
@functional @planned @stable
Feature: Local charm deployment

  Deploy a locally built charm and configure it.

  Background:
    Given I add model 'test'

  Scenario: Deploy a locally built charm with config
    Given I deploy 'slurmctld' from a local charm located at '/tmp/slurmctld.charm' with '3' units
    Given I set 'debug' for app 'slurmctld' to 'true'
    Then the workload status for app 'slurmctld' is 'active'
```

Without `located at '...'`, the `deploy_local` step reads the
`SLURMCTLD_CHARM_PATH` environment variable (see `reference.md`).

## Multi-model integration example

The YAML input:

```yaml
feature: "Cross-model integration"
type: reliability
status: planned
risk: candidate
description: "Integrate slurmctld and slurmd across two models."
scenarios:
  - |-
    Integrate slurmctld and slurmd across models
    Given I add model 'controller'
    Given I add model 'compute'
    Given I deploy 'slurmctld' in model 'controller'
    Given I deploy 'slurmd' in model 'compute'
    Given I integrate 'slurmctld' with 'slurmd'
    Then all agents are 'idle' in models 'controller', 'compute'
```

Note this plan uses `type: reliability` (multi-unit / multi-model
integration test) instead of `functional`. Pick the type that matches the
nature of the test.

## Parametrised scenario (Scenario Outline) example

The YAML input — when `examples` is present and the scenario steps
reference `<param>` tokens, gherkinator emits a `Scenario Outline:`:

```yaml
feature: "Multi-user access"
type: functional
status: planned
risk: beta
description: "Same access flow exercised for several users."
background: |-
  Given I add model 'test'
scenarios:
  - |-
    Grant access by role
    Given I deploy 'access-manager' from channel 'latest/edge'
    When I run action 'grant' on unit 'access-manager/0' with parameters 'username=<username> role=<role>'
    Then the workload status for app 'access-manager' is 'active'
examples:
  - - alice
    - admin
  - - bob
    - viewer
```

Generated `.feature`:

```gherkin
@functional @planned @beta
Feature: Multi-user access

  Same access flow exercised for several users.

  Background:
    Given I add model 'test'

  Scenario Outline: Grant access by role
    Given I deploy 'access-manager' from channel 'latest/edge'
    When I run action 'grant' on unit 'access-manager/0' with parameters 'username=<username> role=<role>'
    Then the workload status for app 'access-manager' is 'active'

    Examples:
      | username | role |
      | alice | admin |
      | bob | viewer |
```

## Multi-document YAML (one file, many features)

A single `test-plan.yaml` can hold many features separated by `---`. Each
document becomes one `.feature` file on generation:

```yaml
feature: "Slurmctld deployment"
type: functional
status: planned
risk: stable
background: |-
  Given I add model 'test'
scenarios:
  - |-
    Deploy slurmctld
    Given I deploy 'slurmctld' from channel 'latest/edge'
    Then the workload status for app 'slurmctld' is 'active'
---
feature: "Slurmd deployment"
type: functional
status: planned
risk: stable
background: |-
  Given I add model 'test'
scenarios:
  - |-
    Deploy slurmd
    Given I deploy 'slurmd' from channel 'latest/edge'
    Then the workload status for app 'slurmd' is 'active'
---
feature: "Cross-model integration"
type: reliability
status: planned
risk: candidate
scenarios:
  - |-
    Integrate slurmctld and slurmd
    Given I add model 'controller'
    Given I add model 'compute'
    Given I deploy 'slurmctld' in model 'controller'
    Given I deploy 'slurmd' in model 'compute'
    Given I integrate 'slurmctld' with 'slurmd'
    Then all agents are 'idle' in models 'controller', 'compute'
```

Running:

```bash
gherkinator validate tests/integration/features/test-plan.yaml
gherkinator generate --format gh tests/integration/features/test-plan.yaml \
  --output-dir tests/integration/features
```

produces three `.feature` files in one shot:
`slurmctld_deployment.feature`, `slurmd_deployment.feature`,
`cross_model_integration.feature`. Each `test_*.py` module loads its own.

## Incremental migration with `--risk` / `--status`

During a multi-day migration, generate only the plans you intend to ship.
`--risk` is cumulative (selects the given level **and** higher), `--status`
is exact-match. See [reference.md](reference.md) for the filtering table.

```bash
# Only the highest-criticality (edge) plans that are newly migrated.
gherkinator generate --format gh tests/integration/features/test-plan.yaml \
  --output-dir tests/integration/features \
  --status planned --risk edge

# Bump to candidate once edge-risk plans are green; adds beta + edge.
gherkinator generate --format gh tests/integration/features/test-plan.yaml \
  --output-dir tests/integration/features \
  --status planned --risk candidate
```

After all `status: planned` plans in a risk band are green, edit each
YAML document's `status: planned` → `status: implemented` and re-run
without filters to regenerate the full set.

## Removing a plan you no longer want

If a plan turns out to be the wrong granularity, drop it via
`gherkinator delete`:

```bash
# Interactive confirmation
gherkinator delete -i tests/integration/features/test-plan.yaml \
  "Slurmctld deployment"

# Non-interactive
gherkinator delete -y -i tests/integration/features/test-plan.yaml \
  "Slurmctld deployment"
```

Then regenerate to drop the matching `.feature` file:

```bash
gherkinator generate --format gh tests/integration/features/test-plan.yaml \
  --output-dir tests/integration/features
```

If the directory is cluttered with stale `.feature` files from old plans,
nuke and regenerate:

```bash
gherkinator clean -d tests/integration/features
gherkinator generate --format gh tests/integration/features/test-plan.yaml \
  --output-dir tests/integration/features
```

## Custom step templates

> This section covers **charm-repo ad-hoc custom steps** — step
> definitions written in your own `conftest.py` or `test_*.py` to
> extend the built-in handlers. If you are adding a new built-in
> step handler to the `pytest-jubilant-bdd` plugin itself
> (modifying `src/pytest_jubilant_bdd/_main.py`), see the
> **`reusable-step-handler`** skill in the pytest-jubilant-bdd repo
> (`.agents/skills/reusable-step-handler/SKILL.md`) instead — it
> covers parser selection (`parse` vs `flexible` vs `re`), `%…%`
> block syntax, private-helper patterns, error class conventions,
> and unit-test wiring.

Custom steps take the `context` fixture and use `context.wait()` for
polling. For the exact `Context` API, defer to the
**`reusable-step-handler`** skill
(`.agents/skills/reusable-step-handler/SKILL.md`); the
`Exception`-catching and `conftest.py` placement rules are in `SKILL.md`
DOs.

### Inspecting action / exec results

```python
"""Custom steps for action-result assertions."""
from pytest_bdd import then, parsers

from pytest_jubilant_bdd import Context


@then(parsers.parse("the action should succeed"))
def assert_action_succeeded(context: Context) -> None:
    """Assert the most recent action completed with return code 0."""
    task = context.action_results.peek()
    assert task.status == "completed"
    assert task.return_code == 0
```

### Custom status / command check with polling

`context.wait()` polls `ready` until it returns `True` three times in a
row, then returns; it raises `TimeoutError` on timeout. See SKILL.md DOs
for why `ready` must catch `Exception`.

```python
from pytest_bdd import then, parsers
from pytest_jubilant_bdd import Context


@then(parsers.parse("the unit '{unit}' workload message contains '{substring}'"))
def assert_message_contains(context: Context, unit: str, substring: str) -> None:
    """Wait until the unit's workload status message contains substring."""
    context.wait(
        ready=lambda ctx: substring in ctx.get_unit(unit).workload_status.message,
    )
```

For `juju.exec`-based polling (where the command may fail transiently),
wrap the call in a try/except:

```python
@then(parsers.parse("a slurm gpu job submitted from unit '{login_unit}' runs on unit '{compute_unit}'"))
def gpu_job_submission(context: Context, login_unit: str, compute_unit: str) -> None:
    """Submit a GPU-requesting job and verify it runs on the compute node."""
    juju = context.get_juju()
    slurmd_result = juju.exec("hostname -s", unit=compute_unit)

    def ready(_ctx: Context) -> bool:
        try:
            sackd_result = juju.exec(
                f"srun --partition compute --gres gpu:1 hostname -s",
                unit=login_unit,
            )
            assert sackd_result.stdout == slurmd_result.stdout
            return True
        except Exception:
            return False

    context.wait(ready=ready)
```

### Shared state within a scenario

Use a function-scoped `scenario_state` fixture when a legacy test captures
state before an action and asserts it changed after — e.g., capture an
initial key in a `Given` step, run a rotation action in a `When` step,
then assert the key changed in a `Then` step. This fixture must live in
`conftest.py`. Use `And` to chain multiple `Given` captures in the YAML
before the `When` step.

```python
import pytest
from pytest_bdd import when, then, parsers
from pytest_jubilant_bdd import Context


@pytest.fixture
def scenario_state() -> dict:
    """State shared between steps in one scenario."""
    return {}


@when(parsers.parse("I capture the output of '{command}' on unit '{unit}'"))
def capture_output(
    context: Context, scenario_state: dict, command: str, unit: str
) -> None:
    result = context.get_juju().exec(command, unit=unit)
    scenario_state["stdout"] = result.stdout


@then(parsers.parse("the captured output should be '{expected}'"))
def assert_captured(scenario_state: dict, expected: str) -> None:
    assert scenario_state["stdout"] == expected
```

### Snapshotting a role→unit mapping before a failover

Use `scenario_state` to snapshot a **role→unit mapping** (primary/replica,
leader/follower) *before* an action that shifts which unit holds the role.
Without the snapshot, a `When` step that re-queries mid-failover may target
the *new* primary and act on the wrong unit.

The example below is generic (no Slurm specifics) and also demonstrates
dual `@given`/`@then` registration.

> **Rule of thumb.** Stack `@given` and `@then` on handlers that only
> *check* state. Never stack `@when` — it's for actions under test.

#### `conftest.py`

```python
import pytest
from pytest_bdd import given, when, then, parsers
from pytest_jubilant_bdd import Context


@pytest.fixture
def scenario_state() -> dict:
    """Per-scenario mutable state shared between Given/When/Then steps."""
    return {}


def _query_roles(context: Context) -> dict:
    """Query live role→unit assignments from the service."""
    juju = context.get_juju()
    out = juju.exec("acmectl ping -j", unit="acme/0").stdout
    import json
    return json.loads(out)


def _roles(context: Context, scenario_state: dict) -> dict:
    """Return the recorded snapshot if present, else query fresh."""
    if "roles" in scenario_state:
        return scenario_state["roles"]
    return _query_roles(context)


@given("I record the current role assignments")
def record_roles(context: Context, scenario_state: dict) -> None:
    """Snapshot the current role→unit mapping for stable references."""
    scenario_state["roles"] = _query_roles(context)


# Stacked @given + @then: same handler, two keywords.
@given(parsers.parse("the acme service that is {role} reports status '{status}'"))
@then(parsers.parse("the acme service that is {role} reports status '{status}'"))
def role_status(context: Context, scenario_state: dict, role: str, status: str) -> None:
    """Assert the service in the given role reports the given status."""
    def ready(_ctx: Context) -> bool:
        try:
            current = _query_roles(context)
            assert role in current, f"role '{role}' not found"
            assert current[role]["status"] == status
            return True
        except Exception:
            return False

    context.wait(ready=ready)


@when("I stop the acme service on the unit that is primary")
def stop_primary(context: Context, scenario_state: dict) -> None:
    """Stop the acme service on the recorded primary unit."""
    juju = context.get_juju()
    roles = _roles(context, scenario_state)   # ← snapshot, not fresh query
    juju.exec("sudo systemctl stop acme", unit=roles["primary"]["unit"])
```

#### YAML test plan

```yaml
feature: "Acme high availability"
type: reliability
status: planned
risk: stable
description: "Failover and recovery for the acme primary/replica service."
background: |-
  Given I add model 'test'
  Given I switch to model 'test'
scenarios:
  - |-
    Service failover to replica
    Given I record the current role assignments
    And the acme service that is primary reports status 'UP'
    And the acme service that is replica reports status 'UP'
    When I stop the acme service on the unit that is primary
    Then the acme service that is replica reports status 'UP'
    And the acme service on the unit that is replica is running as primary
  - |-
    Service recovery after restarting primary
    Given I record the current role assignments
    And the acme service that is primary reports status 'DOWN'
    And the acme service that is replica reports status 'UP'
    When I restart the acme service on the unit that is primary
    Then the acme service that is primary reports status 'UP'
    And the acme service on the unit that is primary is running as primary
    And the acme service on the unit that is replica is running in background mode
```

### Custom step shared across feature files

If a custom step is used by scenarios in multiple `.feature` files, define
it in `conftest.py`:

```python
# conftest.py
from pytest_bdd import parsers, when
from pytest_jubilant_bdd import Context


@when(parsers.parse("I reset the node configuration on unit '{unit}'"))
def reset_node_config(context: Context, unit: str) -> None:
    """Custom step available to ALL test_*_bdd.py modules."""
    juju = context.get_juju()
    juju.run(unit, "set-node-config", params={"reset": True})
```

### Binary availability after `active` status

A charm reaching `active` status means its reconciliation loop has
completed, but binaries it installs may not be immediately available on
the unit's `PATH`. When migrating tests that had `sleep(N)` after
`juju.wait()`, replace the fixed sleep with a `context.wait()` polling
loop that checks for the binary.

#### Before (traditional pytest + jubilant — from `slurm-charms` `test_oci_runtime.py`)

```python
def setup_apptainer(juju: jubilant.Juju) -> None:
    """Deploy and integrate `apptainer` with `slurmctld` and `slurmd`.

    Notes:
        - Sleep for five seconds after the `apptainer` app reaches active
          status to give the cluster enough time to reconfigure.
    """
    juju.deploy(APPTAINER_APP_NAME, channel="latest/edge")
    juju.integrate(APPTAINER_APP_NAME, SLURMCTLD_APP_NAME)
    juju.integrate(APPTAINER_APP_NAME, SLURMD_APP_NAME)
    juju.wait(lambda status: jubilant.all_active(status, APPTAINER_APP_NAME))
    sleep(5)  # <-- apptainer binary may not be on PATH yet


@pytest.mark.order(13)
def test_apptainer_oci_scheduling(juju: jubilant.Juju) -> None:
    """Test that Slurm can schedule jobs using Apptainer."""
    if APPTAINER_APP_NAME not in juju.status().apps:
        setup_apptainer(juju)

    sackd_unit = f"{SACKD_APP_NAME}/0"
    slurmd_unit = f"{SLURMD_APP_NAME}/0"

    juju.exec(
        "apptainer pull /tmp/jammy.sif docker://ghcr.io/charmed-hpc/ubuntu-test:jammy",
        unit=slurmd_unit,
    )
    result = juju.exec(
        f"cd /tmp; srun -p {SLURMD_APP_NAME} --container=/tmp/jammy.sif cat /etc/os-release",
        unit=sackd_unit,
    ).stdout.strip()
    # ... assertions on result
```

#### After (gherkinator-controlled BDD)

The deploy, integrate, and status-wait all map to built-in steps — no
custom deploy handler. The `sleep(5)` becomes a `context.wait()` poll
inside the custom `Then` step:

```yaml
scenarios:
  - |-
    Apptainer OCI scheduling
    Given I deploy 'apptainer' from channel 'latest/edge'
    And I integrate 'apptainer' with 'slurmctld'
    And I integrate 'apptainer' with 'slurmd'
    Then the workload status for app 'apptainer' is 'active'
    Then an apptainer container job submitted from unit 'sackd/0' runs on unit 'slurmd/0'
```

```python
@then(parsers.parse("an apptainer container job submitted from unit '{login_unit}' runs on unit '{compute_unit}'"))
def apptainer_oci_scheduling(context: Context, login_unit: str, compute_unit: str) -> None:
    """Pull an OCI image and run a Slurm job inside an Apptainer container."""
    juju = context.get_juju()

    # Replace sleep(5) — poll until the apptainer binary is on PATH.
    def apptainer_ready(_ctx: Context) -> bool:
        try:
            juju.exec("apptainer --version", unit=compute_unit)
            return True
        except Exception:
            return False

    context.wait(ready=apptainer_ready)

    juju.exec(
        "apptainer pull /tmp/jammy.sif docker://ghcr.io/charmed-hpc/ubuntu-test:jammy",
        unit=compute_unit,
    )
    # ... rest of the test
```

## Migrating action-on-one-unit / state-on-another tests

Some charm actions run on one unit but modify state belonging to a
different unit. In Slurm, `set-node-state` runs on `slurmctld/0` but
changes the state of a node registered to `slurmd/0` / `compute/0`.
The legacy test uses two distinct variables; the YAML test plan has a
single `unit` field per step, so each step must reference the correct
unit.

### Before (traditional pytest + jubilant)

```python
slurmctld_unit = f"{SLURMCTLD_APP_NAME}/0"   # action executor
slurmd_unit = f"{SLURMD_APP_NAME}/0"          # node owner
name = slurmd_unit.replace("/", "-")           # → "compute-0"

juju.run(slurmctld_unit, "set-node-state",
         params={"nodes": name, "state": "down", "reason": "maintenance"})
result = juju.exec(f"scontrol --json show node {name}", unit=slurmctld_unit)
```

### After — correct YAML (action unit ≠ verification unit)

```yaml
scenarios:
  - |-
    Set node state action updates node state and reason
    When I run action 'set-node-state' on unit 'controller/0' with parameters 'nodes=compute-0 state=down reason=maintenance'
    Then the node for unit 'compute/0' has state containing 'DOWN' and reason "'maintenance'"
```

`When` uses `controller/0` (action executor); `Then` uses `compute/0`
(node owner) so `node_name("compute/0")` → `compute-0` matches the
node the action modified.

### Common pitfall — same unit in both steps

```yaml
# WRONG — will silently time out
When I run action 'set-node-state' on unit 'controller/0' with parameters 'nodes=compute-0 state=down reason=maintenance'
Then the node for unit 'controller/0' has state containing 'DOWN' and reason "'maintenance'"
```

`node_name("controller/0")` → `controller-0`, which is not a registered
compute node. `context.wait()` catches the exception and retries silently
until the 3-minute timeout, making it appear "stuck" rather than failing
with a clear assertion error.
