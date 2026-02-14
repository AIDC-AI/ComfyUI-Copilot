#!/usr/bin/env python3
"""
Production dataset generator for ComfyUI-Copilot fine-tuning.

Generates multi-turn tool-calling conversations in OpenAI/ChatML format,
ready for Unsloth QLoRA fine-tuning on Qwen3 8B.

Output: JSONL where each line is a complete conversation with:
  - system prompt
  - user message
  - assistant tool_calls (one or more turns)
  - tool results
  - final assistant text

Usage:
    python generate_dataset.py --output training_data.jsonl --count 8000
    python generate_dataset.py --output training_data.jsonl --count 8000 --future
    python generate_dataset.py --validate  # dry-run to check templates

Enhanced by Claude Opus 4.6
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import sys
import uuid
from pathlib import Path
from typing import Any

# Local imports
from tool_schemas import CURRENT_TOOLS, FUTURE_TOOLS, ALL_TOOLS
from workflow_templates import (
    ALL_TEMPLATES,
    BASIC_TXT2IMG,
    BASIC_TXT2IMG_SDXL,
    BASIC_TXT2IMG_FLUX,
    IMG2IMG,
    INPAINTING,
    UPSCALE_SIMPLE,
    UPSCALE_HIRES,
    TXT2IMG_WITH_LORA,
    TXT2IMG_MULTI_LORA,
    CONTROLNET_CANNY,
    GENERATE_UPSCALE_FACEFIX,
    CHECKPOINTS_SD15,
    CHECKPOINTS_SDXL,
    CHECKPOINTS_FLUX,
    FLUX_UNETS,
    FLUX_CLIPS_L,
    FLUX_CLIPS_T5,
    FLUX_VAES,
    LORA_NAMES,
    CONTROLNET_MODELS,
    UPSCALE_MODELS,
    SAMPLERS,
    SCHEDULERS,
    RESOLUTIONS_SD15,
    RESOLUTIONS_SDXL,
    POSITIVE_PROMPTS,
    NEGATIVE_PROMPTS,
)


# ---------------------------------------------------------------------------
# System prompt (matches what the model sees at inference)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a ComfyUI workflow assistant. You help users build, modify, and run Stable Diffusion workflows.

RULES:
1. Call plan_tasks FIRST to outline your approach.
2. Use search_nodes to find available nodes before building.
3. Use list_available_models to check what models the user has.
4. Build workflows as valid JSON: {"node_id": {"class_type": "Name", "inputs": {...}}}
5. Connections use format: ["source_node_id", output_index]
6. ONLY save_workflow places nodes on canvas. No other tool modifies the workflow.
7. After saving, use validate_workflow to check for errors.
8. If user wants to run it, use execute_workflow then check_execution_result.

PARAMETER KNOWLEDGE:
- SD 1.5: 512x512, CFG 7-8, 20-30 steps, euler/dpmpp_2m
- SDXL: 1024x1024, CFG 5-7, 25-35 steps, euler/dpmpp_2m_sde
- Flux: 1024x1024, CFG 1.0, 20 steps, euler, simple scheduler
- img2img: denoise 0.4-0.8 (lower = closer to original)
- ControlNet: strength 0.5-1.0
- LoRA: strength 0.5-1.0 for subtle, 1.0-1.5 for strong

Always be helpful, concise, and accurate."""

# Constrained (token-limited) variant
SYSTEM_PROMPT_CONSTRAINED = """ComfyUI assistant. Build workflows with tools.
RULES: plan_tasks first. save_workflow is the ONLY tool that places nodes.
Workflow JSON: {"id": {"class_type":"Name","inputs":{...}}} Connections: ["id",idx]"""


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _uid() -> str:
    """Short unique call id."""
    return f"call_{uuid.uuid4().hex[:12]}"


def _seed() -> int:
    return random.randint(1, 2**31)


def _pick(lst: list):
    return random.choice(lst)


def _pick_prompt(category: str | None = None) -> str:
    if category and category in POSITIVE_PROMPTS:
        return _pick(POSITIVE_PROMPTS[category])
    cat = _pick(list(POSITIVE_PROMPTS.keys()))
    return _pick(POSITIVE_PROMPTS[cat])


def _pick_negative() -> str:
    return _pick(NEGATIVE_PROMPTS)


def _fill_workflow(template: dict, overrides: dict[str, Any] | None = None) -> dict:
    """Deep-copy a workflow template and fill in {{PLACEHOLDERS}} with
    realistic random values. Returns ready-to-serialize workflow JSON."""
    wf = copy.deepcopy(template["workflow"])
    # Flatten to JSON string, do replacements, parse back
    s = json.dumps(wf)

    prompt_cat = _pick(list(POSITIVE_PROMPTS.keys()))
    positive = _pick(POSITIVE_PROMPTS[prompt_cat])
    negative = _pick_negative()

    defaults = {
        "{{CHECKPOINT}}": _pick(CHECKPOINTS_SD15),
        "{{CHECKPOINT_SDXL}}": _pick(CHECKPOINTS_SDXL),
        "{{CHECKPOINT_INPAINT}}": _pick(CHECKPOINTS_SD15),
        "{{FLUX_UNET}}": _pick(FLUX_UNETS),
        "{{CLIP_L}}": _pick(FLUX_CLIPS_L),
        "{{CLIP_T5}}": _pick(FLUX_CLIPS_T5),
        "{{FLUX_VAE}}": _pick(FLUX_VAES),
        "{{POSITIVE_PROMPT}}": positive,
        "{{NEGATIVE_PROMPT}}": negative,
        "{{SEED}}": str(_seed()),
        "{{STEPS}}": str(random.choice([15, 20, 25, 30, 35])),
        "{{CFG}}": str(random.choice([5.0, 6.0, 7.0, 7.5, 8.0])),
        "{{SAMPLER}}": _pick(SAMPLERS),
        "{{SCHEDULER}}": _pick(SCHEDULERS),
        "{{DENOISE}}": str(round(random.uniform(0.4, 0.8), 2)),
        "{{WIDTH}}": "512",
        "{{HEIGHT}}": "512",
        "{{INPUT_IMAGE}}": "input_image.png",
        "{{MASK_IMAGE}}": "mask_image.png",
        "{{LORA_NAME}}": _pick(LORA_NAMES),
        "{{LORA_STRENGTH_MODEL}}": str(round(random.uniform(0.5, 1.2), 2)),
        "{{LORA_STRENGTH_CLIP}}": str(round(random.uniform(0.5, 1.2), 2)),
        "{{LORA_NAME_1}}": _pick(LORA_NAMES),
        "{{LORA_NAME_2}}": _pick(LORA_NAMES),
        "{{LORA_STRENGTH_1}}": str(round(random.uniform(0.5, 1.0), 2)),
        "{{LORA_STRENGTH_2}}": str(round(random.uniform(0.3, 0.8), 2)),
        "{{CONTROLNET_MODEL}}": _pick(CONTROLNET_MODELS),
        "{{CONTROLNET_STRENGTH}}": str(round(random.uniform(0.5, 1.0), 2)),
        "{{UPSCALE_MODEL}}": _pick(UPSCALE_MODELS),
    }

    # Assign resolution based on template type
    name = template.get("name", "")
    if "sdxl" in name or "controlnet" in name:
        w, h = _pick(RESOLUTIONS_SDXL)
    elif "flux" in name:
        w, h = _pick(RESOLUTIONS_SDXL)  # Flux uses similar res
    else:
        w, h = _pick(RESOLUTIONS_SD15)
    defaults["{{WIDTH}}"] = str(w)
    defaults["{{HEIGHT}}"] = str(h)

    if overrides:
        defaults.update(overrides)

    for placeholder, value in defaults.items():
        s = s.replace(placeholder, value)

    return json.loads(s)


def _mk_tool_call(name: str, arguments: dict) -> dict:
    """Build an assistant tool_call entry."""
    return {
        "id": _uid(),
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(arguments),
        },
    }


def _mk_tool_result(call_id: str, content: Any) -> dict:
    """Build a tool result message."""
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "content": json.dumps(content) if not isinstance(content, str) else content,
    }


def _mk_assistant_text(text: str) -> dict:
    return {"role": "assistant", "content": text}


def _mk_assistant_tools(tool_calls: list[dict]) -> dict:
    return {"role": "assistant", "content": None, "tool_calls": tool_calls}


def _mk_user(text: str) -> dict:
    return {"role": "user", "content": text}


def _mk_system(text: str) -> dict:
    return {"role": "system", "content": text}


# ---------------------------------------------------------------------------
# Realistic tool result generators
# ---------------------------------------------------------------------------

def _search_result(query: str, found_nodes: list[str]) -> dict:
    """Fake search_nodes result."""
    results = []
    for node in found_nodes[:5]:
        results.append({
            "class_type": node,
            "category": f"{'_'.join(node.split('_')[:1]).lower()}/nodes",
            "display_name": node.replace("_", " "),
        })
    return {"results": results, "total": len(results)}


def _model_list_result(model_type: str, models: list[str]) -> dict:
    """Fake list_available_models result."""
    return {"model_type": model_type, "models": models[:20]}


def _save_result(version_id: str = None) -> dict:
    """Fake save_workflow result."""
    vid = version_id or uuid.uuid4().hex[:8]
    return {
        "success": True,
        "version_id": vid,
        "ext": [
            {"type": "workflow_update", "data": {"workflow_data": "..."}},
            {"type": "workflow_update_complete",
             "data": {"description": "Workflow saved", "version_id": vid}},
        ],
    }


def _validate_result(valid: bool = True, errors: list[str] | None = None) -> dict:
    return {"valid": valid, "errors": errors or []}


def _execute_result() -> dict:
    pid = uuid.uuid4().hex[:12]
    return {"prompt_id": pid, "status": "queued"}


def _check_result(prompt_id: str, done: bool = True) -> dict:
    if done:
        return {
            "prompt_id": prompt_id,
            "status": "completed",
            "outputs": {"7": {"images": [{"filename": "ComfyUI_00001_.png", "type": "output"}]}},
        }
    return {"prompt_id": prompt_id, "status": "running", "progress": 0.6}


def _current_workflow_result(workflow: dict | None = None) -> dict:
    if workflow:
        return {"workflow": workflow}
    return {"workflow": {}, "message": "No workflow loaded"}


# ------ Future tool results ------

def _prepare_image_result(path: str) -> dict:
    return {
        "success": True,
        "output_path": path.replace(".png", "_prepared.png"),
        "original_size": [random.randint(800, 4000), random.randint(800, 4000)],
        "new_size": [512, 512],
        "crop_applied": True,
    }


def _prepare_video_result(path: str) -> dict:
    return {
        "success": True,
        "output_path": path.replace(".mp4", "_prepared/"),
        "frames_extracted": random.randint(16, 64),
        "fps": 8,
        "duration_seconds": round(random.uniform(2.0, 8.0), 1),
    }


def _analyze_image_result() -> dict:
    return {
        "resolution": [random.choice([512, 768, 1024, 2048]), random.choice([512, 768, 1024, 2048])],
        "format": random.choice(["PNG", "JPEG", "WebP"]),
        "faces_detected": random.randint(0, 3),
        "quality_score": round(random.uniform(0.5, 1.0), 2),
        "content_tags": random.sample(["person", "landscape", "indoor", "outdoor", "animal",
                                        "vehicle", "building", "nature", "art", "food"], 3),
        "suggestions": ["Consider upscaling for better detail", "Good candidate for img2img"],
    }


def _suggest_workflow_result(goal: str) -> dict:
    return {
        "recommended_type": "txt2img",
        "architecture": "sd15",
        "reasoning": f"For '{goal}', a standard txt2img pipeline is recommended.",
        "suggested_models": [_pick(CHECKPOINTS_SD15)],
        "estimated_vram_gb": round(random.uniform(3.0, 8.0), 1),
    }


def _optimize_params_result(model_type: str) -> dict:
    presets = {
        "sd15": {"steps": 20, "cfg": 7.0, "sampler": "euler", "scheduler": "normal"},
        "sdxl": {"steps": 25, "cfg": 6.0, "sampler": "dpmpp_2m_sde", "scheduler": "karras"},
        "flux": {"steps": 20, "cfg": 1.0, "sampler": "euler", "scheduler": "simple"},
        "sd3": {"steps": 28, "cfg": 4.5, "sampler": "dpmpp_2m", "scheduler": "sgm_uniform"},
    }
    return presets.get(model_type, presets["sd15"])


def _batch_result(count: int) -> dict:
    return {
        "success": True,
        "batch_id": uuid.uuid4().hex[:8],
        "total_items": count,
        "estimated_time_minutes": round(count * random.uniform(0.5, 2.0), 1),
    }


def _install_node_result(pkg: str) -> dict:
    return {"success": True, "package": pkg, "restart_required": True}


def _run_and_monitor_result() -> dict:
    return {
        "status": "completed",
        "total_time_seconds": round(random.uniform(5.0, 60.0), 1),
        "outputs": [{"filename": f"ComfyUI_{random.randint(1,99999):05d}_.png", "type": "output"}],
    }


# ---------------------------------------------------------------------------
# CONVERSATION GENERATORS
# ---------------------------------------------------------------------------
# Each generator returns a complete list of messages (conversation turns).
# Categories are weighted to control dataset distribution.


def gen_basic_txt2img(include_future: bool = False) -> list[dict]:
    """Simple text-to-image: plan → search → list models → save → validate."""
    template = _pick([BASIC_TXT2IMG, BASIC_TXT2IMG_SDXL, BASIC_TXT2IMG_FLUX])
    name = template["name"]
    prompt_cat = _pick(list(POSITIVE_PROMPTS.keys()))
    positive = _pick(POSITIVE_PROMPTS[prompt_cat])

    # Vary user phrasing
    user_msgs = [
        f"Create a text-to-image workflow for: {positive}",
        f"I want to generate an image of: {positive}",
        f"Build me a workflow that generates: {positive}",
        f"Make a txt2img workflow. Prompt: {positive}",
        f"Generate an image with this description: {positive}",
        f"Can you set up a basic image generation workflow? I want: {positive}",
        f"Help me create a workflow to make: {positive}",
        f"I need a {prompt_cat} image: {positive}",
    ]

    messages = [_mk_system(SYSTEM_PROMPT), _mk_user(_pick(user_msgs))]

    # Turn 1: plan
    plan_call = _mk_tool_call("plan_tasks", {
        "tasks": [
            "Search for required nodes (checkpoint loader, CLIP encode, KSampler, etc.)",
            "List available checkpoint models",
            "Build the txt2img workflow JSON",
            "Save workflow to canvas",
            "Validate the workflow",
        ]
    })
    messages.append(_mk_assistant_tools([plan_call]))
    messages.append(_mk_tool_result(plan_call["id"], {"status": "ok", "tasks_count": 5}))

    # Turn 2: search nodes
    search_call = _mk_tool_call("search_nodes", {"query": "checkpoint sampler"})
    messages.append(_mk_assistant_tools([search_call]))
    relevant_nodes = ["CheckpointLoaderSimple", "KSampler", "CLIPTextEncode",
                      "EmptyLatentImage", "VAEDecode", "SaveImage"]
    if "flux" in name:
        relevant_nodes = ["UNETLoader", "DualCLIPLoader", "VAELoader",
                          "KSampler", "CLIPTextEncode", "EmptySD3LatentImage",
                          "VAEDecode", "SaveImage"]
    messages.append(_mk_tool_result(search_call["id"],
                                     _search_result("checkpoint sampler", relevant_nodes)))

    # Turn 3: list models
    model_type = "checkpoints"
    models = CHECKPOINTS_SD15
    if "sdxl" in name:
        models = CHECKPOINTS_SDXL
    elif "flux" in name:
        models = CHECKPOINTS_FLUX
    list_call = _mk_tool_call("list_available_models", {"model_type": model_type})
    messages.append(_mk_assistant_tools([list_call]))
    messages.append(_mk_tool_result(list_call["id"],
                                     _model_list_result(model_type, models)))

    # Turn 4: save workflow
    filled = _fill_workflow(template, {"{{POSITIVE_PROMPT}}": positive})
    save_call = _mk_tool_call("save_workflow", {
        "workflow_json": json.dumps(filled),
        "description": f"Basic {name} workflow",
    })
    messages.append(_mk_assistant_tools([save_call]))
    messages.append(_mk_tool_result(save_call["id"], _save_result()))

    # Turn 5: validate
    val_call = _mk_tool_call("validate_workflow", {"reason": "check new workflow"})
    messages.append(_mk_assistant_tools([val_call]))
    messages.append(_mk_tool_result(val_call["id"], _validate_result(True)))

    # Final response
    model_name = list(filled.values())[0]["inputs"].get(
        "ckpt_name", filled.get("1", {}).get("inputs", {}).get("unet_name", "model"))
    messages.append(_mk_assistant_text(
        f"I've created a {name.replace('_', ' ')} workflow using {model_name}. "
        f"The workflow is now on your canvas and validated successfully. "
        f"You can hit Queue Prompt to generate the image, or let me know if "
        f"you'd like to adjust any parameters."
    ))

    return messages


def gen_img2img(include_future: bool = False) -> list[dict]:
    """Image-to-image workflow with denoise control."""
    positive = _pick_prompt()

    user_msgs = [
        f"I have an image I want to transform. New style: {positive}",
        f"Do an img2img on my uploaded image with this prompt: {positive}",
        f"Modify my image to look like: {positive}",
        f"Apply this style to my photo: {positive}",
    ]

    messages = [_mk_system(SYSTEM_PROMPT), _mk_user(_pick(user_msgs))]

    # Plan
    plan_call = _mk_tool_call("plan_tasks", {
        "tasks": [
            "Check current workflow for loaded image",
            "Search for img2img-related nodes",
            "List available checkpoints",
            "Build img2img workflow with appropriate denoise",
            "Save and validate",
        ]
    })
    messages.append(_mk_assistant_tools([plan_call]))
    messages.append(_mk_tool_result(plan_call["id"], {"status": "ok", "tasks_count": 5}))

    # Check current workflow
    wf_call = _mk_tool_call("get_current_workflow_for_agent", {"reason": "check for loaded image"})
    messages.append(_mk_assistant_tools([wf_call]))
    messages.append(_mk_tool_result(wf_call["id"], _current_workflow_result()))

    # Search
    search_call = _mk_tool_call("search_nodes", {"query": "VAEEncode LoadImage"})
    messages.append(_mk_assistant_tools([search_call]))
    messages.append(_mk_tool_result(search_call["id"],
                                     _search_result("VAEEncode", ["LoadImage", "VAEEncode",
                                                                   "CheckpointLoaderSimple",
                                                                   "KSampler", "VAEDecode"])))

    # List models
    list_call = _mk_tool_call("list_available_models", {"model_type": "checkpoints"})
    messages.append(_mk_assistant_tools([list_call]))
    messages.append(_mk_tool_result(list_call["id"],
                                     _model_list_result("checkpoints", CHECKPOINTS_SD15)))

    # Save
    filled = _fill_workflow(IMG2IMG, {"{{POSITIVE_PROMPT}}": positive})
    save_call = _mk_tool_call("save_workflow", {
        "workflow_json": json.dumps(filled),
        "description": "img2img workflow",
    })
    messages.append(_mk_assistant_tools([save_call]))
    messages.append(_mk_tool_result(save_call["id"], _save_result()))

    # Validate
    val_call = _mk_tool_call("validate_workflow", {})
    messages.append(_mk_assistant_tools([val_call]))
    messages.append(_mk_tool_result(val_call["id"], _validate_result(True)))

    denoise = filled["6"]["inputs"]["denoise"]
    messages.append(_mk_assistant_text(
        f"Your img2img workflow is ready! I've set the denoise to {denoise} "
        f"— lower values keep more of the original image. "
        f"Load your source image into the LoadImage node and hit Queue Prompt."
    ))

    return messages


def gen_lora_workflow(include_future: bool = False) -> list[dict]:
    """LoRA workflow with model/clip strength tuning."""
    template = _pick([TXT2IMG_WITH_LORA, TXT2IMG_MULTI_LORA])
    prompt_cat = _pick(list(POSITIVE_PROMPTS.keys()))
    positive = _pick(POSITIVE_PROMPTS[prompt_cat])
    lora = _pick(LORA_NAMES)

    user_msgs = [
        f"Create a workflow using the {lora} LoRA for: {positive}",
        f"I want to use my {lora} LoRA. Generate: {positive}",
        f"Add LoRA {lora} to a txt2img workflow. Prompt: {positive}",
        f"Build a workflow with LoRA for {prompt_cat} style: {positive}",
    ]

    messages = [_mk_system(SYSTEM_PROMPT), _mk_user(_pick(user_msgs))]

    plan_call = _mk_tool_call("plan_tasks", {
        "tasks": [
            "Search for LoRA loader node",
            "List available LoRAs and checkpoints",
            "Build txt2img workflow with LoRA applied",
            "Save and validate",
        ]
    })
    messages.append(_mk_assistant_tools([plan_call]))
    messages.append(_mk_tool_result(plan_call["id"], {"status": "ok", "tasks_count": 4}))

    # Search for LoRA node
    search_call = _mk_tool_call("search_nodes", {"query": "LoraLoader"})
    messages.append(_mk_assistant_tools([search_call]))
    messages.append(_mk_tool_result(search_call["id"],
                                     _search_result("LoraLoader", ["LoraLoader", "LoraLoaderModelOnly"])))

    # List LoRAs
    lora_call = _mk_tool_call("list_available_models", {"model_type": "loras"})
    messages.append(_mk_assistant_tools([lora_call]))
    messages.append(_mk_tool_result(lora_call["id"],
                                     _model_list_result("loras", LORA_NAMES)))

    # Save
    filled = _fill_workflow(template, {
        "{{POSITIVE_PROMPT}}": positive,
        "{{LORA_NAME}}": lora,
        "{{LORA_NAME_1}}": lora,
    })
    save_call = _mk_tool_call("save_workflow", {
        "workflow_json": json.dumps(filled),
        "description": f"LoRA workflow with {lora}",
    })
    messages.append(_mk_assistant_tools([save_call]))
    messages.append(_mk_tool_result(save_call["id"], _save_result()))

    val_call = _mk_tool_call("validate_workflow", {})
    messages.append(_mk_assistant_tools([val_call]))
    messages.append(_mk_tool_result(val_call["id"], _validate_result(True)))

    messages.append(_mk_assistant_text(
        f"Done! I've built a workflow with the {lora} LoRA applied. "
        f"The LoRA strengthens the model and CLIP conditioning. "
        f"Adjust the strength values if the effect is too strong or too subtle."
    ))

    return messages


def gen_upscale(include_future: bool = False) -> list[dict]:
    """Upscaling workflow."""
    template = _pick([UPSCALE_SIMPLE, UPSCALE_HIRES])

    user_msgs = [
        "Upscale my image to higher resolution",
        "I need to make this image bigger without losing quality",
        "Create an upscaling workflow for my image",
        "Set up a hi-res fix workflow to upscale",
        "My image is too small, help me upscale it",
    ]

    messages = [_mk_system(SYSTEM_PROMPT), _mk_user(_pick(user_msgs))]

    plan_call = _mk_tool_call("plan_tasks", {
        "tasks": [
            "Search for upscale-related nodes",
            "List available upscale models",
            "Build upscaling workflow",
            "Save and validate",
        ]
    })
    messages.append(_mk_assistant_tools([plan_call]))
    messages.append(_mk_tool_result(plan_call["id"], {"status": "ok", "tasks_count": 4}))

    search_call = _mk_tool_call("search_nodes", {"query": "upscale"})
    messages.append(_mk_assistant_tools([search_call]))
    messages.append(_mk_tool_result(search_call["id"],
                                     _search_result("upscale", ["UpscaleModelLoader",
                                                                 "ImageUpscaleWithModel",
                                                                 "LatentUpscale", "ImageScale"])))

    list_call = _mk_tool_call("list_available_models", {"model_type": "upscale_models"})
    messages.append(_mk_assistant_tools([list_call]))
    messages.append(_mk_tool_result(list_call["id"],
                                     _model_list_result("upscale_models", UPSCALE_MODELS)))

    filled = _fill_workflow(template)
    save_call = _mk_tool_call("save_workflow", {
        "workflow_json": json.dumps(filled),
        "description": f"Upscale workflow ({template['name']})",
    })
    messages.append(_mk_assistant_tools([save_call]))
    messages.append(_mk_tool_result(save_call["id"], _save_result()))

    val_call = _mk_tool_call("validate_workflow", {})
    messages.append(_mk_assistant_tools([val_call]))
    messages.append(_mk_tool_result(val_call["id"], _validate_result(True)))

    messages.append(_mk_assistant_text(
        f"Your {template['name'].replace('_', ' ')} workflow is ready. "
        f"Load your image and run it to upscale. The output will be higher resolution."
    ))

    return messages


def gen_controlnet(include_future: bool = False) -> list[dict]:
    """ControlNet workflow generation."""
    positive = _pick_prompt()
    cn_model = _pick(CONTROLNET_MODELS)

    user_msgs = [
        f"Create a ControlNet workflow using {cn_model}: {positive}",
        f"I want to use ControlNet with my reference image. Style: {positive}",
        f"Set up a canny ControlNet workflow for: {positive}",
        f"Build a ControlNet-guided generation workflow: {positive}",
    ]

    messages = [_mk_system(SYSTEM_PROMPT), _mk_user(_pick(user_msgs))]

    plan_call = _mk_tool_call("plan_tasks", {
        "tasks": [
            "Search for ControlNet nodes",
            "List available ControlNet models",
            "Build ControlNet workflow with edge detection",
            "Save and validate the workflow",
        ]
    })
    messages.append(_mk_assistant_tools([plan_call]))
    messages.append(_mk_tool_result(plan_call["id"], {"status": "ok", "tasks_count": 4}))

    search_call = _mk_tool_call("search_nodes", {"query": "ControlNet"})
    messages.append(_mk_assistant_tools([search_call]))
    messages.append(_mk_tool_result(search_call["id"],
                                     _search_result("ControlNet",
                                                    ["ControlNetLoader",
                                                     "ControlNetApplyAdvanced",
                                                     "CannyEdgePreprocessor"])))

    list_call = _mk_tool_call("list_available_models", {"model_type": "controlnet"})
    messages.append(_mk_assistant_tools([list_call]))
    messages.append(_mk_tool_result(list_call["id"],
                                     _model_list_result("controlnet", CONTROLNET_MODELS)))

    filled = _fill_workflow(CONTROLNET_CANNY, {
        "{{POSITIVE_PROMPT}}": positive,
        "{{CONTROLNET_MODEL}}": cn_model,
    })
    save_call = _mk_tool_call("save_workflow", {
        "workflow_json": json.dumps(filled),
        "description": "ControlNet workflow",
    })
    messages.append(_mk_assistant_tools([save_call]))
    messages.append(_mk_tool_result(save_call["id"], _save_result()))

    val_call = _mk_tool_call("validate_workflow", {})
    messages.append(_mk_assistant_tools([val_call]))
    messages.append(_mk_tool_result(val_call["id"], _validate_result(True)))

    messages.append(_mk_assistant_text(
        f"ControlNet workflow is ready with {cn_model}. "
        f"Load your reference image into the LoadImage node. "
        f"Adjust the ControlNet strength (currently set in the Apply node) to control "
        f"how closely the output follows your reference."
    ))

    return messages


def gen_inpainting(include_future: bool = False) -> list[dict]:
    """Inpainting workflow."""
    positive = _pick_prompt()

    user_msgs = [
        f"I need to inpaint part of my image. Replace with: {positive}",
        f"Set up an inpainting workflow. Fill area: {positive}",
        f"Create an inpaint workflow to fix part of my image: {positive}",
        f"Help me replace a section of my image with: {positive}",
    ]

    messages = [_mk_system(SYSTEM_PROMPT), _mk_user(_pick(user_msgs))]

    plan_call = _mk_tool_call("plan_tasks", {
        "tasks": [
            "Search for inpainting nodes",
            "List available inpainting-compatible checkpoints",
            "Build inpainting workflow with mask support",
            "Save and validate",
        ]
    })
    messages.append(_mk_assistant_tools([plan_call]))
    messages.append(_mk_tool_result(plan_call["id"], {"status": "ok", "tasks_count": 4}))

    search_call = _mk_tool_call("search_nodes", {"query": "inpaint mask VAEEncode"})
    messages.append(_mk_assistant_tools([search_call]))
    messages.append(_mk_tool_result(search_call["id"],
                                     _search_result("inpaint", ["VAEEncodeForInpaint",
                                                                 "LoadImage", "InvertMask"])))

    list_call = _mk_tool_call("list_available_models", {"model_type": "checkpoints"})
    messages.append(_mk_assistant_tools([list_call]))
    messages.append(_mk_tool_result(list_call["id"],
                                     _model_list_result("checkpoints", CHECKPOINTS_SD15)))

    filled = _fill_workflow(INPAINTING, {"{{POSITIVE_PROMPT}}": positive})
    save_call = _mk_tool_call("save_workflow", {
        "workflow_json": json.dumps(filled),
        "description": "Inpainting workflow",
    })
    messages.append(_mk_assistant_tools([save_call]))
    messages.append(_mk_tool_result(save_call["id"], _save_result()))

    val_call = _mk_tool_call("validate_workflow", {})
    messages.append(_mk_assistant_tools([val_call]))
    messages.append(_mk_tool_result(val_call["id"], _validate_result(True)))

    messages.append(_mk_assistant_text(
        "Inpainting workflow is set up. Load your image into the first LoadImage node "
        "and your mask into the second. White areas in the mask will be inpainted. "
        "The grow_mask_by setting adds a slight feather for smoother blending."
    ))

    return messages


def gen_full_pipeline(include_future: bool = False) -> list[dict]:
    """Multi-stage: generate → upscale → face fix. Shows chaining."""
    positive = _pick_prompt("portrait")

    user_msgs = [
        f"Generate a portrait, upscale it, and fix the face: {positive}",
        f"I want a full pipeline: generate a face image, upscale, and restore: {positive}",
        f"Create a complete workflow that generates, upscales, and does face restoration: {positive}",
    ]

    messages = [_mk_system(SYSTEM_PROMPT), _mk_user(_pick(user_msgs))]

    plan_call = _mk_tool_call("plan_tasks", {
        "tasks": [
            "Search for generation, upscale, and face restoration nodes",
            "List available checkpoints and upscale models",
            "Build multi-stage pipeline workflow",
            "Save and validate the complete pipeline",
        ]
    })
    messages.append(_mk_assistant_tools([plan_call]))
    messages.append(_mk_tool_result(plan_call["id"], {"status": "ok", "tasks_count": 4}))

    search_call = _mk_tool_call("search_nodes", {"query": "checkpoint sampler upscale"})
    messages.append(_mk_assistant_tools([search_call]))
    messages.append(_mk_tool_result(search_call["id"],
                                     _search_result("pipeline", ["CheckpointLoaderSimple",
                                                                  "KSampler", "VAEDecode",
                                                                  "UpscaleModelLoader",
                                                                  "ImageUpscaleWithModel"])))

    list_call = _mk_tool_call("list_available_models", {"model_type": "checkpoints"})
    upscale_call = _mk_tool_call("list_available_models", {"model_type": "upscale_models"})
    messages.append(_mk_assistant_tools([list_call, upscale_call]))
    messages.append(_mk_tool_result(list_call["id"],
                                     _model_list_result("checkpoints", CHECKPOINTS_SD15)))
    messages.append(_mk_tool_result(upscale_call["id"],
                                     _model_list_result("upscale_models", UPSCALE_MODELS)))

    filled = _fill_workflow(GENERATE_UPSCALE_FACEFIX, {"{{POSITIVE_PROMPT}}": positive})
    save_call = _mk_tool_call("save_workflow", {
        "workflow_json": json.dumps(filled),
        "description": "Full pipeline: generate → upscale → face fix",
    })
    messages.append(_mk_assistant_tools([save_call]))
    messages.append(_mk_tool_result(save_call["id"], _save_result()))

    val_call = _mk_tool_call("validate_workflow", {})
    messages.append(_mk_assistant_tools([val_call]))
    messages.append(_mk_tool_result(val_call["id"], _validate_result(True)))

    messages.append(_mk_assistant_text(
        f"Complete pipeline ready! The workflow will:\n"
        f"1. Generate a 512x512 image\n"
        f"2. Upscale with {_pick(UPSCALE_MODELS)}\n"
        f"3. Scale to 1024x1024 final output\n"
        f"Hit Queue Prompt to run the full pipeline."
    ))

    return messages


def gen_execute_and_check(include_future: bool = False) -> list[dict]:
    """User asks to run a workflow and check results."""
    user_msgs = [
        "Run the workflow and show me the results",
        "Execute this workflow please",
        "Queue it up and let me know when it's done",
        "Start the generation",
        "Run my workflow",
    ]

    messages = [_mk_system(SYSTEM_PROMPT), _mk_user(_pick(user_msgs))]

    plan_call = _mk_tool_call("plan_tasks", {
        "tasks": [
            "Validate the current workflow first",
            "Execute the workflow",
            "Check execution results",
        ]
    })
    messages.append(_mk_assistant_tools([plan_call]))
    messages.append(_mk_tool_result(plan_call["id"], {"status": "ok", "tasks_count": 3}))

    # Validate first
    val_call = _mk_tool_call("validate_workflow", {"reason": "pre-execution check"})
    messages.append(_mk_assistant_tools([val_call]))
    messages.append(_mk_tool_result(val_call["id"], _validate_result(True)))

    # Execute
    exec_call = _mk_tool_call("execute_workflow", {"reason": "user requested execution"})
    messages.append(_mk_assistant_tools([exec_call]))
    exec_res = _execute_result()
    messages.append(_mk_tool_result(exec_call["id"], exec_res))

    # Check result
    check_call = _mk_tool_call("check_execution_result", {"prompt_id": exec_res["prompt_id"]})
    messages.append(_mk_assistant_tools([check_call]))
    messages.append(_mk_tool_result(check_call["id"],
                                     _check_result(exec_res["prompt_id"], done=True)))

    messages.append(_mk_assistant_text(
        "Workflow executed successfully! The output image has been saved. "
        "You should see it in the preview. Let me know if you'd like any adjustments."
    ))

    return messages


def gen_modify_existing(include_future: bool = False) -> list[dict]:
    """User asks to modify an existing workflow — add LoRA, change model, etc."""
    modification = _pick([
        ("add a LoRA", "lora_addition"),
        ("change the checkpoint model", "model_swap"),
        ("increase the resolution", "resolution_change"),
        ("adjust the CFG scale", "cfg_change"),
        ("change the sampler", "sampler_change"),
        ("add an upscaler at the end", "add_upscale"),
    ])

    user_msgs = [
        f"Can you {modification[0]} in my current workflow?",
        f"I want to {modification[0]}",
        f"Modify my workflow to {modification[0]}",
        f"Please {modification[0]} for me",
    ]

    messages = [_mk_system(SYSTEM_PROMPT), _mk_user(_pick(user_msgs))]

    plan_call = _mk_tool_call("plan_tasks", {
        "tasks": [
            "Get the current workflow",
            f"Modify: {modification[0]}",
            "Save updated workflow",
            "Validate changes",
        ]
    })
    messages.append(_mk_assistant_tools([plan_call]))
    messages.append(_mk_tool_result(plan_call["id"], {"status": "ok", "tasks_count": 4}))

    # Get current workflow
    existing = _fill_workflow(BASIC_TXT2IMG)
    wf_call = _mk_tool_call("get_current_workflow_for_agent", {"reason": "inspect before modification"})
    messages.append(_mk_assistant_tools([wf_call]))
    messages.append(_mk_tool_result(wf_call["id"], _current_workflow_result(existing)))

    # For LoRA addition, also search
    if modification[1] == "lora_addition":
        search_call = _mk_tool_call("search_nodes", {"query": "LoraLoader"})
        messages.append(_mk_assistant_tools([search_call]))
        messages.append(_mk_tool_result(search_call["id"],
                                         _search_result("LoraLoader", ["LoraLoader"])))

        list_call = _mk_tool_call("list_available_models", {"model_type": "loras"})
        messages.append(_mk_assistant_tools([list_call]))
        messages.append(_mk_tool_result(list_call["id"],
                                         _model_list_result("loras", LORA_NAMES)))

        # Build modified workflow with LoRA
        modified = _fill_workflow(TXT2IMG_WITH_LORA)
    elif modification[1] == "model_swap":
        list_call = _mk_tool_call("list_available_models", {"model_type": "checkpoints"})
        messages.append(_mk_assistant_tools([list_call]))
        messages.append(_mk_tool_result(list_call["id"],
                                         _model_list_result("checkpoints", CHECKPOINTS_SD15)))
        modified = copy.deepcopy(existing)
        modified["1"]["inputs"]["ckpt_name"] = _pick(CHECKPOINTS_SD15)
    elif modification[1] == "add_upscale":
        search_call = _mk_tool_call("search_nodes", {"query": "upscale model"})
        messages.append(_mk_assistant_tools([search_call]))
        messages.append(_mk_tool_result(search_call["id"],
                                         _search_result("upscale",
                                                        ["UpscaleModelLoader",
                                                         "ImageUpscaleWithModel"])))
        modified = _fill_workflow(UPSCALE_HIRES)
    else:
        modified = copy.deepcopy(existing)
        if modification[1] == "resolution_change":
            w, h = _pick(RESOLUTIONS_SDXL)
            modified["4"]["inputs"]["width"] = w
            modified["4"]["inputs"]["height"] = h
        elif modification[1] == "cfg_change":
            modified["5"]["inputs"]["cfg"] = random.choice([5.0, 6.0, 8.0, 10.0])
        elif modification[1] == "sampler_change":
            modified["5"]["inputs"]["sampler_name"] = _pick(SAMPLERS)

    save_call = _mk_tool_call("save_workflow", {
        "workflow_json": json.dumps(modified),
        "description": f"Modified workflow: {modification[0]}",
    })
    messages.append(_mk_assistant_tools([save_call]))
    messages.append(_mk_tool_result(save_call["id"], _save_result()))

    val_call = _mk_tool_call("validate_workflow", {})
    messages.append(_mk_assistant_tools([val_call]))
    messages.append(_mk_tool_result(val_call["id"], _validate_result(True)))

    messages.append(_mk_assistant_text(
        f"Done! I've updated your workflow to {modification[0]}. "
        f"The changes are saved and validated. Ready to generate!"
    ))

    return messages


def gen_error_recovery(include_future: bool = False) -> list[dict]:
    """Workflow has validation errors — model handles recovery."""
    positive = _pick_prompt()

    messages = [_mk_system(SYSTEM_PROMPT),
                _mk_user(f"Build a workflow for: {positive}")]

    plan_call = _mk_tool_call("plan_tasks", {
        "tasks": [
            "Build the workflow",
            "Save to canvas",
            "Validate and fix any errors",
        ]
    })
    messages.append(_mk_assistant_tools([plan_call]))
    messages.append(_mk_tool_result(plan_call["id"], {"status": "ok", "tasks_count": 3}))

    # Save a workflow with an intentional issue
    filled = _fill_workflow(BASIC_TXT2IMG, {"{{POSITIVE_PROMPT}}": positive})
    save_call = _mk_tool_call("save_workflow", {
        "workflow_json": json.dumps(filled),
        "description": "Initial workflow attempt",
    })
    messages.append(_mk_assistant_tools([save_call]))
    messages.append(_mk_tool_result(save_call["id"], _save_result()))

    # Validation fails
    val_call = _mk_tool_call("validate_workflow", {})
    messages.append(_mk_assistant_tools([val_call]))
    error_msg = _pick([
        "Node 1: checkpoint file not found",
        "Node 5: missing required input 'model'",
        "Connection error: node 3 output type mismatch",
        "Node 4: invalid dimensions (must be divisible by 8)",
    ])
    messages.append(_mk_tool_result(val_call["id"], _validate_result(False, [error_msg])))

    # Search for fix
    messages.append(_mk_assistant_text(
        f"The validation found an issue: {error_msg}. Let me fix that."
    ))

    # Get available models to fix the issue
    list_call = _mk_tool_call("list_available_models", {"model_type": "checkpoints"})
    messages.append(_mk_assistant_tools([list_call]))
    messages.append(_mk_tool_result(list_call["id"],
                                     _model_list_result("checkpoints", CHECKPOINTS_SD15)))

    # Save fixed version
    fixed = _fill_workflow(BASIC_TXT2IMG, {"{{POSITIVE_PROMPT}}": positive})
    save_call2 = _mk_tool_call("save_workflow", {
        "workflow_json": json.dumps(fixed),
        "description": "Fixed workflow — corrected validation errors",
    })
    messages.append(_mk_assistant_tools([save_call2]))
    messages.append(_mk_tool_result(save_call2["id"], _save_result()))

    val_call2 = _mk_tool_call("validate_workflow", {})
    messages.append(_mk_assistant_tools([val_call2]))
    messages.append(_mk_tool_result(val_call2["id"], _validate_result(True)))

    messages.append(_mk_assistant_text(
        "Fixed! The workflow now validates successfully. The issue was resolved "
        "by using a confirmed available checkpoint. Ready to generate."
    ))

    return messages


def gen_node_details_exploration(include_future: bool = False) -> list[dict]:
    """User asks about specific nodes — model uses get_node_details."""
    node_queries = [
        ("KSampler", "How does the KSampler node work?"),
        ("ControlNetApplyAdvanced", "What inputs does the ControlNet Apply node need?"),
        ("LoraLoader", "Tell me about the LoRA loader node"),
        ("VAEDecode", "What does VAEDecode do?"),
        ("CLIPTextEncode", "How do I use the CLIP text encoder?"),
    ]
    node_class, user_q = _pick(node_queries)

    messages = [_mk_system(SYSTEM_PROMPT), _mk_user(user_q)]

    detail_call = _mk_tool_call("get_node_details", {"node_class": node_class})
    messages.append(_mk_assistant_tools([detail_call]))

    # Realistic node detail response
    detail = {
        "class_type": node_class,
        "inputs": {
            "required": {"model": "MODEL", "positive": "CONDITIONING"},
            "optional": {"seed": "INT", "steps": "INT", "cfg": "FLOAT"},
        },
        "outputs": ["LATENT"],
        "category": "sampling",
    }
    messages.append(_mk_tool_result(detail_call["id"], detail))

    messages.append(_mk_assistant_text(
        f"The **{node_class}** node takes these inputs:\n"
        f"- Required: model, positive/negative conditioning\n"
        f"- Optional: seed, steps, CFG scale, sampler settings\n"
        f"It outputs a latent image that you pass to VAEDecode for the final image."
    ))

    return messages


# ---------------------------------------------------------------------------
# FUTURE TOOL GENERATORS  (include_future=True conversations)
# ---------------------------------------------------------------------------

def gen_full_automation(include_future: bool = False) -> list[dict]:
    """User gives a high-level goal → model plans, builds, executes, checks."""
    if not include_future:
        return gen_basic_txt2img(False)  # fallback

    positive = _pick_prompt()
    user_msgs = [
        f"I just want a beautiful image of: {positive}. Handle everything.",
        f"Generate this for me end to end: {positive}",
        f"Full auto: {positive}",
        f"Just make this happen: {positive}",
    ]

    messages = [_mk_system(SYSTEM_PROMPT), _mk_user(_pick(user_msgs))]

    # Plan
    plan_call = _mk_tool_call("plan_tasks", {
        "tasks": [
            "Analyze the request and suggest optimal workflow",
            "List available models to find the best match",
            "Optimize parameters for the use case",
            "Build and save the workflow",
            "Validate the workflow",
            "Execute and monitor the generation",
        ]
    })
    messages.append(_mk_assistant_tools([plan_call]))
    messages.append(_mk_tool_result(plan_call["id"], {"status": "ok", "tasks_count": 6}))

    # Suggest workflow
    suggest_call = _mk_tool_call("suggest_workflow", {"goal": positive})
    messages.append(_mk_assistant_tools([suggest_call]))
    messages.append(_mk_tool_result(suggest_call["id"], _suggest_workflow_result(positive)))

    # List models
    list_call = _mk_tool_call("list_available_models", {"model_type": "checkpoints"})
    messages.append(_mk_assistant_tools([list_call]))
    messages.append(_mk_tool_result(list_call["id"],
                                     _model_list_result("checkpoints", CHECKPOINTS_SD15)))

    # Optimize params
    opt_call = _mk_tool_call("optimize_parameters", {
        "model_type": "sd15",
        "use_case": _pick(["photo_realistic", "anime", "artistic"]),
    })
    messages.append(_mk_assistant_tools([opt_call]))
    messages.append(_mk_tool_result(opt_call["id"], _optimize_params_result("sd15")))

    # Build and save
    filled = _fill_workflow(BASIC_TXT2IMG, {"{{POSITIVE_PROMPT}}": positive})
    save_call = _mk_tool_call("save_workflow", {
        "workflow_json": json.dumps(filled),
        "description": "Auto-generated optimized workflow",
    })
    messages.append(_mk_assistant_tools([save_call]))
    messages.append(_mk_tool_result(save_call["id"], _save_result()))

    # Validate
    val_call = _mk_tool_call("validate_workflow", {})
    messages.append(_mk_assistant_tools([val_call]))
    messages.append(_mk_tool_result(val_call["id"], _validate_result(True)))

    # Execute and monitor
    run_call = _mk_tool_call("run_and_monitor", {"timeout_seconds": 120, "auto_open_output": True})
    messages.append(_mk_assistant_tools([run_call]))
    messages.append(_mk_tool_result(run_call["id"], _run_and_monitor_result()))

    messages.append(_mk_assistant_text(
        "All done! I've:\n"
        "1. Analyzed your request and chose the best workflow type\n"
        "2. Selected optimal parameters for your model\n"
        "3. Built and saved the workflow\n"
        "4. Executed it — the image is ready!\n\n"
        "The output is displayed. Let me know if you'd like any adjustments."
    ))

    return messages


def gen_image_preparation(include_future: bool = False) -> list[dict]:
    """User wants to prepare media for a workflow."""
    if not include_future:
        return gen_img2img(False)

    user_msgs = [
        "I have a photo I want to use for img2img, can you prep it?",
        "Prepare my image for use as a ControlNet reference",
        "Resize and crop my photo for use in the workflow",
        "My image is 4000x3000, prepare it for SD processing",
    ]

    messages = [_mk_system(SYSTEM_PROMPT), _mk_user(_pick(user_msgs))]

    plan_call = _mk_tool_call("plan_tasks", {
        "tasks": [
            "Analyze the input image",
            "Prepare the image (resize, crop) for the target workflow",
            "Build an img2img workflow using the prepared image",
            "Save and validate",
        ]
    })
    messages.append(_mk_assistant_tools([plan_call]))
    messages.append(_mk_tool_result(plan_call["id"], {"status": "ok", "tasks_count": 4}))

    # Analyze
    analyze_call = _mk_tool_call("analyze_image", {
        "image_path": "user_photo.png",
        "analysis_type": "full",
    })
    messages.append(_mk_assistant_tools([analyze_call]))
    messages.append(_mk_tool_result(analyze_call["id"], _analyze_image_result()))

    # Prepare
    prep_call = _mk_tool_call("prepare_image", {
        "image_path": "user_photo.png",
        "target_width": 512,
        "target_height": 512,
        "crop_mode": "smart",
    })
    messages.append(_mk_assistant_tools([prep_call]))
    messages.append(_mk_tool_result(prep_call["id"], _prepare_image_result("user_photo.png")))

    # Build workflow
    filled = _fill_workflow(IMG2IMG, {"{{INPUT_IMAGE}}": "user_photo_prepared.png"})
    save_call = _mk_tool_call("save_workflow", {
        "workflow_json": json.dumps(filled),
        "description": "img2img with prepared photo",
    })
    messages.append(_mk_assistant_tools([save_call]))
    messages.append(_mk_tool_result(save_call["id"], _save_result()))

    val_call = _mk_tool_call("validate_workflow", {})
    messages.append(_mk_assistant_tools([val_call]))
    messages.append(_mk_tool_result(val_call["id"], _validate_result(True)))

    messages.append(_mk_assistant_text(
        "Your image has been analyzed and prepared:\n"
        "- Resized from the original to 512x512 with smart cropping\n"
        "- An img2img workflow is set up with the prepared image\n"
        "- Denoise is set to a moderate level to keep your original composition\n\n"
        "Ready to generate. Adjust denoise lower to keep more of the original."
    ))

    return messages


def gen_batch_processing(include_future: bool = False) -> list[dict]:
    """User wants to process multiple images/prompts."""
    if not include_future:
        return gen_basic_txt2img(False)

    user_msgs = [
        "Generate 5 variations of a landscape with different seeds",
        "I have 10 images to upscale. Set up batch processing",
        "Run my workflow on these 4 prompts: sunset, moonlight, dawn, golden hour",
        "Batch generate with different styles",
    ]

    messages = [_mk_system(SYSTEM_PROMPT), _mk_user(_pick(user_msgs))]

    plan_call = _mk_tool_call("plan_tasks", {
        "tasks": [
            "Set up the base workflow",
            "Configure batch processing for multiple runs",
            "Execute the batch",
        ]
    })
    messages.append(_mk_assistant_tools([plan_call]))
    messages.append(_mk_tool_result(plan_call["id"], {"status": "ok", "tasks_count": 3}))

    # Build base workflow
    filled = _fill_workflow(BASIC_TXT2IMG)
    save_call = _mk_tool_call("save_workflow", {
        "workflow_json": json.dumps(filled),
        "description": "Base workflow for batching",
    })
    messages.append(_mk_assistant_tools([save_call]))
    messages.append(_mk_tool_result(save_call["id"], _save_result()))

    # Set up batch
    batch_inputs = [str(_seed()) for _ in range(5)]
    batch_call = _mk_tool_call("batch_process", {
        "batch_type": "seeds",
        "inputs": batch_inputs,
        "workflow_node_id": "5",
        "input_field": "seed",
    })
    messages.append(_mk_assistant_tools([batch_call]))
    messages.append(_mk_tool_result(batch_call["id"], _batch_result(5)))

    messages.append(_mk_assistant_text(
        "Batch processing is set up! It will run 5 variations with different seeds. "
        "Estimated time depends on your hardware. The outputs will be saved separately."
    ))

    return messages


def gen_video_preparation(include_future: bool = False) -> list[dict]:
    """User wants to prepare video for AnimateDiff or similar."""
    if not include_future:
        return gen_basic_txt2img(False)

    user_msgs = [
        "I have a video clip I want to use for video-to-video generation",
        "Prepare my video for AnimateDiff processing",
        "Extract frames from my video for img2img batch",
    ]

    messages = [_mk_system(SYSTEM_PROMPT), _mk_user(_pick(user_msgs))]

    plan_call = _mk_tool_call("plan_tasks", {
        "tasks": [
            "Prepare the video (extract frames, resize)",
            "Build a video processing workflow",
            "Save and validate",
        ]
    })
    messages.append(_mk_assistant_tools([plan_call]))
    messages.append(_mk_tool_result(plan_call["id"], {"status": "ok", "tasks_count": 3}))

    prep_call = _mk_tool_call("prepare_video", {
        "video_path": "input_video.mp4",
        "start_time": 0,
        "end_time": 4,
        "extract_frames": True,
        "frame_rate": 8,
        "target_width": 512,
        "target_height": 512,
    })
    messages.append(_mk_assistant_tools([prep_call]))
    messages.append(_mk_tool_result(prep_call["id"], _prepare_video_result("input_video.mp4")))

    messages.append(_mk_assistant_text(
        "Video prepared! Extracted 32 frames at 8 FPS, resized to 512x512. "
        "The frames are ready for AnimateDiff or batch img2img processing. "
        "Would you like me to set up the video generation workflow?"
    ))

    return messages


def gen_install_and_build(include_future: bool = False) -> list[dict]:
    """User needs a custom node installed before building."""
    if not include_future:
        return gen_basic_txt2img(False)

    user_msgs = [
        "I want to use IPAdapter but I don't have it installed",
        "Can you install the AnimateDiff node and set up a video workflow?",
        "I need the face restore node. Install it and build a workflow",
    ]

    messages = [_mk_system(SYSTEM_PROMPT), _mk_user(_pick(user_msgs))]

    plan_call = _mk_tool_call("plan_tasks", {
        "tasks": [
            "Search if the required nodes are available",
            "Install the missing custom node package",
            "Build the workflow using the new nodes",
            "Save and validate",
        ]
    })
    messages.append(_mk_assistant_tools([plan_call]))
    messages.append(_mk_tool_result(plan_call["id"], {"status": "ok", "tasks_count": 4}))

    # Search shows node not found
    search_call = _mk_tool_call("search_nodes", {"query": "IPAdapter"})
    messages.append(_mk_assistant_tools([search_call]))
    messages.append(_mk_tool_result(search_call["id"], {"results": [], "total": 0}))

    # Install
    install_call = _mk_tool_call("install_custom_node", {
        "package_name": "comfyanonymous/ComfyUI_IPAdapter_plus",
        "auto_restart": True,
    })
    messages.append(_mk_assistant_tools([install_call]))
    messages.append(_mk_tool_result(install_call["id"],
                                     _install_node_result("ComfyUI_IPAdapter_plus")))

    messages.append(_mk_assistant_text(
        "IPAdapter has been installed. ComfyUI will restart to load the new nodes. "
        "Once it's back up, I'll build your IPAdapter workflow. "
        "This typically takes about 10-15 seconds."
    ))

    return messages


# ---------------------------------------------------------------------------
# CONSTRAINED (token-limited) GENERATORS — shorter conversations
# ---------------------------------------------------------------------------

def gen_constrained_txt2img(include_future: bool = False) -> list[dict]:
    """Minimal token conversation for constrained providers (Groq free tier)."""
    positive = _pick_prompt()
    template = _pick([BASIC_TXT2IMG, BASIC_TXT2IMG_SDXL])

    messages = [
        _mk_system(SYSTEM_PROMPT_CONSTRAINED),
        _mk_user(f"Make: {positive}"),
    ]

    # Plan (minimal)
    plan_call = _mk_tool_call("plan_tasks", {"tasks": ["Find model", "Build workflow", "Save"]})
    messages.append(_mk_assistant_tools([plan_call]))
    messages.append(_mk_tool_result(plan_call["id"], {"status": "ok"}))

    # Straight to save (constrained models skip search to save tokens)
    filled = _fill_workflow(template, {"{{POSITIVE_PROMPT}}": positive})
    save_call = _mk_tool_call("save_workflow", {
        "workflow_json": json.dumps(filled),
        "description": "txt2img",
    })
    messages.append(_mk_assistant_tools([save_call]))
    messages.append(_mk_tool_result(save_call["id"], _save_result()))

    messages.append(_mk_assistant_text("Workflow saved to canvas. Queue to generate."))

    return messages


def gen_constrained_modify(include_future: bool = False) -> list[dict]:
    """Short modification conversation for constrained mode."""
    messages = [
        _mk_system(SYSTEM_PROMPT_CONSTRAINED),
        _mk_user("Change the steps to 30 and CFG to 8"),
    ]

    wf_call = _mk_tool_call("get_current_workflow_for_agent", {"reason": "modify"})
    messages.append(_mk_assistant_tools([wf_call]))
    existing = _fill_workflow(BASIC_TXT2IMG)
    messages.append(_mk_tool_result(wf_call["id"], _current_workflow_result(existing)))

    modified = copy.deepcopy(existing)
    modified["5"]["inputs"]["steps"] = 30
    modified["5"]["inputs"]["cfg"] = 8.0

    save_call = _mk_tool_call("save_workflow", {
        "workflow_json": json.dumps(modified),
        "description": "Updated steps and CFG",
    })
    messages.append(_mk_assistant_tools([save_call]))
    messages.append(_mk_tool_result(save_call["id"], _save_result()))

    messages.append(_mk_assistant_text("Updated: steps=30, CFG=8. Saved."))

    return messages


# ---------------------------------------------------------------------------
# DATASET COMPOSITION  — weighted category distribution
# ---------------------------------------------------------------------------

# (generator_function, weight, requires_future_tools)
GENERATORS = [
    # Core workflows — high weight
    (gen_basic_txt2img,           25,  False),
    (gen_img2img,                 10,  False),
    (gen_lora_workflow,           12,  False),
    (gen_upscale,                  8,  False),
    (gen_controlnet,              10,  False),
    (gen_inpainting,               6,  False),
    (gen_full_pipeline,            8,  False),

    # Execution & monitoring
    (gen_execute_and_check,       10,  False),
    (gen_modify_existing,         12,  False),
    (gen_error_recovery,           8,  False),
    (gen_node_details_exploration, 6,  False),

    # Constrained (token-limited) conversations
    (gen_constrained_txt2img,      8,  False),
    (gen_constrained_modify,       5,  False),

    # Future tools
    (gen_full_automation,         12,  True),
    (gen_image_preparation,        8,  True),
    (gen_batch_processing,         6,  True),
    (gen_video_preparation,        5,  True),
    (gen_install_and_build,        5,  True),
]


def _select_generator(include_future: bool) -> callable:
    """Weighted random selection of conversation generator."""
    available = [(fn, w) for fn, w, needs_future in GENERATORS
                 if not needs_future or include_future]
    total = sum(w for _, w in available)
    r = random.uniform(0, total)
    cumulative = 0
    for fn, w in available:
        cumulative += w
        if r <= cumulative:
            return fn
    return available[-1][0]


# ---------------------------------------------------------------------------
# DATA AUGMENTATION
# ---------------------------------------------------------------------------

def _augment_user_message(msg: str) -> str:
    """Add natural variation to user messages."""
    prefixes = ["", "Hey, ", "Hi! ", "Please ", "Can you ", "I need to ", ""]
    suffixes = ["", " thanks!", " please", ".", " thx", ""]
    typo_chance = 0.05  # 5% chance of a minor typo

    result = _pick(prefixes) + msg + _pick(suffixes)

    # Occasionally add capitalization variation
    if random.random() < 0.15:
        result = result.lower()
    elif random.random() < 0.1:
        result = result.upper()

    return result


def _augment_conversation(messages: list[dict]) -> list[dict]:
    """Apply augmentation to a conversation."""
    result = []
    for msg in messages:
        msg = copy.deepcopy(msg)
        if msg["role"] == "user" and random.random() < 0.4:
            msg["content"] = _augment_user_message(msg["content"])
        result.append(msg)
    return result


# ---------------------------------------------------------------------------
# MAIN GENERATION PIPELINE
# ---------------------------------------------------------------------------

def generate_example(include_future: bool = True, augment: bool = True) -> dict:
    """Generate one training example.

    Returns a dict with:
      - messages: list of chat messages
      - tools: list of tool schemas
      - metadata: category, template info
    """
    gen_fn = _select_generator(include_future)
    messages = gen_fn(include_future)

    if augment:
        messages = _augment_conversation(messages)

    tools = ALL_TOOLS if include_future else CURRENT_TOOLS

    # Build metadata for validation
    tool_calls_made = []
    for msg in messages:
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                tool_calls_made.append(tc["function"]["name"])

    return {
        "messages": messages,
        "tools": tools,
        "metadata": {
            "generator": gen_fn.__name__,
            "tool_calls": tool_calls_made,
            "num_turns": sum(1 for m in messages if m["role"] == "assistant"),
        },
    }


def generate_dataset(
    count: int = 8000,
    include_future: bool = True,
    augment: bool = True,
    seed: int = 42,
) -> list[dict]:
    """Generate the full dataset.

    Args:
        count: Number of training examples
        include_future: Include future tool conversations
        augment: Apply data augmentation
        seed: Random seed for reproducibility

    Returns:
        List of training examples
    """
    random.seed(seed)
    dataset = []
    seen_hashes = set()

    attempts = 0
    max_attempts = count * 3  # Allow retries for deduplication

    while len(dataset) < count and attempts < max_attempts:
        attempts += 1
        example = generate_example(include_future, augment)

        # Dedup by content hash (skip exact duplicates)
        content_key = json.dumps(
            [m.get("content", "") for m in example["messages"] if m["role"] in ("user", "assistant") and m.get("content")],
            sort_keys=True,
        )
        h = hashlib.md5(content_key.encode()).hexdigest()
        if h in seen_hashes:
            continue
        seen_hashes.add(h)

        dataset.append(example)

        if len(dataset) % 500 == 0:
            print(f"  Generated {len(dataset)}/{count} examples...")

    return dataset


def write_jsonl(dataset: list[dict], output_path: str, include_metadata: bool = False):
    """Write dataset as JSONL for training.

    Each line is a JSON object with 'messages' and 'tools' keys.
    Optionally includes metadata for debugging.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        for example in dataset:
            record = {
                "messages": example["messages"],
                "tools": example["tools"],
            }
            if include_metadata:
                record["metadata"] = example["metadata"]
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote {len(dataset)} examples to {path}")
    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"File size: {size_mb:.1f} MB")


def print_stats(dataset: list[dict]):
    """Print dataset statistics."""
    from collections import Counter

    gen_counts = Counter(ex["metadata"]["generator"] for ex in dataset)
    tool_counts = Counter()
    for ex in dataset:
        for tc in ex["metadata"]["tool_calls"]:
            tool_counts[tc] += 1

    turn_counts = [ex["metadata"]["num_turns"] for ex in dataset]

    print("\n=== Dataset Statistics ===")
    print(f"Total examples: {len(dataset)}")
    print(f"Avg turns per conversation: {sum(turn_counts)/len(turn_counts):.1f}")
    print(f"Min/Max turns: {min(turn_counts)}/{max(turn_counts)}")

    print("\nGenerator distribution:")
    for gen, count in gen_counts.most_common():
        pct = count / len(dataset) * 100
        print(f"  {gen}: {count} ({pct:.1f}%)")

    print("\nTool call distribution:")
    for tool, count in tool_counts.most_common():
        print(f"  {tool}: {count}")

    # Token estimate
    total_chars = sum(
        len(json.dumps(ex["messages"]))
        for ex in dataset
    )
    est_tokens = total_chars / 3.5
    print(f"\nEstimated total tokens: {est_tokens/1e6:.1f}M")
    print(f"Avg tokens per example: {est_tokens/len(dataset):.0f}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate ComfyUI-Copilot training dataset")
    parser.add_argument("--output", "-o", default="training_data.jsonl", help="Output JSONL path")
    parser.add_argument("--count", "-n", type=int, default=8000, help="Number of examples")
    parser.add_argument("--future", action="store_true", help="Include future tool training data")
    parser.add_argument("--no-augment", action="store_true", help="Disable data augmentation")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--validate", action="store_true", help="Dry-run: generate 10 and print")
    parser.add_argument("--metadata", action="store_true", help="Include metadata in output")
    parser.add_argument("--stats", action="store_true", help="Print statistics after generation")

    args = parser.parse_args()

    if args.validate:
        print("=== Validation Mode: generating 10 sample conversations ===\n")
        random.seed(args.seed)
        for i in range(10):
            ex = generate_example(include_future=args.future, augment=not args.no_augment)
            print(f"--- Example {i+1} ({ex['metadata']['generator']}) ---")
            for msg in ex["messages"]:
                role = msg["role"]
                if role == "system":
                    print(f"  [SYSTEM] ({len(msg['content'])} chars)")
                elif role == "user":
                    print(f"  [USER] {msg['content'][:80]}...")
                elif role == "assistant" and msg.get("tool_calls"):
                    calls = [tc["function"]["name"] for tc in msg["tool_calls"]]
                    print(f"  [ASSISTANT → TOOLS] {', '.join(calls)}")
                elif role == "assistant":
                    print(f"  [ASSISTANT] {(msg['content'] or '')[:80]}...")
                elif role == "tool":
                    content = msg["content"][:60] if msg.get("content") else ""
                    print(f"  [TOOL RESULT] {content}...")
            print()
        return

    print(f"Generating {args.count} training examples...")
    print(f"  Future tools: {'yes' if args.future else 'no'}")
    print(f"  Augmentation: {'off' if args.no_augment else 'on'}")
    print(f"  Seed: {args.seed}")
    print()

    dataset = generate_dataset(
        count=args.count,
        include_future=args.future,
        augment=not args.no_augment,
        seed=args.seed,
    )

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = Path(__file__).parent / output_path
    write_jsonl(dataset, str(output_path), include_metadata=args.metadata)

    if args.stats:
        print_stats(dataset)


if __name__ == "__main__":
    main()
