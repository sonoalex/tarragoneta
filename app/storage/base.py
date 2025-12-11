"""Base storage provider interface."""

from abc import ABC, abstractmethod


class StorageProvider(ABC):
    """Abstract storage provider."""

    @abstractmethod
    def save(self, key: str, file_path: str) -> str:
        """Save local file at file_path under key. Returns key."""
        raise NotImplementedError

    @abstractmethod
    def url_for(self, key: str) -> str:
        """Return public (or signed) URL for key."""
        raise NotImplementedError

