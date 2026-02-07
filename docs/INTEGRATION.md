# Integration Guide

This guide explains how paper2wechat integrates with other tools and systems.

## Integration with md2wechat

Paper2wechat is designed to work seamlessly with [md2wechat](https://github.com/geekjourneyx/md2wechat-skill).

### Workflow

```
paper2wechat                    md2wechat
   Input                     Input
    ↓                         ↓
Arxiv Paper         Markdown File
    ↓                         ↓
Content Parsing     HTML Generation
    ↓                         ↓
Adaptation          Style Application  
    ↓                         ↓
Markdown Output     WeChat Article
         \                  /
          \────────────────/
                  ↓
           WeChat Official Account
             (Draft/Publish)
```

### Step 1: Generate Markdown with paper2wechat

```bash
paper2wechat https://arxiv.org/abs/2301.00000 \
  --style academic-tech \
  --images 5 \
  --output article.md
```

### Step 2: Publish with md2wechat

```bash
bash md2wechat/scripts/run.sh convert article.md \
  --draft \
  --cover cover.jpg
```

Or do it in one command:

```bash
paper2wechat https://arxiv.org/abs/2301.00000 \
  --draft \
  --md2wechat-args="--cover cover.jpg"
```

### Output Flow

```
Paper → paper2wechat → Markdown
                           ↓
                      md2wechat
                           ↓
                      HTML + CSS
                           ↓
                      Image Upload
                           ↓
                      Draft/Publish
```

## Integration with PDF Skill

Paper2wechat uses Anthropic's PDF Skill for local PDF processing.

### Libraries Used

- **pdfplumber**: Text extraction with layout preservation
- **pypdf**: Metadata extraction
- **pdfimages** (poppler): Image extraction

### Custom Integration

If you want to provide custom PDF processing:

```python
from paper2wechat import PaperConverter
from paper2wechat.core.paper_fetcher import PaperFetcher

# Create custom fetcher
class CustomFetcher(PaperFetcher):
    def fetch_from_pdf(self, pdf_path):
        # Your custom PDF processing
        paper = self._your_custom_logic(pdf_path)
        return paper

# Use custom fetcher
converter = PaperConverter()
converter.fetcher = CustomFetcher()
article = converter.convert_pdf("paper.pdf")
```

## Integration with Claude API

Paper2wechat uses anth ropic's Claude API for content adaptation.

### Configuration

```bash
export ANTHROPIC_API_KEY=sk-...
```

Or in config file:

```yaml
# ~/.paper2wechat/config.yaml
claude:
  api_key: sk-...
  model: claude-3-sonnet-20240229
```

### Custom Prompts

You can provide custom Claude prompts:

```python
from paper2wechat import PaperConverter

converter = PaperConverter()
converter.adapter.set_custom_prompt(
    system_prompt="Your custom system prompt...",
    user_template="Your custom user template..."
)
```

## Integration with Custom Image APIs

If you want to use a custom image processing service:

```python
from paper2wechat.core.image_processor import ImageProcessor

class CustomImageProcessor(ImageProcessor):
    def compress_image(self, image_path, output_path, max_width=1920):
        # Your custom image processing
        pass

# Use custom processor
converter = PaperConverter()
converter.image_processor = CustomImageProcessor()
```

## API Server Integration

Example of integrating paper2wechat into a web service:

```python
from flask import Flask, request, jsonify
from paper2wechat import PaperConverter

app = Flask(__name__)
converter = PaperConverter(style="academic-tech")

@app.route("/convert", methods=["POST"])
def convert_paper():
    """API endpoint to convert paper"""
    data = request.json
    url = data.get("url")
    style = data.get("style", "academic-tech")
    
    try:
        converter.set_style(style)
        article = converter.convert(url)
        return jsonify({
            "title": article.title,
            "word_count": article.word_count,
            "markdown": article.to_markdown()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=False, port=5000)
```

## Command-line Integration

Use in shell scripts:

```bash
#!/bin/bash

# Convert multiple papers
for url in \
  "https://arxiv.org/abs/2301.00000" \
  "https://arxiv.org/abs/2302.00000" \
  "https://arxiv.org/abs/2303.00000"
do
  paper2wechat "$url" \
    --style academic-tech \
    --output "$(basename ${url##*/}).md"
done

# Publish all
for md_file in *.md; do
  bash md2wechat/scripts/run.sh convert "$md_file" --draft
done
```

## GitHub Actions Integration

Automated paper conversion in CI/CD:

```yaml
# .github/workflows/convert-papers.yml
name: Convert Papers

on:
  push:
    paths:
      - 'papers.txt'

jobs:
  convert:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      
      - name: Install dependencies
        run: |
          pip install -e .
      
      - name: Convert papers
        env:
          WECHAT_APPID: ${{ secrets.WECHAT_APPID }}
          WECHAT_SECRET: ${{ secrets.WECHAT_SECRET }}
        run: |
          # Read papers from papers.txt and convert each
          while IFS= read -r url; do
            paper2wechat "$url" --draft
          done < papers.txt
```

## Python Package Integration

Installing paper2wechat as a dependency:

```python
# requirements.txt
paper2wechat>=0.1.0

# setup.py
install_requires=[
    "paper2wechat>=0.1.0",
]
```

Then in your code:

```python
from paper2wechat import PaperConverter, Article

def my_paper_processing_function(arxiv_url):
    converter = PaperConverter(style="academic-tech")
    article = converter.convert(arxiv_url)
    return article
```

---

See [CLAUDE.md](../CLAUDE.md) for architecture decisions.
