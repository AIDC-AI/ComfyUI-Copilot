"""
Unified model gateway for managing multiple model sources.

This module provides a single interface for searching and downloading models
from multiple sources (HuggingFace, Civitai, Local, etc.)
"""

import asyncio
from typing import Any, Dict, List, Optional, Callable
from .model_source_base import ModelSourceBase, ModelInfo, SearchResult, ModelSourceType
from .huggingface_source import HuggingFaceSource
from .civitai_source import CivitaiSource
from .local_model_scanner import LocalModelScanner
from .logger import log


class ModelGateway:
    """
    Unified gateway for accessing models from multiple sources.

    Manages HuggingFace, Civitai, Local, and potentially other sources,
    providing a unified search and download interface.
    """

    def __init__(
        self,
        enable_huggingface: bool = True,
        enable_civitai: bool = True,
        enable_local: bool = True,
        huggingface_token: Optional[str] = None,
        civitai_api_key: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Initialize the model gateway.

        Args:
            enable_huggingface: Enable HuggingFace source
            enable_civitai: Enable Civitai source
            enable_local: Enable local model scanning
            huggingface_token: Optional HuggingFace API token
            civitai_api_key: Optional Civitai API key
            timeout: Request timeout in seconds
        """
        self.sources: Dict[ModelSourceType, ModelSourceBase] = {}

        # Initialize enabled sources
        if enable_huggingface:
            try:
                self.sources[ModelSourceType.HUGGINGFACE] = HuggingFaceSource(
                    timeout=timeout,
                    api_token=huggingface_token
                )
                log.info("HuggingFace source enabled")
            except Exception as e:
                log.warning(f"Failed to initialize HuggingFace source: {e}")

        if enable_civitai:
            try:
                self.sources[ModelSourceType.CIVITAI] = CivitaiSource(
                    timeout=timeout,
                    api_key=civitai_api_key
                )
                log.info("Civitai source enabled")
            except Exception as e:
                log.warning(f"Failed to initialize Civitai source: {e}")

        if enable_local:
            try:
                self.sources[ModelSourceType.LOCAL] = LocalModelScanner(timeout=timeout)
                log.info("Local model scanner enabled")
            except Exception as e:
                log.warning(f"Failed to initialize local scanner: {e}")

        if not self.sources:
            log.warning("No model sources available!")

    async def close(self):
        """Close all sources and cleanup resources"""
        for source in self.sources.values():
            if hasattr(source, 'close'):
                try:
                    await source.close()
                except Exception as e:
                    log.error(f"Error closing source {source.source_type}: {e}")

    def get_available_sources(self) -> List[ModelSourceType]:
        """Get list of available model sources"""
        return [
            source_type
            for source_type, source in self.sources.items()
            if source.is_available
        ]

    def get_source(self, source_type: ModelSourceType) -> Optional[ModelSourceBase]:
        """Get a specific model source by type"""
        return self.sources.get(source_type)

    async def search_all(
        self,
        query: str,
        page: int = 1,
        page_size: int = 30,
        model_type: Optional[str] = None,
        sort_by: Optional[str] = None,
        sources: Optional[List[ModelSourceType]] = None,
        **kwargs
    ) -> Dict[ModelSourceType, SearchResult]:
        """
        Search across all enabled sources in parallel.

        Args:
            query: Search query
            page: Page number
            page_size: Results per page
            model_type: Filter by model type
            sort_by: Sort criterion
            sources: Specific sources to search (default: all available)
            **kwargs: Source-specific parameters

        Returns:
            Dict mapping source type to search results
        """
        # Determine which sources to search
        search_sources = sources or list(self.sources.keys())
        available_sources = [s for s in search_sources if s in self.sources]

        if not available_sources:
            log.warning("No sources available for search")
            return {}

        # Create search tasks for each source
        async def search_source(source_type: ModelSourceType) -> tuple:
            try:
                source = self.sources[source_type]
                if not source.is_available:
                    return (source_type, SearchResult(
                        models=[],
                        total=0,
                        source=source_type,
                        page=page,
                        page_size=page_size
                    ))

                result = await source.search(
                    query=query,
                    page=page,
                    page_size=page_size,
                    model_type=model_type,
                    sort_by=sort_by,
                    **kwargs
                )
                return (source_type, result)

            except Exception as e:
                log.error(f"Search failed for {source_type}: {e}")
                return (source_type, SearchResult(
                    models=[],
                    total=0,
                    source=source_type,
                    page=page,
                    page_size=page_size
                ))

        # Execute searches in parallel
        tasks = [search_source(source_type) for source_type in available_sources]
        results = await asyncio.gather(*tasks)

        return dict(results)

    async def search_unified(
        self,
        query: str,
        page: int = 1,
        page_size: int = 30,
        model_type: Optional[str] = None,
        sort_by: Optional[str] = None,
        sources: Optional[List[ModelSourceType]] = None,
        **kwargs
    ) -> SearchResult:
        """
        Search across all sources and return unified results.

        This combines results from all sources into a single SearchResult,
        interleaving results and adjusting pagination.

        Args:
            query: Search query
            page: Page number
            page_size: Results per page
            model_type: Filter by model type
            sort_by: Sort criterion
            sources: Specific sources to search (default: all available)
            **kwargs: Source-specific parameters

        Returns:
            Unified SearchResult combining all sources
        """
        # Get results from all sources
        all_results = await self.search_all(
            query=query,
            page=1,  # Get first page from each source
            page_size=page_size * len(self.sources),  # Get more to account for interleaving
            model_type=model_type,
            sort_by=sort_by,
            sources=sources,
            **kwargs
        )

        # Combine all models
        combined_models: List[ModelInfo] = []
        total_count = 0

        for source_type, result in all_results.items():
            combined_models.extend(result.models)
            total_count += result.total

        # Apply unified sorting if needed
        if sort_by == "downloads":
            combined_models.sort(key=lambda m: m.downloads or 0, reverse=True)
        elif sort_by == "likes":
            combined_models.sort(key=lambda m: m.likes or 0, reverse=True)
        elif sort_by == "updated":
            combined_models.sort(key=lambda m: m.last_updated or "", reverse=True)
        elif sort_by == "name":
            combined_models.sort(key=lambda m: m.name.lower())

        # Apply pagination to combined results
        start = (page - 1) * page_size
        end = start + page_size
        page_models = combined_models[start:end]

        return SearchResult(
            models=page_models,
            total=total_count,
            source=ModelSourceType.LOCAL,  # Placeholder, represents "all sources"
            page=page,
            page_size=page_size
        )

    async def get_model_info(self, model_id: str, source_type: Optional[ModelSourceType] = None) -> Optional[ModelInfo]:
        """
        Get information about a specific model.

        Args:
            model_id: Model identifier
            source_type: Specific source to query (if None, tries to infer from model_id)

        Returns:
            ModelInfo if found, None otherwise
        """
        # If source specified, query that source directly
        if source_type:
            source = self.sources.get(source_type)
            if source:
                return await source.get_model_info(model_id)
            return None

        # Try to infer source from model_id
        if model_id.startswith("local:"):
            source = self.sources.get(ModelSourceType.LOCAL)
            if source:
                return await source.get_model_info(model_id)

        elif "/" in model_id:
            # Likely HuggingFace format (username/model)
            source = self.sources.get(ModelSourceType.HUGGINGFACE)
            if source:
                return await source.get_model_info(model_id)

        elif model_id.isdigit():
            # Likely Civitai format (numeric ID)
            source = self.sources.get(ModelSourceType.CIVITAI)
            if source:
                return await source.get_model_info(model_id)

        # If we couldn't infer, try all sources
        for source in self.sources.values():
            try:
                info = await source.get_model_info(model_id)
                if info:
                    return info
            except Exception as e:
                log.debug(f"Source {source.source_type} couldn't find model {model_id}: {e}")
                continue

        return None

    async def download_model(
        self,
        model_id: str,
        dest_dir: str,
        source_type: Optional[ModelSourceType] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        **kwargs
    ) -> str:
        """
        Download a model from the appropriate source.

        Args:
            model_id: Model identifier
            dest_dir: Destination directory
            source_type: Specific source to download from (if None, infers from model_id)
            progress_callback: Progress callback(downloaded_bytes, total_bytes)
            **kwargs: Source-specific download parameters

        Returns:
            Path to downloaded model

        Raises:
            ValueError: If model or source not found
            Exception: If download fails
        """
        # Determine source
        if source_type:
            source = self.sources.get(source_type)
            if not source:
                raise ValueError(f"Source {source_type} not available")
        else:
            # Infer source from model_id
            if model_id.startswith("local:"):
                source = self.sources.get(ModelSourceType.LOCAL)
            elif "/" in model_id:
                source = self.sources.get(ModelSourceType.HUGGINGFACE)
            elif model_id.isdigit():
                source = self.sources.get(ModelSourceType.CIVITAI)
            else:
                raise ValueError(f"Could not infer source from model_id: {model_id}")

            if not source:
                raise ValueError(f"No source available for model_id: {model_id}")

        # Download using the identified source
        return await source.download_model(
            model_id=model_id,
            dest_dir=dest_dir,
            progress_callback=progress_callback,
            **kwargs
        )

    def get_model_url(self, model_id: str, source_type: Optional[ModelSourceType] = None) -> Optional[str]:
        """
        Get the web URL for a model.

        Args:
            model_id: Model identifier
            source_type: Specific source (if None, infers from model_id)

        Returns:
            URL string if found, None otherwise
        """
        # Determine source
        if source_type:
            source = self.sources.get(source_type)
        else:
            # Infer source from model_id
            if model_id.startswith("local:"):
                source = self.sources.get(ModelSourceType.LOCAL)
            elif "/" in model_id:
                source = self.sources.get(ModelSourceType.HUGGINGFACE)
            elif model_id.isdigit():
                source = self.sources.get(ModelSourceType.CIVITAI)
            else:
                return None

        if not source:
            return None

        return source.get_model_url(model_id)


# Global instance
_gateway: Optional[ModelGateway] = None


def get_model_gateway() -> ModelGateway:
    """
    Get or create the global model gateway instance.

    Returns:
        ModelGateway instance
    """
    global _gateway
    if _gateway is None:
        # TODO: Load configuration from environment variables
        _gateway = ModelGateway(
            enable_huggingface=True,
            enable_civitai=True,
            enable_local=True,
        )
    return _gateway


async def close_model_gateway():
    """Close the global model gateway instance"""
    global _gateway
    if _gateway:
        await _gateway.close()
        _gateway = None


# Convenience function for testing
async def test_model_gateway():
    """Test the unified model gateway"""
    gateway = ModelGateway()

    try:
        print("Available sources:", gateway.get_available_sources())

        print("\nTesting unified search for 'stable-diffusion'...")
        result = await gateway.search_unified("stable-diffusion", page_size=10)
        print(f"Found {result.total} total models across all sources, showing {len(result.models)}:")
        for model in result.models[:5]:
            print(f"  [{model.source.value}] {model.name} - {model.id}")

        print("\nTesting source-specific search (HuggingFace only)...")
        hf_results = await gateway.search_all(
            "lora",
            page_size=5,
            sources=[ModelSourceType.HUGGINGFACE]
        )
        for source_type, search_result in hf_results.items():
            print(f"  {source_type.value}: {len(search_result.models)} models")

        print("\nModel gateway test completed successfully!")

    finally:
        await gateway.close()


if __name__ == "__main__":
    asyncio.run(test_model_gateway())
