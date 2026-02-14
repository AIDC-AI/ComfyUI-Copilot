# Quick Reference: How to Contribute to Original Repo

## TL;DR - Fastest Path

**Just want to submit a PR right now?**

1. Go to: https://github.com/AIDC-AI/ComfyUI-Copilot
2. Click: **"New Pull Request"**
3. Click: **"compare across forks"**
4. Set:
   - base repository: `AIDC-AI/ComfyUI-Copilot`
   - head repository: `vehoelite/ComfyUI-Copilot-w-Agent`
5. Click: **"Create Pull Request"**
6. Fill in the template from `PULL_REQUEST_TEMPLATE.md`
7. Submit!

## Common Questions

### "Should I submit one big PR or multiple small ones?"

**Recommended**: Start with an issue to ask the maintainers what they prefer.

**Alternative approaches**:
- **One big PR**: All features at once (easier for you, harder to review)
- **Multiple PRs**: One per feature (LM Studio fixes → Multi-provider → Agent Mode → Voice → Training)

### "What if they don't respond?"

No response after 2+ weeks? Your fork still has value:
- Keep it maintained as a community enhancement
- Share it on ComfyUI Discord, Reddit, forums
- Add GitHub topics to make it discoverable

### "What if they reject my PR?"

That's okay! You can:
- Maintain your fork independently
- The community can still use your enhancements
- You've contributed to the ecosystem

### "How do I add the original repo as upstream?"

```bash
git remote add upstream https://github.com/AIDC-AI/ComfyUI-Copilot.git
git fetch upstream
```

### "Which files are most important to highlight?"

**For LM Studio fixes** (easiest to get merged):
- `backend/controller/llm_api.py`
- `backend/utils/globals.py`
- `HOW_TO_USE_LMSTUDIO.md`

**For everything**:
- `CHANGELOG.md` - Complete list of changes
- `README.md` - Feature comparison table

### "Should I open an issue first?"

**Yes, for large PRs** - Definitely recommended. Use the template in HOW_TO_SUBMIT_PR.md.

**No, for small fixes** - Simple bug fixes can go straight to PR.

### "What if I mess up the PR?"

Don't worry! You can:
- Update the PR by pushing more commits
- Close and re-open a new one
- Ask for help in the PR comments

## Three Main Documents

1. **[NEXT_STEPS.md](./NEXT_STEPS.md)** - Start here for overview and strategy
2. **[HOW_TO_SUBMIT_PR.md](./HOW_TO_SUBMIT_PR.md)** - Detailed step-by-step guide
3. **[CONTRIBUTING.md](./CONTRIBUTING.md)** - General contribution guidelines

## Your Fork's Value Proposition

**You fixed critical bugs**:
- LM Studio was completely broken → now works perfectly
- 5 specific issues fixed (port, URL, model parsing, API key, headers)

**You added major features**:
- Agent Mode (autonomous workflows)
- Multi-Provider (4 providers vs 1)
- Voice I/O (entirely new capability)
- Training pipeline (fine-tuning support)

**You documented everything**:
- Comprehensive README
- Setup guides
- Technical implementation docs
- This contribution documentation!

## Git Commands Cheat Sheet

```bash
# Add upstream
git remote add upstream https://github.com/AIDC-AI/ComfyUI-Copilot.git

# See your changes vs original
git fetch upstream
git diff upstream/main

# Create a feature branch
git checkout -b feature/my-fix

# See all remotes
git remote -v
```

## GitHub Web Interface Path

```
GitHub.com → AIDC-AI/ComfyUI-Copilot → Pull Requests tab → New Pull Request
→ compare across forks → set head to vehoelite → Create Pull Request
```

## Decision Tree

```
Do you want to contribute back to original repo?
├─ Yes, I want to try
│  ├─ Do maintainers seem active? (check recent commits/PRs)
│  │  ├─ Yes → Open issue first, then PR
│  │  └─ No → Submit PR anyway or maintain fork
│  └─ Should I submit all changes at once?
│     ├─ Unsure → Ask in an issue first
│     ├─ Yes → Submit one PR with everything
│     └─ No → Submit LM Studio fixes first, then others
└─ No, I'll maintain my fork
   └─ Make it discoverable (topics, sharing, documentation) ✅ Already done!
```

## Support

- **GitHub Docs**: https://docs.github.com/en/pull-requests
- **This Fork Issues**: https://github.com/vehoelite/ComfyUI-Copilot-w-Agent/issues
- **Original Repo**: https://github.com/AIDC-AI/ComfyUI-Copilot

---

**You're ready to contribute! Choose your path and go for it! 🚀**
