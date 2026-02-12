---
name: paper2wechat-pipeline
description: Orchestrate end-to-end paper2wechat workflow from arXiv input to WeChat-ready outputs by chaining parser, style evidence, article markdown path resolution, and wechat-publisher steps. Use when users ask for 一条龙流程/单入口执行 from arXiv to WeChat draft.
---

# Paper2WeChat Pipeline

Use this skill as the orchestration layer over existing skills:

- `paper2wechat` for parsing + article writing
- `wechat-publisher` for rendering + image upload + draft creation

## Inputs

Required:

- paper input: arXiv URL / arXiv ID / local PDF path

Optional:

- cache root (default `.paper2wechat`)
- article markdown path (`--article-md`)
- publish options (`--theme`, `--upload-images`, `--create-draft`, `--auto-thumb`)

## Command

```bash
python .agents/skills/paper2wechat-pipeline/scripts/run_pipeline.py \
  --paper "2602.09013" \
  --theme ai-insight \
  --upload-images
```

## Behavior

1. Parse paper and extract figures via `paper2wechat/scripts/fetch_paper.sh`.
2. Run style evidence script via `paper2wechat/scripts/detect_style.py`.
3. Resolve expected article markdown path (`.paper2wechat/<paper_id>/outputs/<paper_id>.md`).
4. If markdown exists, call `wechat-publisher/scripts/publish_wechat.py`.
5. If markdown is missing, report parse/style outputs and stop with actionable guidance.

## Notes

- This skill is intentionally non-invasive: it does not change parser/writer logic.
- For true one-shot draft creation, ensure markdown exists first (by Agent writing step) then enable publish flags.
