# paper2wechat (Skill Workflow)

This repository is now maintained as a **skill-first project** for converting Arxiv papers into WeChat-ready articles.

The skill lives at:
- `.claude/skills/paper2wechat/SKILL.md`

## Workflow

This repository uses a skill-driven agent workflow.

## Quick Start (Skill Workflow)

1. Parse paper and extract figures:

```bash
bash .claude/skills/paper2wechat/scripts/fetch_paper.sh "<arxiv_url_or_id_or_pdf>" ".paper2wechat"
```

2. Generate style evidence from parsed content (Agent makes final style decision):

```bash
python .claude/skills/paper2wechat/scripts/detect_style.py ".paper2wechat/parsed/<paper_id>.json" --json
```

3. Let agent generate WeChat article from parsed JSON and template:
- Template: `.claude/skills/paper2wechat/references/article-template.md`
- Recommended output: `.paper2wechat/outputs/<paper_id>.md`
- When output is under `.paper2wechat/outputs`, image links should use `../images/<paper_id>/<image_file>`.

## Skill Packaging Layout

```text
.claude/skills/paper2wechat/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
│   ├── fetch_paper.sh
│   ├── parse_paper.py
│   └── detect_style.py
└── references/
    ├── style-guide.md
    └── article-template.md
```

## Runtime Dependencies

Recommended Python dependencies for parsing:
- `pypdf`
- `pdfplumber`
- `PyMuPDF` (optional but recommended for better figure extraction)
- `Pillow`

## Notes For Skill Marketplace Publishing

- Keep trigger description in `SKILL.md` explicit and specific.
- Keep `agents/openai.yaml` in sync with `SKILL.md` intent.
- Prefer script-backed deterministic steps (`scripts/`) over long prompt-only logic.
- Keep reference docs small and focused (`references/`).
