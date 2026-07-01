---
name: update-agents-skills-readme
description: 'Update the README.md in .agents/skills/ when Copilot agent skills are added, removed, or modified. Use when the set of skills under .agents/skills/ changes and the README must be regenerated to reflect the current state.'
argument-hint: 'Path to the .agents/skills/ directory, or leave blank to use the default location.'
---

# Update the .agents/skills/ README

When to use

- The user has added, removed, or renamed a skill directory under `.agents/skills/`.
- The user asks to update or regenerate the skills README.
- The user asks to document the agent skills in the repository.

## Workflow

1. **Scan the skills directory.** Read the `.agents/skills/` directory to list all subdirectories that contain a `SKILL.md` file. The directory name is the skill identifier.

2. **Read each SKILL.md.** For each skill directory, read the `SKILL.md` file and extract the YAML frontmatter:
   - `name` — the skill name used in the table
   - `description` — the one-line description used in the table
   - `argument-hint` — used in the per-skill "When to use" section

3. **Read the introduction.** Extract the first heading and the introductory paragraph(s) immediately following it for the per-skill summary.

4. **Read the Process section.** Summarize the numbered steps from the "Process" section (or "Workflow" section) into a concise bullet list for the per-skill "Summary" section.

5. **Read the Constraints section.** Extract the key constraint rules (DO/DON'T statements) for the per-skill "Key constraints" section.

6. **Regenerate the README.** Write the `README.md` file at `.agents/skills/README.md` following the output format below.

7. **Verify consistency.** Confirm that every skill directory with a `SKILL.md` appears in the table, and that every table entry links to a valid `SKILL.md` file.

## Output format

The generated `README.md` must follow this structure exactly:

```markdown
# <repo-name> agentic skills

A collection of GitHub Copilot agent skills for <domain> development workflows.

## Skills

| Skill | Description |
|---|---|
| [`<name>`](<directory>/SKILL.md) | <description from YAML frontmatter> |
| ... | ... |

---

## <name>

<introductory paragraph from the skill's SKILL.md>

### When to use

Invoke this skill when <argument-hint, rephrased as prose>.

### Summary

1. <first step of the process>
2. <second step of the process>
3. ...

### Key constraints

- <constraint 1>
- <constraint 2>
- ...

See [<directory>/SKILL.md](<directory>/SKILL.md) for the full <description of what the skill covers>.
```

### Per-skill section rules

- The heading must be the skill `name` from the YAML frontmatter.
- The introductory paragraph must be the first paragraph after the top-level heading in the `SKILL.md`.
- The "When to use" section must rephrase the `argument-hint` as natural prose.
- The "Summary" section must list the Process/Workflow steps as a numbered bullet list.
- The "Key constraints" section must extract the most important DO/DON'T rules from the Constraints section.
- The final line must be a "See" link pointing to the full `SKILL.md`.

### Skills table rules

- The Skill column must use the `name` from the YAML frontmatter, wrapped in a link to the `SKILL.md` file.
- The Description column must use the `description` from the YAML frontmatter.
- Rows must be in alphabetical order by skill name.

## Notes

- If a subdirectory under `.agents/skills/` does not contain a `SKILL.md` file, skip it.
- If a `SKILL.md` file does not have YAML frontmatter, use the directory name as the skill name and the first sentence of the introduction as the description.
- If a `SKILL.md` file has no "Process" or "Workflow" section, omit the "Summary" section for that skill.
- If a `SKILL.md` file has no "Constraints" section, omit the "Key constraints" section for that skill.
- The `argument-hint` may contain instructions to "ASK THE USER BEFORE PROCEEDING". In that case, rephrase it to describe the context in which the skill should be invoked.

## Constraints

- DO NOT skip any skill directory that contains a valid `SKILL.md` file.
- DO NOT invent or assume descriptions, process steps, or constraints that are not present in the source `SKILL.md`.
- DO NOT use Latin terms or abbreviations such as e.g. or i.e. Use English equivalents.
- DO NOT change the directory name when linking to the `SKILL.md`. Use the actual directory name on disk.
- DO keep the skills table in alphabetical order.
- DO keep prose concise and factual.
- DO use the exact wording from the `SKILL.md` frontmatter for names and descriptions in the table.
- DO verify that every link in the table points to a file that exists.