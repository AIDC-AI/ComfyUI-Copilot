# Contributing to ComfyUI-Copilot-w-Agent

Thank you for your interest in contributing! This guide will help you contribute changes back to the original repository.

## How to Submit Changes to the Original Repository

This fork contains significant enhancements to the original [AIDC-AI/ComfyUI-Copilot](https://github.com/AIDC-AI/ComfyUI-Copilot) repository. Here's how to contribute these changes back:

### Step 1: Set Up Upstream Remote

If you haven't already, add the original repository as an upstream remote:

```bash
git remote add upstream https://github.com/AIDC-AI/ComfyUI-Copilot.git
git fetch upstream
```

Verify your remotes:
```bash
git remote -v
# Should show:
# origin    https://github.com/vehoelite/ComfyUI-Copilot-w-Agent.git (fetch)
# origin    https://github.com/vehoelite/ComfyUI-Copilot-w-Agent.git (push)
# upstream  https://github.com/AIDC-AI/ComfyUI-Copilot.git (fetch)
# upstream  https://github.com/AIDC-AI/ComfyUI-Copilot.git (push)
```

### Step 2: Prepare Your Changes

Before submitting a pull request, ensure your changes are ready:

1. **Sync with upstream** (optional, but recommended):
   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```

2. **Create a feature branch** for your changes:
   ```bash
   git checkout -b feature/describe-your-changes
   ```

3. **Review your changes**:
   ```bash
   git diff upstream/main..HEAD
   ```

### Step 3: Submit a Pull Request

#### Option A: Via GitHub Web Interface (Recommended for Beginners)

1. **Navigate to the original repository**: https://github.com/AIDC-AI/ComfyUI-Copilot

2. **Click "New Pull Request"**

3. **Click "compare across forks"**

4. **Set the base and compare branches**:
   - Base repository: `AIDC-AI/ComfyUI-Copilot`
   - Base branch: `main` (or their default branch)
   - Head repository: `vehoelite/ComfyUI-Copilot-w-Agent`
   - Compare branch: Your feature branch (or `main` if you want to submit all changes)

5. **Fill out the PR template** (see PULL_REQUEST_TEMPLATE.md for guidance)

6. **Submit the PR** and wait for review

#### Option B: Via GitHub CLI (Advanced)

If you have GitHub CLI installed:

```bash
# Make sure you're on the branch you want to submit
git checkout feature/your-feature

# Create a PR to the upstream repository
gh pr create --repo AIDC-AI/ComfyUI-Copilot --base main --head vehoelite:feature/your-feature --title "Your PR Title" --body-file PULL_REQUEST_TEMPLATE.md
```

### Step 4: Communication

#### Before Submitting a Large PR

Since this fork contains extensive changes, consider these approaches:

1. **Open an Issue First**: Create an issue in the original repository describing your enhancements and asking if they'd be interested in a PR. Example:

   ```markdown
   Title: Proposed Enhancements: Agent Mode, Multi-Provider Support, Voice I/O, LM Studio Fixes
   
   Hi! I've been working on a fork of ComfyUI-Copilot and have implemented several
   enhancements that might be of interest:
   
   - Agent Mode (autonomous multi-step workflows)
   - Multi-provider support (OpenAI, Groq, Anthropic, LM Studio)
   - Fixed LM Studio integration
   - Voice I/O (STT + streaming TTS)
   - Fine-tuning pipeline
   
   Full details: https://github.com/vehoelite/ComfyUI-Copilot-w-Agent
   
   Would you be interested in a PR for these features? I can submit them as:
   1. One large PR with all changes
   2. Multiple smaller PRs, one per feature
   3. Specific features you're most interested in
   
   Let me know your preference!
   ```

2. **Break Into Smaller PRs**: Instead of one massive PR, consider submitting features individually:
   - PR 1: LM Studio fixes (most straightforward)
   - PR 2: Multi-provider support
   - PR 3: Agent Mode
   - PR 4: Voice I/O
   - PR 5: Fine-tuning pipeline

   This makes review easier and increases the chance of acceptance.

3. **Maintain Your Fork**: If the upstream isn't actively accepting PRs, you can maintain your fork as a community-enhanced version. Make sure to:
   - Clearly credit the original authors
   - Keep your README updated showing it's a fork
   - Sync periodically with upstream changes

### Step 5: After Submitting

1. **Be responsive** to review comments
2. **Make requested changes** promptly
3. **Be patient** - large PRs take time to review
4. **Be prepared** for rejection - not all features may align with the original project's goals

## Alternative: Make Your Fork Discoverable

If the upstream repository isn't accepting contributions, you can make your fork more discoverable:

1. **Add topics to your GitHub repo**: 
   - Go to your repo settings
   - Add topics like: `comfyui`, `comfyui-plugin`, `ai-assistant`, `comfyui-copilot`, `enhanced-fork`

2. **Create a discussion post** in the original repo (if they have discussions enabled)

3. **Share on ComfyUI communities**:
   - ComfyUI Discord
   - Reddit r/comfyui
   - ComfyUI forum

4. **Keep your README clear** that it's an enhanced fork (already done!)

## Changes Summary

For reference, here's a summary of major enhancements in this fork:

### New Features (v3.0)
- **Agent Mode**: Autonomous multi-step workflow building with PLAN/EXECUTE/VALIDATE/REPORT loop
- **Multi-Provider Support**: OpenAI, Groq, Anthropic, LM Studio (any OpenAI-compatible API)
- **Voice I/O**: Speech-to-text and streaming text-to-speech with VAD
- **Fine-Tuning Pipeline**: Complete training pipeline for Qwen3 models

### Bug Fixes
- **LM Studio Integration**: Fixed broken port, URL normalization, model listing, API key handling
- **Provider-Aware Timeouts**: Different timeout strategies for different providers
- **Loop Prevention**: Tool budget enforcement and duplicate call detection
- **None-safe Metadata**: Defensive programming for metadata handling

### Architecture Improvements
- Provider detection and auto-configuration
- 4-tab settings modal with auto-fill
- Streaming TTS with sentence extraction
- Voice activity detection (VAD) recorder
- Canvas rule enforcement (only save_workflow modifies canvas)
- Consumer GPU-friendly training pipeline

## Questions?

If you have questions about contributing:
1. Check the [GitHub Docs on Forking](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks)
2. See the [GitHub Docs on Pull Requests](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests)
3. Open an issue in this repository for help

## Code of Conduct

Be respectful, professional, and constructive in all interactions. Remember that the original maintainers may have different priorities or design philosophies.
