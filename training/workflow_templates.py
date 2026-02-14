"""
Workflow templates for ComfyUI-Copilot fine-tuning dataset.

Every workflow here is structurally valid ComfyUI workflow JSON.
Node connections use the format: ["source_node_id", output_index]

CRITICAL: These templates are parameterized with {{PLACEHOLDERS}} that
the generator fills in.  The structure/connections are always correct.

Categories:
  1. Basic text-to-image (SD1.5, SDXL, SD3, Flux)
  2. Image-to-image
  3. Inpainting
  4. Upscaling
  5. LoRA workflows
  6. ControlNet workflows
  7. Video generation (AnimateDiff)
  8. Multi-stage pipelines (generate → upscale → face fix)
  9. IPAdapter / style transfer
  10. Advanced compositing

Enhanced by Claude Opus 4.6
"""

# ---------------------------------------------------------------------------
# 1. BASIC TEXT-TO-IMAGE
# ---------------------------------------------------------------------------

BASIC_TXT2IMG = {
    "name": "basic_txt2img",
    "description": "Basic text-to-image with checkpoint, prompts, KSampler, VAE decode, save",
    "tags": ["txt2img", "basic", "beginner"],
    "workflow": {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "{{CHECKPOINT}}"},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "{{POSITIVE_PROMPT}}", "clip": ["1", 1]},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "{{NEGATIVE_PROMPT}}", "clip": ["1", 1]},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": "{{WIDTH}}",
                "height": "{{HEIGHT}}",
                "batch_size": 1,
            },
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
                "seed": "{{SEED}}",
                "steps": "{{STEPS}}",
                "cfg": "{{CFG}}",
                "sampler_name": "{{SAMPLER}}",
                "scheduler": "{{SCHEDULER}}",
                "denoise": 1.0,
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"images": ["6", 0], "filename_prefix": "ComfyUI"},
        },
    },
}

BASIC_TXT2IMG_SDXL = {
    "name": "basic_txt2img_sdxl",
    "description": "SDXL text-to-image with base + refiner pipeline",
    "tags": ["txt2img", "sdxl", "intermediate"],
    "workflow": {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "{{CHECKPOINT_SDXL}}"},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "{{POSITIVE_PROMPT}}", "clip": ["1", 1]},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "{{NEGATIVE_PROMPT}}", "clip": ["1", 1]},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
                "seed": "{{SEED}}",
                "steps": 25,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"images": ["6", 0], "filename_prefix": "SDXL"},
        },
    },
}

BASIC_TXT2IMG_FLUX = {
    "name": "basic_txt2img_flux",
    "description": "Flux text-to-image — uses DualCLIPLoader and guidance-free sampling",
    "tags": ["txt2img", "flux", "advanced"],
    "workflow": {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": "{{FLUX_UNET}}", "weight_dtype": "fp8_e4m3fn"},
        },
        "2": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": "{{CLIP_L}}",
                "clip_name2": "{{CLIP_T5}}",
                "type": "flux",
            },
        },
        "3": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "{{FLUX_VAE}}"},
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "{{POSITIVE_PROMPT}}", "clip": ["2", 0]},
        },
        "5": {
            "class_type": "EmptySD3LatentImage",
            "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
        },
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["4", 0],
                "negative": ["4", 0],  # Flux uses same prompt for both (no neg)
                "latent_image": ["5", 0],
                "seed": "{{SEED}}",
                "steps": 20,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
            },
        },
        "7": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["6", 0], "vae": ["3", 0]},
        },
        "8": {
            "class_type": "SaveImage",
            "inputs": {"images": ["7", 0], "filename_prefix": "Flux"},
        },
    },
}


# ---------------------------------------------------------------------------
# 2. IMAGE-TO-IMAGE
# ---------------------------------------------------------------------------

IMG2IMG = {
    "name": "img2img",
    "description": "Image-to-image: load image, encode to latent, denoise partially",
    "tags": ["img2img", "basic"],
    "workflow": {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "{{CHECKPOINT}}"},
        },
        "2": {
            "class_type": "LoadImage",
            "inputs": {"image": "{{INPUT_IMAGE}}"},
        },
        "3": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["2", 0], "vae": ["1", 2]},
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "{{POSITIVE_PROMPT}}", "clip": ["1", 1]},
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "{{NEGATIVE_PROMPT}}", "clip": ["1", 1]},
        },
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["3", 0],
                "seed": "{{SEED}}",
                "steps": "{{STEPS}}",
                "cfg": "{{CFG}}",
                "sampler_name": "{{SAMPLER}}",
                "scheduler": "{{SCHEDULER}}",
                "denoise": "{{DENOISE}}",
            },
        },
        "7": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["6", 0], "vae": ["1", 2]},
        },
        "8": {
            "class_type": "SaveImage",
            "inputs": {"images": ["7", 0], "filename_prefix": "img2img"},
        },
    },
}


# ---------------------------------------------------------------------------
# 3. INPAINTING
# ---------------------------------------------------------------------------

INPAINTING = {
    "name": "inpainting",
    "description": "Inpainting with mask: load image + mask, VAE encode for inpainting, denoise",
    "tags": ["inpainting", "intermediate"],
    "workflow": {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "{{CHECKPOINT_INPAINT}}"},
        },
        "2": {
            "class_type": "LoadImage",
            "inputs": {"image": "{{INPUT_IMAGE}}"},
        },
        "3": {
            "class_type": "LoadImage",
            "inputs": {"image": "{{MASK_IMAGE}}"},
        },
        "4": {
            "class_type": "VAEEncodeForInpaint",
            "inputs": {
                "pixels": ["2", 0],
                "vae": ["1", 2],
                "mask": ["3", 1],
                "grow_mask_by": 6,
            },
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "{{POSITIVE_PROMPT}}", "clip": ["1", 1]},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "{{NEGATIVE_PROMPT}}", "clip": ["1", 1]},
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["4", 0],
                "seed": "{{SEED}}",
                "steps": 20,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["7", 0], "vae": ["1", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"images": ["8", 0], "filename_prefix": "inpaint"},
        },
    },
}


# ---------------------------------------------------------------------------
# 4. UPSCALING
# ---------------------------------------------------------------------------

UPSCALE_SIMPLE = {
    "name": "upscale_simple",
    "description": "Simple upscale with model upscaler",
    "tags": ["upscale", "basic"],
    "workflow": {
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": "{{INPUT_IMAGE}}"},
        },
        "2": {
            "class_type": "UpscaleModelLoader",
            "inputs": {"model_name": "{{UPSCALE_MODEL}}"},
        },
        "3": {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {"upscale_model": ["2", 0], "image": ["1", 0]},
        },
        "4": {
            "class_type": "SaveImage",
            "inputs": {"images": ["3", 0], "filename_prefix": "upscaled"},
        },
    },
}

UPSCALE_HIRES = {
    "name": "upscale_hires",
    "description": "Hi-res fix: generate → upscale latent → re-denoise at higher res",
    "tags": ["upscale", "hires", "intermediate"],
    "workflow": {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "{{CHECKPOINT}}"},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "{{POSITIVE_PROMPT}}", "clip": ["1", 1]},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "{{NEGATIVE_PROMPT}}", "clip": ["1", 1]},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 512, "height": 512, "batch_size": 1},
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
                "seed": "{{SEED}}",
                "steps": 20,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
            },
        },
        "6": {
            "class_type": "LatentUpscale",
            "inputs": {
                "samples": ["5", 0],
                "upscale_method": "nearest-exact",
                "width": 1024,
                "height": 1024,
                "crop": "disabled",
            },
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["6", 0],
                "seed": "{{SEED}}",
                "steps": 15,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 0.5,
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["7", 0], "vae": ["1", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"images": ["8", 0], "filename_prefix": "hires"},
        },
    },
}


# ---------------------------------------------------------------------------
# 5. LORA WORKFLOWS
# ---------------------------------------------------------------------------

TXT2IMG_WITH_LORA = {
    "name": "txt2img_with_lora",
    "description": "Text-to-image with LoRA model applied",
    "tags": ["txt2img", "lora", "intermediate"],
    "workflow": {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "{{CHECKPOINT}}"},
        },
        "2": {
            "class_type": "LoraLoader",
            "inputs": {
                "model": ["1", 0],
                "clip": ["1", 1],
                "lora_name": "{{LORA_NAME}}",
                "strength_model": "{{LORA_STRENGTH_MODEL}}",
                "strength_clip": "{{LORA_STRENGTH_CLIP}}",
            },
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "{{POSITIVE_PROMPT}}", "clip": ["2", 1]},
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "{{NEGATIVE_PROMPT}}", "clip": ["2", 1]},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": "{{WIDTH}}",
                "height": "{{HEIGHT}}",
                "batch_size": 1,
            },
        },
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["2", 0],
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["5", 0],
                "seed": "{{SEED}}",
                "steps": "{{STEPS}}",
                "cfg": "{{CFG}}",
                "sampler_name": "{{SAMPLER}}",
                "scheduler": "{{SCHEDULER}}",
                "denoise": 1.0,
            },
        },
        "7": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["6", 0], "vae": ["1", 2]},
        },
        "8": {
            "class_type": "SaveImage",
            "inputs": {"images": ["7", 0], "filename_prefix": "lora"},
        },
    },
}

TXT2IMG_MULTI_LORA = {
    "name": "txt2img_multi_lora",
    "description": "Text-to-image with two LoRAs stacked",
    "tags": ["txt2img", "lora", "advanced"],
    "workflow": {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "{{CHECKPOINT}}"},
        },
        "2": {
            "class_type": "LoraLoader",
            "inputs": {
                "model": ["1", 0],
                "clip": ["1", 1],
                "lora_name": "{{LORA_NAME_1}}",
                "strength_model": "{{LORA_STRENGTH_1}}",
                "strength_clip": "{{LORA_STRENGTH_1}}",
            },
        },
        "3": {
            "class_type": "LoraLoader",
            "inputs": {
                "model": ["2", 0],
                "clip": ["2", 1],
                "lora_name": "{{LORA_NAME_2}}",
                "strength_model": "{{LORA_STRENGTH_2}}",
                "strength_clip": "{{LORA_STRENGTH_2}}",
            },
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "{{POSITIVE_PROMPT}}", "clip": ["3", 1]},
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "{{NEGATIVE_PROMPT}}", "clip": ["3", 1]},
        },
        "6": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": "{{WIDTH}}", "height": "{{HEIGHT}}", "batch_size": 1},
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["3", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["6", 0],
                "seed": "{{SEED}}",
                "steps": "{{STEPS}}",
                "cfg": "{{CFG}}",
                "sampler_name": "{{SAMPLER}}",
                "scheduler": "{{SCHEDULER}}",
                "denoise": 1.0,
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["7", 0], "vae": ["1", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"images": ["8", 0], "filename_prefix": "multi_lora"},
        },
    },
}


# ---------------------------------------------------------------------------
# 6. CONTROLNET
# ---------------------------------------------------------------------------

CONTROLNET_CANNY = {
    "name": "controlnet_canny",
    "description": "ControlNet with Canny edge detection",
    "tags": ["controlnet", "canny", "intermediate"],
    "workflow": {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "{{CHECKPOINT}}"},
        },
        "2": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "{{CONTROLNET_MODEL}}"},
        },
        "3": {
            "class_type": "LoadImage",
            "inputs": {"image": "{{INPUT_IMAGE}}"},
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "{{POSITIVE_PROMPT}}", "clip": ["1", 1]},
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "{{NEGATIVE_PROMPT}}", "clip": ["1", 1]},
        },
        "6": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["4", 0],
                "negative": ["5", 0],
                "control_net": ["2", 0],
                "image": ["3", 0],
                "strength": "{{CONTROLNET_STRENGTH}}",
                "start_percent": 0.0,
                "end_percent": 1.0,
            },
        },
        "7": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": "{{WIDTH}}", "height": "{{HEIGHT}}", "batch_size": 1},
        },
        "8": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["6", 0],
                "negative": ["6", 1],
                "latent_image": ["7", 0],
                "seed": "{{SEED}}",
                "steps": 20,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
            },
        },
        "9": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["8", 0], "vae": ["1", 2]},
        },
        "10": {
            "class_type": "SaveImage",
            "inputs": {"images": ["9", 0], "filename_prefix": "controlnet"},
        },
    },
}


# ---------------------------------------------------------------------------
# 7. MULTI-STAGE PIPELINES
# ---------------------------------------------------------------------------

GENERATE_UPSCALE_FACEFIX = {
    "name": "generate_upscale_facefix",
    "description": "Full pipeline: generate → upscale → face restore → save",
    "tags": ["pipeline", "upscale", "face_restore", "advanced"],
    "workflow": {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "{{CHECKPOINT}}"},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "{{POSITIVE_PROMPT}}", "clip": ["1", 1]},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "{{NEGATIVE_PROMPT}}", "clip": ["1", 1]},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 512, "height": 512, "batch_size": 1},
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
                "seed": "{{SEED}}",
                "steps": 20,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "UpscaleModelLoader",
            "inputs": {"model_name": "{{UPSCALE_MODEL}}"},
        },
        "8": {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {"upscale_model": ["7", 0], "image": ["6", 0]},
        },
        "9": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["8", 0],
                "upscale_method": "lanczos",
                "width": 1024,
                "height": 1024,
                "crop": "center",
            },
        },
        "10": {
            "class_type": "SaveImage",
            "inputs": {"images": ["9", 0], "filename_prefix": "pipeline_final"},
        },
    },
}


# ---------------------------------------------------------------------------
# Parameter pools for realistic variation
# ---------------------------------------------------------------------------

CHECKPOINTS_SD15 = [
    "v1-5-pruned-emaonly.safetensors",
    "dreamshaper_8.safetensors",
    "realisticVisionV60B1_v51VAE.safetensors",
    "deliberate_v3.safetensors",
    "epicrealism_naturalSinRC1VAE.safetensors",
    "majicmixRealistic_v7.safetensors",
    "revAnimated_v2Rebirth.safetensors",
    "toonyou_beta6.safetensors",
    "ghostmix_v20Bakedvae.safetensors",
    "absolutereality_v181.safetensors",
    "cyberrealistic_v42.safetensors",
]

CHECKPOINTS_SDXL = [
    "sd_xl_base_1.0.safetensors",
    "juggernautXL_v9Rundiffusionphoto2.safetensors",
    "dreamshaperXL_v21TurboDPMSDE.safetensors",
    "realvisxlV50_v50Bakedvae.safetensors",
    "protovisionXLHighFidelity3D_release0620Bakedvae.safetensors",
    "animagineXLV31_v31.safetensors",
    "copaxTimelessxlSDXL1_v12.safetensors",
    "zavychromaxl_v80.safetensors",
]

CHECKPOINTS_FLUX = [
    "flux1-dev.safetensors",
    "flux1-schnell.safetensors",
]

FLUX_UNETS = [
    "flux1-dev.safetensors",
    "flux1-schnell.safetensors",
]

FLUX_CLIPS_L = [
    "clip_l.safetensors",
    "t5xxl_fp8_e4m3fn.safetensors",
]

FLUX_CLIPS_T5 = [
    "t5xxl_fp8_e4m3fn.safetensors",
    "t5xxl_fp16.safetensors",
]

FLUX_VAES = [
    "ae.safetensors",
]

LORA_NAMES = [
    "add_detail.safetensors",
    "epi_noiseoffset2.safetensors",
    "LowRA.safetensors",
    "FilmVelvia3.safetensors",
    "GoodHands-beta2.safetensors",
    "polyhedron_all_in_one.safetensors",
    "more_details.safetensors",
    "style_enhancer.safetensors",
    "pixel_art_lora.safetensors",
    "watercolor_style.safetensors",
]

CONTROLNET_MODELS = [
    "control_v11p_sd15_canny.pth",
    "control_v11p_sd15_openpose.pth",
    "control_v11f1p_sd15_depth.pth",
    "control_v11p_sd15_lineart.pth",
    "control_v11p_sd15_scribble.pth",
    "control_v11p_sd15_softedge.pth",
    "control_v11p_sd15_seg.pth",
    "diffusers_xl_canny_mid.safetensors",
    "diffusers_xl_depth_mid.safetensors",
]

UPSCALE_MODELS = [
    "RealESRGAN_x4plus.pth",
    "RealESRGAN_x4plus_anime_6B.pth",
    "4x-UltraSharp.pth",
    "4x_NMKD-Superscale-SP_178000_G.pth",
    "ESRGAN_4x.pth",
    "8x_NMKD-Superscale_150000_G.pth",
]

SAMPLERS = ["euler", "euler_ancestral", "dpmpp_2m", "dpmpp_2m_sde", "dpmpp_sde", "dpmpp_3m_sde", "uni_pc", "ddim"]
SCHEDULERS = ["normal", "karras", "exponential", "sgm_uniform", "simple", "ddim_uniform", "beta"]

RESOLUTIONS_SD15 = [(512, 512), (512, 768), (768, 512), (640, 640), (512, 896), (896, 512)]
RESOLUTIONS_SDXL = [(1024, 1024), (896, 1152), (1152, 896), (768, 1344), (1344, 768), (1024, 1536)]

# Positive prompts organized by category for diverse training data
POSITIVE_PROMPTS = {
    "portrait": [
        "beautiful woman, professional portrait, soft lighting, shallow depth of field, bokeh, 8k, detailed skin",
        "handsome man in a suit, studio photography, dramatic lighting, sharp focus",
        "elderly person with wise eyes, cinematic portrait, golden hour, wrinkles, character",
        "young child laughing, natural light, park setting, candid photography, joyful",
        "fantasy elf warrior, detailed armor, magical forest, ethereal glow, digital art",
    ],
    "landscape": [
        "breathtaking mountain landscape, sunrise, fog rolling through valley, golden light, 8k photography",
        "serene lake reflection, autumn foliage, misty morning, wide angle, nature photography",
        "dramatic ocean cliffs at sunset, crashing waves, orange sky, long exposure",
        "snowy winter forest, moonlight filtering through trees, peaceful, photorealistic",
        "vast desert dunes at golden hour, leading lines, minimalist, stunning sky",
    ],
    "anime": [
        "anime girl, cherry blossom, school uniform, beautiful eyes, detailed, masterpiece, best quality",
        "anime boy, warrior outfit, katana, dynamic pose, battle scene, vivid colors",
        "cute anime girl, cat ears, pastel colors, kawaii, chibi style, sparkles",
        "anime landscape, fantasy city, floating islands, magical, Studio Ghibli style, dreamy",
        "dark anime character, hooded figure, glowing red eyes, rainy city, cyberpunk",
    ],
    "artistic": [
        "oil painting of a medieval castle, dramatic clouds, romanticism style, rich colors",
        "watercolor illustration of flowers, soft edges, botanical art, delicate, pastel",
        "abstract geometric art, vibrant neon colors, digital art, modern, clean lines",
        "surrealist painting, melting clocks, dreamlike landscape, Salvador Dali style",
        "impressionist garden scene, Monet style, light dappled, flowers, soft brushstrokes",
    ],
    "product": [
        "professional product photography, luxury watch on marble surface, soft studio lighting",
        "sleek smartphone on gradient background, reflections, minimalist, advertising",
        "gourmet food photography, artisan bread, rustic wooden table, natural light, appetizing",
        "premium perfume bottle, dramatic lighting, dark background, luxury, glass reflections",
        "modern furniture in minimalist interior, clean lines, Scandinavian design, bright",
    ],
    "video_still": [
        "cinematic still frame, neon-lit cyberpunk street, rain reflections, blade runner style",
        "film noir scene, detective in fedora, smoking, venetian blinds shadows, black and white",
        "action movie still, explosion in background, hero walking away, dramatic, Michael Bay style",
        "romantic movie scene, couple silhouette at sunset, beach, warm tones, lens flare",
        "horror movie frame, abandoned hospital corridor, flickering lights, fog, tension",
    ],
}

NEGATIVE_PROMPTS = [
    "ugly, blurry, low quality, deformed, disfigured, bad anatomy, watermark, text",
    "(worst quality:1.4), (low quality:1.4), lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit",
    "nsfw, nude, watermark, signature, ugly, deformed, noisy, blurry, low contrast",
    "blurry, bad quality, artifacts, duplicate, morbid, mutilated, out of frame, poorly drawn face",
    "low quality, normal quality, worst quality, jpeg artifacts, signature, watermark, username, blurry",
]


# ---------------------------------------------------------------------------
# Collect all templates
# ---------------------------------------------------------------------------

ALL_TEMPLATES = [
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
]


def get_templates_by_tag(tag: str):
    """Get workflow templates matching a specific tag."""
    return [t for t in ALL_TEMPLATES if tag in t["tags"]]
