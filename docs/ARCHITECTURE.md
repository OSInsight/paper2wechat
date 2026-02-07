# Project Architecture

## Overview

Paper2WeChat converts academic papers into WeChat-compatible articles through a modular pipeline:

```
Paper Source (URL/PDF)
        ↓
    [Fetcher]
        ↓
    [Parser]
        ↓
[Image Processor] ← Content Analyzer
        ↓
[Content Adapter]
        ↓
  [Style Engine]
        ↓
[Markdown Generator]
        ↓
   Markdown Output
        ↓
   [md2wechat]
        ↓
  WeChat Article
```

## Core Modules

### 1. PaperFetcher (`core/paper_fetcher.py`)

**Responsibility**: Extract content from paper sources

**Inputs**: URL or file path  
**Outputs**: Paper object with metadata and content

**Key Methods**:
- `fetch_from_url(url)` - Get Arxiv paper via URL
- `fetch_from_pdf(pdf_path)` - Parse local PDF
- `parse_arxiv_url(url)` - Extract paper ID from URL

**Implementation Details**:
- Uses Arxiv API for metadata
- Uses PDF Skill for PDF processing (pdfplumber + pypdf)
- Extracts: title, authors, abstract, full text, figures, tables

**Error Handling**:
- Network errors (retry logic)
- Invalid URLs (validation)
- PDF parsing errors (fallback to text)

---

### 2. PaperParser (`core/models.py`)

**Responsibility**: Structure and represent paper data

**Key Classes**:
```
Paper
├── title: str
├── authors: List[str]
├── abstract: str
├── sections: List[Section]
└── images: List[ImageInfo]

Section
├── title: str
├── content: str
├── level: int
└── images: List[ImageInfo]

ImageInfo
├── url: str
├── caption: str
├── position: int
└── relevance_score: float
```

**Purpose**: Normalized representation of paper structure for downstream processing

---

### 3. ImageProcessor (`core/image_processor.py`)

**Responsibility**: Extract, evaluate, and prepare images

**Inputs**: List of images, article content  
**Outputs**: List of selected, relevant images

**Pipeline**:
1. **Extract**: Get all images from paper
2. **Evaluate**: Calculate relevance to content
3. **Select**: Choose top N by relevance + position
4. **Prepare**: Compress and format for WeChat

**Integration Points**:
- Consumes image processing skills (if available)
- Coordinates with ContentAdapter for relevance matching
- Uploads to WeChat via subprocess calls

---

### 4. ContentAdapter (`core/content_adapter.py`)

**Responsibility**: Convert academic content to accessible format

**Inputs**: Academic text, style, max length  
**Outputs**: Adapted, summary-level content

**Process**:
1. **Summarize**: Extract key points (academic 10k → 2-5k words)
2. **Simplify**: Technical → accessible language
3. **Structure**: Add subheadings, breaks, transitions
4. **Enhance**: Add context, explanations, examples
5. **Style**: Apply selected style rules

**Key Decisions**:
- Always preserves scientific accuracy
- Uses Claude API for content transformation
- Respects word count limits for WeChat

**Prompt Engineering**:
- System prompt includes style guide
- Few-shot examples in prompts/
- Context includes original abstract

---

### 5. MarkdownGenerator (`core/markdown_generator.py`)

**Responsibility**: Format adapted content as markdown

**Inputs**: Article object  
**Outputs**: WeChat-compatible markdown

**Features**:
- Proper markdown syntax
- Image placeholder syntax
- Heading hierarchy
- Code block support
- Quote/emphasis formatting

**Output Format**:
```markdown
# Title

> Summary

## Section 1
Content...

## Section 2
Content...

## Figures
![Description](url)
```

---

### 6. Converter (`core/converter.py`)

**Responsibility**: Orchestrate the entire pipeline

**Public API**:
```python
converter = PaperConverter(style="academic-tech")

# From URL
article = converter.convert("https://arxiv.org/abs/...")

# From PDF
article = converter.convert_pdf("./paper.pdf")

# To file
article.save_markdown("output.md")

# To WeChat
converter.upload_to_wechat(article, draft=True)
```

**Pipeline Orchestration**:
- Calls each module in correct order
- Handles errors gracefully
- Reports progress (verbose mode)
- Measures processing time

---

## Data Flow

### Request Flow

```
CLI Input
  ↓
PaperConverter.convert()
  ├→ PaperFetcher.fetch_from_url()
  │    └→returns Paper
  ├→ ContentAdapter.adapt()
  │    └→returns adapted_content
  ├→ ImageProcessor.select_images()
  │    └→returns List[ImageInfo]
  ├→ Article.__init__()
  ├→ MarkdownGenerator.generate()
  └→ returns Article
```

### Data Structures

**Paper** (Raw Content):
- Large, unstructured
- Contains full text, may have raw formatting
- Includes all available metadata

**Article** (Processed Content):
- Adapted length (2000-5000 words)
- Clean structure with sections
- Selected images with relevance scores
- Ready for publishing

---

## Configuration & Extensibility

### Styles

**Location**: `prompts/academic_styles.md`

**Structure**:
```
academic-science:
  description: "Scientific rigor..."
  system_prompt: "You are a translator of science..."
  tone_examples: [...]

academic-tech:
  description: "Technical insights..."
  ...
```

**How to Add Style**:
1. Add entry to `prompts/academic_styles.md`
2. Update `PaperConverter.list_styles()`
3. Test with sample papers

### Custom Prompts

Users can provide custom adaptation prompts:
```python
converter.set_custom_prompt(
    style_name="my-style",
    system_prompt="Your instructions...",
)
```

---

## Error Handling Strategy

```
FetchError
├── NetworkError → Retry with backoff
├── URLError → Return helpful message
└── PDFError → Try alternative extraction

AdaptationError
├── APIError → Retry Claude call
├── TimeoutError → Return partial content
└── ValidationError → Fall back to raw summary

PublishError
├── AuthError → Guide user to config
├── UploadError → Save locally, suggest manual upload
└── SizeLimitError → Suggest truncation
```

---

## Performance Characteristics

| Operation   | Time       | Notes                    |
| ----------- | ---------- | ------------------------ |
| Fetch (URL) | 3-5s       | Arxiv API + PDF download |
| Fetch (PDF) | 1-2s       | Local file parsing       |
| Adapt       | 10-30s     | Claude API call          |
| Images      | 2-5s       | Download + compress      |
| Generate    | <1s        | Markdown templating      |
| **Total**   | **20-40s** | Per paper                |

---

## Integration Points

### With md2wechat
- Calls `bash md2wechat/scripts/run.sh convert` for publishing
- Outputs WeChat-compatible markdown
- Reuses style system (where applicable)

### With PDF Skill
- Uses `pdfplumber` for text extraction
- Uses `pypdf` for metadata
- Uses `pdfimages` tool for image extraction

### With Anthropic Claude
- Main AI backbone for adaptation
- Uses `anthropic>=0.7.0` SDK
- Streaming support for long responses

---

## Testing Strategy

```
Unit Tests:
- paper_fetcher: Mock Arxiv API, validate parsing
- content_adapter: Test summarization with fixtures
- image_processor: Validate ranking algorithm
- markdown_generator: Compare output format

Integration Tests:
- End-to-end: Sample paper URL → final article
- PDF mode: Sample PDF → final article
- Style variations: Same paper, different styles

Fixture Data:
- Sample Arxiv papers
- Sample PDFs
- Expected outputs for regression testing
```

---

## Future Architecture Changes

### Phase 2
- Move to async/await for parallel processing
- Add LRU cache for fetched papers
- Implement streaming responses for large documents

### Phase 3
- Plugin system for custom processors
- API server for web integration
- Database for caching/history

---

See [CLAUDE.md](../CLAUDE.md) for design rationale.
