# Paper2WeChat 📄➡️📱

将 Arxiv 论文转换为微信公众号文章，具备实用摘要、PDF 图片提取和风格自适应能力。

> **🤖 给 AI Agent**: 如果你是帮助用户使用此工具的 AI 助手，请查看 [`.claude/skills/paper2wechat/SKILL.md`](.claude/skills/paper2wechat/SKILL.md) 了解 Agent 专用指令。
>
> **👤 给人类用户**: 继续阅读下面的 CLI、API 和开发文档。

[English Version](README.md)

## ✨ 功能特点

- 🔗 **自动论文解析** - 直接从 Arxiv URL 或本地 PDF 获取
- 📸 **PDF 图片提取** - 从 PDF 提取图表并插入 markdown
- 🎨 **多种风格** - 学术科学、学术技术、学术趋势、学术应用
- 📝 **内容自适应** - 智能摘要和语言转换
- ⚡ **一键发布** - 与微信和 md2wechat 直接集成
- 🐍 **Python API** - 嵌入到你的应用中
- 🛠️ **CLI 工具** - 快速命令行界面
- 🤖 **AI Skill** - 通过 Claude 进行自然语言交互

## 🚀 快速开始

### 安装

```bash
# 从源代码安装
git clone https://github.com/OSInsight/paper2wechat.git
cd paper2wechat
pip install -e .
```

### 使用

#### 1. CLI - 最简单的方式

```bash
# 最基础的使用
paper2wechat https://arxiv.org/abs/2301.00000
# 默认输出：outputs/2301.00000.md

# 完整参数
paper2wechat https://arxiv.org/abs/2301.00000 \
  --style academic-tech \
  --images 5 \
  --max-length 4500 \
  --output outputs/article.md \
  --preview

# 上传到微信草稿
paper2wechat https://arxiv.org/abs/2301.00000 --draft --cover

# 从本地 PDF
paper2wechat ./paper.pdf --style academic-science
```

说明：CLI 默认要求你配置 `OPENROUTER_API_KEY` 或 `ANTHROPIC_API_KEY`。  
如果你明确接受低质量规则改写，可加 `--allow-rule-based`。

#### 2. Python API

```python
from paper2wechat import PaperConverter

# 初始化转换器
converter = PaperConverter(style="academic-tech", max_images=5)

# 从 Arxiv URL 转换
article = converter.convert("https://arxiv.org/abs/2301.00000")

# 或从 PDF 转换
article = converter.convert_pdf("./paper.pdf")

# 输出为 Markdown
markdown = article.to_markdown()
article.save_markdown("output.md")

# 预览
print(article.preview())

# 上传到微信（需要配置）
converter.upload_to_wechat(article, draft=True)
```

#### 3. AI Skill（通过 Claude）

```
你: "帮我把这篇论文转成微信公众号文章"
链接: https://arxiv.org/abs/2301.00000

Claude: [使用 paper2wechat skill 处理]
1. 获取论文内容...
2. 分析论文结构...
3. 选择关键图片...
4. 生成 markdown...
5. 准备预览或发布
```

也可以直接用 Agent 自动模式（无需手工拼 CLI 参数）：

```bash
bash skills/paper2wechat/scripts/run.sh agent "把这篇论文转公众号：https://arxiv.org/abs/2510.21603"
```

对话式 Agent 工作流不强制你提供 API Key；Agent 可基于解析结果直接生成中文稿件。

## 🎯 架构

```
Arxiv URL/PDF
    ↓
[论文获取器]
    ↓
[内容解析器] → 提取标题、摘要、关键章节、图表
    ↓
[图片处理器] → 识别、选择和准备图片
    ↓
[内容适配器] → 摘要、转换为易懂的语言
    ↓
[风格引擎] → 应用所选风格（科学/技术/趋势/应用）
    ↓
[Markdown 生成器] → 生成微信兼容的 markdown
    ↓
输出：.md 文件 → [md2wechat] → 微信文章
```

## 📚 文档


- [文档/架构说明](docs/ARCHITECTURE.md) - 完整架构解释
- [文档/API 参考](docs/API.md) - Python API 文档
- [文档/风格定义](docs/STYLES.md) - 风格定义和示例
- [技能/论文转微信/SKILL.md](skills/paper2wechat/SKILL.md) - AI Skill 指南
- [CLAUDE.md](CLAUDE.md) - 项目设计文档（用于 AI 助手上下文）

## 🎨 可用风格

| 风格                 | 描述                 | 适合               |
| -------------------- | -------------------- | ------------------ |
| **academic-science** | 科学严谨，易懂的解释 | AI 算法、基础科学  |
| **academic-tech**    | 技术洞察，开发者友好 | 工程、框架、工具   |
| **academic-trend**   | 面向未来，强调创新   | 新兴领域、突破发现 |
| **academic-applied** | 实践应用，真实影响   | 行业应用、使用案例 |

## 🔌 集成

### 与 md2wechat 集成

无缝集成 [md2wechat](https://github.com/geekjourneyx/md2wechat-skill) 进行发布：

```bash
# 生成 markdown
paper2wechat https://arxiv.org/abs/2301.00000 --output outputs/article.md

# 然后通过 md2wechat 发布
bash md2wechat/scripts/run.sh convert outputs/article.md --draft --cover cover.jpg
```

## 📁 输出与缓存目录

默认生成和缓存目录：

- `outputs/<paper-id>.md`：最终 markdown
- `.paper2wechat/downloads/`：下载的 Arxiv PDF
- `.paper2wechat/parsed/`：解析后的结构化 JSON
- `.paper2wechat/images/<paper-id>/`：从 PDF 提取的原始图片
- `outputs/assets/<markdown名>/`：为 markdown 复制的可显示图片

## 🛠️ 配置

### 环境变量

```bash
# 用于 LLM 改写（推荐）
export OPENROUTER_API_KEY=your_openrouter_key
export OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
# 可选：自定义 OpenRouter 地址和应用标识
export OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
export OPENROUTER_SITE_URL=https://your-site.example
export OPENROUTER_APP_NAME=paper2wechat

# 可选：直连 Anthropic（当未配置 OpenRouter 时回退）
export ANTHROPIC_API_KEY=your_anthropic_key

# 用于微信发布（可选）
export WECHAT_APPID=your_appid
export WECHAT_SECRET=your_secret

# 用于图片 API（可选）
export IMAGE_API_KEY=your_key
export IMAGE_API_BASE=your_api_base
```

### 配置文件

创建 `~/.paper2wechat/config.yaml`：

```yaml
wechat:
  appid: your_appid
  secret: your_secret

image:
  api_key: your_key
  max_width: 1920
  auto_compress: true

defaults:
  style: academic-tech
  max_images: 5
```

## 📦 项目结构

```
paper2wechat/
├── CLAUDE.md                         # AI 设计文档
├── README.md                         # 英文说明
├── README.zh.md                      # 中文说明
├── setup.py                          # Python 包配置
├── requirements.txt                  # 依赖
│
├── paper2wechat/
│   ├── __init__.py
│   └── core/                         # 核心模块
│       ├── cli.py                    # CLI 入口
│       ├── paper_fetcher.py          # URL/PDF 获取与图片提取
│       ├── content_adapter.py        # 内容公众号化
│       ├── image_processor.py        # 图片排序/选择/压缩
│       ├── converter.py              # 端到端流程
│       ├── models.py                 # 数据模型
│       └── markdown_generator.py     # markdown 生成
│
├── skills/                           # Claude Skill 定义
│   └── paper2wechat/
│       ├── SKILL.md                 # Skill 文档
│       └── scripts/
│           └── run.sh               # CLI 包装器
│
├── prompts/                          # 提示词模板
│   └── academic_styles.md
│
├── examples/                         # 使用示例
│
├── tests/                            # 测试
│
└── docs/                             # 详细文档
    ├── ARCHITECTURE.md
    ├── API.md
    ├── STYLES.md
    └── INTEGRATION.md
```

## 🚀 路线图

### 第 1 阶段 (MVP) 
- [x] 支持 Arxiv URL 获取
- [x] 基础的内容提取和适配
- [x] 1-2 个默认风格
- [x] 输出为 markdown（本地）
- [ ] md2wechat 集成（依赖外部仓库和配置）

### 第 2 阶段 - 增强
- [x] 基础 PDF 图片提取与 markdown 插图
- [ ] 智能图片识别和选择
- [ ] 5+ 学术风格
- [ ] 表格自动识别
- [ ] 本地 PDF + 网页源
- [ ] 批量处理

### 第 3 阶段 - 高级
- [ ] AI 痕迹移除（humanizer）
- [ ] 自动封面生成
- [ ] 内容分析评分
- [ ] 发布计划
- [ ] 风格自定义

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解指南。

## 📄 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE)

## 🙏 致谢

- [md2wechat](https://github.com/geekjourneyx/md2wechat-skill) - 智能微信发布
- [PDF Skill](https://github.com/anthropics/skills) - 鲁棒的 PDF 处理
- [pdfplumber](https://github.com/jsvine/pdfplumber) - 文本提取
- [Anthropic Claude](https://www.anthropic.com/) - AI 核心

## 📧 支持

- 在 GitHub 上提交 issue
- 查看 [FAQ](docs/FAQ.md)
- 阅读 [故障排除](docs/TROUBLESHOOTING.md)

---

**用 ❤️ 为学术社区打造**
