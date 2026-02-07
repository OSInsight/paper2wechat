# FAQ - Frequently Asked Questions

## Installation & Setup

**Q: How do I install paper2wechat?**

A: Clone the repository and install:
```bash
git clone https://github.com/yourusername/paper2wechat.git
cd paper2wechat
pip install -e .
```

**Q: What Python version is required?**

A: Python 3.8 or higher.

## Usage

**Q: Can I use my own Arxiv papers?**

A: Yes! paper2wechat works with any publicly available Arxiv paper. Just provide the URL.

**Q: Does it work with PDFs I already have?**

A: Yes, use the `--pdf` flag to process local PDF files.

**Q: How long does conversion take?**

A: Typically 20-40 seconds per paper (depends on paper length and API response time).

## Styles

**Q: Which style should I choose?**

A: Depends on your paper:
- **academic-science**: Fundamental research, math-heavy papers
- **academic-tech**: Tools, frameworks, engineering papers
- **academic-trend**: Emerging fields, breakthrough research
- **academic-applied**: Industry applications, practical use cases

**Q: Can I create custom styles?**

A: Yes! See [docs/STYLES.md](../docs/STYLES.md) for how to extend styles.

## Publishing

**Q: How do I publish to WeChat?**

A: Use the `--draft` flag:
```bash
paper2wechat https://arxiv.org/abs/2301.00000 --draft
```

Or manually use md2wechat:
```bash
paper2wechat ... --output article.md
bash md2wechat/scripts/run.sh convert article.md --draft
```

**Q: Do I need to configure WeChat credentials?**

A: Only if you want to auto-publish. Set `WECHAT_APPID` and `WECHAT_SECRET` environment variables.

## Content Quality

**Q: Is the converted content accurate?**

A: Yes, we maintain scientific accuracy while making it accessible. Review before publishing.

**Q: Can I edit the output?**

A: Absolutely! The output is markdown, easy to edit before publishing.

**Q: How much do papers get shortened?**

A: Academic papers (often 10,000+ words) are adapted to 2,000-5,000 words for WeChat.

## Troubleshooting

**Q: I get "command not found: paper2wechat"**

A: Verify installation: `pip install -e .` in the project directory

**Q: Paper fetching fails**

A: Check your internet connection and the Arxiv URL format.

**Q: WeChat upload fails**

A: Verify WECHAT_APPID and WECHAT_SECRET are set correctly.

## Contribution

**Q: How can I contribute?**

A: See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

**Q: Can I add new styles?**

A: Yes! Submit a PR with your style prompt and example outputs.

## Support

For more help, see:
- [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Detailed troubleshooting
- [QUICKSTART.md](../QUICKSTART.md) - Getting started
- Open an issue on GitHub
