---
name: create-juju-integration-interface-readme
description: 'Create README files for standalone Juju integration interface implementation packages and libraries. Use when writing, reviewing, or generating a README for an interface library package that implements a provider/requirer pattern for Juju charm relations.'
argument-hint: 'ASK THE USER BEFORE PROCEEDING if they do not provide a package name or directory when the load this skill'
---

# Skill: Create Juju integration interface implementation README

When to use

- The user asks to create or draft a README for an interface library package.
- The user asks to document a Juju integration interface implementation.
- The user points to a package directory containing provider/requirer classes and asks for documentation.

## Workflow

1. **Identify the interface package.** Locate the package directory. It will typically contain a `src/` directory with an `__init__.py` (or similar module) that defines the provider and requirer classes, data models (often pydantic), and custom events.

2. **Read the source code.** Read the main module file(s) to extract:
   - The package name and import path.
   - Provider and Requirer class names.
   - Custom events emitted by each side.
   - Data models (pydantic `BaseModel` subclasses or similar) that define the schema of relation data exchanged.
   - Any constants, enums, or type aliases relevant to the interface contract.
   - How secrets or sensitive data are handled (for example, Juju Secrets).

3. **Determine data flow direction.** Identify which fields flow from Requirer to Provider, and which flow from Provider to Requirer. This determines the arrows and labels in the mermaid diagram.

4. **Generate the README** following the output format below.

5. **Verify accuracy.** Cross-reference the generated README against the source code to ensure all documented fields, events, and behaviors are accurate.

## Output format

The generated README MUST follow this structure exactly:

```markdown
# `<package_name>`

## Usage

<One or two paragraphs describing what this interface does and when a charm would use it.>

To install, add `<pip-package-name>` to your Python dependencies. Then in your Python code, import as:

\```python
from <import_path> import <key_classes>
\```

## Direction

The `<interface_name>` interface implements a provider/requirer pattern.
The Provider is <description of provider role>.
The Requirer is <description of requirer role>.

\```mermaid
flowchart TD
    Requirer -- <fields sent by requirer> --> Provider
    Provider -- <fields sent by provider> --> Requirer
\```

## Behavior

<Brief prose describing the overall interaction between Provider and Requirer.>

### Provider

- Is expected to <behavior 1>.
- Is expected to <behavior 2>.
- ...

### Requirer

- Is expected to <behavior 1>.
- Is expected to <behavior 2>.
- ...

## Integration data

<Description of what data is exchanged and how it is structured. Mention whether data is passed via the relation databag, Juju Secrets, or both.>

[\[Pydantic Schema\]](<relative path to schema file, if available>)

### Example

\```yaml
provider:
  app: {<fields>}
  unit: {<fields>}
requirer:
  app: {<fields>}
  unit: {<fields>}
\```

## Examples

### Requirer charm

\```python
<Complete, minimal example of a charm using the Requirer side of the interface.
Include imports, class definition, __init__ with handler registration, and event callbacks.>
\```

### Provider charm

\```python
<Complete, minimal example of a charm using the Provider side of the interface.
Include imports, class definition, __init__ with handler registration, and event callbacks.>
\```
```

## Notes

- If the package only exposes one side (for example, only a Requirer library for external charms to consume), include only that side in the Examples section but still document both sides in the Behavior section.
- The mermaid diagram arrows should be labeled with the key data field names exchanged in each direction. Use comma-separated field names on the arrow labels.
- The Integration data YAML example should show realistic but non-sensitive placeholder values.
- If the source code references a separate `schema.py` file, link to it in the Integration data section.
- The Examples section should show how the library is actually used inside a charm's `src/charm.py`, including event observation and handler methods.

## Reference examples

The following upstream READMEs demonstrate the expected style and level of detail:

- `canonical/charmlibs` — `interfaces/filesystem_info/interface/v0/README.md`
- `canonical/charmlibs` — `interfaces/etcd_client/interface/v0/README.md`
- `canonical/data-platform-charmlibs` — `interfaces/README.md` (for code example style in the Examples section)

Use the GitHub MCP server to query these examples if the server is available in the current harness environment

## Constraints

- DO NOT USE Latin terms or abbreviations such as e.g. or i.e.
- DO USE English equivalents to Latin terms or abbreviations such as 'for example' (instead of e.g.) and 'that is' (instead of i.e.).
- DO NOT invent or assume data fields, events, or behaviors that are not present in the source code. If something is unclear, ask the user.
- DO keep prose concise and factual.
- DO use bullet lists for Provider and Requirer behavior expectations.
- DO use fenced code blocks with language identifiers (`python`, `yaml`, `mermaid`).
