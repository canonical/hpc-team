---
name: write-charm-unit-tests
description: Write regression-focused unit tests for Juju charms (ops / ops.testing) that pin real failure modes instead of chasing coverage, with mutation-based verification of test rigor. Use when asked to improve a charm's unit test coverage, add meaningful unit tests, or audit whether existing tests would catch regressions.
---

# Write meaningful charm unit tests

## Core principle

Coverage is a side effect, not the goal. Every test must pin a behavior whose breakage
would hurt in production; a test that cannot fail when the code breaks is worse than no
test — false confidence plus a higher coverage number.

The workflow has five phases. Do not skip Phase 4 (mutation verification); it is what
separates this skill from ordinary coverage work. "Auditing tests written with this
skill", near the end, reuses the same judgment for review.

`reference.md` holds the lookups: how to run the suite and get a coverage report, the
mutation harness constraints, and an `ops.testing` quick reference. Read it when you
need a specific invocation or API detail; the rules below are the part to internalize.

## Phase 1: Map coverage gaps to behavior, not line counts

1. Run the suite under branch coverage and get the missing-lines report — in
   charmed-hpc repos, `just unit <charm>` then
   `uv run coverage report --show-missing --skip-covered` (see `reference.md` for the
   full invocation and troubleshooting). Record the baseline pass/fail and warning
   counts too; Phase 5 needs them to separate your noise from pre-existing noise.
2. Read the source at every uncovered range and classify each gap: unexecuted handler
   bodies; error/edge branches; status-evaluation branches (the operator-facing
   surface); log-only lines, `pragma: nocover`, and trivial guards (skip these).
3. Rank by consequence of breakage, highest first: irreversible failure modes (source
   comments saying "corrupts the deployment" or "unrecoverable", or past-incident
   error text, are the triage signal), then operational flows (secret rotation,
   reconfiguration), parsing/branching logic, status surface. Never test log lines or
   cosmetic branches.
4. Check how other charmed-hpc repos (e.g. `filesystem-charms`, `sssd-operator`) test
   the same kind of handler — if they cover it and this charm does not, the gap likely
   matters.
5. Read the integration suite before writing anything, and do not duplicate it.
   Integration owns end-to-end outcomes on a real model; unit owns what integration
   cannot reach: pure logic and validators, failure injection (library error →
   `BlockedStatus` + defer), file-content bookkeeping, intermediate statuses, and
   destructive scenarios a real deployment must never be subjected to. Where both
   layers could test a behavior, integration wins.

## Phase 2: Study the suite's conventions before writing anything

- Read `conftest.py` and 2–3 existing tests. Match their fixtures, parametrization,
  naming, module-level `EXAMPLE_*` constants, and assertion style; new tests must be
  indistinguishable from existing ones.
- **Take the house style from code nobody just touched.** Untouched modules are the
  control group; a recently edited file may itself be the drift. When the target suite
  has no precedent, read other charmed-hpc repos (e.g. `filesystem-charms`,
  `sssd-operator`) for how they trigger the same events (e.g. `testing.Secret` +
  `ctx.on.secret_changed`, `relation_changed` with `remote_app_data`).
- **Reuse the "make the unit healthy" helper instead of open-coding it.** Every charm
  needs one way to patch its service manager to installed/active/ready. If it exists,
  call it; if you find the same two or three `mocker.patch.object` calls repeated
  across tests, hoist them into `conftest.py` as a plain function taking
  `(manager, mocker)`. This is the highest-value cleanup available in a charm suite.
- Before adding a shared fixture or helper to `conftest.py`, grep the test modules for
  an identical local fixture — keep exactly one definition, since duplicates drift.
  Fixture names, `scope=`/`ids=`, and centralized boundary patches (`shutil.chown`,
  `subprocess.run`) should match what sibling test modules already use. Check
  docstrings too: copy-pasted conftests routinely name the wrong charm.
- **Prefer the public API over vendored internals.** Use `testing.Manager` and
  `testing.errors.UncaughtCharmError`, not `from scenario import Manager` or
  `from scenario.errors import ...` — those reach into `ops.testing`'s bundled
  implementation. They pass review easily because they work, so grep for them.
- **One spelling per concept.** `side_effect=exc` over generator-throw tricks;
  `ops.ActiveStatus` over `testing.ActiveStatus` (both compare equal, so nothing fails
  — grep, don't rely on the suite). Name handler tests after the handler
  (`test_on_install`, not `test_install`).
- Add tests to the existing test module unless the repo's organization clearly directs
  otherwise (e.g. a separate `test_ha.py`, or `test_config.py` for pure
  validator/config-model tests when other charmed-hpc repos do that). New test files
  and new test classes are convention changes, not defaults: put a test in the topical
  class that already exists rather than adding a single-test class beside it.
- Harness-driven handler tests are unit tests in charm repos — `ops.testing` exists
  for exactly this, and the existing suite runs them under the unit target.

## Phase 3: Write tests that drive real events

These rules come from real review findings; violating them produces tests that pass
while the code is broken.

1. **Drive behavior through the harness, never by calling private handlers with fake
   events.** Use `manager.run()` with real events. Direct invocation like
   `manager.charm._on_something(Mock(...))` bypasses event dispatch and passes even if
   the charm stopped observing the event. If a library event seems impossible to
   trigger, read the library source first — it usually fires from relation data you
   control.
2. **Never mock the thing under test.** Mock only external boundaries (systemd, apt,
   `subprocess`) and unrelated collaborators.
3. **Assertions against Mocks you constructed yourself are dead weight.**
   `event.defer.assert_not_called()` on a Mock you built proves nothing. Spy on the
   real method instead (e.g. `mocker.patch.object(ops.EventBase, "defer")`).
4. **Assert on durable outcomes:** file contents, databag contents, service-call
   semantics (`restart` vs `reload`), final unit status — not internal call counts
   alone.
5. **Pin deliberate design decisions that look like bugs.** Example: a handler that
   intentionally does not defer on unusable input (deferral would retry broken data
   forever). Someone will "fix" it; the test is the only thing stopping them.
6. **Parametrize input variants** — IPv6 vs IPv4, empty vs garbage, single vs multiple
   values, container vs physical deployment. This is where silent production breakage
   lives.
7. **Test convergence, not just single-shot behavior.** Fire the same event twice and
   assert the end state is singular — no duplicated config lines or databag entries.
   `relation-changed` fires often in production; handlers that append instead of
   converge corrupt config over time.
8. **Test re-run idempotency for hooks that re-execute.** The `start` hook runs again
   after a reboot: pre-create the handler's output files and assert they survive
   untouched while expected side effects still happen.
9. **Pair absence assertions with a positive one.** "Non-leader does not write the
   config file" passes vacuously if a gate blocked the handler entirely; also assert
   something the handler must do to prove execution reached the body.
10. **Name the failure mode in the docstring.** State the production breakage the test
    guards against. A test whose author cannot name its failure mode is coverage
    padding; delete it.
11. **Use domain-realistic test data.** Values that would be invalid in production
    confuse reviewers and can mask validation gaps. Derive realistic values from the
    source — e.g. a managed service is typically named after the Juju application.
12. **Verify dependency behavior empirically before asserting it.** Parse formats,
    valid field names, and dedup semantics live in the charm's dependencies — run a
    throwaway probe against the real library first. Probes sometimes reveal the charm
    silently relies on a library guarantee.
13. **Construct lifecycle states by running the lifecycle, not by fabricating the end
    state.** The harness enforces real Juju invariants (e.g. `secret-remove` is
    rejected for the tracked or latest revision); fabricated end states are rejected
    outright or test a state Juju cannot produce.
14. **When one repo fixes a bug, check the other charmed-hpc repos for the same
    shape.** Grep for the call pattern, not the fix: e.g. if a repo widened its
    `except` around `service.restart()` to also catch the underlying daemon error,
    grep other repos for direct `service.{restart,reload,stop,disable,enable}()` calls
    and check what each catches. Charmed-hpc charms share conventions and libraries,
    so a bug in one is often latent in the others.
15. **Establish exception hierarchies from source, never from the name.** The decisive
    evidence is a wrapping site (`except LowLevelError: raise CharmLibError(...) from
    e`), which proves the types are distinct and explains why handlers that go through
    the wrapping helper get away with catching only the wrapper — a handler calling
    the raw method directly bypasses that protection. State the hierarchy in the test
    docstring.
16. **Check what lies outside the `try` block.** Handlers often guard parsing and
    file-writing but leave the service restart unguarded on the last line — the new
    state is already on disk, so a failure there leaves the unit in Juju `error` with
    no defer and no retry. Read handlers to the final line.
17. **Give equivalent behaviors an equivalent shape.** If the status surface is tested
    elsewhere as one `test_update_status` parametrized over
    `(installed, joined, active, expected)`, do not hand-roll one test per status.
    Matching shapes let reviewers diff behavior instead of structure.
18. **When adding a test to a parametrized class, honor its parameters.** Dropping a
    test into a `leader`-parametrized class without adding the `leader` parameter and
    branching its assertions silently stops covering the non-leader path.

## Phase 4: Mutation-verify every test (the scrutiny step)

Coverage says the line executed; mutation testing says the test would catch the line
being wrong. For each behavior under test:

1. Apply one small, plausible mutation — a bug a real contributor might write: flip a
   branch condition; swap `restart()` → `reload()`; delete a cleanup call; add an
   `event.defer()` to an error branch; swap two similar collaborators; disable a
   string transform; drop one write in a multi-write handler; narrow an `except` tuple
   to one member.
2. Run the full suite. The mutation must be **killed** — at least one test fails.
3. A surviving mutation usually means the test is decorative: fix it or delete it; do
   not rationalize keeping it. The one exception is a provably unreachable branch —
   there the source is redundant defense-in-depth; verify reachability, report the
   survivor as such, and leave the test alone.
4. Restore pristine source after each mutation; verify with `git status` that the
   working tree contains only intended changes.
5. If the repo stages charms into a build directory, mutate the staged copy and keep a
   pristine backup; never leave mutations in the source tree.

Hand-picked mutations (8–10 per session) suffice; `mutmut`-style tools are not
required. Run them through the atomic harness in `scripts/mutate.py` — see
`reference.md` for why its apply/run/restore, junit-XML, and re-sync constraints are
load-bearing.

## Phase 5: Report honestly

- Report coverage before/after as a consequence of the tests, not the objective.
- List remaining uncovered lines and why they are intentionally uncovered; do not
  write tests to close them.
- Flag the weakest tests you added so the user can trim them.
- State the conceptual limit: mutation testing proves tests detect *change*, not that
  current behavior is *correct* — the tests lock in existing behavior as the spec.
- Surface real bugs found while testing. Do not work around a suspected bug in the
  test, enshrine it as the spec, or fix the source unasked — report what the test
  revealed and let the user decide. If they want the suite green first, mark the test
  `xfail(strict=True, reason=<defect>)`; it becomes the regression guard when the bug
  is fixed.
- Run the repo's linter and formatter over every touched file, then re-run the suite.
  Reflowed lines can reorganize more than expected, so never report green from a
  pre-format run.
- **Never report a change as verified when it was not.** If tooling dies mid-session,
  say exactly which changes ran green and which are inspection-only, and name the
  command the user should run — per change, not per session.
- **Separate pre-existing noise from yours.** Compare warnings and failures against
  the Phase 1 baseline; unchanged warning counts come from vendored libraries and are
  out of scope — say so.

## Auditing tests written with this skill

When reviewing coverage-focused test additions (yours or another agent's):

1. Read the source each test covers; confirm the documented failure mode is real and
   its breakage would hurt in production.
2. Confirm fixtures satisfy the handler's condition gates (`wait_unless` /
   `block_unless` decorators, leader state, required secrets, mounts, key files) —
   absence assertions are vacuous if a gate blocked execution.
3. Coverage-padding tells: assertions on self-built mocks, tests of library or
   framework behavior, docstrings that cannot name a failure mode, fixtures
   duplicating existing ones.
4. Flag the weakest tests so the user can judge whether they earn their place.
