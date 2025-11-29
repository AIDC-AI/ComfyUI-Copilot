"""
Abstract base class for model sources (HuggingFace, Civitai, Local, etc.)

This module defines the interface that all model sources must implement
to provide a unified API for searching and downloading models.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class ModelSourceType(Enum):
    """Enumeration of supported model source types"""
    HUGGINGFACE = "huggingface"
    CIVITAI = "civitai"
    LOCAL = "local"
    MODELSCOPE = "modelscope"  # Legacy support


@dataclass
class ModelInfo:
    """
    Standardized model information across all sources.

    This format is returned by all model sources and consumed by the frontend.
    """
    # Required fields
    id: str                          # Unique identifier (e.g., "stabilityai/stable-diffusion-2-1")
    name: str                        # Display name
    source: ModelSourceType          # Which source this came from

    # Optional fields
    path: Optional[str] = None       # Path/namespace (e.g., "stabilityai")
    description: Optional[str] = None
    downloads: Optional[int] = None
    likes: Optional[int] = None
    tags: Optional[List[str]] = None
    last_updated: Optional[str] = None  # ISO timestamp or Unix timestamp
    size: Optional[int] = None       # Size in bytes
    model_type: Optional[str] = None # "checkpoint", "lora", "vae", etc.
    thumbnail_url: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None

    # Source-specific metadata (flexible dict for any additional data)
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "source": self.source.value,
            "path": self.path,
            "description": self.description,
            "downloads": self.downloads,
            "likes": self.likes,
            "tags": self.tags or [],
            "last_updated": self.last_updated,
            "size": self.size,
            "model_type": self.model_type,
            "thumbnail_url": self.thumbnail_url,
            "author": self.author,
            "license": self.license,
            "metadata": self.metadata or {}
        }


@dataclass
class SearchResult:
    """
    Result from a model search operation.
    """
    models: List[ModelInfo]
    total: int
    source: ModelSourceType
    page: int = 1
    page_size: int = 30

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "models": [m.to_dict() for m in self.models],
            "total": self.total,
            "source": self.source.value,
            "page": self.page,
            "page_size": self.page_size
        }


class ModelSourceBase(ABC):
    """
    Abstract base class for model sources.

    All model sources (HuggingFace, Civitai, Local, etc.) must implement this interface
    to ensure consistent behavior across different sources.
    """

    def __init__(self, timeout: float = 30.0):
        """
        Initialize the model source.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout

    @property
    @abstractmethod
    def source_type(self) -> ModelSourceType:
        """Return the type of this model source"""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this model source is currently available.

        Returns:
            True if the source can be used, False otherwise
        """
        pass

    @abstractmethod
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
        Search for models matching the query.

        Args:
            query: Search query string
            page: Page number (1-indexed)
            page_size: Number of results per page
            model_type: Filter by model type (e.g., "checkpoint", "lora")
            sort_by: Sort criterion (e.g., "downloads", "updated", "likes")
            **kwargs: Source-specific additional parameters

        Returns:
            SearchResult containing matching models

        Raises:
            Exception: If search fails
        """
        pass

    @abstractmethod
    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """
        Get detailed information about a specific model.

        Args:
            model_id: Unique identifier for the model

        Returns:
            ModelInfo if found, None otherwise
        """
        pass

    @abstractmethod
    async def download_model(
        self,
        model_id: str,
        dest_dir: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        **kwargs
    ) -> str:
        """
        Download a model to the specified directory.

        Args:
            model_id: Unique identifier for the model
            dest_dir: Destination directory path
            progress_callback: Optional callback(downloaded_bytes, total_bytes)
            **kwargs: Source-specific additional parameters (e.g., revision, filename)

        Returns:
            Path to the downloaded model directory/file

        Raises:
            Exception: If download fails
        """
        pass

    @abstractmethod
    def get_model_url(self, model_id: str) -> str:
        """
        Get the web URL for viewing this model in a browser.

        Args:
            model_id: Unique identifier for the model

        Returns:
            Full URL to the model's page
        """
        pass

    def supports_download(self) -> bool:
        """
        Check if this source supports downloading models.

        Returns:
            True if download_model() is implemented, False otherwise
        """
        return True

    async def validate_model_id(self, model_id: str) -> bool:
        """
        Validate if a model ID is properly formatted for this source.

        Args:
            model_id: Model identifier to validate

        Returns:
            True if valid, False otherwise
        """
        # Default implementation - override if source has specific format requirements
        return bool(model_id and len(model_id.strip()) > 0)
