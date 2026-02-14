"""
Tool schemas for ComfyUI-Copilot fine-tuning dataset.

These schemas define EXACTLY what tools the model will see at inference time.
They match the @function_tool decorated functions in agent_mode_tools.py,
PLUS future tools planned for the roadmap.

Every schema here becomes part of the training data.  The model learns
to call these tools with correct argument types and values.

Enhanced by Claude Opus 4.6
"""

# ---------------------------------------------------------------------------
# Current tools (match agent_mode_tools.py exactly)
# ---------------------------------------------------------------------------

CURRENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "plan_tasks",
            "description": "Create a step-by-step plan. Call first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of task descriptions",
                    }
                },
                "required": ["tasks"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_nodes",
            "description": "Search installed ComfyUI nodes by name/category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for node name or category",
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional search keywords",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_node_details",
            "description": "Get input/output spec for a node class.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_class": {
                        "type": "string",
                        "description": "Exact node class_type name",
                    }
                },
                "required": ["node_class"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_available_models",
            "description": "List model files by type: checkpoints|loras|vae|controlnet|upscale_models|embeddings|clip",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_type": {
                        "type": "string",
                        "description": "Model category to list",
                        "default": "checkpoints",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_workflow_for_agent",
            "description": "Get current session workflow JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why you need the workflow",
                        "default": "inspect",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_workflow",
            "description": "Save workflow JSON to canvas. ONLY tool that places nodes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workflow_json": {
                        "type": "string",
                        "description": "Complete workflow as JSON string",
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of what was changed",
                        "default": "Agent mode checkpoint",
                    },
                },
                "required": ["workflow_json"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_workflow",
            "description": "Validate current workflow for errors. Does NOT run it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "default": "check",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_workflow",
            "description": "Execute current workflow. Returns prompt_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "default": "run",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_execution_result",
            "description": "Check if execution is done. Returns outputs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt_id": {
                        "type": "string",
                        "description": "The prompt_id from execute_workflow",
                    }
                },
                "required": ["prompt_id"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Future tools (planned features — train the model on these NOW)
# ---------------------------------------------------------------------------

FUTURE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "prepare_image",
            "description": "Prepare an image for use in a workflow: resize, crop, convert format, adjust quality.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the input image",
                    },
                    "target_width": {
                        "type": "integer",
                        "description": "Target width in pixels",
                    },
                    "target_height": {
                        "type": "integer",
                        "description": "Target height in pixels",
                    },
                    "crop_mode": {
                        "type": "string",
                        "enum": ["center", "face", "smart", "none"],
                        "description": "How to crop if aspect ratio differs",
                        "default": "smart",
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["png", "jpg", "webp"],
                        "default": "png",
                    },
                },
                "required": ["image_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "prepare_video",
            "description": "Prepare a video for use in a workflow: extract frames, trim, resize.",
            "parameters": {
                "type": "object",
                "properties": {
                    "video_path": {
                        "type": "string",
                        "description": "Path to the input video",
                    },
                    "start_time": {
                        "type": "number",
                        "description": "Start time in seconds",
                        "default": 0,
                    },
                    "end_time": {
                        "type": "number",
                        "description": "End time in seconds (0 = full video)",
                        "default": 0,
                    },
                    "extract_frames": {
                        "type": "boolean",
                        "description": "Extract individual frames",
                        "default": False,
                    },
                    "frame_rate": {
                        "type": "integer",
                        "description": "Target FPS for frame extraction",
                        "default": 8,
                    },
                    "target_width": {
                        "type": "integer",
                        "description": "Resize width (0 = keep original)",
                        "default": 0,
                    },
                    "target_height": {
                        "type": "integer",
                        "description": "Resize height (0 = keep original)",
                        "default": 0,
                    },
                },
                "required": ["video_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_image",
            "description": "Analyze an image: detect content, faces, resolution, quality issues, and suggest improvements.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the image to analyze",
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": ["full", "faces", "quality", "content", "style"],
                        "description": "What to analyze",
                        "default": "full",
                    },
                },
                "required": ["image_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_workflow",
            "description": "Recommend a workflow type, architecture, and parameters based on the user's goal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "What the user wants to achieve",
                    },
                    "available_models": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Models the user has installed",
                    },
                    "constraints": {
                        "type": "object",
                        "description": "Optional constraints: max_vram, speed_priority, quality_priority",
                    },
                },
                "required": ["goal"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_parameters",
            "description": "Suggest optimal KSampler parameters (steps, CFG, sampler, scheduler) for a given model and use case.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_type": {
                        "type": "string",
                        "enum": ["sd15", "sdxl", "sd3", "flux", "cascade", "pixart", "hunyuan"],
                        "description": "Base model architecture",
                    },
                    "use_case": {
                        "type": "string",
                        "enum": ["photo_realistic", "anime", "artistic", "fast_preview", "high_quality", "video"],
                        "description": "Target use case",
                    },
                    "speed_priority": {
                        "type": "boolean",
                        "description": "Prioritize speed over quality",
                        "default": False,
                    },
                },
                "required": ["model_type", "use_case"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "batch_process",
            "description": "Set up batch processing to run a workflow on multiple inputs (images, prompts, or parameter variations).",
            "parameters": {
                "type": "object",
                "properties": {
                    "batch_type": {
                        "type": "string",
                        "enum": ["images", "prompts", "params", "seeds"],
                        "description": "What to batch over",
                    },
                    "inputs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of input values to iterate",
                    },
                    "workflow_node_id": {
                        "type": "string",
                        "description": "Node ID to inject batch values into",
                    },
                    "input_field": {
                        "type": "string",
                        "description": "Field name on the node to vary",
                    },
                },
                "required": ["batch_type", "inputs", "workflow_node_id", "input_field"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "install_custom_node",
            "description": "Install a ComfyUI custom node package from GitHub or the registry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": "Package name or GitHub URL",
                    },
                    "auto_restart": {
                        "type": "boolean",
                        "description": "Restart ComfyUI after install",
                        "default": True,
                    },
                },
                "required": ["package_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_and_monitor",
            "description": "Execute workflow, monitor progress, and return final results including output images/video paths.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Max time to wait for completion",
                        "default": 300,
                    },
                    "auto_open_output": {
                        "type": "boolean",
                        "description": "Automatically display output images",
                        "default": True,
                    },
                },
                "required": [],
            },
        },
    },
]


# All tools combined
ALL_TOOLS = CURRENT_TOOLS + FUTURE_TOOLS


def get_tools(include_future: bool = True):
    """Get tool schemas for dataset generation."""
    if include_future:
        return ALL_TOOLS
    return CURRENT_TOOLS
