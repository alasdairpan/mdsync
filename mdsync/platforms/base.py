"""Abstract base class for platform implementations.

This module defines the Platform interface that all platform implementations
must follow to enable consistent behavior across different sync targets.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class Platform(ABC):
    """Abstract base class for platform sync implementations.

    This class defines the minimal interface for syncing markdown content
    to various platforms like Notion, Confluence, WordPress, etc.
    """

    def __init__(self, token: str, parent_id: str):
        """Initialize platform with authentication token and parent container.

        Args:
            token: API token for authentication
            parent_id: Parent container ID (e.g., Notion page ID)
        """
        self.token = token
        self.parent_id = parent_id

    @abstractmethod
    def sync(
        self,
        file_path: Path,
        blocks: list[dict[str, Any]],
        parent_id: str,
    ) -> Any:
        """Sync markdown content (as blocks) to the platform.

        Args:
            file_path: Path to the markdown file being synced
            blocks: List of platform-specific block dictionaries
            parent_id: Parent container ID for this specific file

        Returns:
            Created page ID or URL

        Raises:
            Exception: If sync fails
        """
        pass

    @abstractmethod
    def create_container(self, name: str, parent_id: str) -> str:
        """Create a container (folder/page) for nested content.

        Args:
            name: Name of the container
            parent_id: Parent container ID

        Returns:
            Created container ID

        Raises:
            Exception: If container creation fails
        """
        pass
