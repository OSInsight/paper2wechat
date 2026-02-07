# Paper2WeChat 📄➡️📱

Convert Arxiv papers to WeChat Official Account articles with practical summarization, PDF image extraction, and style adaptation.

[中文版本](README.zh.md)

## ✨ Features

- 🔗 **Auto Paper Parsing** - Direct from Arxiv URL or local PDF
- 📸 **PDF Image Extraction** - Extract paper figures from PDF and insert into markdown
- 🎨 **Multiple Styles** - Academic-science, academic-tech, academic-trend, academic-applied
- 📝 **Content Adaptation** - Intelligent summarization and language conversion
- ⚡ **One-Click Publishing** - Direct integration with WeChat and md2wechat
- 🐍 **Python API** - Embed in your own applications
- 🛠️ **CLI Tool** - Command-line interface for quick usage
- 🤖 **AI Skill** - Natural language interaction via Claude

## 🚀 Quick Start

### Installation

```bash
# From PyPI (coming soon)
pip install paper2wechat

# From source
git clone https://github.com/yourusername/paper2wechat.git
cd paper2wechat
pip install -e .
```

### Usage

#### 1. CLI - Simplest Way

```bash
# Most basic usage
paper2wechat https://arxiv.org/abs/2301.00000
# Default output: outputs/2301.00000.md

# With options
paper2wechat https://arxiv.org/abs/2301.00000 \
  --style academic-tech \
  --images 5 \
  --max-length 4500 \
  --output outputs/article.md \
  --preview

# Upload to WeChat draft
paper2wechat https://arxiv.org/abs/2301.00000 --draft --cover

# From local PDF
paper2wechat ./paper.pdf --style academic-science
```

#### 2. Python API

```python
from paper2wechat import PaperConverter

# Initialize converter
converter = PaperConverter(style="academic-tech", max_images=5)

# Convert from Arxiv
article = converter.convert("https://arxiv.org/abs/2301.00000")

# Or from PDF
article = converter.convert_pdf("./paper.pdf")

# Output as Markdown
markdown = article.to_markdown()
article.save_markdown("output.md")

# Preview
print(article.preview())

# Upload to WeChat (requires config)
converter.upload_to_wechat(article, draft=True)
```

#### 3. AI Skill (via Claude)

```
You: "Help me convert this paper to a WeChat article"
Link: https://arxiv.org/abs/2301.00000

Claude: [Using paper2wechat skill to process]
1. Fetching paper content...
2. Analyzing structure...
3. Selecting key images...
4. Generating markdown...
5. Ready for preview or publishing
```

## 🎯 Architecture

```
Arxiv URL/PDF
    ↓
[Paper Fetcher]
    ↓
[Content Parser] → Extract title, abstract, key sections, figures
    ↓
[Image Processor] → Identify, select, and prepare images
    ↓
[Content Adapter] → Summarize, convert to accessible language
    ↓
[Style Engine] → Apply chosen style (science/tech/trend/applied)
    ↓
[Markdown Generator] → Generate WeChat-compatible markdown
    ↓
Output: .md file → [md2wechat] → WeChat article
```

## 📚 Documentation

- [QUICKSTART.md](QUICKSTART.md) - 5-minute guide to get started
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Full architecture explanation
- [docs/API.md](docs/API.md) - Python API reference
- [docs/STYLES.md](docs/STYLES.md) - Style definitions and examples
- [skills/paper2wechat/SKILL.md](skills/paper2wechat/SKILL.md) - AI Skill guide
- [CLAUDE.md](CLAUDE.md) - Project design document (for AI assistant context)

## 🎨 Available Styles

| Style                | Description                                   | Best For                                  |
| -------------------- | --------------------------------------------- | ----------------------------------------- |
| **academic-science** | Scientific rigor, understandable explanations | AI algorithms, fundamental science        |
| **academic-tech**    | Technical insights, developer-friendly        | Engineering, frameworks, tools            |
| **academic-trend**   | Future-focused, emphasizes innovation         | Emerging fields, breakthrough discoveries |
| **academic-applied** | Practical applications, real-world impact     | Industry applications, use cases          |

## 🔌 Integration

### With md2wechat
Seamless integration with [md2wechat](https://github.com/geekjourneyx/md2wechat-skill) for publishing:

```bash
# Generate markdown
paper2wechat https://arxiv.org/abs/2301.00000 --output outputs/article.md

# Then publish via md2wechat
bash md2wechat/scripts/run.sh convert outputs/article.md --draft --cover cover.jpg
```

## 📁 Output & Cache

By default, generated artifacts are saved in:

- `outputs/<paper-id>.md` - final markdown
- `.paper2wechat/downloads/` - downloaded Arxiv PDFs
- `.paper2wechat/parsed/` - parsed structured JSON
- `.paper2wechat/images/<paper-id>/` - extracted raw images from PDF
- `outputs/assets/<markdown-name>/` - images copied for markdown display

## 🛠️ Configuration

### Environment Variables

```bash
# For WeChat publishing (optional)
export WECHAT_APPID=your_appid
export WECHAT_SECRET=your_secret

# For image API (optional)
export IMAGE_API_KEY=your_key
export IMAGE_API_BASE=your_api_base

# For custom styles
export PAPER2WECHAT_STYLES_DIR=/path/to/custom/styles
```

### Config File

Create `~/.paper2wechat/config.yaml`:

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

## 📦 Project Structure

```
paper2wechat/
├── CLAUDE.md                         # Design document for AI
├── README.md                         # This file
├── QUICKSTART.md                     # Quick start guide
├── setup.py                          # Python package setup
├── requirements.txt                  # Dependencies
│
├── paper2wechat/
│   ├── __init__.py
│   └── core/                         # Core modules
│       ├── cli.py                    # CLI entrypoint
│       ├── paper_fetcher.py          # URL/PDF fetch + parse + image extraction
│       ├── content_adapter.py        # Adapt content for WeChat
│       ├── image_processor.py        # Rank/select/compress images
│       ├── converter.py              # End-to-end conversion pipeline
│       ├── models.py                 # Data models
│       └── markdown_generator.py     # Generate markdown
│
├── skills/                           # Claude Skill definition
│   └── paper2wechat/
│       ├── SKILL.md                 # Skill documentation
│       ├── references/
│       │   ├── academic-styles.md
│       │   ├── arxiv-guide.md
│       │   └── examples.md
│       └── scripts/
│           └── run.sh               # CLI wrapper
│
├── prompts/                          # Prompt templates
│   ├── arxiv_parser.md
│   ├── content_adapter.md
│   ├── academic_styles.md
│   └── image_selector.md
│
├── examples/                         # Usage examples
│   ├── sample-arxiv.txt
│   └── output-example.md
│
├── tests/                            # Tests
│   ├── test_paper_fetcher.py
│   ├── test_content_adapter.py
│   └── test_integration.py
│
└── docs/                             # Detailed documentation
    ├── ARCHITECTURE.md
    ├── API.md
    ├── STYLES.md
    └── INTEGRATION.md
```

## 🚀 Roadmap

### Phase 1 (MVP) ✓ In Progress
- [x] Support Arxiv URL fetching
- [x] Basic content extraction and adaptation
- [x] 1-2 default styles
- [x] Output as markdown
- [ ] md2wechat integration (depends on external repo/config)

### Phase 2 - Enhanced
- [x] Basic PDF image extraction and markdown insertion
- [ ] Smart image recognition and selection
- [ ] 5+ academic styles
- [ ] Table auto-detection
- [ ] Local PDF + web sources
- [ ] Batch processing

### Phase 3 - Advanced
- [ ] AI trace removal (humanizer)
- [ ] Auto cover generation
- [ ] Content analysis scoring
- [ ] Publishing schedule
- [ ] Style customization UI

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [md2wechat](https://github.com/geekjourneyx/md2wechat-skill) - Smart WeChat publishing
- [PDF Skill](https://github.com/anthropics/skills) - Robust PDF processing
- [pdfplumber](https://github.com/jsvine/pdfplumber) - Text extraction
- [Anthropic Claude](https://www.anthropic.com/) - AI powering the conversion

## 📧 Support

- Open an issue on GitHub
- Check existing [FAQ](docs/FAQ.md)
- Read [TROUBLESHOOTING](docs/TROUBLESHOOTING.md)

---

**Made with ❤️ for the academic community**
