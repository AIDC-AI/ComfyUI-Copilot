# 🚀 How to Use LMStudio with ComfyUI-Copilot

LMStudio allows you to run powerful language models locally on your machine. Here's a step-by-step guide to set it up with ComfyUI-Copilot.

## 📥 Step 1: Install LMStudio

1. **Download LMStudio** from [https://lmstudio.ai/](https://lmstudio.ai/)
2. **Install** the application on your computer
3. **Launch** LMStudio

## 🤖 Step 2: Download a Model

1. **Open LMStudio**
2. **Go to the "Discover" tab**
3. **Search for a model**. Recommended options:
   - **Llama 3.1 8B Instruct** (good balance of performance and quality)
   - **CodeLlama 7B** (excellent for code-related tasks)
   - **Mistral 7B Instruct** (fast and efficient)
   - **Phi-3.5 Mini** (very fast, smaller model)
4. **Click "Download"** for your chosen model

## 🔧 Step 3: Start LMStudio Server

1. **Go to the "Developer" tab** in LMStudio
2. **Select your downloaded model** from the dropdown
3. **Click "Start Server"**
4. **Note the server URL** (usually `http://localhost:1234`)
   - If you changed the port in LMStudio, use that port number instead

## ⚙️ Step 4: Configure ComfyUI-Copilot

1. **Open ComfyUI-Copilot** in your browser
2. **Click the settings/configuration button** (usually in the top-right area)
3. **Look for "LLM Configuration" or "API Configuration"** section
4. **Expand the configuration panel** if it's collapsed
4. **Configure the settings**:
   - **API Key**: Leave this **completely empty** (LMStudio doesn't need one)
   - **Server URL**: Enter `http://localhost:1234/api/v1` (or your custom port)
     - Always add `/api/v1` at the end for LMStudio's native API
6. **Click "Verify"** to test the connection
7. **Save** the configuration

## ✅ Step 5: Verify It's Working

1. **Test the connection** - you should see "LMStudio connection successful!"
2. **Try a simple chat** - ask ComfyUI-Copilot a question
3. **Check model availability** - the model dropdown should show your LMStudio model

## 🔍 Troubleshooting

### ❌ "Connection Failed" Error
- **Check LMStudio is running**: Make sure the server is started in LMStudio
- **Verify the URL**: Ensure you're using the correct port and added `/v1`
- **Check firewall**: Make sure port 1234 (or your custom port) isn't blocked
- **Restart LMStudio**: Sometimes restarting the server helps

### ❌ "No Models Found" 
- **Load a model**: Make sure you've selected and loaded a model in LMStudio
- **Wait for loading**: Some models take time to load completely
- **Check LMStudio logs**: Look at the LMStudio console for error messages

### ❌ "API Key Error"
- **Leave API key empty**: LMStudio doesn't require API keys
- **Clear any existing key**: Remove any text from the API key field

## 🎯 Common LMStudio URLs

- **Default**: `http://localhost:1234/v1`
- **Custom port**: `http://localhost:YOUR_PORT/v1`
- **Network access**: `http://YOUR_IP:1234/v1` (if accessing from another machine)

## 💡 Pro Tips

1. **Model Performance**: Larger models give better results but need more RAM/GPU
2. **GPU Acceleration**: Enable GPU acceleration in LMStudio for faster responses
3. **Context Length**: Adjust context length in LMStudio based on your needs
4. **Multiple Models**: You can switch models in LMStudio without reconfiguring ComfyUI-Copilot
5. **Offline Usage**: Once set up, everything works offline!

## 🆚 LMStudio vs OpenAI

| Feature | LMStudio | OpenAI API |
|---------|----------|------------|
| **Cost** | Free (after initial setup) | Pay per token |
| **Privacy** | 100% local | Data sent to OpenAI |
| **Speed** | Depends on your hardware | Usually very fast |
| **Models** | Open source models | GPT-4, GPT-3.5, etc. |
| **Setup** | Requires installation | Just API key |
| **Offline** | ✅ Works offline | ❌ Needs internet |

## 🎉 You're Ready!

Once configured, you can use all ComfyUI-Copilot features with your local LMStudio models:
- Workflow generation and debugging
- Parameter suggestions
- Model recommendations  
- Chat assistance
- And more!

Everything runs locally on your machine for complete privacy and control.