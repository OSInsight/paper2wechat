# Contributing to Paper2WeChat

We welcome contributions to help make paper2wechat better!

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Create a feature branch**: `git checkout -b feature/your-feature`
4. **Make your changes** and test thoroughly
5. **Submit a pull request** with a clear description

## Development Setup

```bash
# Clone your fork
git clone https://github.com/yourname/paper2wechat.git
cd paper2wechat

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
pip install -r requirements.txt

# Install development tools (optional but recommended)
pip install pytest black flake8 mypy
```

## Code Style

- Use **Python 3.8+** syntax
- Follow **PEP 8** style guide
- Add **type hints** to functions
- Write **docstrings** for modules and classes
- Keep functions focused and well-named

### Format your code

```bash
# Format with black
black .

# Check with flake8
flake8 core/

# Type checking
mypy core/
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core

# Run specific test
pytest tests/test_paper_fetcher.py
```

## Pull Request Process

1. **Ensure tests pass**: `pytest`
2. **Update documentation** if needed
3. **Add a clear description** of your changes
4. **Reference any related issues**: "Closes #123"
5. **Wait for review** and respond to feedback

## Areas for Contribution

### High Priority
- [ ] Paper fetching implementation
- [ ] Content adaptation with Claude API
- [ ] Image processing pipeline
- [ ] Test coverage

### Medium Priority
- [ ] Additional academic styles
- [ ] Better error handling
- [ ] Performance optimization
- [ ] Documentation improvements

### Low Priority
- [ ] Nice-to-have features
- [ ] UI/UX improvements
- [ ] Example expansions

## Reporting Issues

When reporting bugs, please include:
- **Description** of the issue
- **Steps to reproduce**
- **Expected behavior**
- **Actual behavior**
- **Environment** (OS, Python version, etc.)

## Questions?

- Open an issue with the `question` label
- Check existing issues and discussions
- See [CLAUDE.md](CLAUDE.md) for project design context

## Code of Conduct

Please be respectful and inclusive. We're building a community together!

---

Happy contributing! 🚀
