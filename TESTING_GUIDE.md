# Phase 1 Testing Guide

## Understanding the Changes

**Important**: Phase 1 focused on **backend security hardening only**. The UI has not changed yet - that's Phase 2. However, the **behavior** behind the scenes is completely different.

## Verify You're on the Correct Branch

### 1. Check Git Branch
```bash
cd custom_nodes/ComfyUI-Copilot
git branch
# Should show: * feature/phase1-security-hardening

git log --oneline -1
# Should show: 2f6add6 Phase 1: Backend Security Hardening - Complete
```

### 2. Verify Key Files Exist
```bash
# Check for new files that only exist in the feature branch
ls -la .env.local.template
ls -la PHASE1_COMPLETE.md
ls -la implementation_plan.md
ls -la backend/utils/local_session_manager.py
```

If these files exist, you're on the correct branch.

### 3. Check Configuration in Code
```bash
# Verify the security settings are in place
grep "DISABLE_EXTERNAL_CONNECTIONS" backend/utils/globals.py
grep "LOCAL_LLM_BASE_URL" backend/utils/globals.py
```

Expected output should show:
```python
DISABLE_EXTERNAL_CONNECTIONS = os.getenv("DISABLE_EXTERNAL_CONNECTIONS", "true").lower() == "true"
LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://sparkle:8000/v1")
```

## Testing the Implementation

### Step 1: Verify Your Local LLM is Running

First, test that your DGX Spark LLM is accessible:
```bash
curl -X GET http://sparkle:8000/v1/models
```

Expected response: JSON with available models. If this fails, the LLM isn't accessible.

### Step 2: Restart ComfyUI

**IMPORTANT**: You must restart ComfyUI for the Python backend changes to take effect:
```bash
# Stop ComfyUI if it's running (Ctrl+C)
# Then restart it
python main.py
```

### Step 3: Check the Startup Logs

When ComfyUI starts with the Copilot plugin, look for these messages in the terminal:

```
[ComfyUI-Copilot] Local-only mode enabled
[ComfyUI-Copilot] Using local LLM at: http://sparkle:8000/v1
[ComfyUI-Copilot] External connections disabled
[ComfyUI-Copilot] Telemetry disabled
```

If you see these, the new configuration is active.

### Step 4: Test Chat Functionality

1. **Open ComfyUI in your browser**
2. **Open the Copilot chat panel** (same UI as before)
3. **Send a test message** (e.g., "Hello, can you help me?")

### Step 5: Monitor Behavior Changes

Watch the ComfyUI terminal logs when you send a message. You should see:

**✅ Expected behavior (Phase 1 working):**
```
[ComfyUI-Copilot] Local-only mode: Generated session UUID: abc123...
[ComfyUI-Copilot] Created new local session: abc123...
[ComfyUI-Copilot] Local-only mode: Using local LLM at http://sparkle:8000/v1
[ComfyUI-Copilot] External connections disabled - running in local-only mode
```

**❌ Old behavior (not on feature branch):**
```
[ComfyUI-Copilot] ComfyUI Copilot API key extracted and stored
[ComfyUI-Copilot] Connecting to external server...
```

### Step 6: Verify Session Database

After sending a message, check that the local session database was created:
```bash
# From the ComfyUI-Copilot directory
ls -la data/sessions.db
```

If this file exists, local session management is working.

### Step 7: Check for External Connections

Use network monitoring to verify no external connections are made:

**Option A - Using lsof (macOS/Linux):**
```bash
# While ComfyUI is running and you're chatting
sudo lsof -i -P | grep Python | grep ESTABLISHED
```

You should see connections to:
- ✅ `sparkle:8000` (your local LLM)
- ✅ `localhost` (ComfyUI web server)
- ❌ NO connections to `onrender.com` or other external servers

**Option B - Using Little Snitch/network monitor:**
If you have network monitoring software, verify that Python/ComfyUI is NOT connecting to:
- `comfyui-copilot-server.onrender.com`
- Any external tracking/analytics services

## Expected Differences

### What WILL Look Different:
1. **Terminal logs** - Show "Local-only mode" messages
2. **No API key requirement** - System generates UUIDs automatically
3. **Local LLM responses** - Responses come from your DGX Spark
4. **Session storage** - `data/sessions.db` file created
5. **No external connections** - Network monitoring shows only local traffic

### What Will NOT Look Different (Phase 2):
1. **UI appearance** - Same interface
2. **Chat panel design** - Unchanged
3. **API key input field** - Still visible (removed in Phase 2)
4. **Model selection dropdown** - Still shows old options (fixed in Phase 2)

## Troubleshooting

### Problem: "No module named 'local_session_manager'"
**Solution**: You're not on the feature branch. Run:
```bash
git checkout feature/phase1-security-hardening
git pull origin feature/phase1-security-hardening
```
Then restart ComfyUI.

### Problem: Chat not responding
**Check**:
1. Is your LLM at http://sparkle:8000/v1 running?
   ```bash
   curl http://sparkle:8000/v1/models
   ```
2. Check ComfyUI logs for error messages
3. Verify firewall isn't blocking sparkle:8000

### Problem: Still seeing "API key required" errors
**Cause**: Old behavior, not on feature branch or ComfyUI not restarted.
**Solution**:
1. Verify branch: `git branch`
2. Restart ComfyUI completely
3. Clear browser cache

### Problem: Seeing connections to onrender.com
**Cause**: Not on feature branch or old code cached.
**Solution**:
1. Stop ComfyUI
2. Verify branch and files
3. Delete `__pycache__` directories:
   ```bash
   find . -type d -name __pycache__ -exec rm -rf {} +
   ```
4. Restart ComfyUI

## Quick Verification Checklist

- [ ] On `feature/phase1-security-hardening` branch
- [ ] New files exist (.env.local.template, PHASE1_COMPLETE.md, etc.)
- [ ] ComfyUI restarted after checkout
- [ ] Terminal shows "Local-only mode" messages
- [ ] `data/sessions.db` file created after chat
- [ ] LLM at http://sparkle:8000/v1 is accessible
- [ ] No external connections to onrender.com
- [ ] Chat responds with messages from local LLM

## Testing Scenarios

### Test 1: New Session Creation
1. Send message: "Hello"
2. Check logs for: "Created new local session"
3. Check `data/sessions.db` exists

### Test 2: Session Persistence
1. Send first message
2. Note the session UUID in logs
3. Send second message
4. Verify same session UUID is reused
5. Check logs for: "Updated activity for session"

### Test 3: Local LLM Communication
1. Send message: "Write a simple Python function"
2. Verify response comes from your LLM
3. Check logs show: "Using local LLM at http://sparkle:8000/v1"
4. Response should match your LLM's style/capabilities

### Test 4: No External Dependencies
1. Disconnect from internet (optional but definitive)
2. Chat should still work (assuming sparkle is on local network)
3. Or: Monitor network and verify no external traffic

## Success Criteria

✅ **Phase 1 is working correctly if:**
1. Terminal logs show "Local-only mode" messages
2. No connections to comfyui-copilot-server.onrender.com
3. Chat responses come from http://sparkle:8000/v1
4. Local session database (`data/sessions.db`) is created and used
5. No external API key is required for operation
6. All chat functionality works with local LLM

## Next Steps After Successful Testing

Once you've verified Phase 1 is working:
1. Document any issues or unexpected behavior
2. Test all major chat features (workflow generation, node recommendations, etc.)
3. Ready to begin Phase 2: Frontend updates
4. Consider merging the feature branch to main

---

**Note**: The UI changes in Phase 2 will make it more obvious that you're in local mode, with the API key field removed and clear "Local Mode" indicators.
