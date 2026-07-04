# Lightweight Agent Skill Installation

This repository has two different install surfaces:

- Python package/runtime: installs `document_briefing_cache` code and templates.
- Agent skill bundle: installs only `skills/document-briefing-cache`.

Do not install the repository root as an agent skill. Root-copy installers can copy tests, docs, examples, eval fixtures, source code, and validation scripts into the host skill directory. Use the lightweight skill subdirectory instead.

## Bundle Contents

The installable skill bundle is:

```text
skills/document-briefing-cache/
  SKILL.md
  agents/openai.yaml
  references/
    architecture.md
    schema.md
    llm-contract.md
    best-practices.md
```

It intentionally excludes `tests`, `docs`, `examples`, `evals`, `src`, and `scripts`.

## Codex

Codex skills use a directory containing `SKILL.md`. Codex reads only skill metadata at startup, then loads `SKILL.md` and referenced files progressively when the skill is relevant.

Recommended installs:

```bash
# User skill directory
mkdir -p ~/.agents/skills
cp -R skills/document-briefing-cache ~/.agents/skills/document-briefing-cache

# Repository-local interoperable path
mkdir -p .agents/skills
cp -R skills/document-briefing-cache .agents/skills/document-briefing-cache
```

When using a GitHub skill installer, select the subpath `skills/document-briefing-cache`, not the repository root.

## Claude Code

Claude Code project skills are stored under `.claude/skills/<skill-name>/SKILL.md`; personal skills are stored under `~/.claude/skills/<skill-name>/SKILL.md`.

Recommended installs:

```bash
mkdir -p ~/.claude/skills
cp -R skills/document-briefing-cache ~/.claude/skills/document-briefing-cache

mkdir -p .claude/skills
cp -R skills/document-briefing-cache .claude/skills/document-briefing-cache
```

For Claude API skill upload flows, zip a common root that contains this bundle, not the whole repository.

## Gemini CLI

Gemini CLI supports user and workspace skill directories, including interoperable `.agents/skills` locations. It also supports installing a skill from a Git repository subpath.

Recommended installs:

```bash
gemini skills install https://github.com/dd3ok/document-briefing-cache-skill.git --path skills/document-briefing-cache --scope user

mkdir -p ~/.agents/skills
cp -R skills/document-briefing-cache ~/.agents/skills/document-briefing-cache
```

## Antigravity

Google describes Antigravity skills as lightweight, open-format agent extensions and points users to `npx skills add` for compatible installations. Because installer flags vary by version, do not accept an install unless it selects the `document-briefing-cache` skill under `skills/document-briefing-cache`.

Recommended install:

```bash
mkdir -p .agents/skills
cp -R skills/document-briefing-cache .agents/skills/document-briefing-cache
```

Optional installer flow:

```bash
npx skills add dd3ok/document-briefing-cache-skill
```

Use the interactive prompt to select only `document-briefing-cache`, then verify the installed directory contains only `SKILL.md`, `agents/openai.yaml`, and `references/*.md`.

## OpenClaw

OpenClaw discovers skills from workspace `skills`, project `.agents/skills`, personal `~/.agents/skills`, and managed `~/.openclaw/skills` locations.

Recommended installs:

```bash
mkdir -p skills .agents/skills ~/.agents/skills
cp -R skills/document-briefing-cache .agents/skills/document-briefing-cache

openclaw skills install ./skills/document-briefing-cache --as document-briefing-cache
```

Run `openclaw skills list` or `openclaw skills check` after installation.

## Hermes

Hermes uses `~/.hermes/skills` for primary skill storage and supports Agent Skills compatible repositories. It can install a single GitHub skill path.

Recommended installs:

```bash
hermes skills install dd3ok/document-briefing-cache-skill/skills/document-briefing-cache

mkdir -p ~/.hermes/skills
cp -R skills/document-briefing-cache ~/.hermes/skills/document-briefing-cache
```

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
