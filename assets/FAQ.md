## Installation Issues

### How to properly install ComfyUI-Copilot without errors?

The recommended way is to clone the repo into `ComfyUI/custom_nodes` and install requirements:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/AIDC-AI/ComfyUI-Copilot.git
cd ComfyUI-Copilot
pip install -r requirements.txt
```

On Windows, use the embedded Python shipped with ComfyUI, e.g.:

```bash
python_embedded\python.exe -m pip install -r requirements.txt
```

(Avoid using Manager installation if possible.)

---

### Why does pip install show dependency conflicts for ComfyUI-Copilot?

This usually happens due to incompatible OpenAI library versions. Fix by editing
`custom_nodes/ComfyUI-Copilot/requirements.txt` to ensure:

* `openai>=1.5.0`
* `openai-agents>=0.3.0`
  Then reinstall with:

```bash
pip install --force-reinstall -r requirements.txt
```

---

### Why does installing via ComfyUI Manager fail?

Manager may cause permission errors. Solutions:

1. Run ComfyUI with admin/root privileges, e.g. `sudo python main.py`.
2. If update fails, delete the Copilot folder and reinstall manually.
3. Manual Git installation is generally more reliable.

---

## Runtime & UI Issues

### Why is ComfyUI-Copilot blank or not showing after installation?

You must click the **Copilot activation button** on the left panel of ComfyUI to enable it.
Also make sure you paste and save a valid API key, otherwise the panel stays blank.

---

### Why does the Copilot UI break or disappear with a non-default theme?

This is a known bug. Users reported that dark/custom themes cause UI issues.
Workaround: switch back to the **default theme**.

---

### How to get and activate the Copilot API key?

Open Copilot panel → click “*” button → enter your email → you’ll receive an API key.
Paste the key into the input field and click **Save** to activate.

---

### Does ComfyUI-Copilot support offline mode or local AI models?

Currently no. Copilot relies on external LLM APIs (e.g. OpenAI GPT, Claude) and requires internet access.

---