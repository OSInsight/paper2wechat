# paper2wechat（Skill 工作流）

这个仓库已经调整为 **只服务 skills 工作流**，用于把 Arxiv 论文转换为公众号文章。

技能入口：
- `.agents/skills/paper2wechat/SKILL.md`

## 当前工作流

本仓库使用基于 skill 的 Agent 工作流。

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
```

## 运行依赖

建议安装的 Python 依赖：
- `pypdf`
- `pdfplumber`
- `PyMuPDF`（可选但推荐，用于更稳健图像提取）
- `Pillow`

## 面向 Skills 广场发布的注意点

- `SKILL.md` 的触发描述要具体、可判定。
- `agents/openai.yaml` 要和 `SKILL.md` 保持一致。
- 能脚本化的步骤优先放在 `scripts/`，提高稳定性。
- 参考文档放在 `references/`，保持短小、按需加载。
