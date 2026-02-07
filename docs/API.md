# Python API Reference

This document provides a complete reference for the paper2wechat Python API.

## Main Classes

### PaperConverter

Main class for converting papers.

```python
from paper2wechat import PaperConverter

converter = PaperConverter(
    style="academic-tech",  # Default style
    max_images=5,           # Max images to include
    max_length=5000,        # Max content length (words)
)
```

**Methods**:

#### `convert(url: str, output_path: Optional[str] = None) -> Article`

Convert paper from Arxiv URL.

```python
article = converter.convert("https://arxiv.org/abs/2301.00000")

# With output path
article = converter.convert(
    "https://arxiv.org/abs/2301.00000",
    output_path="article.md"
)
```

#### `convert_pdf(pdf_path: str, output_path: Optional[str] = None) -> Article`

Convert paper from local PDF.

```python
article = converter.convert_pdf("./my-paper.pdf")
```

#### `set_style(style: str) -> None`

Change conversion style.

```python
converter.set_style("academic-science")
```

#### `list_styles() -> List[str]`

Get available styles.

```python
styles = PaperConverter.list_styles()
# ['academic-science', 'academic-tech', 'academic-trend', 'academic-applied']
```

---

### Article

Converted article object.

```python
from paper2wechat import Article

# Create article (usually via PaperConverter)
article: Article = converter.convert("...")
```

**Attributes**:

- `title: str` - Article title
- `content: str` - Main content
- `style: str` - Conversion style used
- `word_count: int` - Content length
- `images: List[ImageInfo]` - Selected images
- `summary: Optional[str]` - Brief summary
- `tags: List[str]` - Topic tags
- `generated_at: datetime` - Generation timestamp

**Methods**:

#### `preview(max_length: int = 500) -> str`

Get preview of content.

```python
preview = article.preview(max_length=200)
print(preview)  # First 200 chars of content
```

#### `to_markdown() -> str`

Convert to markdown string.

```python
markdown_text = article.to_markdown()
```

#### `save_markdown(filepath: str) -> None`

Save as markdown file.

```python
article.save_markdown("output.md")
```

#### `from_markdown(filepath: str, style: str) -> Article`

Load article from markdown (class method).

```python
article = Article.from_markdown("article.md", style="academic-tech")
```

---

### Paper

Original paper data.

```python
from paper2wechat import Paper

paper: Paper  # Returned from PaperFetcher
```

**Attributes**:

- `title: str` - Paper title
- `authors: List[str]` - Author list
- `abstract: str` - Paper abstract
- `sections: List[Section]` - Paper sections
- `images: List[ImageInfo]` - All available images
- `arxiv_id: Optional[str]` - Arxiv ID
- `url: Optional[str]` - Source URL

**Methods**:

#### `full_text: str` (property)

Get complete concatenated text.

```python
full = paper.full_text  # All sections concatenated
```

---

### Section

A section of a paper.

```python
from paper2wechat import Section

section: Section
```

**Attributes**:

- `title: str` - Section title
- `content: str` - Section content
- `level: int` - Heading level (1-6)
- `images: List[ImageInfo]` - Images in section

---

### ImageInfo

Information about an image.

```python
from paper2wechat import ImageInfo

image: ImageInfo
```

**Attributes**:

- `url: str` - Image URL
- `caption: str` - Image caption/title
- `position: int` - Position in document
- `relevance_score: float` - Relevance to content (0-1)
- `is_selected: bool` - Whether selected for output

---

## Usage Examples

### Basic Conversion

```python
from paper2wechat import PaperConverter

converter = PaperConverter()

# Convert from URL
article = converter.convert("https://arxiv.org/abs/2301.00000")

# Save to markdown
article.save_markdown("output.md")

# Print info
print(f"Title: {article.title}")
print(f"Words: {article.word_count}")
print(f"Images: {len(article.images)}")
```

### Custom Style

```python
converter = PaperConverter(style="academic-science")

article = converter.convert("https://arxiv.org/abs/2301.00000")
```

### Batch Processing

```python
papers = [
    "https://arxiv.org/abs/2301.00000",
    "https://arxiv.org/abs/2302.00000",
    "https://arxiv.org/abs/2303.00000",
]

for i, url in enumerate(papers):
    article = converter.convert(url)
    article.save_markdown(f"paper_{i}.md")
    print(f"✅ Converted {url}")
```

### PDF Conversion

```python
converter = PaperConverter(style="academic-tech", max_images=4)

article = converter.convert_pdf("./research.pdf")
article.save_markdown("research-article.md")
```

### Access Metadata

```python
article = converter.convert("...")

# Access original paper
paper = article.original_paper

# Get all information
print(f"Authors: {', '.join(paper.authors)}")
print(f"Abstract: {paper.abstract}")

# Access images
for image in article.images:
    print(f"  - {image.caption} (relevance: {image.relevance_score:.2f})")
```

### Modify and Re-save

```python
article = Article.from_markdown("article.md")

# Modify content
article.title = "New Title"
article.tags = ["AI", "Machine Learning"]

# Save updated version
article.save_markdown("article-updated.md")
```

---

## Error Handling

```python
from paper2wechat import PaperConverter
from paper2wechat.core.paper_fetcher import FetchError

converter = PaperConverter()

try:
    article = converter.convert("https://arxiv.org/abs/2301.00000")
except FetchError as e:
    print(f"Failed to fetch paper: {e}")
except Exception as e:
    print(f"Conversion error: {e}")
```

---

## Advanced Usage

### Custom Configuration

```python
converter = PaperConverter(
    style="academic-tech",
    max_images=7,
    max_length=6000  # Longer articles
)
```

### Check Available Styles

```python
available_styles = PaperConverter.list_styles()

for style in available_styles:
    converter.set_style(style)
    article = converter.convert("...")
    print(f"{style}: {article.word_count} words")
```

### Integration with md2wechat

```python
from paper2wechat import PaperConverter
import subprocess

# Generate article
converter = PaperConverter()
article = converter.convert("https://arxiv.org/abs/...")
article.save_markdown("temp.md")

# Publish with md2wechat
subprocess.run([
    "bash", "md2wechat/scripts/run.sh", "convert",
    "temp.md", "--draft"
])
```

---

## Type Hints

All functions are fully type-hinted:

```python
from typing import List, Optional
from paper2wechat import PaperConverter, Article

def process_papers(urls: List[str], style: str = "academic-tech") -> List[Article]:
    converter = PaperConverter(style=style)
    articles: List[Article] = []
    
    for url in urls:
        try:
            article: Article = converter.convert(url)
            articles.append(article)
        except Exception as e:
            print(f"Error processing {url}: {e}")
    
    return articles
```

---

See [ARCHITECTURE.md](ARCHITECTURE.md) for implementation details.
