# Troubleshooting Guide

## Common Issues

### Installation Issues

#### "pip install -e . is not working"

**Solution**:
```bash
# Make sure you're in the project directory
cd paper2wechat

# Try with upgrade
pip install -e . --upgrade

# Or install dependencies first
pip install -r requirements.txt
pip install -e .
```

#### "ModuleNotFoundError: No module named 'paper2wechat'"

**Solutions**:
1. Install the package: `pip install -e .`
2. Make sure you're in the correct directory
3. Try `python -m paper2wechat` instead of `paper2wechat`

### Fetching Issues

#### "Failed to fetch paper from URL"

**Possible causes**:
- Invalid Arxiv URL (should be `https://arxiv.org/abs/XXXX.XXXXX`)
- No internet connection
- Arxiv server temporarily down

**Solution**:
```bash
# Verify URL format
paper2wechat https://arxiv.org/abs/2301.00000

# Test connection
curl https://arxiv.org/
```

#### "Connection timeout"

**Solution**:
- Check your internet connection
- Try again in a few minutes (Arxiv might be overloaded)
- Set timeout: `paper2wechat --timeout 60`

#### "PDF parsing failed"

**Possible causes**:
- PDF is scanned image (not searchable)
- PDF is corrupted or encrypted

**Solutions**:
```bash
# Try to extract text manually
pdftotext input.pdf output.txt

# Or convert to searchable PDF first
# (Use OCR tool like Tesseract)
```

### Content Issues

#### "Output is too short"

**Possible causes**:
- Short paper (< 2000 words)
- Aggressive summarization

**Solutions**:
```bash
# Increase max length
paper2wechat https://arxiv.org/abs/... --max-length 7000

# Or skip summarization (keep full content)
paper2wechat https://arxiv.org/abs/... --no-summarize
```

#### "Generated content seems wrong"

**Check**:
1. Review the output markdown manually
2. Try with `--preview` flag
3. Check if original paper fetching was correct: `paper2wechat --verbose`

**Solution**:
- Edit the markdown file manually before publishing
- Report issue with paper URL (might be edge case)

### Image Issues

#### "No images found"

**Possible causes**:
- Paper has no embedded images
- Images couldn't be extracted from PDF

**Solutions**:
```bash
# Skip image processing
paper2wechat https://arxiv.org/abs/... --images 0

# Or manually add images after generation
# Edit the markdown and add: ![description](imageurl.jpg)
```

#### "Images are very small/pixelated"

**Solution**:
- Original paper images might be low quality
- Edit markdown to use better quality versions
- Resize images: `paper2wechat --max-width 2048`

#### "Image upload to WeChat fails"

**Possible causes**:
- Image format not supported (should be JPG, PNG, GIF)
- Image too large
- WeChat API issues

**Solutions**:
```bash
# Reduce image size
paper2wechat https://arxiv.org/abs/... --image-max-width 1920

# Or disable images
paper2wechat https://arxiv.org/abs/... --images 0

# Then upload article without images, add images manually in WeChat editor
```

### WeChat Integration Issues

#### "WECHAT_APPID not configured"

**Solution**:
```bash
# Set environment variables
export WECHAT_APPID=your_appid
export WECHAT_SECRET=your_secret

# Or create config file at: ~/.paper2wechat/config.yaml
wechat:
  appid: your_appid
  secret: your_secret
```

#### "Failed to create draft"

**Possible causes**:
1. Invalid credentials (WECHAT_APPID/SECRET)
2. WeChat account not verified
3. Content size exceeds limit (>1MB)
4. IP not in WeChat whitelist

**Solutions**:
```bash
# Check credentials
paper2wechat --show-config

# Add IP to WeChat whitelist:
# 1. Get your IP: curl ifconfig.me
# 2. Go to WeChat Developer Platform
# 3. Settings → IP Whitelist
# 4. Add your IP, wait 5-10 minutes

# For large content, upload manually
paper2wechat https://arxiv.org/abs/... --output article.md
# Then paste content in WeChat editor manually
```

#### "Access Token expired"

**Solution**:
- This should auto-refresh, but if not:
```bash
# Re-initialize config
rm ~/.paper2wechat/config.yaml
paper2wechat --init-config
```

### Style Issues

#### "Output doesn't match the style I chose"

**Check**:
1. Verify you selected the right style: `paper2wechat --list-styles`
2. Try a different style
3. This is expected - style is applied to tone/structure, content depends on paper

**Solutions**:
```bash
# Try different styles to see differences
paper2wechat https://arxiv.org/abs/... --style academic-science --preview
paper2wechat https://arxiv.org/abs/... --style academic-tech --preview

# Edit style prompts if needed (~/.paper2wechat/styles/)
```

### Performance Issues

#### "Conversion is very slow"

**Possible causes**:
- Large paper (100+ pages)
- Slow internet
- API service latency

**Typical times**:
- URL fetch: 3-5s
- Content adaptation: 10-30s
- Image processing: 2-5s
- Total: 20-40s per paper

**Note**: First conversion might be slower due to dependency downloads.

### Error Messages

#### "RequestError: Max retries exceeded"

**Solution**:
```bash
# Retry with backoff
sleep 10
paper2wechat https://arxiv.org/abs/...

# Or increase retry timeout
PAPER2WECHAT_TIMEOUT=60 paper2wechat ...
```

#### "JSONDecodeError: ..."

**Possible causes**:
- Corrupted response from API
- Network interruption

**Solution**:
- Retry the command
- Check internet connection
- Try with `--verbose` for more details

#### "UnicodeEncodeError: ..."

**Solution**:
```bash
# Set UTF-8 encoding
export PYTHONIOENCODING=utf-8
paper2wechat ...
```

## Getting Help

Still stuck? Try these:

1. **Check documentation**:
   - [QUICKSTART.md](../QUICKSTART.md)
   - [CLAUDE.md](../CLAUDE.md) - Design document
   - [docs/ARCHITECTURE.md](ARCHITECTURE.md)

2. **Check FAQ**:
   - [docs/FAQ.md](FAQ.md)

3. **Enable verbose output**:
   ```bash
   paper2wechat https://arxiv.org/abs/... --verbose
   ```

4. **Open an issue on GitHub**:
   - Include the error message
   - Include `--verbose` output
   - Include paper URL
   - Include your environment (OS, Python version)

5. **Check existing issues**:
   - Search GitHub issues for similar problems

---

**Still need help?** We're here to support you! 🙌
