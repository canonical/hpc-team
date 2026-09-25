# Reference: running charm unit suites, coverage, and `ops.testing`

Companion to `SKILL.md`. Look things up here; the workflow and the rules live in
`SKILL.md`.

## Running the suite and getting a missing-lines report

In charmed-hpc repos the entry point is `just unit <charm>`, which delegates to
`scripts/repository.py unit <charm>`. That stages the charm into `_build/<charm>/` and
runs the suite under `coverage`, then combines per-charm data into a root `.coverage`.

- Branch measurement requires `branch = true` under `[tool.coverage.run]` in the
  charm's (or root) `pyproject.toml`.
- Missing-lines table, from the repo root:
  `uv run coverage report --show-missing --skip-covered`. Add
  `--include='_build/<charm>/src/*'` if the staged charm sources do not appear.
- `just unit` with no argument runs every charm; pass the charm name to iterate
  quickly on one.

### Running pytest directly

The staged build dir is the import root, so this reproduces what `just unit <charm>`
does:

```
PYTHONPATH=_build/<charm>/src:_build/<charm>/lib \
  <venv>/bin/python -m pytest _build/<charm>/tests/unit
```

Useful when `uv` cannot write its cache (read-only `~/.cache/uv` in a sandbox) — `uv
run` fails before pytest starts, but the existing `.venv` works. Add
`-p no:cacheprovider` on a read-only tree.

### Troubleshooting

- **Broken `pyproject.toml`** (e.g. unresolved merge conflict markers) breaks
  pytest/coverage config discovery: run with `-c <charm pyproject.toml>` and set
  `COVERAGE_RCFILE`. Unparseable TOML also takes down `ruff` and `uv` repo-wide while
  the tests still run, so check for it first:
  `grep -rn '<<<<<<<\|>>>>>>>' --include=*.toml --include=*.lock --include=*.py`.
- **Stale staged copy.** A checkout with no `.venv` can borrow another checkout's
  interpreter only if the charm `src/` trees match — diff them first. Signature skew
  surfaces as a confusing `TypeError` inside the harness (e.g. `__init__() got an
  unexpected keyword argument`), meaning the staged copy is stale, not that the test is
  wrong. Delete stray files copied into another repo's gitignored `_build/`.

## Mutation harness (Phase 4)

Copy `scripts/mutate.py` from this skill, adapt its CONFIG block, and define each
mutation as `(file, exact old text, replacement)`. Three constraints are load-bearing,
each learned from a real failure:

- **Apply, run, and restore in one process.** A mutation left applied across tool
  invocations can silently vanish, producing a false SURVIVED that condemns a sound
  test. Assert the file is pristine before each mutation and verify the restore after.
- **Collect verdicts from junit XML, not the terminal** (`--tb=no -rN -p no:warnings
  --junitxml=<path>`). pytest's failure rendering can itself crash (pytest 9 +
  pyfakefs: `bestrelpath` `ValueError` on identical paths), and a crashed run reports
  nothing.
- **Re-sync the staging before the first mutation.** A stale staged copy tests old
  code. Refresh staged `src/` and `tests/` from the real source (keeping fetched
  `lib/`) and confirm the pristine copy passes before mutating.

Helpers copied into the target repo are throwaway — delete them when done.

## `ops.testing` quick reference (ops 3.x / scenario)

### State components

- **Secrets:** `testing.Secret(label=..., tracked_content={...})`, included in
  `testing.State(secrets={...})`.
- **Relations:** `testing.Relation(endpoint=..., interface=..., remote_app_name=...,
  remote_app_data={...})`, triggered with `ctx.on.relation_changed(relation)`. Custom
  interface databag values are often `json.dumps`-encoded; check the interface's
  serializer before writing databag fixtures.
- **Peer relations:** `testing.PeerRelation(endpoint=..., interface=...,
  local_app_data={...})`; read back via `state.get_relation(rel.id).local_app_data`.
  Peer `relation_changed` requires `remote_unit=N` (the consistency checker rejects it
  otherwise); add the peer unit to `peers_data` and set `planned_units` explicitly
  (default 1) when a gate counts observed units.

### Filesystem

- pyfakefs `fs` fixture; pre-create `/etc/...` files in conftest; patch `shutil.chown`
  and `subprocess.run` (the charm's service user does not exist on test hosts).
- `fs.add_mount_point(path)` satisfies `Path.is_mount()` gates.
- Repeated events: reuse one input `State` across multiple `ctx(event, state)` runs.
  pyfakefs persists within a test; databag writes do not — thread the output state
  forward if later runs depend on them.

### Outcomes and failures

- Uncaught charm exceptions: `manager.run()` raises
  `scenario.errors.UncaughtCharmError`; inspect `excinfo.value.__cause__`.
- Deferred events: on the output `State` (`state.deferred`), or spy
  `ops.EventBase.defer`.
- Actions: `manager.run()` raises `testing.ActionFailed`; `.message` is the exact
  string passed to `event.fail()`. Leader-only guards and failure paths are unit
  territory even when integration covers the happy path.

### Secrets lifecycle

- `ctx.on.secret_changed(secret)` requires an observer-owned secret (`owner=None`) —
  the harness refuses owned secrets. For owner-side revision tracking, call
  `get_secret(label=...).get_content(refresh=True)` directly.
- `ctx.on.secret_remove(secret, revision=N)` requires an owned secret and a revision
  that is neither tracked nor latest — build the real rotation sequence first (rotate,
  track, then remove the old revision).

### Patching and harness limits

- Patch charm-imported helpers in the charm's namespace
  (`mocker.patch("charm.is_container", ...)`). Conditions passed to `block_unless` /
  `wait_unless` decorators bind at import time and cannot be patched — satisfy them
  with real state (files, mounts, relations). Conditions called inside a handler body
  resolve at call time and patch fine.
- Departing units are always remote (`JUJU_DEPARTING_UNIT` is built from the remote
  app name), so "this unit is departing" cannot be expressed through the harness. Call
  the handler directly with a stub event and a comment explaining why — the one
  sanctioned exception to the drive-real-events rule.
