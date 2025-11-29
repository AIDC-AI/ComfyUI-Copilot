"""
Local model scanner implementation.

Scans ComfyUI's model directories and indexes existing model files.
"""

import os
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import folder_paths
from .model_source_base import ModelSourceBase, ModelInfo, SearchResult, ModelSourceType
from .logger import log


class LocalModelScanner(ModelSourceBase):
    """
    Local model scanner implementation.

    Scans ComfyUI's configured model directories and indexes existing files
    to make them searchable through the same interface as remote sources.
    """

    # Supported model file extensions
    MODEL_EXTENSIONS = {
        ".safetensors", ".ckpt", ".pt", ".pth", ".bin",
        ".onnx", ".pb", ".tflite", ".h5"
    }

    def __init__(self, timeout: float = 30.0):
        """
        Initialize local model scanner.

        Args:
            timeout: Not used for local scanning, kept for interface compatibility
        """
        super().__init__(timeout)
        self._model_cache: Optional[List[ModelInfo]] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_ttl = 300  # Cache for 5 minutes

    @property
    def source_type(self) -> ModelSourceType:
        return ModelSourceType.LOCAL

    @property
    def is_available(self) -> bool:
        """Local scanner is always available"""
        return True

    def _should_refresh_cache(self) -> bool:
        """Check if cache should be refreshed"""
        if self._model_cache is None or self._cache_timestamp is None:
            return True

        age = datetime.now().timestamp() - self._cache_timestamp
        return age > self._cache_ttl

    def _infer_model_type(self, file_path: str, model_type_key: str) -> str:
        """
        Infer specific model type from file path and folder type.

        Args:
            file_path: Full path to the model file
            model_type_key: ComfyUI folder key (e.g., "checkpoints", "loras")

        Returns:
            Inferred model type
        """
        path_lower = file_path.lower()
        filename = os.path.basename(path_lower)

        # Map ComfyUI folder keys to model types
        folder_type_map = {
            "checkpoints": "checkpoint",
            "loras": "lora",
            "vae": "vae",
            "vae_approx": "vae",
            "controlnet": "controlnet",
            "clip": "clip",
            "clip_vision": "clip_vision",
            "style_models": "style",
            "embeddings": "embedding",
            "hypernetworks": "hypernetwork",
            "upscale_models": "upscaler",
            "unet": "unet",
            "diffusion_models": "checkpoint",
        }

        base_type = folder_type_map.get(model_type_key, model_type_key)

        # Further refine based on filename patterns
        if "lora" in filename or "lycoris" in filename:
            return "lora"
        elif "controlnet" in filename or "control_" in filename:
            return "controlnet"
        elif "vae" in filename:
            return "vae"
        elif "clip" in filename:
            return "clip"
        elif "upscale" in filename or "esrgan" in filename:
            return "upscaler"
        elif "embedding" in filename or "textual" in filename:
            return "embedding"

        return base_type

    def _extract_tags_from_filename(self, filename: str) -> List[str]:
        """
        Extract potential tags from filename.

        Args:
            filename: Model filename

        Returns:
            List of extracted tags
        """
        tags = []
        filename_lower = filename.lower()

        # Common patterns in model names
        tag_patterns = {
            "sd15": "sd1.5",
            "sd1.5": "sd1.5",
            "sd2": "sd2",
            "sd2.1": "sd2.1",
            "sdxl": "sdxl",
            "sd3": "sd3",
            "flux": "flux",
            "realistic": "realistic",
            "anime": "anime",
            "cartoon": "cartoon",
            "3d": "3d",
            "photorealistic": "photorealistic",
            "portrait": "portrait",
            "landscape": "landscape",
            "fp16": "fp16",
            "fp32": "fp32",
            "ema": "ema",
            "pruned": "pruned",
        }

        for pattern, tag in tag_patterns.items():
            if pattern in filename_lower:
                tags.append(tag)

        return tags

    async def _scan_models(self) -> List[ModelInfo]:
        """
        Scan all configured model directories and build model index.

        Returns:
            List of ModelInfo for all found models
        """
        models = []

        try:
            # Get all configured folder types from ComfyUI
            folder_names_and_paths = folder_paths.folder_names_and_paths

            for model_type_key, (paths_list, _extensions) in folder_names_and_paths.items():
                for base_path in paths_list:
                    if not os.path.exists(base_path):
                        continue

                    # Walk directory tree
                    for root, _dirs, files in os.walk(base_path):
                        for file in files:
                            # Check if file has a supported extension
                            ext = os.path.splitext(file)[1].lower()
                            if ext not in self.MODEL_EXTENSIONS:
                                continue

                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, base_path)

                            # Get file stats
                            try:
                                stat = os.stat(full_path)
                                size = stat.st_size
                                modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
                            except Exception as e:
                                log.warning(f"Could not stat file {full_path}: {e}")
                                size = 0
                                modified = None

                            # Create model info
                            model_type = self._infer_model_type(full_path, model_type_key)
                            tags = self._extract_tags_from_filename(file)

                            # Use relative path as ID for local models
                            model_id = f"local:{model_type_key}/{rel_path}"

                            model_info = ModelInfo(
                                id=model_id,
                                name=file,
                                source=ModelSourceType.LOCAL,
                                path=os.path.dirname(rel_path) if os.path.dirname(rel_path) else None,
                                description=f"Local model in {model_type_key}",
                                downloads=None,  # Not applicable for local
                                likes=None,  # Not applicable for local
                                tags=tags,
                                last_updated=modified,
                                size=size,
                                model_type=model_type,
                                thumbnail_url=None,
                                author=None,
                                license=None,
                                metadata={
                                    "full_path": full_path,
                                    "relative_path": rel_path,
                                    "folder_type": model_type_key,
                                    "base_path": base_path,
                                }
                            )

                            models.append(model_info)

            log.info(f"Local scan found {len(models)} models")

        except Exception as e:
            log.error(f"Error scanning local models: {e}")
            import traceback
            traceback.print_exc()

        return models

    async def _get_models(self, force_refresh: bool = False) -> List[ModelInfo]:
        """
        Get cached models or refresh if needed.

        Args:
            force_refresh: Force a fresh scan even if cache is valid

        Returns:
            List of ModelInfo
        """
        if force_refresh or self._should_refresh_cache():
            self._model_cache = await self._scan_models()
            self._cache_timestamp = datetime.now().timestamp()

        return self._model_cache or []

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
        Search local models.

        Args:
            query: Search query (searches in filename and path)
            page: Page number (1-indexed)
            page_size: Results per page
            model_type: Filter by model type
            sort_by: Sort by "name", "size", "updated"
            **kwargs: Additional filters:
                - force_refresh: bool - Force rescan of directories

        Returns:
            SearchResult with matching models
        """
        try:
            force_refresh = kwargs.get("force_refresh", False)
            all_models = await self._get_models(force_refresh=force_refresh)

            # Filter by query (case-insensitive search in name and path)
            query_lower = query.lower()
            filtered = [
                m for m in all_models
                if query_lower in m.name.lower() or
                   (m.path and query_lower in m.path.lower())
            ]

            # Filter by model type
            if model_type:
                filtered = [m for m in filtered if m.model_type == model_type]

            # Sort results
            if sort_by == "name":
                filtered.sort(key=lambda m: m.name.lower())
            elif sort_by == "size":
                filtered.sort(key=lambda m: m.size or 0, reverse=True)
            elif sort_by == "updated":
                filtered.sort(
                    key=lambda m: m.last_updated or "",
                    reverse=True
                )

            # Paginate
            total = len(filtered)
            start = (page - 1) * page_size
            end = start + page_size
            page_models = filtered[start:end]

            return SearchResult(
                models=page_models,
                total=total,
                source=self.source_type,
                page=page,
                page_size=page_size
            )

        except Exception as e:
            log.error(f"Local search failed: {e}")
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
        Get information about a specific local model.

        Args:
            model_id: Local model ID (format: "local:folder_type/path")

        Returns:
            ModelInfo if found, None otherwise
        """
        try:
            all_models = await self._get_models()
            for model in all_models:
                if model.id == model_id:
                    return model
            return None

        except Exception as e:
            log.error(f"Failed to get local model info for {model_id}: {e}")
            return None

    async def download_model(
        self,
        model_id: str,
        dest_dir: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        **kwargs
    ) -> str:
        """
        "Download" a local model (just returns the existing path).

        Args:
            model_id: Local model ID
            dest_dir: Ignored for local models
            progress_callback: Ignored for local models
            **kwargs: Ignored

        Returns:
            Path to the existing model file
        """
        try:
            model_info = await self.get_model_info(model_id)
            if not model_info or not model_info.metadata:
                raise ValueError(f"Local model {model_id} not found")

            full_path = model_info.metadata.get("full_path")
            if not full_path or not os.path.exists(full_path):
                raise ValueError(f"Local model file not found: {full_path}")

            log.info(f"Local model already exists at: {full_path}")

            # Call progress callback with full size to indicate completion
            if progress_callback and model_info.size:
                progress_callback(model_info.size, model_info.size)

            return full_path

        except Exception as e:
            log.error(f"Failed to get local model {model_id}: {e}")
            raise

    def get_model_url(self, model_id: str) -> str:
        """Get the file path for a local model"""
        # For local models, return the file:// URL
        return f"file://local/{model_id}"

    async def validate_model_id(self, model_id: str) -> bool:
        """
        Validate local model ID format.

        Valid format: "local:folder_type/path"
        """
        if not model_id:
            return False
        return model_id.startswith("local:")

    def supports_download(self) -> bool:
        """Local scanner doesn't download, it just references existing files"""
        return False

    async def refresh_cache(self):
        """Force a refresh of the model cache"""
        await self._get_models(force_refresh=True)


# Convenience function for testing
async def test_local_scanner():
    """Test local model scanner implementation"""
    scanner = LocalModelScanner()

    try:
        print("Testing local model scan...")
        result = await scanner.search("", page_size=10)  # Empty query = all models
        print(f"Found {result.total} local models, showing {len(result.models)}:")
        for model in result.models[:5]:
            size_mb = model.size / 1024 / 1024 if model.size else 0
            print(f"  - {model.name} ({model.model_type}, {size_mb:.2f} MB)")

        print("\nTesting search...")
        search_result = await scanner.search("sd", page_size=5)
        print(f"Search for 'sd' found {search_result.total} models:")
        for model in search_result.models:
            print(f"  - {model.name}")

        print("\nLocal scanner test completed successfully!")

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_local_scanner())
