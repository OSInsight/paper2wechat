---
name: paper2wechat
description: Convert Arxiv papers to WeChat Official Account articles. Extracts paper content and images, then rewrites for WeChat audience using multiple academic styles (science, tech, trend, applied).
metadata: {"openclaw": {"emoji": "📄", "homepage": "https://github.com/OSInsight/paper2wechat"}}
---

# Paper to WeChat

Converts Arxiv academic papers into WeChat Official Account articles optimized for public engagement.

## How It Works

This is a **hybrid approach**: I use paper2wechat tools to extract and parse the paper, then use my own writing capabilities to create an engaging article.

## Part 1: Fetch and Parse the Paper

You will be given an Arxiv URL, Arxiv ID, or local PDF file. For example:

```
https://arxiv.org/abs/2510.21603
2510.21603
./paper.pdf
convert this paper to WeChat: https://arxiv.org/abs/2301.00000
```

### Step 1a: Normalize the input

Extract and validate:
- **Arxiv URL** → Extract the ID (e.g., `2510.21603`)
- **Arxiv ID** → Already have it (e.g., `2510.21603`)
- **Local PDF** → Get the file path (e.g., `./paper.pdf`)

### Step 1b: Run the fetch tool

From the project root, run:

```bash
python -m paper2wechat.core.fetch_cli <url_or_id_or_path> --verbose
```

Parameters:
- `<url_or_id_or_path>` - Arxiv URL, Arxiv ID, or local PDF path
- `--cache-dir .paper2wechat` - Cache directory (default)
- `--verbose` - Show detailed progress

This will:
- Download the paper from Arxiv (if needed and not cached)
- Extract text, structure, title, authors, abstract, sections
- Parse images and figures from PDF
- Save parsed data to `.paper2wechat/parsed/{paper_id}.json`
- Save images to `.paper2wechat/images/{paper_id}/`

**Example output:**
```
Parsed cache: .paper2wechat/parsed/2510_21603.json
Images dir: .paper2wechat/images/2510_21603
```

### Step 1c: Verify the tool's output

Check files were created:
```bash
ls .paper2wechat/parsed/*.json
ls .paper2wechat/images/*/
```

Read the JSON to verify:
```bash
cat .paper2wechat/parsed/2510_21603.json | head -50
```

Content should include:
- `title` - Paper title
- `authors` - Author names
- `abstract` - Paper abstract
- `sections` - Array of sections with content
- `images` - Array of image metadata (url, caption, relevance_score)

---

## Part 2: Understand User Intent

Extract from the user's original request:

| Parameter | How to Extract | Default |
|-----------|---|---|
| **Style** | Keywords: "science/scientific" → academic-science, "tech/engineering" → academic-tech, "trend/future" → academic-trend, "applied/practical" → academic-applied | academic-tech |
| **Length** | Keywords: "concise/brief/short", "under XXXX chars", or number range | 5000 characters |
| **Focus** | Keywords: "methodology", "results", "applications", "innovation" | Balanced from abstract & intro |

---

## Part 3: Read and Analyze the Paper

### Step 3a: Load the JSON

Read `.paper2wechat/parsed/{paper_id}.json` to access structured data:

```json
{
  "title": "...",
  "authors": [...],
  "abstract": "...",
  "sections": [
    {
      "title": "Introduction",
      "content": "...",
      "level": 1
    },
    ...
  ],
  "images": [
    {
      "url": ".paper2wechat/images/2510_21603/...",
      "caption": "Fig 1: ..."
    },
    ...
  ]
}
```

### Step 3b: Understand the paper deeply

Read through and analyze:
- **Problem** - What challenge does this address?
- **Novelty** - What's genuinely new?
- **Method** - How do they approach it?
- **Results** - Key findings and metrics
- **Impact** - Who benefits? Real-world applications?
- **Limitations** - Acknowledged gaps or constraints
- **GitHub/Code** - Search for GitHub links in:
  - Abstract or introduction (common patterns: "code available at", "github.com/", "open-source")
  - End of paper ("Code Availability" section)
  - Footnotes and references
  - Author homepages mentioned in the paper

Pay special attention to images - they often reveal key insights.

---

## Part 4: Write the WeChat Article

Now use my own writing capabilities to transform this content.

### Style Guidelines

**IMPORTANT**: Do NOT add any auto-generated disclaimers or tool credits at the end (e.g., “本文由Paper2WeChat自动生成”).

| Style | Perspective | Tone | Examples |
|-------|---|---|---|
| **academic-science** | Rigorous methodology, scientific validity | Careful, structured, evidence-focused | "这项研究采用严谨的科学方法..." |
| **academic-tech** | Practical applications, engineering solutions | Tech-savvy, forward-looking, actionable | "这个框架解决了工程师们的难题..." |
| **academic-trend** | Emerging paradigm, market impact | Exciting, future-focused, visionary | "这标志着该领域的重大突破..." |
| **academic-applied** | Real-world usage, business value | Results-driven, practical, ROI-focused | "实际应用中能带来..." |

### Article Structure

```
# [Engaging Title - Mix Academic Rigor with Accessibility]

> 📋 **论文信息**
> - **标题**: [Full Title]
> - **作者**: [Names]
> - **单位**: [Institution(s)]
> - **发表时间**: [Date/Year]
> - **论文链接**: [Arxiv link]
> - **开源代码**: [GitHub link] (如果论文开源，否则省略此行)

## 导读 👁️

[2-3 sentences: Why readers should care - personal benefit or industry impact]

## 核心观点 💡

[3-5 key insights, clearly organized:]
- Main finding
- Key innovation
- Practical value
- Limitation or caveat
- Future direction

## [Section 2: Methodology/Approach] 🔧

[Explain the approach in accessible language]
[Use analogies for complex concepts]
[Connect to existing knowledge]

[Image reference if available]

## [Section 3: Results/Impact] 📊

[Present findings with specific metrics]
[What does the data show?]
[How does it compare to alternatives?]

[Image reference if available]

## 启示与应用 🚀

[Real-world implications]
[Who benefits and how?]
[Potential industry applications]
[What readers can do with this knowledge]

## 扩展阅读 📚

**IMPORTANT**: Do NOT repeat the paper link or basic info here (already in top section)
Only include:
- Related research systems or products (with brief descriptions)
- Relevant academic works (authors, year, key contribution)
- Code/datasets if different from main paper
- Further reading for interested readers

Example:
- [Related System Name](url) - Brief description
- Author et al. (Year) - Key contribution

**关键词**: #话题1 #话题2 #话题3
```

### Writing Principles

1. **Accuracy first** - Never sacrifice correctness for simplicity
2. **Bridge the gap** - Explain jargon through analogy and example
3. **Tell a story** - Hook → Problem → Solution → Impact
4. **Scannable** - Use headings, bullets, and clear structure
5. **Engaging** - Open with relevance; close with takeaway
6. **Connected** - Link to reader's world and experience

### Keyword Requirement

- Always include a **关键词** line using hashtag format at the end of the article.
- Default to 5-8 tags summarizing topic, method, and application area.

**Translation example:**
- "Attention mechanisms" → "模型能够像人一样阅读，自动关注重要信息，忽略干扰"
- "Gradient descent" → "逐步调整参数，像爬山人寻找最低点"

---

## Part 5: Create the Output File

Save the generated article as Markdown:

```bash
outputs/{paper_id}.md
```

The file should start with:

```markdown
---
title: [Title]
authors: [Authors]
arxiv_id: [ID]
style: [academic-science|academic-tech|academic-trend|academic-applied]
---

# [Title in Chinese]
...
```

---

## Example Workflow

### Example 1: Simple Request

**User:** "Convert this paper to a WeChat article: https://arxiv.org/abs/2301.00000"

**Steps:**
1. ✅ Run: `python -m paper2wechat.core.fetch_cli https://arxiv.org/abs/2301.00000 --verbose`
2. ✅ Read: `.paper2wechat/parsed/2301_00000.json`
3. ✅ Intent: Default style (academic-tech), 5000 chars
4. ✅ Analyze: Understand the paper from JSON
5. ✅ Write: Article in academic-tech style
6. ✅ Save: `outputs/2301.00000.md`

**Output:**
```
✅ Article: outputs/2301.00000.md
📊 Stats: ~4500 chars, 3 images referenced
🔗 Original: https://arxiv.org/abs/2301.00000
```

---

### Example 2: Custom Style and Length

**User:** "Turn this PDF into an applied research article, keep it under 3000 chars: paper.pdf"

**Steps:**
1. ✅ Run: `python -m paper2wechat.core.fetch_cli ./paper.pdf --verbose`
2. ✅ Read parsed JSON
3. ✅ Intent: academic-applied, 3000 chars max
4. ✅ Analyze with focus on applications
5. ✅ Write: Concise, practical-oriented article
6. ✅ Save: `outputs/[stem].md`

---

### Example 3: Emphasize Methodology

**User:** "Convert with academic-science style, focus on methodology details"

**Steps:**
1. ✅ Extract and parse
2. ✅ Intent: academic-science, detailed (~6000 chars)
3. ✅ Pay close attention to Methods section
4. ✅ Write: Article highlighting methodological rigor
5. ✅ Save: `outputs/[id].md`

---

## Checklist

As you work:

```
Progress:
- [ ] Step 1: Run fetch_cli with correct input
- [ ] Step 1: Verify JSON and images created
- [ ] Step 2: Extract user intent (style, length, focus)
- [ ] Step 3: Load and read parsed JSON  
- [ ] Step 3: Understand core contributions and real-world impact
- [ ] Step 4: Write article in selected style
- [ ] Step 4: Follow structure and writing principles
- [ ] Step 4: Reference extracted images naturally
- [ ] Step 4: Add **关键词** line at the end
- [ ] Step 5: Save to outputs/ with proper naming
- [ ] Step 5: Report results to user
```

---

## Important Notes

1. **Tool success** - fetch_cli should complete without errors. If it fails:
   - Check URL format: `https://arxiv.org/abs/YYMM.NNNNN`
   - For PDFs, ensure file is readable
   - Check network for Arxiv access

2. **Image handling** - Extracted images are stored locally with captions. Reference them this way:
   ```
  ![Figure description](../.paper2wechat/images/{paper_id}/page_XXX_YYY.png)
   ```
  - Because the article is saved under outputs/, image links must be relative to outputs/.
  - Use ../.paper2wechat/... (not .paper2wechat/...) so Markdown renders correctly.

3. **Quality depends on:**
   - Deep understanding of paper (Part 3)
   - Appropriate style choice (Part 2)
   - Clear structure and flow (Part 4)
   - Balance: accuracy > simplicity

4. **Always verify** - The JSON output should have:
   - Non-empty title and abstract
   - At least 2-3 sections
   - Images extracted (usually 3+ for CS papers)

---

## Tips for Best Results

1. **Read the abstract first** - Get the big picture
2. **Study the figures** - Visual layouts reveal key insights
3. **Identify the core novelty** - What's genuinely new?
4. **Know your audience** - Academic? Business? General interest?
5. **Use specific numbers** - Include metrics and results
6. **Structure matters** - Clear headings and flow
7. **Hook readers** - First paragraph should explain why they should read
