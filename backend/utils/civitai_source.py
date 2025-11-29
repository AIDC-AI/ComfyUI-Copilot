"""
Civitai model source implementation.

Provides access to models hosted on civitai.com
"""

import asyncio
import os
from typing import Any, Dict, List, Optional, Callable
import aiohttp
from .model_source_base import ModelSourceBase, ModelInfo, SearchResult, ModelSourceType
from .logger import log


class CivitaiSource(ModelSourceBase):
    """
    Civitai model source implementation.

    Uses the Civitai API for searching and downloading models.
    API Documentation: https://github.com/civitai/civitai/wiki/REST-API-Reference
    """

    API_BASE = "https://civitai.com/api/v1"
    CIVITAI_BASE = "https://civitai.com"

    def __init__(self, timeout: float = 30.0, api_key: Optional[str] = None):
        """
        Initialize Civitai source.

        Args:
            timeout: Request timeout in seconds
            api_key: Optional Civitai API key for authenticated requests
        """
        super().__init__(timeout)
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def source_type(self) -> ModelSourceType:
        return ModelSourceType.CIVITAI

    @property
    def is_available(self) -> bool:
        """Check if Civitai API is reachable"""
        return True

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            headers = {
                "User-Agent": "ComfyUI-Copilot/1.0",
                "Content-Type": "application/json"
            }

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
        Parse Civitai API response into ModelInfo.

        Civitai API returns models with this structure:
        {
            "id": 12345,
            "name": "Realistic Vision",
            "description": "A photorealistic model...",
            "type": "Checkpoint",
            "creator": {
                "username": "SG_161222",
                "image": "https://..."
            },
            "tags": ["photorealistic", "landscape"],
            "modelVersions": [
                {
                    "id": 67890,
                    "name": "v5.0",
                    "downloadUrl": "https://...",
                    "files": [
                        {
                            "name": "realisticVision_v50.safetensors",
                            "sizeKB": 2082642,
                            "type": "Model",
                            "downloadUrl": "https://..."
                        }
                    ],
                    "images": [...],
                    "downloadCount": 123456,
                    "stats": {
                        "downloadCount": 123456,
                        "ratingCount": 789,
                        "rating": 4.8
                    }
                }
            ],
            "stats": {
                "downloadCount": 200000,
                "favoriteCount": 5000,
                "commentCount": 300,
                "ratingCount": 1000,
                "rating": 4.9
            }
        }
        """
        model_id = str(data.get("id", ""))
        name = data.get("name", "Unknown")
        model_type_raw = data.get("type", "").lower()

        # Map Civitai types to our standard types
        type_map = {
            "checkpoint": "checkpoint",
            "lora": "lora",
            "textualinversion": "embedding",
            "hypernetwork": "hypernetwork",
            "aestheticgradient": "aesthetic",
            "controlnet": "controlnet",
            "poses": "poses",
            "vae": "vae",
            "upscaler": "upscaler",
            "motionmodule": "motion",
        }
        model_type = type_map.get(model_type_raw, model_type_raw)

        # Get creator info
        creator = data.get("creator", {})
        author = creator.get("username", "Unknown")

        # Get stats
        stats = data.get("stats", {})
        downloads = stats.get("downloadCount", 0)
        likes = stats.get("favoriteCount", 0)

        # Get latest version info for additional metadata
        versions = data.get("modelVersions", [])
        latest_version = versions[0] if versions else {}

        # Get thumbnail from latest version's images
        thumbnail_url = None
        images = latest_version.get("images", [])
        if images and len(images) > 0:
            thumbnail_url = images[0].get("url")

        # Calculate total size from latest version files
        size = None
        files = latest_version.get("files", [])
        if files:
            size = sum(f.get("sizeKB", 0) for f in files) * 1024  # Convert KB to bytes

        # Get tags
        tags = data.get("tags", [])
        if isinstance(tags, list) and len(tags) > 0:
            # Civitai sometimes returns tag objects instead of strings
            if isinstance(tags[0], dict):
                tags = [t.get("name", "") for t in tags]

        return ModelInfo(
            id=model_id,
            name=name,
            source=ModelSourceType.CIVITAI,
            path=None,  # Civitai doesn't use path/namespace
            description=data.get("description", ""),
            downloads=downloads,
            likes=likes,
            tags=tags,
            last_updated=latest_version.get("updatedAt") or latest_version.get("createdAt"),
            size=size,
            model_type=model_type,
            thumbnail_url=thumbnail_url,
            author=author,
            license=None,  # Civitai doesn't consistently provide license info
            metadata={
                "civitai_id": model_id,
                "nsfw": data.get("nsfw", False),
                "rating": stats.get("rating"),
                "rating_count": stats.get("ratingCount"),
                "comment_count": stats.get("commentCount"),
                "latest_version_id": latest_version.get("id"),
                "latest_version_name": latest_version.get("name"),
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
        Search Civitai models.

        Args:
            query: Search query
            page: Page number (1-indexed)
            page_size: Results per page (max 100)
            model_type: Filter by model type ("checkpoint", "lora", etc.)
            sort_by: Sort by "downloads", "likes", "newest", "rating"
            **kwargs: Additional filters:
                - nsfw: bool - Include NSFW content (default: False)
                - tags: List[str] - Filter by tags

        Returns:
            SearchResult with matching models
        """
        try:
            session = await self._get_session()

            # Civitai API parameters
            params = {
                "query": query,
                "limit": min(page_size, 100),  # Civitai max is 100
                "page": page,
            }

            # Add model type filter (Civitai uses "types" parameter)
            if model_type:
                # Map our standard types to Civitai types
                reverse_type_map = {
                    "checkpoint": "Checkpoint",
                    "lora": "LORA",
                    "embedding": "TextualInversion",
                    "hypernetwork": "Hypernetwork",
                    "controlnet": "Controlnet",
                    "vae": "VAE",
                    "upscaler": "Upscaler",
                }
                civitai_type = reverse_type_map.get(model_type.lower(), model_type.capitalize())
                params["types"] = civitai_type

            # Add sort parameter
            if sort_by:
                sort_map = {
                    "downloads": "Most Downloaded",
                    "likes": "Most Liked",
                    "newest": "Newest",
                    "rating": "Highest Rated",
                    "updated": "Most Downloaded",  # Civitai doesn't have "recently updated"
                }
                params["sort"] = sort_map.get(sort_by, "Most Downloaded")

            # Add NSFW filter (default to false)
            nsfw = kwargs.get("nsfw", False)
            params["nsfw"] = "true" if nsfw else "false"

            # Add tag filter if provided
            if "tags" in kwargs:
                tags = kwargs["tags"]
                if isinstance(tags, list):
                    params["tag"] = ",".join(tags)
                else:
                    params["tag"] = tags

            # Add API key if available
            if self.api_key:
                headers = {"Authorization": f"Bearer {self.api_key}"}
            else:
                headers = None

            log.info(f"Civitai search: {params}")

            async with session.get(
                f"{self.API_BASE}/models",
                params=params,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    log.error(f"Civitai API error {response.status}: {error_text}")
                    return SearchResult(
                        models=[],
                        total=0,
                        source=self.source_type,
                        page=page,
                        page_size=page_size
                    )

                data = await response.json()

                # Civitai returns paginated results with metadata
                items = data.get("items", [])
                metadata = data.get("metadata", {})
                total = metadata.get("totalItems", len(items))

                models = [self._parse_model(item) for item in items]

                return SearchResult(
                    models=models,
                    total=total,
                    source=self.source_type,
                    page=page,
                    page_size=page_size
                )

        except Exception as e:
            log.error(f"Civitai search failed: {e}")
            import traceback
            traceback.print_exc()
            return SearchResult(
                models=[],
                total=0,
                source=self.source_type,
                page=page,
                page_size=page_size
            )

    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """
        Get detailed information about a specific Civitai model.

        Args:
            model_id: Civitai model ID (numeric)

        Returns:
            ModelInfo if found, None otherwise
        """
        try:
            session = await self._get_session()

            headers = None
            if self.api_key:
                headers = {"Authorization": f"Bearer {self.api_key}"}

            async with session.get(
                f"{self.API_BASE}/models/{model_id}",
                headers=headers
            ) as response:
                if response.status != 200:
                    log.warning(f"Civitai model not found: {model_id}")
                    return None

                data = await response.json()
                return self._parse_model(data)

        except Exception as e:
            log.error(f"Failed to get Civitai model info for {model_id}: {e}")
            return None

    async def download_model(
        self,
        model_id: str,
        dest_dir: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        **kwargs
    ) -> str:
        """
        Download a Civitai model file.

        Args:
            model_id: Civitai model ID (numeric)
            dest_dir: Destination directory
            progress_callback: Optional callback(downloaded_bytes, total_bytes)
            **kwargs: Additional arguments:
                - version_id: Specific version to download (default: latest)
                - file_name: Specific file to download (default: primary file)

        Returns:
            Path to downloaded file
        """
        try:
            # Get model info to find download URL
            model_info = await self.get_model_info(model_id)
            if not model_info or not model_info.metadata:
                raise ValueError(f"Model {model_id} not found or has no versions")

            version_id = kwargs.get("version_id")
            if not version_id:
                version_id = model_info.metadata.get("latest_version_id")

            if not version_id:
                raise ValueError(f"No version found for model {model_id}")

            # Get version details to find download URL
            session = await self._get_session()
            headers = None
            if self.api_key:
                headers = {"Authorization": f"Bearer {self.api_key}"}

            async with session.get(
                f"{self.API_BASE}/model-versions/{version_id}",
                headers=headers
            ) as response:
                if response.status != 200:
                    raise ValueError(f"Version {version_id} not found")

                version_data = await response.json()
                files = version_data.get("files", [])

                if not files:
                    raise ValueError(f"No files found for version {version_id}")

                # Find the primary model file or use the first one
                file_name = kwargs.get("file_name")
                download_file = None

                if file_name:
                    # Find specific file by name
                    download_file = next((f for f in files if f.get("name") == file_name), None)
                else:
                    # Find primary file or first Model type file
                    download_file = next((f for f in files if f.get("primary", False)), None)
                    if not download_file:
                        download_file = next((f for f in files if f.get("type") == "Model"), None)
                    if not download_file:
                        download_file = files[0]

                if not download_file:
                    raise ValueError(f"Could not find file to download")

                download_url = download_file.get("downloadUrl")
                if not download_url:
                    raise ValueError(f"No download URL for file")

                # Download the file
                file_name = download_file.get("name", f"model_{model_id}.safetensors")
                file_size = download_file.get("sizeKB", 0) * 1024  # Convert to bytes
                dest_path = os.path.join(dest_dir, file_name)

                # Ensure destination directory exists
                os.makedirs(dest_dir, exist_ok=True)

                log.info(f"Downloading {file_name} from Civitai to {dest_path}")

                # Download with progress tracking
                async with session.get(download_url) as download_response:
                    if download_response.status != 200:
                        raise ValueError(f"Download failed with status {download_response.status}")

                    downloaded = 0
                    with open(dest_path, "wb") as f:
                        async for chunk in download_response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback:
                                progress_callback(downloaded, file_size)

                log.info(f"Civitai model downloaded to: {dest_path}")
                return dest_path

        except Exception as e:
            log.error(f"Civitai download failed for {model_id}: {e}")
            raise

    def get_model_url(self, model_id: str) -> str:
        """Get the web URL for a Civitai model"""
        return f"{self.CIVITAI_BASE}/models/{model_id}"

    async def validate_model_id(self, model_id: str) -> bool:
        """
        Validate Civitai model ID format.

        Valid format: Numeric string
        """
        if not model_id:
            return False
        return model_id.isdigit()


# Convenience function for testing
async def test_civitai_source():
    """Test Civitai source implementation"""
    source = CivitaiSource()

    try:
        print("Testing Civitai search...")
        result = await source.search("realistic", page_size=5, sort_by="downloads")
        print(f"Found {result.total} models, showing {len(result.models)}:")
        for model in result.models[:3]:
            print(f"  - {model.name} (ID: {model.id}, downloads: {model.downloads}, type: {model.model_type})")

        print("\nTesting get_model_info...")
        if result.models:
            first_model_id = result.models[0].id
            model_info = await source.get_model_info(first_model_id)
            if model_info:
                print(f"  Model: {model_info.name}")
                print(f"  Author: {model_info.author}")
                print(f"  Type: {model_info.model_type}")
                print(f"  Size: {model_info.size / 1024 / 1024:.2f} MB" if model_info.size else "  Size: Unknown")

        print("\nCivitai source test completed successfully!")

    finally:
        await source.close()


if __name__ == "__main__":
    asyncio.run(test_civitai_source())
