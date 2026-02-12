---
name: wechat-publisher
description: Publish locally generated Markdown articles to WeChat Official Account workflow. Converts Markdown to WeChat-friendly rich text HTML, uploads local images to WeChat image hosting via MP API, and optionally creates draft articles in backend. Use when users ask to把本地md上传到公众号编辑器、解决本地图片无法显示、自动建草稿.
---

# WeChat Publisher

Execute this workflow after article markdown already exists (for example from `paper2wechat`).

## Inputs

Required:

- Markdown file path, typically `.paper2wechat/<paper_id>/outputs/<paper_id>.md`

Optional:

- WeChat AppID / AppSecret (for image upload and draft creation)
- whether to upload images
- whether to create draft
- draft metadata: title/author/digest/thumb_media_id/content_source_url
- theme: `clean` / `card` / `tech` / `minimal` / `wechat-classic` / `ai-insight`（推荐 AI 公众号）
- keep first H1 in draft body: `--keep-h1-in-draft` (default removes first H1 to avoid duplicated title)

Credential sources (choose one):

1) Environment variables (recommended for local runs):

```bash
export WECHAT_APP_ID="..."
export WECHAT_APP_SECRET="..."
```

2) CLI args:

```bash
python .agents/skills/wechat-publisher/scripts/publish_wechat.py \
  --input-md ".paper2wechat/<paper_id>/outputs/<paper_id>.md" \
  --upload-images \
  --app-id "..." \
  --app-secret "..."
```

Do not commit secrets to git.

Default token cache path:

- `<workspace_root>/.wechat-token.json` (shared across different papers)

## Step 1: Resolve Markdown Assets

Run:

```bash
python .agents/skills/wechat-publisher/scripts/publish_wechat.py --input-md ".paper2wechat/<paper_id>/outputs/<paper_id>.md"
```

This baseline run does not require API credentials.
It generates WeChat-friendly HTML and a copy helper page:

- `.paper2wechat/<paper_id>/outputs/<paper_id>.wechat.html`
- `.paper2wechat/<paper_id>/outputs/<paper_id>.wechat.paste.html`
- `.paper2wechat/<paper_id>/outputs/<paper_id>.wechat.themes.html` (local theme switch preview: clean/card/tech/minimal/wechat-classic/ai-insight)

If default style is not preferred, switch theme:

```bash
python .agents/skills/wechat-publisher/scripts/publish_wechat.py \
  --input-md ".paper2wechat/<paper_id>/outputs/<paper_id>.md" \
  --theme card
```

## Step 2: Upload Local Images To WeChat (Optional)

If markdown contains local image links and you want them available in WeChat backend:

```bash
WECHAT_APP_ID="..." WECHAT_APP_SECRET="..." \
python .agents/skills/wechat-publisher/scripts/publish_wechat.py \
  --input-md ".paper2wechat/<paper_id>/outputs/<paper_id>.md" \
  --upload-images
```

Expected artifacts:

- `image-map.json` in the same `outputs/` directory
- `image-hash-map.json` in the same `outputs/` directory (dedupe by file hash)
- html files with image links rewritten to WeChat-hosted URLs

Image upload dedupe:

- If image file path exists in map and content hash unchanged, uploader reuses existing URL and does not re-upload.
- If image content changes, uploader uploads again and refreshes mapping.

## Step 3: Create Draft In WeChat Backend (Optional)

To directly create a draft in Official Account backend:

```bash
WECHAT_APP_ID="..." WECHAT_APP_SECRET="..." \
python .agents/skills/wechat-publisher/scripts/publish_wechat.py \
  --input-md ".paper2wechat/<paper_id>/outputs/<paper_id>.md" \
  --upload-images \
  --create-draft \
  --auto-thumb
```

`--auto-thumb` will pick a suitable image from markdown (prefer framework/overview-like figures), upload it as permanent material, and use the returned `thumb_media_id` automatically.

Title behavior:

- Publisher tries full title first.
- If WeChat returns title-length error (`45003`), it retries with shorter title candidates.

Expected artifact:

- `publish-result.json` in `outputs/` containing `media_id`

## Notes

- Keep this skill independent from `paper2wechat`; do not modify existing parser or writing flow.
- For stable rendering, prefer uploading images first, then generate html.
- If API mode is unavailable, `*.wechat.paste.html` remains the fallback path: open it in browser and copy rich text into editor.

## Resources

- `scripts/publish_wechat.py`: deterministic publisher entrypoint
- `references/config-example.env`: local env variable template
