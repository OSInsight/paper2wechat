---
name: paper2wechat
description: Convert Arxiv papers (URL, Arxiv ID, or local PDF) into WeChat Official Account markdown articles with practical summaries, TeX-source-first figure extraction (PDF fallback), and auto-recommended writing style based on parsed paper content (academic-science, academic-tech, academic-trend, academic-applied). Use when users ask to解读论文、转公众号文章、提炼可落地要点、自动配图或按受众调整语气和篇幅.
---

# Paper2WeChat

Execute this workflow when producing a Chinese WeChat article from an Arxiv paper.

## Inputs

Accept one of:
- Arxiv URL: `https://arxiv.org/abs/2301.00000`
- Arxiv ID: `2301.00000`
- Local PDF path: `./paper.pdf`

Optionally accept:
- user preferred style (optional override)
- max length
- max images
- output path

## Step 1: Parse Paper And Extract Figures

Run:

```bash
bash .agents/skills/paper2wechat/scripts/fetch_paper.sh "<url_or_id_or_pdf>" ".paper2wechat"
```

Expect output lines like:
- `Parsed cache: .paper2wechat/<paper_id>/parsed/<paper_id>.json`
- `Images dir: .paper2wechat/<paper_id>/images`

Image extraction behavior:
- For arXiv URL/ID: prefer TeX source images first, then fallback to PDF caption-based extraction.
- For local PDF: use PDF extraction path directly.

Verify parser output before writing:
- `title`, `authors`, `affiliations`, `abstract`
- `sections`
- `images` with `url` and `caption`

If no images are extracted, continue with text-only article and state that figures were unavailable.

## Step 2: Generate Style Evidence For Agent Decision

Use parsed JSON to generate style evidence from paper content (title, abstract, sections, captions):

```bash
python .agents/skills/paper2wechat/scripts/detect_style.py ".paper2wechat/<paper_id>/parsed/<paper_id>.json" --json
```

Rules:
- Treat script output as evidence, not final style lock.
- If user explicitly requires a style, user preference overrides all.
- If `confidence_band` is `high`, usually adopt top candidate.
- If `confidence_band` is `medium` or `low`, let Agent choose from top-2 or use hybrid style.
- If top-2 are close, hybrid style is allowed (for example `academic-tech + academic-applied`).

See `references/style-guide.md` for interpretation rules.

## Step 3: Build A Practical Summary

Produce a practical summary section before long-form explanation.
Ensure it answers all items below:
- 论文解决了什么问题
- 方法的核心创新是什么
- 关键结果指标是什么（优先写具体数字）
- 读者可以直接借鉴的做法是什么
- 落地边界和风险是什么

Keep this summary scannable with 4-6 bullets.

## Step 4: Generate The Article

In this skill, article rewriting is done by the Agent directly from parsed JSON.

Use `references/article-template.md` as the output scaffold and adapt tone by chosen style.
Template is a baseline, not a rigid format: adjust section names/order by paper type and audience.
Extract useful links directly during writing from parsed JSON text:
- open-source repo links (GitHub/GitLab/HuggingFace, if present)
- related papers/resources for further reading

For image links:
- default output file is under `.paper2wechat/<paper_id>/outputs/`
- use relative image paths like `../images/<image_file>`
- image filename must come from `.paper2wechat/<paper_id>/parsed/<paper_id>.json` (`images[].url`) instead of guessed naming patterns
- never guess filenames like `page_*.png` when parsed JSON provides `src_*.png`.

For image count:
- Do not hard-code to 1-2 images.
- Default to dynamic range `2-6` when images are available.
- Select by relevance and narrative fit: overview/framework first, then method details, then key results.
- Avoid near-duplicate figures or too many small/local patches from one big figure.
- If user sets `max images`, obey it.

Always include:
- concise 导读
- practical summary section
- method/result sections with context
- 机构/单位信息（优先使用 `affiliations`，缺失时写“未明确注明”）
- 开源地址（如果论文或项目提供）
- 扩展阅读（相关研究 + 技术工具/资源）
- `关键词` hashtag line

Style-aware structure guidance:
- `academic-science`: emphasize assumptions, experiment setup, reproducibility limits.
- `academic-tech`: emphasize architecture, implementation details, engineering trade-offs.
- `academic-trend`: emphasize direction shifts, ecosystem implications, future outlook.
- `academic-applied`: emphasize use cases, rollout constraints, KPI/ROI.

## Step 4.5: Persist Markdown File

After drafting content, write the final markdown to file.

Default output path:
- `.paper2wechat/<paper_id>/outputs/<paper_id>.md`

Rules:
- Unless user explicitly asks for chat-only output, always write/update the markdown file.
- Ensure output directory exists before writing.
- Do not only return content in the chat pane.
- After writing, report the absolute or repo-relative file path in the response.

Never add tool-credit disclaimers like “本文由...自动生成”.
Never output tool-wrapper artifacts in markdown body, including:
- `</content>`
- `<parameter name="filePath">...`
- local absolute paths like `/Users/...`

## Step 5: Validate Output Quality

Check the final markdown file:
- Structure is complete and readable on mobile.
- Style and tone match requested audience.
- Dynamic `2-6` images are inserted with contextual text and captions when available and appropriate.
- Claims and numbers align with source content.
- Output path exists (default: `.paper2wechat/<paper_id>/outputs/<paper_id>.md`).
- MUST verify every image link resolves from output file directory.
- MUST verify markdown does not contain tool-wrapper artifacts (`</content>`, `<parameter name="filePath">`, absolute local paths).

## Resources

- `scripts/fetch_paper.sh`: standalone entrypoint to parse paper and extract figures into cache.
- `scripts/parse_paper.py`: standalone parser with caption-aware figure extraction and fallback strategies.
- `scripts/detect_style.py`: recommend style from parsed paper content.
- `references/style-guide.md`: style selection rules and wording constraints.
- `references/article-template.md`: reusable WeChat article scaffold.
