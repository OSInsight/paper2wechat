# Repository Context (Skill-Only)

This repository is maintained as a **skill-only** project.

## Primary Goal

Develop and publish the `paper2wechat` skill located at:
- `.claude/skills/paper2wechat/SKILL.md`

## Preferred Workflow

1. Update skill behavior in `.claude/skills/paper2wechat/SKILL.md`.
2. Put deterministic operations into `.claude/skills/paper2wechat/scripts/`.
3. Put reference guidance into `.claude/skills/paper2wechat/references/`.
4. Keep `agents/openai.yaml` aligned with skill intent.

## Parsing and Image Extraction

- `scripts/parse_paper.py` is the parser entrypoint.
- It carries the proven parser and image extraction logic directly in skill scripts.

## Quality Bar

- Keep docs and file structure aligned with marketplace publishing.
- Keep workflow descriptions focused on current behavior.
