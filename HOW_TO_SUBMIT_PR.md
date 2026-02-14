# How to Submit a Pull Request to the Original Repository

This guide provides step-by-step instructions for submitting your enhancements from this fork back to the original [AIDC-AI/ComfyUI-Copilot](https://github.com/AIDC-AI/ComfyUI-Copilot) repository.

## Quick Start

**TL;DR**: Go to https://github.com/AIDC-AI/ComfyUI-Copilot, click "New Pull Request", click "compare across forks", set head to `vehoelite:main`, and submit.

## Detailed Guide

### Before You Start

This fork contains **extensive changes** (v3.0 with Agent Mode, Multi-Provider, Voice I/O, LM Studio fixes). Consider these approaches:

#### Approach 1: Open an Issue First (Recommended)

Before submitting a large PR, gauge interest from the maintainers:

1. Go to https://github.com/AIDC-AI/ComfyUI-Copilot/issues
2. Click "New Issue"
3. Use this template:

```markdown
Title: 🚀 Enhanced Fork Available: Agent Mode, Multi-Provider, Voice I/O, LM Studio Fixes

Hi AIDC-AI team! 👋

I've been working on an enhanced fork of ComfyUI-Copilot and wanted to share what I've built. The fork adds several major features while maintaining compatibility with your v2.0 architecture.

## Fork Repository
https://github.com/vehoelite/ComfyUI-Copilot-w-Agent

## Major Enhancements

### 1. Agent Mode (Autonomous Workflow Building)
- PLAN/EXECUTE/VALIDATE/REPORT loop
- Multi-step task breakdown and execution
- Tool budget system with loop prevention
- Visual progress tracking

### 2. Multi-Provider Support
- OpenAI, Groq, Anthropic, LM Studio
- Any OpenAI-compatible API
- Provider-aware timeouts and optimizations
- 4-tab settings UI

### 3. Fixed LM Studio Integration
The original LM Studio integration had several critical bugs:
- ❌ Wrong port (1235 vs 1234)
- ❌ URL normalization failed
- ❌ Model listing didn't parse LM Studio format
- ❌ Required API key when unnecessary
All now fixed and fully working ✅

### 4. Voice I/O
- Speech-to-text with Voice Activity Detection
- Streaming text-to-speech with sentence boundaries
- Provider-specific TTS/STT engines

### 5. Fine-Tuning Pipeline
- Complete QLoRA training for Qwen3
- Consumer GPU optimized (RTX 5060 8GB tested)
- 18 conversation generators

## Documentation
- Detailed CHANGELOG.md with all fixes
- Complete README with feature comparison table
- LM Studio setup guides
- PULL_REQUEST_TEMPLATE.md ready

## Contribution Options

I'd love to contribute these back if you're interested. We could:

**Option A**: Submit one comprehensive PR with all changes
**Option B**: Break into smaller feature PRs (LM Studio fixes → Multi-provider → Agent Mode → Voice → Training)
**Option C**: Cherry-pick specific features you want

Which approach would work best for you? The LM Studio fixes alone would be valuable since the current integration is broken.

## Test Coverage
- Tested with OpenAI, Groq, Anthropic, LM Studio
- Works with existing ComfyUI workflows
- Backward compatible with v2.0 settings

Let me know your thoughts!
```

#### Approach 2: Submit Smaller, Focused PRs

Instead of one massive PR, submit features incrementally:

##### PR 1: LM Studio Fixes (Start Here - High Value, Low Risk)
**Files**: ~10 files
**Impact**: Fixes broken functionality
**Benefit**: Clear improvement, easy to review

##### PR 2: Multi-Provider Support
**Files**: ~20 files
**Impact**: Enables Groq, Anthropic, any OpenAI-compatible API
**Benefit**: Reduces vendor lock-in

##### PR 3: Agent Mode
**Files**: ~30 files
**Impact**: New autonomous workflow building
**Benefit**: Major feature enhancement

##### PR 4: Voice I/O
**Files**: ~15 files
**Impact**: Speech interaction
**Benefit**: Accessibility and UX improvement

##### PR 5: Fine-Tuning Pipeline
**Files**: ~5 files in `/training`
**Impact**: Model training capability
**Benefit**: Enables customization

#### Approach 3: Maintain as Community Fork

If upstream isn't actively accepting PRs or has different design goals:

1. **Keep your fork discoverable**:
   - Add GitHub topics: `comfyui`, `comfyui-plugin`, `ai-assistant`, `enhanced-fork`
   - Clear README showing it's an enhanced fork (already done ✅)
   
2. **Share in communities**:
   - ComfyUI Discord
   - Reddit r/comfyui
   - ComfyUI forum
   
3. **Sync with upstream regularly**:
   ```bash
   git fetch upstream
   git merge upstream/main
   ```

### Step-by-Step PR Submission

#### Setup (One-Time)

1. **Add upstream remote** (if not already done):
   ```bash
   git remote add upstream https://github.com/AIDC-AI/ComfyUI-Copilot.git
   git fetch upstream
   ```

2. **Verify remotes**:
   ```bash
   git remote -v
   # Should show:
   # origin    https://github.com/vehoelite/ComfyUI-Copilot-w-Agent.git
   # upstream  https://github.com/AIDC-AI/ComfyUI-Copilot.git
   ```

#### Submitting the PR

##### Method 1: GitHub Web Interface (Easiest)

1. **Navigate to original repo**: https://github.com/AIDC-AI/ComfyUI-Copilot

2. **Click "New Pull Request"** (green button near top)

3. **Click "compare across forks"** (blue link)

4. **Configure the comparison**:
   - **base repository**: `AIDC-AI/ComfyUI-Copilot`
   - **base**: `main` (or their default branch)
   - **head repository**: `vehoelite/ComfyUI-Copilot-w-Agent`
   - **compare**: `main` (or your feature branch)

5. **Review the changes**: GitHub will show a diff of all changes

6. **Click "Create Pull Request"**

7. **Fill in the PR details**:
   - **Title**: Use format like "Add Agent Mode, Multi-Provider Support, Voice I/O, and Fix LM Studio"
   - **Description**: Copy from PULL_REQUEST_TEMPLATE.md and fill in details
   - Be clear about what you're contributing
   - Reference the CHANGELOG.md for detailed changes

8. **Submit the PR**

##### Method 2: GitHub CLI (Advanced)

If you have [GitHub CLI](https://cli.github.com/) installed:

```bash
# For all changes
gh pr create \
  --repo AIDC-AI/ComfyUI-Copilot \
  --base main \
  --head vehoelite:main \
  --title "v3.0 Enhancements: Agent Mode, Multi-Provider, Voice I/O, LM Studio Fixes" \
  --body-file PULL_REQUEST_TEMPLATE.md

# For specific feature branch
gh pr create \
  --repo AIDC-AI/ComfyUI-Copilot \
  --base main \
  --head vehoelite:feature/lmstudio-fixes \
  --title "Fix LM Studio Integration" \
  --body "Fixes broken LM Studio support (port, URL normalization, model listing, API key handling)"
```

#### PR Best Practices

1. **Clear Title**: Summarize what the PR does in one line
   - Good: "Fix LM Studio integration and add multi-provider support"
   - Bad: "Updates"

2. **Detailed Description**: Use the PULL_REQUEST_TEMPLATE.md
   - What changes were made
   - Why they were needed
   - How to test them
   - Any breaking changes

3. **Reference Documentation**:
   - Link to CHANGELOG.md for full details
   - Link to new docs (HOW_TO_USE_LMSTUDIO.md, etc.)
   - Show before/after if UI changed

4. **Be Responsive**:
   - Watch for review comments
   - Address feedback promptly
   - Be open to suggestions

5. **Be Patient**:
   - Large PRs take time to review
   - Maintainers may have different priorities
   - Some features may not align with their vision

### What to Expect

#### Possible Outcomes

1. **✅ Accepted**: PR is merged (might take time for review)
2. **📝 Revision Requested**: Changes needed before merge
3. **⏸️ Deferred**: They're interested but need to think about it
4. **❌ Declined**: Doesn't fit their roadmap
5. **🔇 No Response**: Maintainers might be busy/inactive

#### If PR is Declined or No Response

This doesn't mean your work is wasted:

1. **Keep your fork maintained**:
   - Continue improving independently
   - Sync with upstream when they release updates
   - Build a user community

2. **Make it discoverable**:
   - Add GitHub topics
   - Update README highlighting it's an enhanced fork (done ✅)
   - Share on ComfyUI communities

3. **Document the difference**:
   - Feature comparison table (done ✅)
   - Clear upgrade guide (in CHANGELOG.md)
   - Migration instructions

### Preparing Feature Branches for Smaller PRs

If you choose to submit features separately:

#### For LM Studio Fixes Only

```bash
# Create a feature branch
git checkout -b feature/lmstudio-fixes

# Cherry-pick relevant commits or make targeted changes
# Test thoroughly

# Push to your fork
git push origin feature/lmstudio-fixes

# Submit PR using that branch
gh pr create --repo AIDC-AI/ComfyUI-Copilot --head vehoelite:feature/lmstudio-fixes
```

#### For Multi-Provider Support

```bash
git checkout -b feature/multi-provider
# Include LM Studio fixes as they're foundational
# Push and create PR
```

### Files to Highlight in PRs

When submitting, emphasize these key files:

#### LM Studio Fixes PR
- `backend/controller/llm_api.py` - Fixed model listing, API key handling
- `backend/utils/globals.py` - Fixed URL normalization
- `backend/service/mcp_client.py` - API key placeholder
- `ui/src/components/chat/ApiKeyModal.tsx` - Correct port, optional API key
- `HOW_TO_USE_LMSTUDIO.md` - Setup guide

#### Multi-Provider PR
- `backend/utils/globals.py` - Provider detection
- `backend/agent_factory.py` - Provider-aware configuration
- `ui/src/components/chat/ApiKeyModal.tsx` - 4-tab interface

#### Agent Mode PR
- `backend/service/agent_mode.py` - Main orchestration
- `backend/service/agent_mode_tools.py` - Tool budget, loop prevention
- `ui/src/components/chat/AgentModeIndicator.tsx` - Visual progress

#### Voice I/O PR
- `ui/src/utils/streamingTTS.ts` - Streaming TTS
- `ui/src/utils/vadRecorder.ts` - Voice activity detection
- `backend/controller/llm_api.py` - TTS/STT endpoints

### Communication Tips

When interacting with maintainers:

1. **Be respectful**: They built the original, you're proposing changes
2. **Be clear**: Explain what you did and why
3. **Be flexible**: They may want things done differently
4. **Be helpful**: Offer to make changes or split the PR
5. **Give credit**: Always acknowledge their original work

### Useful Commands

```bash
# See what changed compared to upstream
git fetch upstream
git diff upstream/main..HEAD

# Count lines changed
git diff upstream/main --shortstat

# List changed files
git diff upstream/main --name-only

# View commit log
git log upstream/main..HEAD --oneline

# Create a patch file (alternative to PR)
git format-patch upstream/main --stdout > enhancements.patch
```

## Questions?

- **About submitting PRs**: See [GitHub Docs - Creating a Pull Request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork)
- **About this fork**: Open an issue in this repository
- **About the original**: Open an issue in AIDC-AI/ComfyUI-Copilot

## Final Checklist

Before submitting your PR:

- [ ] All changes are committed and pushed to your fork
- [ ] Tests pass (if applicable)
- [ ] Documentation is updated (README, CHANGELOG, etc.)
- [ ] PULL_REQUEST_TEMPLATE.md is filled out
- [ ] You've reviewed your own changes
- [ ] You're ready to respond to feedback
- [ ] You've decided which approach (one large PR vs. multiple smaller PRs)
- [ ] You've opened an issue first (if large PR)

Good luck! 🚀
