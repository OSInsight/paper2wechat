# Example: Converting an Arxiv Paper

This example demonstrates basic usage of paper2wechat.

## Input

Paper: https://arxiv.org/abs/2301.00000 (Example - replace with real paper)

## Command

```bash
paper2wechat https://arxiv.org/abs/2301.00000 \
  --style academic-tech \
  --images 4 \
  --output example-output.md
```

## Output

Generated `example-output.md` contains:
- Converted title and abstract
- Summarized sections (Introduction, Methods, Results, Discussion, Conclusion)
- Key figures extracted and positioned
- Total length: 2000-5000 words (WeChat-friendly)

## Next Steps

1. **Review** the markdown file for quality
2. **Edit** if needed for your audience
3. **Publish** to WeChat using:
   ```bash
   paper2wechat ./example-output.md --draft
   ```

## Tips

- Different styles work better for different papers
  - **academic-science**: For math-heavy, fundamental research
  - **academic-tech**: For tools, frameworks, engineering papers
  - **academic-trend**: For cutting-edge, emerging field papers
  - **academic-applied**: For industry applications

- Adjust `--images` based on paper type (3-7 images usually works well)

- Preview first: `--preview` flag shows output without saving

---

See [QUICKSTART.md](../QUICKSTART.md) for more examples.
