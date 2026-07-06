# Lightweight Agent Skill Installation

Last checked: 2026-07-04

## Verified surfaces

- Codex local and repository skill folders
- Claude Code personal and project skill folders

## Community-compatible notes

- Gemini CLI
- Antigravity
- OpenClaw
- Hermes

Community host commands below are examples to verify against the current host documentation before use. Prefer any current host option that installs the `skills/briefprint` subdirectory without copying the repository root.

| Host | Install example | Drift risk | Required post-check |
| --- | --- | --- | --- |
| Gemini CLI | Use the current `gemini skills` subpath flow or copy the bundle to `.agents/skills/briefprint`. | Installer flags can change. | Verify the installed directory is `skills/briefprint`, not the repository root. |
| Antigravity | `npx skills add dd3ok/briefprint`, then select only `briefprint` when prompted. | Interactive selection can copy too much if the root is selected. | Verify only `SKILL.md`, `agents/openai.yaml`, and `references/*.md` were installed. |
| OpenClaw | Use the current OpenClaw installer for local `./skills/briefprint`, or copy the bundle to `.agents/skills/briefprint`. | Discovery paths vary by workspace and user scope. | Run the host's skills list/check command and verify the selected path. |
| Hermes | Use the current Hermes single-path install for `dd3ok/briefprint/skills/briefprint`, or copy the bundle to `~/.hermes/skills/briefprint`. | GitHub path syntax can drift. | Verify only the lightweight bundle files are present. |

Use the source links at the end of this document to confirm current host syntax before publishing or automating these examples.

This repository has two different install surfaces:

- Python package/runtime: installs `document_briefing_cache` code and templates.
- Agent skill bundle: installs only `skills/briefprint`.

Do not install the repository root as an agent skill. Root-copy installers can copy tests, docs, examples, eval fixtures, source code, and validation scripts into the host skill directory. Use the lightweight skill subdirectory instead.

The skill bundle is static install-time guidance. Briefprint's runtime cache lives under `--cache-dir`; it is not part of the agent skill bundle. Installing, updating, or removing the agent skill does not migrate, prune, or delete runtime caches. No portable agent-skill host contract currently provides automatic eviction for generated document state. Do not write document caches into the installed skill directory.

## Bundle Contents

The installable skill bundle is:

```text
skills/briefprint/
  SKILL.md
  agents/openai.yaml
  references/
    architecture.md
    schema.md
    llm-contract.md
    best-practices.md
```

It intentionally excludes `tests`, `docs`, `examples`, `evals`, `src`, and `scripts`.

## Verify installed files

After installation, the skill directory should contain only these files:

```text
SKILL.md
agents/openai.yaml
references/architecture.md
references/schema.md
references/llm-contract.md
references/best-practices.md
```

It must not contain development or runtime directories such as `.github`, `docs`, `evals`, `examples`, `scripts`, `src`, or `tests`.

## Codex

Codex skills use a directory containing `SKILL.md`. Codex reads only skill metadata at startup, then loads `SKILL.md` and referenced files progressively when the skill is relevant.

Recommended installs:

```bash
# User skill directory
mkdir -p ~/.agents/skills
cp -R skills/briefprint ~/.agents/skills/briefprint

# Repository-local interoperable path
mkdir -p .agents/skills
cp -R skills/briefprint .agents/skills/briefprint
```

When using a GitHub skill installer, select the subpath `skills/briefprint`, not the repository root.

## Claude Code

Claude Code project skills are stored under `.claude/skills/<skill-name>/SKILL.md`; personal skills are stored under `~/.claude/skills/<skill-name>/SKILL.md`.

Recommended installs:

```bash
mkdir -p ~/.claude/skills
cp -R skills/briefprint ~/.claude/skills/briefprint

mkdir -p .claude/skills
cp -R skills/briefprint .claude/skills/briefprint
```

For Claude API skill upload flows, zip a common root that contains this bundle, not the whole repository.

## Validation

Local repository validation checks that the installable bundle stays small and does not include development-only directories:

```bash
python -m pytest tests/test_installable_skill_bundle.py
python scripts/validate_skill.py
```

Python package installation is separate from agent skill installation. The wheel installs only the runtime package and templates. Source distributions may include repository test and documentation files for source-level validation, but those files are not installed into site-packages during normal pip installation.

## Source Notes

- OpenAI Codex skills: https://developers.openai.com/codex/skills
- Claude Code skills: https://docs.anthropic.com/en/docs/claude-code/skills
- Claude API skills guide: https://platform.claude.com/docs/en/build-with-claude/skills-guide
- Gemini CLI skills: https://geminicli.com/docs/cli/skills/
- Google Antigravity skills codelab: https://codelabs.developers.google.com/getting-started-with-antigravity-skills
- OpenClaw skills: https://docs.openclaw.ai/tools/skills
- Hermes skills: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
