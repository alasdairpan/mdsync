"""Notion platform implementation.

This module implements the Platform interface for Notion using direct REST API calls.
Uses Notion API version 2025-09-03 for page creation and block operations.
"""

import random
import time
from pathlib import Path
from typing import Any, Union

import requests
from rich.console import Console

from ..constants import SAFE_EMOJIS
from .base import Platform

# Notion API limits
MAX_RICH_TEXT_LENGTH = 1600  # Notion API limit is 2000, using 1600 for safety margin
MAX_BLOCKS_PER_REQUEST = 100
RATE_LIMIT_DELAY = 0.35  # ~3 requests per second (1/3 = 0.33, add buffer)


class NotionPlatform(Platform):
    """Notion platform implementation using REST API v2025-09-03."""

    API_VERSION = "2025-09-03"
    BASE_URL = "https://api.notion.com/v1"

    def __init__(
        self,
        token: str,
        parent_id: str,
        console: Console,
        page_icon: bool = False,
        page_title: str = "filename",
    ):
        """Initialize Notion platform with API token and parent page ID.

        Args:
            token: Notion integration token
            parent_id: Parent page ID where content will be synced
            console: Rich Console for output
            page_icon: Whether to add random emoji icons to pages (default: False)
            page_title: How to determine page titles: 'heading' or 'filename' (default: 'filename')
        """
        super().__init__(token, parent_id)
        self.page_icon = page_icon
        self.page_title = page_title
        self.console = console
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Notion-Version": self.API_VERSION,
                "Content-Type": "application/json",
            }
        )
        self._last_request_time = 0.0  # Track last request for rate limiting

    def sync(
        self,
        file_path: Path,
        blocks: list[dict[str, Any]],
        parent_id: str,
    ) -> tuple[str, str, list[str]]:
        """Sync markdown content to Notion as a new page.

        Creates a new page with title from level 1 heading or folder name.
        If level 1 heading is used as title, it's removed from content.
        Handles 100-block-per-request chunking automatically.

        Args:
            file_path: Path to the markdown file being synced
            blocks: List of Notion block dictionaries
            parent_id: Parent page ID

        Returns:
            Tuple of (page_url, page_id, list of block_ids)

        Raises:
            requests.HTTPError: If API request fails
        """
        # Determine page title and whether to skip first block
        title, skip_first = self._extract_title(file_path, blocks)

        # Create the page with icon if enabled
        icon = random.choice(SAFE_EMOJIS) if self.page_icon else None
        page_id = self._create_page(title, parent_id, icon=icon)

        # Append blocks to the page, excluding heading_1 if used as title
        content_blocks = blocks[1:] if skip_first else blocks
        block_ids = []
        if content_blocks:
            block_ids = self._append_blocks(page_id, content_blocks)

        return self._get_page_url(page_id), page_id, block_ids

    def _extract_title(self, file_path: Path, blocks: list[dict[str, Any]]) -> tuple[str, bool]:
        """Extract page title based on page_title mode.

        Args:
            file_path: Path to the markdown file
            blocks: List of Notion block dictionaries

        Returns:
            Tuple of (title string, whether to skip first block in content)
        """
        if self.page_title == "heading":
            # Extract from first heading (any level)
            if blocks:
                first_block = blocks[0]
                block_type = first_block.get("type", "")

                # Check if first block is any heading type
                if block_type in ["heading_1", "heading_2", "heading_3"]:
                    heading_block = first_block.get(block_type, {})
                    rich_text = heading_block.get("rich_text", [])
                    if rich_text and rich_text[0].get("text"):
                        title = rich_text[0]["text"]["content"]
                        return title, True  # Skip first block (heading) in content

            # No heading found, use default
            return "New page", False
        else:
            # filename mode: use exact filename
            return file_path.stem, False  # Don't skip any blocks

    def create_container(self, name: str, parent_id: str) -> str:
        """Create a nested page (container) for directory structure.

        Args:
            name: Name of the directory/container
            parent_id: Parent page ID

        Returns:
            Created page ID

        Raises:
            requests.HTTPError: If API request fails
        """
        icon = random.choice(SAFE_EMOJIS) if self.page_icon else None
        return self._create_page(name.title(), parent_id, icon=icon)

    def _create_page(self, title: str, parent_id: str, icon: Union[str, None] = None) -> str:
        """Create a new page in Notion with retry logic.

        Args:
            title: Page title
            parent_id: Parent page ID
            icon: Emoji icon for the page (None to omit icon)

        Returns:
            Created page ID

        Raises:
            requests.HTTPError: If API request fails after retries
        """
        # Truncate title if too long
        if len(title) > MAX_RICH_TEXT_LENGTH:
            self.console.print(
                f"[yellow]⚠ Title exceeds {MAX_RICH_TEXT_LENGTH} chars ({len(title)}), truncating...[/yellow]"
            )
            title = title[:MAX_RICH_TEXT_LENGTH]

        payload = {
            "parent": {"page_id": parent_id},
            "properties": {"title": {"title": [{"text": {"content": title}}]}},
        }

        # Add icon if provided
        if icon:
            payload["icon"] = {"type": "emoji", "emoji": icon}

        response = self._make_request("POST", f"{self.BASE_URL}/pages", json=payload)
        return str(response.json()["id"])

    def update_block(self, block_id: str, block_content: dict[str, Any]) -> None:
        """Update a single block's content.

        Note: Notion API does not allow updating children directly. This method
        only updates the block's rich_text content (for link resolution).
        Nested children blocks are not modified during updates.

        Args:
            block_id: The ID of the block to update
            block_content: The block content object (e.g., {"paragraph": {"rich_text": [...]}})

        Raises:
            ValueError: If block content is invalid
            requests.HTTPError: If API request fails
        """
        # Extract and validate block type from block_content
        block_type = block_content.get("type")
        if not block_type or block_type not in block_content:
            raise ValueError("Invalid block content: missing type or type data")

        # Note: Children blocks cannot be updated via this endpoint and are ignored
        # This is a limitation of the Notion API - children must be updated separately
        payload = {block_type: block_content[block_type]}

        self._make_request("PATCH", f"{self.BASE_URL}/blocks/{block_id}", json=payload)

    def _append_blocks(
        self,
        page_id: str,
        blocks: list[dict[str, Any]],
        chunk_size: int = MAX_BLOCKS_PER_REQUEST,
    ) -> list[str]:
        """Append blocks to a Notion page with automatic chunking.

        Validates block content against Notion API limits before sending.

        Args:
            page_id: Target page ID
            blocks: List of block dictionaries
            chunk_size: Maximum blocks per request (default: 100, Notion limit)

        Returns:
            List of created block IDs in the same order as input blocks

        Raises:
            requests.HTTPError: If API request fails
        """
        # Validate and sanitize blocks
        validated_blocks = self._validate_blocks(blocks)

        # Split blocks into chunks
        num_chunks = (len(validated_blocks) + chunk_size - 1) // chunk_size
        if num_chunks > 1:
            self.console.print(
                f"[green]⚠ Appending {len(validated_blocks)} blocks in {num_chunks} chunks[/green]"
            )

        all_block_ids: list[str] = []
        for i in range(0, len(validated_blocks), chunk_size):
            chunk = validated_blocks[i : i + chunk_size]
            payload = {"children": chunk}

            response = self._make_request(
                "PATCH", f"{self.BASE_URL}/blocks/{page_id}/children", json=payload
            )

            # Extract block IDs from response
            response_data = response.json()
            created_blocks = response_data.get("results", [])
            chunk_block_ids = [block["id"] for block in created_blocks]
            all_block_ids.extend(chunk_block_ids)

        return all_block_ids

    def _make_request(
        self, method: str, url: str, max_retries: int = 3, **kwargs: Any
    ) -> requests.Response:
        """Make HTTP request with rate limiting and retry logic.

        Implements rate limiting (3 req/sec average) and handles 429 responses.

        Args:
            method: HTTP method (GET, POST, PATCH, etc.)
            url: Full URL for the request
            max_retries: Maximum retry attempts for 429 errors
            **kwargs: Additional arguments to pass to requests

        Returns:
            Response object

        Raises:
            requests.HTTPError: If request fails after retries
        """
        for attempt in range(max_retries):
            # Rate limiting: ensure minimum delay between requests
            elapsed = time.time() - self._last_request_time
            if elapsed < RATE_LIMIT_DELAY:
                sleep_time = RATE_LIMIT_DELAY - elapsed
                self.console.print(f"[dim]⏱ Rate limiting: waiting {sleep_time:.2f}s[/dim]")
                time.sleep(sleep_time)

            self._last_request_time = time.time()

            try:
                response = self._session.request(method, url, **kwargs)

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "1"))
                    if attempt < max_retries - 1:
                        if self.console:
                            self.console.print(
                                f"[yellow]⚠ Rate limited (429). Retrying in {retry_after}s (attempt {attempt + 1}/{max_retries})[/yellow]"
                            )
                        time.sleep(retry_after)
                        continue
                    else:
                        if self.console:
                            self.console.print(
                                f"[red]✗ Rate limited after {max_retries} attempts[/red]"
                            )

                # Check for errors and display detailed message
                if not response.ok:
                    try:
                        error_json = response.json()
                        if self.console and "code" in error_json:
                            self.console.print(
                                f"[red]✗ Notion API Error ({response.status_code}): {error_json.get('code')} - {error_json.get('message', '')}[/red]"
                            )
                    except Exception:
                        pass

                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                if self.console:
                    self.console.print(
                        f"[red]✗ Request failed: {method} {url} - {type(e).__name__}: {e}[/red]"
                    )
                raise

        # This should never be reached as the loop should always return or raise
        raise RuntimeError(
            f"Request failed after {max_retries} retries without raising an exception"
        )

    def _validate_blocks(self, blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate and sanitize blocks to meet Notion API limits.

        Truncates rich text content exceeding 2000 characters.

        Args:
            blocks: List of block dictionaries

        Returns:
            Validated list of blocks
        """
        validated = []
        for block in blocks:
            validated_block = self._validate_block(block)
            validated.append(validated_block)
        return validated

    def _validate_block(self, block: dict[str, Any]) -> dict[str, Any]:
        """Validate and sanitize a single block.

        Recursively validates nested blocks and truncates long rich text.

        Args:
            block: Block dictionary

        Returns:
            Validated block dictionary
        """
        block = block.copy()
        block_type = block.get("type")

        if not block_type:
            return block

        # Get the block content
        content = block.get(block_type, {})
        if not isinstance(content, dict):
            return block

        # Validate rich_text arrays
        if "rich_text" in content and isinstance(content["rich_text"], list):
            content["rich_text"] = self._validate_rich_text_array(content["rich_text"])

        # Validate nested children recursively
        if "children" in content and isinstance(content["children"], list):
            content["children"] = self._validate_blocks(content["children"])

        block[block_type] = content
        return block

    def _validate_rich_text_array(
        self, rich_text_array: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Validate rich text array elements.

        Splits text content exceeding 2000 characters into multiple elements.
        Notion allows up to 100 elements in a rich_text array.

        Args:
            rich_text_array: Array of rich text objects

        Returns:
            Validated rich text array with long text split across multiple elements
        """
        validated = []
        for item in rich_text_array:
            if item.get("type") == "text":
                text_obj = item.get("text", {})
                content = text_obj.get("content", "")

                # Fix invalid relative URLs by setting them to null
                link = text_obj.get("link")
                if link and isinstance(link, dict):
                    url = link.get("url")
                    if url and not url.startswith(("http://", "https://", "#", "mailto:", "//")):
                        # Unresolved relative link - set to None to avoid Notion API error
                        text_obj["link"] = None

                # Split if exceeds limit
                if len(content) > MAX_RICH_TEXT_LENGTH:
                    # Split content into chunks of MAX_RICH_TEXT_LENGTH
                    chunks = [
                        content[i : i + MAX_RICH_TEXT_LENGTH]
                        for i in range(0, len(content), MAX_RICH_TEXT_LENGTH)
                    ]

                    if self.console:
                        self.console.print(
                            f"[green]⚠ Content exceeds {MAX_RICH_TEXT_LENGTH} chars ({len(content)}), splitting into {len(chunks)} parts[/green]"
                        )

                    # Create a separate rich_text object for each chunk
                    # Important: preserve annotations and other properties
                    for chunk in chunks:
                        chunk_item: dict[str, Any] = {
                            "type": "text",
                            "text": {
                                "content": chunk,
                            },
                        }

                        # Preserve link if exists
                        if "link" in text_obj:
                            chunk_item["text"]["link"] = text_obj["link"]

                        # Preserve annotations if exists
                        if "annotations" in item:
                            chunk_item["annotations"] = item["annotations"]

                        validated.append(chunk_item)
                else:
                    validated.append(item)
            else:
                validated.append(item)
        return validated

    def _get_page_url(self, page_id: str) -> str:
        """Convert page ID to Notion page URL.

        Args:
            page_id: Notion page ID (with or without dashes)

        Returns:
            Full Notion page URL
        """
        # Remove dashes from page ID for URL
        clean_id = page_id.replace("-", "")
        return f"https://www.notion.so/{clean_id}"
