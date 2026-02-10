# Contributing to paper2wechat (Skill-Only)

This repository is skill-first.

Primary contribution target:
- `.agents/skills/paper2wechat/`

## What To Contribute

- Improve skill triggering and workflow clarity in `SKILL.md`.
- Improve deterministic scripts in `scripts/`.
- Improve writing/style references in `references/`.
- Keep `agents/openai.yaml` aligned with skill behavior.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Validation Checklist

1. `SKILL.md` frontmatter is valid (`name` and `description`).
2. Script help output is clear (`--help`).
3. End-to-end parse flow works:

```bash
bash .agents/skills/paper2wechat/scripts/fetch_paper.sh "<arxiv_url_or_id_or_pdf>" ".paper2wechat"
python .agents/skills/paper2wechat/scripts/detect_style.py ".paper2wechat/parsed/<paper_id>.json" --json
```

4. Workflow descriptions reflect current skill behavior.

## Scope Guardrails

Do not add:
- unrelated tooling that is not used by the skill workflow

## Pull Requests

- Keep changes small and focused.
- Update README/README.zh if behavior changes.
- Include before/after notes for skill behavior changes.
