"""
HuggingFace model source implementation.

Provides access to models hosted on huggingface.co
"""

import asyncio
from typing import Any, Dict, List, Optional, Callable
import aiohttp
from .model_source_base import ModelSourceBase, ModelInfo, SearchResult, ModelSourceType
from .logger import log


class HuggingFaceSource(ModelSourceBase):
    """
    HuggingFace model source implementation.

    Uses the HuggingFace Hub API for searching and huggingface_hub library for downloading.
    API Documentation: https://huggingface.co/docs/hub/api
    """

    API_BASE = "https://huggingface.co/api"
    HF_BASE = "https://huggingface.co"

    def __init__(self, timeout: float = 30.0, api_token: Optional[str] = None):
        """
        Initialize HuggingFace source.

        Args:
            timeout: Request timeout in seconds
            api_token: Optional HuggingFace API token for authenticated requests
        """
        super().__init__(timeout)
        self.api_token = api_token
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def source_type(self) -> ModelSourceType:
        return ModelSourceType.HUGGINGFACE

    @property
    def is_available(self) -> bool:
        """Check if HuggingFace API is reachable"""
        # TODO: Could add a health check here
        return True

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            headers = {
                "User-Agent": "ComfyUI-Copilot/1.0"
            }
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"

            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self._session

    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _parse_model(self, data: Dict[str, Any]) -> ModelInfo:
        """
        Parse HuggingFace API response into ModelInfo.

        HuggingFace API returns models with this structure:
        {
            "id": "stabilityai/stable-diffusion-2-1",
            "modelId": "stabilityai/stable-diffusion-2-1",  # Same as id
            "author": "stabilityai",
            "downloads": 123456,
            "likes": 789,
            "tags": ["diffusers", "text-to-image"],
            "pipeline_tag": "text-to-image",
            "lastModified": "2024-01-15T10:30:00.000Z",
            "private": false,
            "sha": "abc123...",
            ...
        }
        """
        model_id = data.get("id") or data.get("modelId", "")
        parts = model_id.split("/")
        author = parts[0] if len(parts) > 1 else data.get("author", "")
        name = parts[-1] if parts else model_id

        # Infer model type from tags
        tags = data.get("tags", [])
        model_type = None
        if "lora" in tags or "LoRA" in tags:
            model_type = "lora"
        elif "checkpoint" in tags or "diffusers" in tags:
            model_type = "checkpoint"
        elif "vae" in tags or "VAE" in tags:
            model_type = "vae"
        elif "text-encoder" in tags:
            model_type = "clip"
        elif "controlnet" in tags:
            model_type = "controlnet"
        else:
            # Use pipeline_tag if available
            pipeline_tag = data.get("pipeline_tag", "")
            if pipeline_tag:
                model_type = pipeline_tag

        return ModelInfo(
            id=model_id,
            name=name,
            source=ModelSourceType.HUGGINGFACE,
            path=author,
            description=data.get("description"),
            downloads=data.get("downloads"),
            likes=data.get("likes"),
            tags=tags,
            last_updated=data.get("lastModified"),
            size=None,  # HuggingFace API doesn't return total size in list endpoint
            model_type=model_type,
            thumbnail_url=None,  # Could construct from model_id if needed
            author=author,
            license=data.get("license"),
            metadata={
                "pipeline_tag": data.get("pipeline_tag"),
                "private": data.get("private", False),
                "sha": data.get("sha"),
                "library_name": data.get("library_name"),
            }
        )

    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 30,
        model_type: Optional[str] = None,
        sort_by: Optional[str] = None,
        **kwargs
    ) -> SearchResult:
        """
        Search HuggingFace models.

        Args:
            query: Search query
            page: Page number (not directly supported by HF API, we use limit/offset)
            page_size: Results per page
            model_type: Filter by model type/tag
            sort_by: Sort by "downloads", "likes", "updated", etc.
            **kwargs: Additional filters (e.g., author, library, tags)

        Returns:
            SearchResult with matching models
        """
        try:
            session = await self._get_session()

            # HuggingFace API parameters
            params = {
                "search": query,
                "limit": page_size,
            }

            # Calculate offset from page number (1-indexed)
            if page > 1:
                params["skip"] = (page - 1) * page_size

            # Add sort parameter
            if sort_by:
                sort_map = {
                    "downloads": "downloads",
                    "likes": "likes",
                    "updated": "lastModified",
                    "created": "createdAt"
                }
                params["sort"] = sort_map.get(sort_by, sort_by)

            # Add model type filter if specified
            if model_type:
                params["filter"] = model_type

            # Add additional filters from kwargs
            if "author" in kwargs:
                params["author"] = kwargs["author"]
            if "tags" in kwargs:
                # HuggingFace accepts comma-separated tags
                if isinstance(kwargs["tags"], list):
                    params["filter"] = ",".join(kwargs["tags"])
                else:
                    params["filter"] = kwargs["tags"]

            log.info(f"HuggingFace search: {params}")

            async with session.get(f"{self.API_BASE}/models", params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    log.error(f"HuggingFace API error {response.status}: {error_text}")
                    return SearchResult(
                        models=[],
                        total=0,
                        source=self.source_type,
                        page=page,
                        page_size=page_size
                    )

                data = await response.json()

                # HuggingFace returns a simple list of models, not paginated with total count
                # We estimate total based on whether we got a full page
                models = [self._parse_model(item) for item in data]
                estimated_total = len(models)
                if len(models) == page_size:
                    # Likely more results exist
                    estimated_total = page * page_size + 1

                return SearchResult(
                    models=models,
                    total=estimated_total,
                    source=self.source_type,
                    page=page,
                    page_size=page_size
                )

        except Exception as e:
            log.error(f"HuggingFace search failed: {e}")
            return SearchResult(
                models=[],
                total=0,
                source=self.source_type,
                page=page,
                page_size=page_size
            )

    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """
        Get detailed information about a specific HuggingFace model.

        Args:
            model_id: Model identifier (e.g., "stabilityai/stable-diffusion-2-1")

        Returns:
            ModelInfo if found, None otherwise
        """
        try:
            session = await self._get_session()

            async with session.get(f"{self.API_BASE}/models/{model_id}") as response:
                if response.status != 200:
                    log.warning(f"HuggingFace model not found: {model_id}")
                    return None

                data = await response.json()
                return self._parse_model(data)

        except Exception as e:
            log.error(f"Failed to get HuggingFace model info for {model_id}: {e}")
            return None

    async def download_model(
        self,
        model_id: str,
        dest_dir: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        **kwargs
    ) -> str:
        """
        Download a HuggingFace model using huggingface_hub library.

        Args:
            model_id: Model identifier (e.g., "stabilityai/stable-diffusion-2-1")
            dest_dir: Destination directory
            progress_callback: Optional callback(downloaded_bytes, total_bytes)
            **kwargs: Additional arguments:
                - revision: Git revision (branch, tag, commit hash)
                - allow_patterns: List of file patterns to download
                - ignore_patterns: List of file patterns to ignore

        Returns:
            Path to downloaded model directory
        """
        try:
            # Import huggingface_hub (similar to modelscope import)
            from huggingface_hub import snapshot_download

            revision = kwargs.get("revision", "main")
            allow_patterns = kwargs.get("allow_patterns")
            ignore_patterns = kwargs.get("ignore_patterns")

            # Create progress wrapper if callback provided
            if progress_callback:
                # TODO: Implement progress tracking for HuggingFace downloads
                # huggingface_hub uses tqdm by default, we'd need to hook into that
                log.warning("Progress callback not yet implemented for HuggingFace downloads")

            # Download using snapshot_download (blocks, so run in thread)
            from functools import partial

            download_func = partial(
                snapshot_download,
                repo_id=model_id,
                cache_dir=dest_dir,
                revision=revision,
                allow_patterns=allow_patterns,
                ignore_patterns=ignore_patterns,
                token=self.api_token,  # Use token if available
            )

            local_dir = await asyncio.to_thread(download_func)
            log.info(f"HuggingFace model downloaded to: {local_dir}")
            return local_dir

        except ImportError as e:
            raise RuntimeError(
                "huggingface_hub library not installed. "
                "Please install with: pip install huggingface_hub"
            ) from e
        except Exception as e:
            log.error(f"HuggingFace download failed for {model_id}: {e}")
            raise

    def get_model_url(self, model_id: str) -> str:
        """Get the web URL for a HuggingFace model"""
        return f"{self.HF_BASE}/{model_id}"

    async def validate_model_id(self, model_id: str) -> bool:
        """
        Validate HuggingFace model ID format.

        Valid format: "username/model-name" or "organization/model-name"
        """
        if not model_id:
            return False

        parts = model_id.split("/")
        return len(parts) == 2 and all(len(p.strip()) > 0 for p in parts)


# Convenience function for testing
async def test_huggingface_source():
    """Test HuggingFace source implementation"""
    source = HuggingFaceSource()

    try:
        print("Testing HuggingFace search...")
        result = await source.search("stable-diffusion", page_size=5)
        print(f"Found {result.total} models, showing {len(result.models)}:")
        for model in result.models[:3]:
            print(f"  - {model.id} (downloads: {model.downloads}, likes: {model.likes})")

        print("\nTesting get_model_info...")
        if result.models:
            model_info = await result.models[0].get_model_info(result.models[0].id)
            if model_info:
                print(f"  Model: {model_info.name}")
                print(f"  Author: {model_info.author}")
                print(f"  Tags: {model_info.tags}")

        print("\nHuggingFace source test completed successfully!")

    finally:
        await source.close()


if __name__ == "__main__":
    asyncio.run(test_huggingface_source())
