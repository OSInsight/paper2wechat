# Repository Context (Skill-Only)

This repository is maintained as a **skill-only** project.

## Skills

### Available skills
- paper2wechat: Convert Arxiv papers (URL, Arxiv ID, or local PDF) into WeChat Official Account markdown articles with practical summaries and auto-recommended writing style. (file: `./.agents/skills/paper2wechat/SKILL.md`)
- wechat-publisher: Convert local markdown articles into WeChat-rich-text HTML, upload local images via MP API, and optionally create draft articles. (file: `./.agents/skills/wechat-publisher/SKILL.md`)

### Trigger rules
- If the user provides an arXiv URL/ID or asks to解读论文/转公众号文章/提炼要点，prefer using `paper2wechat` for this turn.

## Primary Goal

Develop and publish the `paper2wechat` skill located at:
- `.agents/skills/paper2wechat/SKILL.md`

## Preferred Workflow

1. Update skill behavior in `.agents/skills/paper2wechat/SKILL.md`.
2. Put deterministic operations into `.agents/skills/paper2wechat/scripts/`.
3. Put reference guidance into `.agents/skills/paper2wechat/references/`.
4. Keep `agents/openai.yaml` aligned with skill intent.

## Parsing and Image Extraction

- `scripts/parse_paper.py` is the parser entrypoint.
- It carries the proven parser and image extraction logic directly in skill scripts.

## Quality Bar

- Keep docs and file structure aligned with marketplace publishing.
- Keep workflow descriptions focused on current behavior.
