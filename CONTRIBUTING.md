# Contributing to AI Trading Agent

Thank you for your interest in contributing! Here's how to get started.

## Getting Started

1. **Fork the repository**
   - Click "Fork" on GitHub

2. **Clone your fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ai-trading-agent.git
   cd ai-trading-agent
   ```

3. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Set up development environment**
   ```bash
   bash setup.sh
   ```

5. **Make your changes**
   - Write code
   - Add/update tests
   - Update documentation if needed

6. **Test your changes**
   ```bash
   pytest tests/ -v
   make lint
   ```

7. **Commit and push**
   ```bash
   git add .
   git commit -m "feat: description of changes"
   git push origin feature/your-feature-name
   ```

8. **Create a Pull Request**
   - Go to GitHub
   - Click "New Pull Request"
   - Describe your changes
   - Wait for review

## Coding Standards

- Use clear variable names
- Add docstrings to functions
- Include type hints
- Write tests for new features
- Follow PEP 8 style guide
- Keep lines under 120 characters

## Commit Message Format

```
type(scope): subject

type: feat, fix, docs, style, refactor, test, chore
scope: backend, telegram, tests, docs
subject: clear, concise description (lowercase, no period)

Example:
feat(chart_agent): add support for custom timeframes
fix(news_agent): handle missing RSS feed data
docs: update deployment guide
```

## Issues & Bug Reports

If you find a bug:
1. Check if issue already exists
2. Create new issue with:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - System info (OS, Python version)

## Feature Requests

For new features:
1. Open an issue first to discuss
2. Get approval before implementing
3. Follow the PR process above

## Questions?

- Ask in GitHub Discussions
- Check existing issues/PRs
- Review documentation

Thank you for contributing! 🚀
