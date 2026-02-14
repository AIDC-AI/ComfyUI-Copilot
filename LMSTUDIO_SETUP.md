# LMStudio Integration with ComfyUI-Copilot

ComfyUI-Copilot now supports LMStudio as a local LLM provider. This allows you to run powerful language models locally on your machine without sending data to external APIs.

## Setup Instructions

### 1. Install and Configure LMStudio

1. Download and install LMStudio from [https://lmstudio.ai/](https://lmstudio.ai/)
2. Download a compatible model (e.g., Llama 3.1, CodeLlama, or other OpenAI-compatible models)
3. Start the LMStudio server:
   - Open LMStudio
   - Go to the "Developer" tab
   - Click "Start Server"
   - Default server will run on `http://localhost:1234`

### 2. Configure ComfyUI-Copilot

1. In the ComfyUI-Copilot interface, go to the LLM configuration settings
2. Set the following parameters:
   - **Base URL**: `http://localhost:1234/api/v1` (or your LMStudio server URL)
   - **API Key**: Leave empty (LMStudio typically doesn't require an API key)
   - **Model**: Select the model you loaded in LMStudio

### 3. Verify Connection

1. Click the "Verify Connection" button
2. You should see "LMStudio connection successful" if everything is configured correctly

## Supported Features

- ✅ Model listing from LMStudio
- ✅ Chat completions
- ✅ Streaming responses
- ✅ All ComfyUI-Copilot features (workflow generation, debugging, etc.)

## Common LMStudio URLs

- Default: `http://localhost:1234/api/v1`
- Custom port: `http://localhost:YOUR_PORT/api/v1`
- Network access: `http://YOUR_IP:1234/api/v1`

## Troubleshooting

### Connection Issues
- Ensure LMStudio server is running
- Check that the port (default 1234) is not blocked by firewall
- Verify the URL format includes `/api/v1` at the end

### Model Not Loading
- Make sure you have downloaded and loaded a model in LMStudio
- Check LMStudio console for any error messages
- Try restarting the LMStudio server

### Performance Issues
- LMStudio performance depends on your hardware
- Consider using quantized models for better performance
- Adjust LMStudio's GPU/CPU allocation settings

## Benefits of Using LMStudio

1. **Privacy**: All data stays on your local machine
2. **No API costs**: No per-token charges
3. **Offline capability**: Works without internet connection
4. **Custom models**: Use any compatible model you prefer
5. **Full control**: Adjust model parameters and behavior

## Model Recommendations

For ComfyUI-Copilot, we recommend:
- **Llama 3.1 8B Instruct** (good balance of performance and quality)
- **CodeLlama 7B/13B** (excellent for code-related tasks)
- **Mistral 7B Instruct** (fast and efficient)

Choose models based on your hardware capabilities and requirements.