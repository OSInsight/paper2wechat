# Quick Start Guide ⚡

Get up and running with paper2wechat in 5 minutes!

## 1. Install

```bash
# Clone the repository
git clone https://github.com/yourusername/paper2wechat.git
cd paper2wechat

# Install in development mode
pip install -e .
```

## 2. First Conversion

### Option A: CLI (Simplest)

```bash
# Convert an Arxiv paper to markdown
paper2wechat https://arxiv.org/abs/2301.00000

# Default output file: outputs/2301.00000.md
```

### Option B: Python Script

```python
from paper2wechat import PaperConverter

converter = PaperConverter()
article = converter.convert("https://arxiv.org/abs/2301.00000")
article.save_markdown("article.md")

print("✅ Article saved to article.md")
print(f"📊 Length: {article.word_count} words")
print(f"🖼️  Images: {len(article.images)}")
```

## 3. Preview Your Article

```bash
# In terminal
paper2wechat https://arxiv.org/abs/2301.00000 --preview

# Or check the generated markdown file
cat outputs/2301.00000.md
```

## 4. Publish to WeChat (Optional)

### Step 1: Configure WeChat

Get your AppID and Secret from [WeChat Developer Platform](https://developers.weixin.qq.com/):

```bash
# Set environment variables
export WECHAT_APPID=your_appid_here
export WECHAT_SECRET=your_secret_here
```

### Step 2: Upload to Draft

```bash
# Using paper2wechat
paper2wechat https://arxiv.org/abs/2301.00000 \
  --output article.md \
  --draft

# Or using md2wechat
bash md2wechat/scripts/run.sh convert article.md --draft --cover cover.jpg
```

## Different Styles

Try different writing styles:

```bash
# Academic-tech style (default)
paper2wechat https://arxiv.org/abs/2301.00000 --style academic-tech

# Scientific style - for fundamental research
paper2wechat https://arxiv.org/abs/2301.00000 --style academic-science

# Trend style - emphasize innovation
paper2wechat https://arxiv.org/abs/2301.00000 --style academic-trend

# Applied style - focus on real-world impact
paper2wechat https://arxiv.org/abs/2301.00000 --style academic-applied
```

## Local PDF Files

```bash
# From a local PDF
paper2wechat ./my-paper.pdf --style academic-tech

# With specific number of images
paper2wechat ./my-paper.pdf --images 3
```

## Batch Processing

```python
from paper2wechat import PaperConverter

converter = PaperConverter(style="academic-tech")

papers = [
    "https://arxiv.org/abs/2301.00000",
    "https://arxiv.org/abs/2302.00000",
    "https://arxiv.org/abs/2303.00000",
]

for i, paper_url in enumerate(papers):
    article = converter.convert(paper_url)
    article.save_markdown(f"paper_{i}.md")
    print(f"✅ Converted {paper_url}")
```

## Common Issues

**Q: "Command not found: paper2wechat"**  
A: Make sure you installed with `pip install -e .` in the project directory.

**Q: "Failed to fetch paper"**  
A: Check your internet connection and verify the Arxiv URL is correct (https://arxiv.org/abs/XXXX.XXXXX).

**Q: "WeChat upload failed"**  
A: Check your WECHAT_APPID and WECHAT_SECRET are set correctly.

**Q: "Images not showing"**  
A: Some papers have images that can't be extracted. Use `--images 0` to skip images.

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for more help.

## Next Steps

- 📚 Read [docs/STYLES.md](docs/STYLES.md) to understand different styles
- 🔌 Check [docs/INTEGRATION.md](docs/INTEGRATION.md) for advanced integration
- 💻 See [examples/](examples/) for sample code
- 🎓 Visit [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for technical details

## 💡 Tips

1. **Test first**: Use `--preview` flag to check output before publishing
2. **Choose style carefully**: Different styles work better for different paper types
3. **Customize content**: The generated markdown is just a start - feel free to edit it
4. **Add cover**: Manually provide a cover image with `--cover image.jpg`
5. **Check length**: Very long papers may need manual editing due to WeChat limits

---

**Ready to convert your first paper? Let's go!** 🚀
