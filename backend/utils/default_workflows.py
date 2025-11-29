"""
Default Workflow Templates

Provides a set of default workflow templates for common use cases.
These templates are loaded into the database on first run.
"""

import uuid
from typing import List
from .workflow_templates import WorkflowTemplate


def get_default_templates() -> List[WorkflowTemplate]:
    """
    Get list of default workflow templates.

    Returns:
        List of WorkflowTemplate objects
    """
    templates = []

    # Template 1: Simple Text-to-Image (SD 1.5)
    templates.append(WorkflowTemplate(
        id=str(uuid.uuid4()),
        name="Simple Text-to-Image (SD 1.5)",
        description="Basic text-to-image workflow using Stable Diffusion 1.5. Great for beginners and quick generations.",
        category="text2image",
        tags=["sd15", "simple", "beginner-friendly", "fast"],
        required_models=["sd-v1-5.safetensors"],
        workflow_data={
            "1": {
                "inputs": {
                    "ckpt_name": "sd-v1-5.safetensors"
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "2": {
                "inputs": {
                    "text": "a beautiful landscape, highly detailed, 8k",
                    "clip": ["1", 0]
                },
                "class_type": "CLIPTextEncode"
            },
            "3": {
                "inputs": {
                    "text": "blurry, low quality, distorted",
                    "clip": ["1", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "4": {
                "inputs": {
                    "seed": 42,
                    "steps": 20,
                    "cfg": 7.0,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler"
            },
            "5": {
                "inputs": {
                    "width": 512,
                    "height": 512,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage"
            },
            "6": {
                "inputs": {
                    "samples": ["4", 0],
                    "vae": ["1", 2]
                },
                "class_type": "VAEDecode"
            },
            "7": {
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": ["6", 0]
                },
                "class_type": "SaveImage"
            }
        },
        version="1.0",
        rating=4.5
    ))

    # Template 2: SDXL Text-to-Image
    templates.append(WorkflowTemplate(
        id=str(uuid.uuid4()),
        name="SDXL Text-to-Image",
        description="High-quality text-to-image using SDXL. Produces superior results with better prompt understanding.",
        category="text2image",
        tags=["sdxl", "high-quality", "advanced"],
        required_models=["sd_xl_base_1.0.safetensors"],
        workflow_data={
            "1": {
                "inputs": {
                    "ckpt_name": "sd_xl_base_1.0.safetensors"
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "2": {
                "inputs": {
                    "text": "a professional photo of a serene mountain landscape at sunset, ultra detailed, 8k",
                    "clip": ["1", 0]
                },
                "class_type": "CLIPTextEncode"
            },
            "3": {
                "inputs": {
                    "text": "blurry, low quality, distorted, watermark",
                    "clip": ["1", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "4": {
                "inputs": {
                    "seed": 42,
                    "steps": 30,
                    "cfg": 8.0,
                    "sampler_name": "dpmpp_2m",
                    "scheduler": "karras",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler"
            },
            "5": {
                "inputs": {
                    "width": 1024,
                    "height": 1024,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage"
            },
            "6": {
                "inputs": {
                    "samples": ["4", 0],
                    "vae": ["1", 2]
                },
                "class_type": "VAEDecode"
            },
            "7": {
                "inputs": {
                    "filename_prefix": "SDXL_",
                    "images": ["6", 0]
                },
                "class_type": "SaveImage"
            }
        },
        version="1.0",
        rating=4.8
    ))

    # Template 3: Image-to-Image
    templates.append(WorkflowTemplate(
        id=str(uuid.uuid4()),
        name="Image-to-Image Transformation",
        description="Transform an existing image with AI. Useful for style transfer, enhancement, and variations.",
        category="img2img",
        tags=["img2img", "transformation", "style-transfer"],
        required_models=["sd-v1-5.safetensors"],
        workflow_data={
            "1": {
                "inputs": {
                    "ckpt_name": "sd-v1-5.safetensors"
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "2": {
                "inputs": {
                    "image": "input_image.png",
                    "upload": "image"
                },
                "class_type": "LoadImage"
            },
            "3": {
                "inputs": {
                    "pixels": ["2", 0],
                    "vae": ["1", 2]
                },
                "class_type": "VAEEncode"
            },
            "4": {
                "inputs": {
                    "text": "a beautiful painting, artistic, detailed",
                    "clip": ["1", 0]
                },
                "class_type": "CLIPTextEncode"
            },
            "5": {
                "inputs": {
                    "text": "blurry, low quality",
                    "clip": ["1", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "6": {
                "inputs": {
                    "seed": 42,
                    "steps": 20,
                    "cfg": 7.0,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 0.7,  # Lower denoise to preserve input image
                    "model": ["1", 0],
                    "positive": ["4", 0],
                    "negative": ["5", 0],
                    "latent_image": ["3", 0]
                },
                "class_type": "KSampler"
            },
            "7": {
                "inputs": {
                    "samples": ["6", 0],
                    "vae": ["1", 2]
                },
                "class_type": "VAEDecode"
            },
            "8": {
                "inputs": {
                    "filename_prefix": "img2img_",
                    "images": ["7", 0]
                },
                "class_type": "SaveImage"
            }
        },
        version="1.0",
        rating=4.3
    ))

    # Template 4: Simple Upscale
    templates.append(WorkflowTemplate(
        id=str(uuid.uuid4()),
        name="4x Image Upscale",
        description="Upscale images 4x using AI upscaling models. Great for enhancing low-resolution images.",
        category="upscale",
        tags=["upscale", "enhancement", "4x"],
        required_models=["RealESRGAN_x4plus.pth"],
        workflow_data={
            "1": {
                "inputs": {
                    "image": "input_image.png",
                    "upload": "image"
                },
                "class_type": "LoadImage"
            },
            "2": {
                "inputs": {
                    "upscale_model_name": "RealESRGAN_x4plus.pth"
                },
                "class_type": "UpscaleModelLoader"
            },
            "3": {
                "inputs": {
                    "upscale_model": ["2", 0],
                    "image": ["1", 0]
                },
                "class_type": "ImageUpscaleWithModel"
            },
            "4": {
                "inputs": {
                    "filename_prefix": "upscaled_",
                    "images": ["3", 0]
                },
                "class_type": "SaveImage"
            }
        },
        version="1.0",
        rating=4.6
    ))

    # Template 5: Inpainting
    templates.append(WorkflowTemplate(
        id=str(uuid.uuid4()),
        name="Image Inpainting",
        description="Fill in masked areas of an image with AI-generated content. Perfect for removing objects or filling missing areas.",
        category="inpaint",
        tags=["inpaint", "mask", "object-removal"],
        required_models=["sd-v1-5-inpainting.ckpt"],
        workflow_data={
            "1": {
                "inputs": {
                    "ckpt_name": "sd-v1-5-inpainting.ckpt"
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "2": {
                "inputs": {
                    "image": "input_image.png",
                    "upload": "image"
                },
                "class_type": "LoadImage"
            },
            "3": {
                "inputs": {
                    "image": "mask.png",
                    "upload": "mask",
                    "channel": "alpha"
                },
                "class_type": "LoadImageMask"
            },
            "4": {
                "inputs": {
                    "grow_mask_by": 6,
                    "pixels": ["2", 0],
                    "vae": ["1", 2],
                    "mask": ["3", 0]
                },
                "class_type": "VAEEncodeForInpaint"
            },
            "5": {
                "inputs": {
                    "text": "seamless background, natural, detailed",
                    "clip": ["1", 0]
                },
                "class_type": "CLIPTextEncode"
            },
            "6": {
                "inputs": {
                    "text": "blurry, artifacts, low quality",
                    "clip": ["1", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "7": {
                "inputs": {
                    "seed": 42,
                    "steps": 25,
                    "cfg": 8.0,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["5", 0],
                    "negative": ["6", 0],
                    "latent_image": ["4", 0]
                },
                "class_type": "KSampler"
            },
            "8": {
                "inputs": {
                    "samples": ["7", 0],
                    "vae": ["1", 2]
                },
                "class_type": "VAEDecode"
            },
            "9": {
                "inputs": {
                    "filename_prefix": "inpaint_",
                    "images": ["8", 0]
                },
                "class_type": "SaveImage"
            }
        },
        version="1.0",
        rating=4.4
    ))

    return templates


def initialize_default_templates():
    """
    Initialize the database with default templates if it's empty.

    Returns:
        Number of templates added
    """
    from .workflow_templates import get_template_manager
    from ..utils.logger import log

    manager = get_template_manager()
    stats = manager.get_statistics()

    # Only add defaults if database is empty
    if stats.get("total_templates", 0) > 0:
        log.info(f"Template database already has {stats['total_templates']} templates, skipping initialization")
        return 0

    templates = get_default_templates()
    added_count = 0

    for template in templates:
        if manager.add_template(template):
            added_count += 1

    log.info(f"Initialized workflow template database with {added_count} default templates")
    return added_count
