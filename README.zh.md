# paper2wechat（Skill 工作流）

这个仓库已经调整为 **只服务 skills 工作流**，用于把 Arxiv 论文转换为公众号文章。

技能入口：
- `.agents/skills/paper2wechat/SKILL.md`
- `.agents/skills/wechat-publisher/SKILL.md`

## 当前工作流

本仓库使用基于 skill 的 Agent 工作流。

- `paper2wechat`：负责论文解析与文章生成
- `wechat-publisher`：负责 markdown 转公众号富文本、图片上传、草稿创建

## 快速开始（Skill 工作流）

1. 解析论文并提取图像：

```bash
bash .agents/skills/paper2wechat/scripts/fetch_paper.sh "<arxiv链接或ID或本地PDF>" ".paper2wechat"
```

2. 基于解析结果生成风格证据（最终风格由 Agent 决策）：

```bash
python .agents/skills/paper2wechat/scripts/detect_style.py ".paper2wechat/parsed/<paper_id>.json" --json
```

3. 由 Agent 基于解析 JSON 和模板生成公众号文章：
- 模板：`.agents/skills/paper2wechat/references/article-template.md`
- 推荐输出路径：`.paper2wechat/outputs/<paper_id>.md`
- 当文章输出到 `.paper2wechat/outputs` 时，图片链接使用 `../images/<paper_id>/<image_file>`。

## Skill 目录结构

```text
.agents/skills/paper2wechat/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
│   ├── fetch_paper.sh
│   ├── parse_paper.py
│   └── detect_style.py
└── references/
    ├── style-guide.md
    └── article-template.md

.agents/skills/wechat-publisher/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
│   └── publish_wechat.py
└── references/
        └── config-example.env
```

## 独立发布器（wechat-publisher）快速开始

1. 仅转换为可粘贴公众号富文本页面：

```bash
python .agents/skills/wechat-publisher/scripts/publish_wechat.py \
    --input-md ".paper2wechat/<paper_id>/outputs/<paper_id>.md"
```

2. 上传本地图片到公众号图床并替换正文图片链接：

```bash
WECHAT_APP_ID="..." WECHAT_APP_SECRET="..." \
python .agents/skills/wechat-publisher/scripts/publish_wechat.py \
    --input-md ".paper2wechat/<paper_id>/outputs/<paper_id>.md" \
    --upload-images
```

3. 可选：创建公众号草稿（需要封面 `thumb_media_id`）：

```bash
WECHAT_APP_ID="..." WECHAT_APP_SECRET="..." \
python .agents/skills/wechat-publisher/scripts/publish_wechat.py \
    --input-md ".paper2wechat/<paper_id>/outputs/<paper_id>.md" \
    --upload-images \
    --create-draft \
    --thumb-media-id "<thumb_media_id>"
```

默认输出：
- `.paper2wechat/<paper_id>/outputs/<paper_id>.wechat.html`
- `.paper2wechat/<paper_id>/outputs/<paper_id>.wechat.paste.html`
- `.paper2wechat/<paper_id>/outputs/image-map.json`（上传图片时）
- `.paper2wechat/<paper_id>/outputs/publish-result.json`（创建草稿时）

## 运行依赖

建议安装的 Python 依赖：
- `pypdf`
- `pdfplumber`
- `PyMuPDF`（可选但推荐，用于更稳健图像提取）
- `Pillow`
- `requests`
- `Markdown`

## 面向 Skills 广场发布的注意点

- `SKILL.md` 的触发描述要具体、可判定。
- `agents/openai.yaml` 要和 `SKILL.md` 保持一致。
- 能脚本化的步骤优先放在 `scripts/`，提高稳定性。
- 参考文档放在 `references/`，保持短小、按需加载。
