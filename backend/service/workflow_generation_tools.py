"""
Local Workflow Generation Tools

Provides local implementations of workflow recall and generation
to replace external MCP services.
"""

import json
import uuid
from typing import List, Dict, Any, Optional
from agents.tool import function_tool

from ..utils.workflow_templates import get_template_manager, WorkflowTemplate
from ..utils.logger import log


@function_tool
async def recall_workflow_local(
    query: str = "",
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 5
) -> str:
    """
    Search for existing workflow templates locally.

    This tool searches the local workflow template database for workflows
    matching the user's requirements. Use this when the user wants to find
    or reuse existing workflows.

    Args:
        query: Search query describing what kind of workflow (e.g., "text to image", "controlnet pose")
        category: Filter by category (text2image, img2img, controlnet, upscale, etc.)
        tags: List of tags to filter by (e.g., ["sdxl", "realistic", "portrait"])
        limit: Maximum number of results to return (default: 5)

    Returns:
        JSON string containing matching workflow templates with their metadata

    Example:
        recall_workflow_local(
            query="realistic portrait generation",
            category="text2image",
            tags=["sdxl", "realistic"],
            limit=3
        )
    """
    try:
        manager = get_template_manager()

        # Search templates
        templates = manager.search_templates(
            query=query,
            category=category,
            tags=tags,
            limit=limit,
            sort_by="usage_count"  # Prefer popular templates
        )

        if not templates:
            return json.dumps({
                "success": True,
                "count": 0,
                "message": "No matching workflows found. Try different search terms or use gen_workflow_local to create a new one.",
                "templates": []
            })

        # Convert templates to response format
        template_list = []
        for template in templates:
            template_list.append({
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "tags": template.tags,
                "author": template.author,
                "version": template.version,
                "required_models": template.required_models,
                "usage_count": template.usage_count,
                "rating": template.rating,
                # Include workflow data for immediate use
                "workflow_data": template.workflow_data,
                "workflow_data_ui": template.workflow_data_ui
            })

        return json.dumps({
            "success": True,
            "count": len(template_list),
            "message": f"Found {len(template_list)} matching workflow(s)",
            "templates": template_list
        }, ensure_ascii=False)

    except Exception as e:
        log.error(f"Failed to recall workflows: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to search workflow templates"
        })


@function_tool
async def gen_workflow_local(
    description: str,
    category: str = "text2image",
    model_preference: Optional[str] = None,
    additional_requirements: Optional[str] = None
) -> str:
    """
    Generate a new workflow based on description and requirements.

    This tool generates a workflow from templates, adapting it to the user's
    specific requirements. It first searches for the most suitable template,
    then customizes it based on the parameters.

    Args:
        description: Description of what the workflow should do (e.g., "Generate realistic portraits with controlnet")
        category: Workflow category (text2image, img2img, controlnet, upscale, inpaint, etc.)
        model_preference: Preferred model system (sdxl, sd15, flux, etc.)
        additional_requirements: Any additional specific requirements

    Returns:
        JSON string containing the generated workflow and metadata

    Example:
        gen_workflow_local(
            description="Create a portrait with pose control",
            category="controlnet",
            model_preference="sdxl",
            additional_requirements="high quality, photorealistic"
        )
    """
    try:
        manager = get_template_manager()

        # Build search tags based on requirements
        search_tags = []
        if model_preference:
            search_tags.append(model_preference.lower())

        # Parse additional requirements for tags
        if additional_requirements:
            req_lower = additional_requirements.lower()
            common_tags = ["realistic", "anime", "portrait", "landscape", "high-quality", "fast", "controlnet", "lora"]
            for tag in common_tags:
                if tag in req_lower:
                    search_tags.append(tag)

        # Search for best matching template
        templates = manager.search_templates(
            query=description,
            category=category,
            tags=search_tags if search_tags else None,
            limit=1,
            sort_by="rating"  # Prefer highly-rated templates
        )

        if not templates:
            # No exact match - try broader search
            templates = manager.search_templates(
                query="",
                category=category,
                limit=1,
                sort_by="usage_count"
            )

        if not templates:
            return json.dumps({
                "success": False,
                "message": f"No templates available for category '{category}'. Please add templates first or try recall_workflow_local to search existing workflows.",
                "workflow_data": None
            })

        # Use the best matching template
        template = templates[0]

        # Generate a new workflow based on the template
        # For now, we use the template as-is, but in the future we could:
        # - Swap models based on model_preference
        # - Adjust parameters based on requirements
        # - Add/remove nodes based on additional_requirements

        workflow_data = template.workflow_data.copy()

        # Increment usage count for the template
        manager.increment_usage(template.id)

        return json.dumps({
            "success": True,
            "message": f"Generated workflow based on template '{template.name}'",
            "template_used": {
                "id": template.id,
                "name": template.name,
                "description": template.description
            },
            "workflow_data": workflow_data,
            "workflow_data_ui": template.workflow_data_ui,
            "required_models": template.required_models,
            "notes": f"This workflow is based on the '{template.name}' template. You can further customize it using the workflow rewrite agent."
        }, ensure_ascii=False)

    except Exception as e:
        log.error(f"Failed to generate workflow: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to generate workflow from templates"
        })


@function_tool
async def list_workflow_categories() -> str:
    """
    List all available workflow categories.

    Returns:
        JSON string containing list of categories and their counts
    """
    try:
        manager = get_template_manager()
        stats = manager.get_statistics()

        return json.dumps({
            "success": True,
            "categories": stats.get("categories", []),
            "total_templates": stats.get("total_templates", 0),
            "total_usage": stats.get("total_usage", 0),
            "average_rating": stats.get("average_rating", 0.0)
        })

    except Exception as e:
        log.error(f"Failed to list categories: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })


# Compatibility aliases for external MCP tool names
# This allows seamless replacement without changing agent instructions
recall_workflow = recall_workflow_local
gen_workflow = gen_workflow_local
