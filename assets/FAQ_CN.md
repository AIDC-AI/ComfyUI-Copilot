### 安装相关

**Q: 如何正确安装 ComfyUI-Copilot？**
**A:** 推荐方法是在 `ComfyUI/custom_nodes` 文件夹下克隆仓库，并安装依赖：

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/AIDC-AI/ComfyUI-Copilot.git
cd ComfyUI-Copilot
pip install -r requirements.txt
```

在 Windows 环境下，需使用 ComfyUI 自带的 Python，例如：

```bash
python_embedded\python.exe -m pip install -r requirements.txt
```

（避免使用插件管理器安装时权限问题。）

---

**Q: 为什么安装时会遇到 pip 依赖冲突？**
**A:** 主要原因是 OpenAI 相关库版本不兼容。解决方案：修改
`custom_nodes/ComfyUI-Copilot/requirements.txt`，确保依赖如下：

* `openai>=1.5.0`
* `openai-agents>=0.3.0`
  然后执行：

```bash
pip install --force-reinstall -r requirements.txt
```

---

**Q: 使用 ComfyUI Manager 安装时出错怎么办？**
**A:** Manager 插件可能因权限不足报错。解决办法：

1. 用管理员权限运行 ComfyUI，例如 `sudo python main.py`。
2. 如果更新失败，删除 `ComfyUI-Copilot` 文件夹，手动重新安装。
3. 手动 Git 安装通常比 Manager 更可靠。

---

### 运行与界面相关

**Q: 安装后 Copilot 界面空白或不显示怎么办？**
**A:** 需要在 ComfyUI 界面左侧点击 **Copilot 启动按钮** 才能激活插件。
另外必须先输入并保存 API Key，否则界面不会加载正常。

---

**Q: 为什么 Copilot 界面在暗色主题下显示异常？**
**A:** 已有用户反馈更换主题后 Copilot 窗口显示不正常。
解决方法：切换回 **默认主题** 使用。

---

**Q: 如何获取并激活 Copilot API Key？**
**A:** 在 Copilot 界面点击 “*” 按钮 → 输入邮箱 → 系统会发送 API Key。
将密钥粘贴回输入框并点击 **保存**，即可完成激活。

---

**Q: Copilot 是否支持离线运行或本地模型？**
**A:** 目前不支持。Copilot 依赖远程大语言模型（如 OpenAI GPT、Claude），必须联网使用。

---