# Paper2WeChat 项目设计文档

> 本文档为 AI 助手设计，记录项目的完整设计思路、需求分析和技术决策。后续开发时，可直接参考此文档快速上下文。

## 📌 项目概述

**项目名称**：paper2wechat  
**目标**：将学术论文（Arxiv）自动转换为微信公众号文章  
**用途**：帮助内容创作者/学术工作者快速将论文转化为普及性公众号文章  
**开发模式**：与 AI 助手协作开发并开源发布

---

## 🎯 核心需求分析

### 用户输入
- **输入方式**：Arxiv URL 或本地 PDF 文件
- **输入信息**：可选指定风格、图片数量、自定义提示
- **风格缺省行为**：未指定风格时，先推荐并征询确认（默认）

### 处理流程
```
Input (URL/PDF) 
  → 论文内容获取
  → 结构解析
  → 内容提取
  → 图片处理
  → 公众号适配
  → 风格应用
  → Markdown 生成
```

### 输出形式
- **格式**：本地 Markdown 文件（可直接用 md2wechat 发布）
- **可选**：一键上传到微信公众号草稿箱
- **内容**：完整的公众号文章（包含标题、摘要、正文、图片）

---

## 🔧 核心功能

### 1. 论文内容获取
- **支持形式**：
  - Arxiv URL（如 `https://arxiv.org/abs/2301.00000`）
  - 本地 PDF 文件
  
- **提取信息**：
  - 标题、作者、发布日期
  - 摘要（Abstract）
  - 完整文本内容
  - 内嵌图表和图片

### 2. 结构化内容解析
- **识别论文章节**：
  - Introduction（介绍）
  - Methods/Methodology（方法）
  - Results（结果）
  - Discussion（讨论）
  - Conclusion（结论）
  
- **提取关键信息**：
  - 核心创新点
  - 关键发现
  - 实践意义

### 3. 智能内容适配
- **长度控制**：
  - 自动摘要（学术 10000+ 字 → 公众号 2000-5000 字）
  - 两段式：简要版 + 完整版
  
- **语言转换**：
  - 学术语言 → 通俗语言
  - 专业概念 → 生活化比喻
  - 保持准确性

### 4. 图片处理
- **图片识别**：自动从论文中提取关键图表
- **智能选择**：基于相关性评估选择 3-5 张最重要的图
- **格式处理**：压缩、转换、上传到微信素材库
- **标题生成**：为每张图生成说明文字

### 5. 多风格支持
围绕"学术内容如何在微信讲好故事"，提供不同的呈现风格：

| 风格                 | 特点                 | 适用场景             |
| -------------------- | -------------------- | -------------------- |
| **academic-science** | 科学严谨，深入浅出   | AI 算法、基础科学    |
| **academic-tech**    | 技术洞察，面向开发者 | 工程技术、框架应用   |
| **academic-trend**   | 前沿趋势，强调创新   | 新兴领域、颠覆性发现 |
| **academic-applied** | 实践应用，关注落地   | 应用实例、产业意义   |

### 6. 风格推荐与确认流程

当用户未显式指定风格时，系统先根据论文内容做风格推荐，并征询是否使用：

- **默认**：推荐 + 询问确认
- **可选**：用户明确表示"以后自动用推荐"后，切换为自动使用推荐风格
- **会话记忆**：同一会话内保持用户选择的策略（默认询问或自动使用）

---

## 🏗️ 项目架构

### 核心模块结构

```
paper2wechat/
├── core/                           # 核心处理模块
│   ├── paper_fetcher.py           # 论文获取（URL/PDF）
│   ├── paper_parser.py            # 论文结构解析
│   ├── content_adapter.py         # 内容公众号化
│   ├── image_processor.py         # 图片识别和处理
│   └── markdown_generator.py      # Markdown 生成
│
├── skills/paper2wechat/            # Skill 定义（给 AI 用）
│   ├── SKILL.md                   # Skill 文档
│   ├── references/
│   │   ├── academic-styles.md     # 学术风格定义
│   │   ├── arxiv-guide.md         # Arxiv 论文准则
│   │   └── examples.md            # 使用示例
│   └── scripts/
│       └── run.sh                 # CLI 入口
│
├── prompts/                        # 提示词库
│   ├── arxiv_parser.md            # 论文解析 prompt
│   ├── content_adapter.md         # 内容适配 prompt  
│   ├── academic_styles.md         # 风格定义 prompt
│   └── image_selector.md          # 图片选择 prompt
│
├── examples/                       # 示例
│   ├── sample-arxiv.txt           # 示例论文数据
│   └── output-example.md          # 输出示例
│
├── tests/                          # 测试
│   ├── test_paper_fetcher.py
│   ├── test_content_adapter.py
│   └── test_integration.py
│
└── docs/                           # 文档
    ├── ARCHITECTURE.md            # 详细架构说明
    ├── API.md                     # Python API 文档
    ├── STYLES.md                  # 风格定义详解
    └── INTEGRATION.md             # 集成指南
```

---

## 🛠️ 技术栈决策

### 复用的 Skills

#### 1. **md2wechat Skill** ✅ 
- **用途**：复用其写作风格系统、Humanizer、微信发布功能
- **集成点**：
  - 复用 `write` 命令进行内容适配
  - 复用风格系统（dan-koe 为基础扩展）
  - 复用 `humanize` 进行 AI 痕迹移除
  - 复用 `convert` 命令进行最终转换和发布
- **优势**：不重复造轮子，充分利用现有基础设施

#### 2. **PDF Skill** ✅
- **用途**：处理本地 PDF 文件的提取
- **具体使用**：
  - `pdfplumber` - 保留优化布局的文本提取
  - `pypdf` - 元数据提取（标题、作者）
  - `pdfimages` - 图片提取
- **优势**：官方维护，功能完整

#### 3. **第三方 Skills**（待评估）
需要在 [skills.sh](http://skills.sh/) 上搜索的：
- **网页爬虫 Skill**：获取 Arxiv 网页元数据（标题、摘要链接等）
  - 搜索关键词：`web scraper`, `fetch content`, `html parser`
- **图片处理 Skill**：图片压缩和优化
  - 搜索关键词：`image compress`, `image resize`
- **HTTP Skill**：如果需要调用 Arxiv API
  - 搜索关键词：`http`, `curl request`

### 为什么不自己写？
- 集中精力在核心的"论文→公众号"转换逻辑
- 复用社区 skills 以保持项目轻量
- 降低维护成本

---

## 📱 使用体验设计

### 方式 1：CLI 命令行（最简单）
```bash
# 最简单的使用
paper2wechat https://arxiv.org/abs/2301.00000

# 完整参数
paper2wechat https://arxiv.org/abs/2301.00000 \
  --style academic-tech \
  --images 5 \
  --output article.md \
  --draft \                    # 自动上传微信
  --cover                      # 自动生成封面
```

### 方式 2：Python API（程序集成）
```python
from paper2wechat import PaperConverter

converter = PaperConverter(style="academic-tech")
article = converter.convert("https://arxiv.org/abs/2301.00000")
article.to_markdown("output.md")
article.upload_to_wechat(draft=True)
```

### 方式 3：Skill/AI 交互（自然语言）
```
用户："帮我把这篇论文转成公众号文章"
链接：https://arxiv.org/abs/2301.00000

AI (paper2wechat Skill):
1. 获取论文内容
2. 分析论文结构和关键点
3. 选择合适的风格和图片
4. 生成 Markdown
5. 提供预览和发布选项
```

---

## 🎨 内容适配策略

### 长度控制算法

**目标**：保留核心内容，压缩至 2000-5000 字

**策略**：
1. **必保留**：标题、摘要、关键贡献（核心 30-40%）
2. **可简化**：方法细节、相关工作（压缩至 20-30%）
3. **可删除**：数学推导、大量引用（删除 60-70%）

### 语言转换示例

**学术表述**：
> "本文提出了一种基于Transformer架构的多头自注意力机制，通过引入线性复杂度的近似方法，有效降低了计算复杂度。"

**公众号表述**：
> "我们设计了一个'聪慧的大脑'（Transformer），它能同时关注文本中的多个部分。不同于传统方法的高计算成本，我们的创新让它在保持聪慧的同时，也变得更'廉价'。"

### 图片配文示例

**原论文图片标题**：
> "Figure 3: Spatial attention maps for different test samples across model variants."

**公众号配文**：
> "▲ 不同模型版本对样本的关注热力图。地图上越红的地方，说明模型看得越仔细"

---

## 📊 开发计划

### MVP 第 1 阶段（基础功能）
**目标**：能基础转换 Arxiv 论文 → Markdown

- ✅ 支持 Arxiv URL 获取内容
- ✅ 基础论文解析（标题、摘要、章节）
- ✅ 内容智能摘要
- ✅ 1-2 个默认风格
- ✅ 输出 Markdown（本地）
- ✅ 集成 md2wechat 发布

**关键交付物**：
- `paper_fetcher.py` - 支持 URL 获取
- `paper_parser.py` - 基础解析
- `content_adapter.py` - 摘要和适配
- CLI 框架

### 第 2 阶段（多模态增强）
**目标**：提升内容质量，支持多种论文源

- 📸 智能图片识别和选择
- 🎨 5+ 学术风格
- 📊 表格自动识别
- 🗂️ 支持本地 PDF+网页两种源
- 🔄 批量处理

**关键交付物**：
- `image_processor.py` - 图片处理
- 学术风格库扩展
- PDF 集成

### 第 3 阶段（高级功能）
**目标**：专业级内容质量，一键发布

- 🤖 AI 痕迹移除（复用 humanizer）
- 📱 自动封面生成
- 🔄 批量处理多篇论文
- 📈 内容分析（字数、结构评分）
- 🚀 预设发布计划

---

## 🔌 集成方案详解

### 与 md2wechat 的集成

**流程**：
```
paper2wechat (我们) 
  → 生成 Markdown 
  → 调用 md2wechat CLI
  → 微信发布
```

**具体实现**：
```python
# paper2wechat/core/markdown_generator.py

class MarkdownGenerator:
    def generate_for_wechat(self, article_data, style):
        # 生成符合 md2wechat 要求的 Markdown
        markdown = self._generate_markdown(article_data, style)
        return markdown
    
    def publish_to_wechat(self, markdown_path, draft=True):
        # 调用 md2wechat CLI
        import subprocess
        cmd = [
            'bash', 'md2wechat/scripts/run.sh', 'convert',
            markdown_path,
            '--draft' if draft else ''
        ]
        subprocess.run(cmd)
```

### 与 PDF Skill 的集成

**流程**：
```
本地 PDF 
  → PDF Skill (pdfplumber)
  → 文本 + 图片
  → 后续处理同 URL
```

**具体实现**：
```python
# paper2wechat/core/paper_fetcher.py

from pypdf import PdfReader
import pdfplumber

class PaperFetcher:
    def fetch_from_pdf(self, pdf_path):
        # 1. 获取元数据
        reader = PdfReader(pdf_path)
        metadata = reader.metadata
        
        # 2. 提取文本
        with pdfplumber.open(pdf_path) as pdf:
            text = "".join(page.extract_text() for page in pdf.pages)
            tables = [t for p in pdf.pages for t in (p.extract_tables() or [])]
        
        # 3. 提取图片
        images = self._extract_images(pdf_path)
        
        return {
            'title': metadata.title,
            'text': text,
            'tables': tables,
            'images': images
        }
```

---

## 💡 关键设计决策

### 1. 为什么用 Markdown 作为中间格式？
- ✅ 与 md2wechat 生态兼容
- ✅ 易于人工二次编辑
- ✅ 可版本控制
- ✅ 易于转换为其他格式

### 2. 为什么分离提示词库？
- ✅ 便于迭代调整（无需修改代码）
- ✅ 支持用户自定义提示词
- ✅ 便于 prompt 版本管理
- ✅ 便于学习和贡献

### 3. 为什么设计三层用户界面（CLI + API + Skill）？
- ✅ CLI：对快速用户最友好
- ✅ API：对开发者/集成最友好
- ✅ Skill：对 AI 用户最友好
- ✅ 层次清晰，各司其职

### 4. 为什么不自己做微信发布？
- ✅ md2wechat 已经做得很好
- ✅ 避免重复开发
- ✅ 专注于"论文转换"核心
- ✅ 形成互补的生态

---

## 🚀 开源发布计划

### 发布前 Checklist

```
文档：
✅ README.md - 项目概述、特性、安装
✅ README.md - 包含快速开始指南
✅ docs/ARCHITECTURE.md - 架构详解
✅ docs/API.md - Python API 文档
✅ SKILL.md - Skill 文档
✅ CONTRIBUTING.md - 贡献指南

代码：
✅ setup.py - pip 安装支持
✅ requirements.txt - 依赖声明
✅ 完整源代码（包含注释）
✅ 类型提示（Python 3.8+）
✅ 单元测试

示例和样本：
✅ examples/ - 实际使用示例
✅ 测试通过的论文案例

开源治理：
✅ LICENSE - MIT License
✅ .gitignore - Git 配置
✅ CODE_OF_CONDUCT.md - 社区规范
```

### 推荐发布流程
1. **GitHub 开源** - 作为主仓库
2. **PyPI 发布** - 支持 `pip install paper2wechat`
3. **Anthropic Skills 社区** - 登记为官方 Skill
4. **文档网站**（可选）- ReadTheDocs

---

## 🎓 已做决策记录

### 论文选择
- ✅ 主要处理 Arxiv 论文（特别是 AI 相关）
- ✅ 支持本地 PDF（扩展性）
- ✅ 优先支持英文论文（可扩展中文）

### 内容风格
- ✅ 提供 4 种学术风格（科学、技术、趋势、应用）
- ✅ 风格可扩展，支持社区贡献
- ✅ 默认风格：academic-tech（技术洞察）

### 图片处理
- ✅ 自动识别和提取
- ✅ 基于相关性的智能选择（3-5 张）
- ✅ 上传到微信素材库
- ✅ 比例推荐：16:9（公众号首图）和灵活尺寸

### 集成策略
- ✅ 复用 md2wechat 完整发布链路
- ✅ 复用 PDF Skill 进行 PDF 处理
- ✅ 待搜索其他辅助 skills
- ✅ 最小化新依赖

---

## � Claude Code 集成指南

paper2wechat 采用独特的架构实现 Claude Code 集成：**完全由 Claude 的文本生成能力完成，不依赖任何外部代码执行**。

### 集成方式

**SKILL.md 文件** (`.claude/skills/paper2wechat/SKILL.md`)
- 解释 Claude 在 Claude Code 中如何工作
- 描述论文提取、内容改写、文章生成的完整流程
- 提供自然语言交互指南
- 强调这是由 Claude 能力完成，不涉及 Python/bash 代码执行

### 用户体验

用户在 Claude Code 中直接与 AI 对话：

```
"Convert this paper to a WeChat article: https://arxiv.org/abs/2510.21603"
"Rewrite this PDF in academic-tech style, keep it brief"
"Turn this research into content for business-minded WeChat followers"
```

### Claude 的处理步骤

1. **解析用户意图** - 理解论文来源、期望风格、长度偏好
2. **提取论文内容** - 从 Arxiv 或本地 PDF 获取关键信息
3. **分析和理解** - 深入理解核心问题、创新点、实际意义
4. **创意改写** - 用自身文本生成能力，将学术内容转换为微信友好的文章
5. **生成 Markdown** - 输出格式化的 Markdown，可直接使用
6. **反馈和保存** - 告知用户结果、路径和统计信息

### 为什么不执行代码？

paper2wechat 项目中有 Python 工具（converter.py 等），但在 Claude Code 中：
- **不调用** Python 脚本或 CLI
- **不需要** API key 配置
- **完全依赖** Claude 的文本生成和理解能力
- **更简洁** - 用户只需提供论文 URL 或文件

这样的设计：
- ✅ 用户体验流畅（纯对话，无配置）
- ✅ 减少依赖（不需要安装 Python 包）
- ✅ 降低犯错风险（不执行外部代码）
- ✅ 充分利用 Claude 的 AI 能力

### 与其他模式的区别

paper2wechat 支持多种使用方式：

| 方式                   | 执行方式            | 适合场景                 |
| ---------------------- | ------------------- | ------------------------ |
| **Claude Code (推荐)** | Claude 直接生成文章 | 快速、简洁、无需配置     |
| **Python CLI**         | 调用 converter.py   | 批量处理、需要高质量输出 |
| **Python API**         | 程序集成            | 应用内部使用             |

---

## �📞 后续开发指南

### Q: 我在新项目中和你对话时，应该怎么使用本文档？
**A**: 只需告诉我"按照 paper2wechat 项目设计继续"，或指定具体功能模块，我会自动参考此文档快速上下文。

### Q: 如果需要调整设计怎么办？
**A**: 直接告诉我，我会更新本文档并在代码中反映这些变化。本文档是 living document，会根据开发进展持续更新。

### Q: 关键的 API/接口定义在哪？
**A**: 查看 `docs/API.md`（开发中），或直接参考 `core/` 目录下的模块。

---

## 🌟 最后

这个项目有以下亮点：
- 🎯 解决实际问题（学术论文→大众传播）
- 🔗 充分复用现有生态（md2wechat + PDF Skill）
- 📚 清晰的分层架构（易于维护和扩展）
- 🚀 友好的用户体验（3 种界面）
- 💡 有良好的可扩展性（风格、提示词都独立）

**准备开始实现了！** 💪
