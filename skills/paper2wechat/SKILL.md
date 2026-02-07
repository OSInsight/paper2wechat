---
name: paper2wechat
description: Convert Arxiv papers to WeChat Official Account articles with intelligent summarization, content adaptation, and image processing. Integrates with md2wechat for direct publishing.
metadata: {
  "emoji": "📄→📱",
  "homepage": "https://github.com/yourusername/paper2wechat",
  "requires": ["curl", "pdfimages"],
  "integrates": ["md2wechat", "pdf"],
  "primaryEnv": "WECHAT_APPID"
}
---

# Paper to WeChat

Convert academic papers from Arxiv to WeChat Official Account articles with intelligent content adaptation and multi-style support.

## Quick Start

```bash
# Convert Arxiv paper to markdown
bash skills/paper2wechat/scripts/run.sh convert https://arxiv.org/abs/2301.00000

# With custom style
bash skills/paper2wechat/scripts/run.sh convert https://arxiv.org/abs/2301.00000 --style academic-tech

# Preview HTML
bash skills/paper2wechat/scripts/run.sh convert https://arxiv.org/abs/2301.00000 --preview

# From local PDF
bash skills/paper2wechat/scripts/run.sh convert ./paper.pdf --style academic-science

# Upload to WeChat draft
bash skills/paper2wechat/scripts/run.sh convert https://arxiv.org/abs/2301.00000 --draft
```

## Features

### 1. Paper Fetching
- Direct Arxiv URL support (e.g., `https://arxiv.org/abs/2301.00000`)
- Local PDF file support
- Automatic metadata extraction (title, authors, date)
- Abstract and full content extraction

### 2. Smart Content Parsing
- Automatic section detection (Introduction, Methods, Results, Discussion, Conclusion)
- Key findings extraction
- Technical concepts identification
- Table and figure detection

### 3. Content Adaptation
- Intelligent summarization (academic 10,000+ words → 2000-5000 for WeChat)
- Language conversion (academic → accessible)
- Concept explanation with analogies
- Preserve scientific accuracy

### 4. Image Processing
- Auto-detect important figures from papers
- Intelligent selection (3-5 most relevant images)
- Image compression and format conversion
- WeChat-compatible sizing and formats

### 5. Multiple Styles
- **academic-science**: For fundamental research, emphasize scientific rigor
- **academic-tech**: For engineering/tools, practical insights
- **academic-trend**: For emerging fields, innovation focus
- **academic-applied**: For industry applications, real-world impact

### 6. WeChat Integration
- Direct publishing to WeChat drafts
- Cover image generation/upload
- Content size optimization
- One-click publishing via md2wechat

## Complete Workflow

### Step 1: Fetch Paper

```bash
bash skills/paper2wechat/scripts/run.sh fetch https://arxiv.org/abs/2301.00000
```

Extracts title, abstract, full text, and figure information.

### Step 2: Select Style

```bash
# Show available styles
bash skills/paper2wechat/scripts/run.sh styles

# Choose based on paper type:
# - AI theory papers → academic-science
# - Framework/tool papers → academic-tech
# - New field papers → academic-trend
# - Application papers → academic-applied
```

If the user does not specify a style, first recommend one based on paper content and ask for confirmation before proceeding.

### Step 3: Generate Content

```bash
bash skills/paper2wechat/scripts/run.sh adapt \
  https://arxiv.org/abs/2301.00000 \
  --style academic-tech \
  --images 5
```

Generates:
- Summarized content (2000-5000 words)
- Accessible language version
- Key figures extracted and positioned
- Optimized for WeChat reading

### Step 4: Generate Markdown

```bash
bash skills/paper2wechat/scripts/run.sh markdown \
  https://arxiv.org/abs/2301.00000 \
  --style academic-tech \
  --output article.md
```

Output: WeChat-compatible Markdown file.

### Step 5: Preview or Publish

```bash
# Preview in markdown
bash skills/paper2wechat/scripts/run.sh markdown \
  https://arxiv.org/abs/2301.00000 \
  --preview

# Or publish directly to WeChat
bash skills/paper2wechat/scripts/run.sh publish \
  https://arxiv.org/abs/2301.00000 \
  --draft \
  --cover-style auto
```

## Natural Language Usage

You can also interact with this skill in natural language:

### Generate Article from Paper

```
"Convert this Arxiv paper to a WeChat article: https://arxiv.org/abs/2301.00000"
"Turn this paper into a public-friendly article with technical style"
"Create a WeChat article from this academic paper, emphasizing practical applications"
```

I will:
1. Fetch and analyze the paper
2. Extract key content and figures
3. Recommend a style if none is specified (ask for confirmation by default)
4. Generate adapted markdown content
5. Provide preview and publishing options

### With Custom Requirements

```
"Generate a WeChat article from https://arxiv.org/abs/2301.00000 
with these requirements:
- Use academic-tech style
- Include 4 key figures
- Add a brief introduction about why this matters
- Keep content under 3000 words"
```

### Batch Processing

```
"Convert these 3 papers to WeChat articles:
1. https://arxiv.org/abs/2301.00000
2. https://arxiv.org/abs/2302.00000
3. https://arxiv.org/abs/2303.00000
All with academic-tech style."
```

## Configuration

### Required for WeChat Publishing

| Variable | Description |
|----------|-------------|
| `WECHAT_APPID` | WeChat Official Account AppID |
| `WECHAT_SECRET` | WeChat API Secret |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `PAPER2WECHAT_STYLE` | Default conversion style | academic-tech |
| `PAPER2WECHAT_IMAGES` | Default number of images | 5 |
| `PAPER2WECHAT_MAX_LENGTH` | Max content length (words) | 5000 |
| `IMAGE_API_KEY` | For image generation/processing | (optional) |
| `PAPER2WECHAT_AUTO_STYLE` | Auto-use recommended style without asking | false |

### Config File

Create `~/.paper2wechat/config.yaml`:

```yaml
wechat:
  appid: your_appid
  secret: your_secret

defaults:
  style: academic-tech
  max_images: 5
  max_length: 5000

image_processing:
  auto_compress: true
  max_width: 1920
```

## Examples

### Example 1: Simple Arxiv Conversion

**Input**:
```
Paper: https://arxiv.org/abs/2301.00000
Style: academic-tech
```

**Process**:
1. Fetch paper metadata and content
2. Extract 5 key figures
3. Summarize and adapt for WeChat
4. Apply academic-tech style
5. Generate markdown

**Output**: `article.md` (2000-5000 words, WeChat-ready)

### Example 2: PDF File with Custom Settings

**Input**:
```
File: ./research-paper.pdf
Style: academic-science
Images: 3
Output: science-article.md
```

**Process**:
1. Parse PDF (text + images)
2. Extract top 3 figures by relevance
3. Emphasize scientific rigor and precision
4. Generate adapted content

**Output**: `science-article.md`

### Example 3: Batch Processing

**Input**:
```
Papers:
- https://arxiv.org/abs/2301.00000
- https://arxiv.org/abs/2302.00000
- https://arxiv.org/abs/2303.00000
Style: academic-trend (all)
```

**Process**:
1. Convert all 3 papers in sequence
2. Emphasize innovation and future impact
3. Generate 3 markdown files
4. Provide summary report

**Output**:
```
✅ paper_2301.md (2345 words, 4 images)
✅ paper_2302.md (3124 words, 5 images)
✅ paper_2303.md (2876 words, 3 images)
```

## Integration with md2wechat

After converting, seamlessly publish via md2wechat:

```bash
# 1. Convert paper to markdown
paper2wechat https://arxiv.org/abs/2301.00000 --output article.md

# 2. Publish to WeChat (using md2wechat)
bash md2wechat/scripts/run.sh convert article.md --draft --cover cover.jpg
```

Or do it in one command:

```bash
paper2wechat https://arxiv.org/abs/2301.00000 --draft
```

## Troubleshooting

### "Failed to fetch paper"
- Check internet connection
- Verify Arxiv URL format (https://arxiv.org/abs/XXXX.XXXXX)
- Try with `--verbose` for detailed error

### "No images found"
- Some papers have only text
- Use `--images 0` to skip image processing
- Or manually add images later

### "WeChat upload failed"
- Check WECHAT_APPID and WECHAT_SECRET
- Verify account is verified (not blocked)
- Check content size (< 1MB)

### "Image processing failed"
- Try with fewer images (e.g., `--images 2`)
- Check if PDF has searchable images
- Update pdfimages: `brew install poppler` (macOS)

## Advanced Features

### Custom Prompts

Create custom adaptation prompts in `prompts/`:

```yaml
# prompts/my-style.yaml
name: my-custom-style
description: My custom adaptation style
system_prompt: |
  You are a content adapter for WeChat...
  [Your custom instructions]
```

Then use:
```bash
paper2wechat https://arxiv.org/abs/2301.00000 --style my-custom-style
```

### Post-Processing

Generated markdown can be further processed:

```python
from paper2wechat import Article

article = Article.from_markdown("article.md")

# Remove AI traces
article.humanize(intensity="medium")

# Extract quotes
quotes = article.extract_quotes()

# Generate cover prompt
cover_prompt = article.generate_cover_prompt()
```

## References

- [Academic Styles](references/academic-styles.md) - Detailed style definitions
- [Arxiv Guide](references/arxiv-guide.md) - How papers are processed
- [Examples](references/examples.md) - Full conversion examples
- [API Reference](../../docs/API.md) - Complete Python API

---

## Statistics

This skill can convert:
- ✅ Any Arxiv paper (millions available)
- ✅ Local PDF files (any academic paper)
- ✅ Typical conversion time: 30-60 seconds per paper
- ✅ Output: WeChat-compatible markdown (ready to publish)

**Happy converting! 📄➡️📱**
