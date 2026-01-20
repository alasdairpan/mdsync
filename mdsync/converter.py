"""Markdown to Notion blocks converter.

This module uses mistletoe to parse markdown into AST and transforms
AST nodes to Notion block format.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

import mistletoe.block_token as block_token
import mistletoe.span_token as span_token
from mistletoe.latex_renderer import LaTeXRenderer
from mistletoe.latex_token import Math


@dataclass
class ParseResult:
    """Result of parsing a markdown file.

    Attributes:
        blocks: List of Notion block dictionaries
        blocks_with_links: List of (block_index, relative_link_path) tuples for blocks containing relative links
    """

    blocks: list[dict[str, Any]]
    blocks_with_links: list[tuple[int, str]]  # (block_index, relative_link_path)


class _BlockLinkTracker:
    """Helper class to track relative links in a block."""

    def __init__(self) -> None:
        self.relative_links: list[str] = []  # List of relative link paths

    def add_link(self, target: str, is_relative: bool) -> None:
        """Track a link target.

        Args:
            target: The link target URL/path
            is_relative: Whether this is a relative link to resolve
        """
        if is_relative:
            self.relative_links.append(target)


def parse_markdown(
    file_path: Path,
    page_map: Optional[dict[Path, str]] = None,
) -> ParseResult:
    """Parse a markdown file and convert it to Notion blocks.

    Args:
        file_path: Path to the markdown file to parse
        page_map: Optional mapping of file paths to Notion page URLs for resolving relative links

    Returns:
        ParseResult containing blocks and metadata about relative links

    Raises:
        FileNotFoundError: If the markdown file doesn't exist
        ValueError: If the file cannot be parsed
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Use LaTeXRenderer context to enable Math token parsing
    with LaTeXRenderer(), open(file_path, encoding="utf-8") as f:
        doc = block_token.Document(f)

    blocks: list[dict[str, Any]] = []
    blocks_with_links: list[tuple[int, str]] = []  # (block_index, relative_link_path)

    if doc.children:
        for child in doc.children:
            block_idx = len(blocks)
            link_tracker = _BlockLinkTracker()
            transformed = _transform_block(child, file_path, page_map, link_tracker)

            if isinstance(transformed, list):
                # For lists, each item gets its own index
                for i, _block in enumerate(transformed):
                    # If this list had relative links, record each block with each link
                    for rel_link in link_tracker.relative_links:
                        blocks_with_links.append((block_idx + i, rel_link))
                blocks.extend(transformed)
            elif transformed is not None:
                # For single blocks, record each relative link
                for rel_link in link_tracker.relative_links:
                    blocks_with_links.append((block_idx, rel_link))
                blocks.append(transformed)

    return ParseResult(
        blocks=blocks,
        blocks_with_links=blocks_with_links,
    )


def _transform_block(
    token: Any,
    file_path: Path,
    page_map: Optional[dict[Path, str]],
    link_tracker: _BlockLinkTracker,
) -> Union[dict[str, Any], list[dict[str, Any]], None]:
    """Transform a block token into Notion block(s).

    Args:
        token: The block token to transform
        file_path: Path to the current markdown file
        page_map: Optional mapping of file paths to Notion page URLs
        link_tracker: Tracker for relative links in this block

    Returns:
        A Notion block dict, list of blocks, or None if unsupported
    """
    if isinstance(token, block_token.Heading):
        return _transform_heading(token, file_path, page_map, link_tracker)
    elif isinstance(token, block_token.Paragraph):
        return _transform_paragraph(token, file_path, page_map, link_tracker)
    elif isinstance(token, (block_token.CodeFence, block_token.BlockCode)):
        return _transform_code_block(token)
    elif isinstance(token, block_token.Quote):
        return _transform_blockquote(token, file_path, page_map, link_tracker)
    elif isinstance(token, block_token.List):
        return _transform_list(token, file_path, page_map, link_tracker)
    elif isinstance(token, block_token.Table):
        return _transform_table(token, file_path, page_map, link_tracker)
    elif isinstance(token, block_token.ThematicBreak):
        return {"type": "divider", "divider": {}}
    else:
        # Unsupported block type
        return None


def _transform_heading(
    node: block_token.Heading,
    file_path: Path,
    page_map: Optional[dict[Path, str]],
    link_tracker: _BlockLinkTracker,
) -> dict[str, Any]:
    """Transform a heading node to Notion heading block."""
    level = node.level
    if level > 3:
        level = 3  # Notion only supports h1, h2, h3

    block_type = f"heading_{level}"
    rich_text = _transform_inline_formatting(
        list(node.children) if node.children else [],
        file_path,
        page_map,
        link_tracker,
    )

    return {
        "type": block_type,
        block_type: {
            "rich_text": rich_text,
            "color": "default",
            "is_toggleable": False,
        },
    }


def _transform_paragraph(
    node: block_token.Paragraph,
    file_path: Path,
    page_map: Optional[dict[Path, str]],
    link_tracker: _BlockLinkTracker,
) -> dict[str, Any]:
    """Transform a paragraph node to Notion paragraph block.

    Special case: If the paragraph contains only a Math token (block equation),
    convert it to an equation block instead of a paragraph.
    """
    children_list = list(node.children) if node.children else []

    # Check if this paragraph contains only a single Math token (block equation)
    if len(children_list) == 1 and isinstance(children_list[0], Math):
        math_token = children_list[0]
        # Extract expression, removing $$ delimiters and whitespace
        content = math_token.content.strip()
        if content.startswith("$$") and content.endswith("$$"):
            expression = content[2:-2].strip()
        else:
            expression = content

        return {
            "type": "equation",
            "equation": {"expression": expression},
        }

    # Normal paragraph with inline content
    rich_text = _transform_inline_formatting(children_list, file_path, page_map, link_tracker)

    return {
        "type": "paragraph",
        "paragraph": {
            "rich_text": rich_text,
            "color": "default",
        },
    }


def _transform_code_block(
    node: Union[block_token.CodeFence, block_token.BlockCode],
) -> dict[str, Any]:
    """Transform a code block node to Notion code block."""
    # Extract language (default to "plain text")
    language = getattr(node, "language", "plain text") or "plain text"

    # Get the code content
    content = ""
    if node.children:
        children_list = list(node.children)
        if children_list:
            first_child = children_list[0]
            content = str(getattr(first_child, "content", ""))

    return {
        "type": "code",
        "code": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": content},
                }
            ],
            "language": _map_language(language),
            "caption": [],
        },
    }


def _transform_list(
    node: block_token.List,
    file_path: Path,
    page_map: Optional[dict[Path, str]],
    link_tracker: _BlockLinkTracker,
) -> list[dict[str, Any]]:
    """Transform a list node to Notion list blocks."""
    blocks: list[dict[str, Any]] = []
    is_ordered = hasattr(node, "loose") and node.start is not None

    block_type = "numbered_list_item" if is_ordered else "bulleted_list_item"

    if node.children:
        for item in node.children:
            if isinstance(item, block_token.ListItem):
                # Extract inline content from paragraph children and nested blocks
                rich_text: list[dict[str, Any]] = []
                children_blocks: list[dict[str, Any]] = []

                if item.children:
                    for child in item.children:
                        if isinstance(child, block_token.Paragraph) and child.children:
                            rich_text.extend(
                                _transform_inline_formatting(
                                    list(child.children), file_path, page_map, link_tracker
                                )
                            )
                        elif isinstance(child, block_token.List):
                            # Handle nested lists
                            nested_blocks = _transform_list(
                                child, file_path, page_map, link_tracker
                            )
                            children_blocks.extend(nested_blocks)
                        else:
                            # Handle other nested blocks (code, quotes, etc.)
                            transformed = _transform_block(child, file_path, page_map, link_tracker)
                            if isinstance(transformed, list):
                                children_blocks.extend(transformed)
                            elif transformed is not None:
                                children_blocks.append(transformed)

                # Check for task list syntax (- [ ] or - [x])
                is_task_list = False
                is_checked = False
                if rich_text and len(rich_text) > 0:
                    first_text = rich_text[0]
                    if first_text.get("type") == "text":
                        content = first_text["text"]["content"]
                        # Check for task list markers
                        if (
                            content.startswith("[ ] ")
                            or content.startswith("[x] ")
                            or content.startswith("[] ")
                            or content.startswith("[X] ")
                        ):
                            is_task_list = True
                            is_checked = content[1].lower() == "x"
                            # Remove the checkbox syntax from the text
                            first_text["text"]["content"] = (
                                content[4:] if len(content) > 4 else content[3:]
                            )

                # Create appropriate block type
                if is_task_list:
                    block_data: dict[str, Any] = {
                        "rich_text": rich_text,
                        "checked": is_checked,
                        "color": "default",
                    }
                    if children_blocks:
                        block_data["children"] = children_blocks

                    block = {
                        "type": "to_do",
                        "to_do": block_data,
                    }
                else:
                    block_data = {
                        "rich_text": rich_text,
                        "color": "default",
                    }
                    if children_blocks:
                        block_data["children"] = children_blocks

                    block = {
                        "type": block_type,
                        block_type: block_data,
                    }

                blocks.append(block)

    return blocks


def _transform_table(
    node: block_token.Table,
    file_path: Path,
    page_map: Optional[dict[Path, str]],
    link_tracker: _BlockLinkTracker,
) -> dict[str, Any]:
    """Transform a table node to Notion table block."""
    # Count columns from first row
    first_row = None
    if node.children:
        children_list = list(node.children)
        if children_list:
            first_row = children_list[0]

    table_width = 0
    if first_row and hasattr(first_row, "children") and first_row.children:
        table_width = len(list(first_row.children))

    # Transform rows
    children: list[dict[str, Any]] = []
    if node.children:
        for row in node.children:
            if isinstance(row, block_token.TableRow) and row.children:
                cells: list[list[dict[str, Any]]] = []
                for cell in row.children:
                    cell_children = (
                        list(cell.children) if hasattr(cell, "children") and cell.children else []
                    )
                    cell_content = _transform_inline_formatting(
                        cell_children, file_path, page_map, link_tracker
                    )
                    cells.append(cell_content)

                children.append({"type": "table_row", "table_row": {"cells": cells}})

    return {
        "type": "table",
        "table": {
            "table_width": table_width,
            "has_column_header": True,  # Assume first row is header
            "has_row_header": False,
            "children": children,
        },
    }


def _transform_blockquote(
    node: block_token.Quote,
    file_path: Path,
    page_map: Optional[dict[Path, str]],
    link_tracker: _BlockLinkTracker,
) -> dict[str, Any]:
    """Transform a blockquote node to Notion quote block."""
    # Collect all text from children
    rich_text: list[dict[str, Any]] = []
    if node.children:
        for child in node.children:
            if isinstance(child, block_token.Paragraph) and child.children:
                rich_text.extend(
                    _transform_inline_formatting(
                        list(child.children), file_path, page_map, link_tracker
                    )
                )

    return {
        "type": "quote",
        "quote": {
            "rich_text": rich_text,
            "color": "default",
        },
    }


def _transform_inline_formatting(
    tokens: Iterable[Any],
    file_path: Path,
    page_map: Optional[dict[Path, str]],
    link_tracker: _BlockLinkTracker,
) -> list[dict[str, Any]]:
    """Transform inline formatting (bold, italic, code, links) to Notion rich text.

    Args:
        tokens: Iterable of inline tokens
        file_path: Path to the current markdown file
        page_map: Optional mapping of file paths to Notion page URLs
        link_tracker: Tracker for relative links
    """
    rich_text: list[dict[str, Any]] = []

    for token in tokens:
        if isinstance(token, span_token.RawText):
            rich_text.append(
                {
                    "type": "text",
                    "text": {"content": token.content, "link": None},
                    "annotations": {
                        "bold": False,
                        "italic": False,
                        "strikethrough": False,
                        "underline": False,
                        "code": False,
                        "color": "default",
                    },
                }
            )
        elif isinstance(token, span_token.Strong):
            # Bold text
            if token.children:
                for child_text in _transform_inline_formatting(
                    token.children, file_path, page_map, link_tracker
                ):
                    child_text["annotations"]["bold"] = True
                    rich_text.append(child_text)
        elif isinstance(token, span_token.Emphasis):
            # Italic text
            if token.children:
                for child_text in _transform_inline_formatting(
                    token.children, file_path, page_map, link_tracker
                ):
                    child_text["annotations"]["italic"] = True
                    rich_text.append(child_text)
        elif isinstance(token, span_token.Strikethrough):
            # Strikethrough text
            if token.children:
                for child_text in _transform_inline_formatting(
                    token.children, file_path, page_map, link_tracker
                ):
                    child_text["annotations"]["strikethrough"] = True
                    rich_text.append(child_text)
        elif isinstance(token, span_token.InlineCode):
            content = ""
            if token.children:
                children_list = list(token.children)
                if children_list:
                    first_child = children_list[0]
                    content = str(getattr(first_child, "content", ""))

            rich_text.append(
                {
                    "type": "text",
                    "text": {"content": content, "link": None},
                    "annotations": {
                        "bold": False,
                        "italic": False,
                        "strikethrough": False,
                        "underline": False,
                        "code": True,
                        "color": "default",
                    },
                }
            )
        elif isinstance(token, span_token.Link):
            # Extract text content from link children
            link_text = ""
            if token.children:
                for child in token.children:
                    if isinstance(child, span_token.RawText):
                        link_text += child.content

            # Determine if this is a relative link and resolve it
            link_url = token.target
            if link_url and not link_url.startswith(("http://", "https://", "#", "mailto:", "//")):
                # This is a relative link
                link_tracker.add_link(link_url, True)

                # If page_map is provided, try to resolve the link
                if page_map:
                    try:
                        # Resolve relative path from current file's directory
                        current_dir = file_path.parent
                        target_path = (current_dir / link_url).resolve()

                        # Check if target exists in page_map
                        if target_path in page_map:
                            link_url = page_map[target_path]
                    except (ValueError, OSError):
                        # If path resolution fails, keep original relative URL
                        # This can happen if the link points outside the workspace
                        pass

            rich_text.append(
                {
                    "type": "text",
                    "text": {"content": link_text, "link": {"url": link_url}},
                    "annotations": {
                        "bold": False,
                        "italic": False,
                        "strikethrough": False,
                        "underline": False,
                        "code": False,
                        "color": "default",
                    },
                }
            )
        elif isinstance(token, span_token.LineBreak):
            # Convert line breaks to newline characters
            rich_text.append(
                {
                    "type": "text",
                    "text": {"content": "\n", "link": None},
                    "annotations": {
                        "bold": False,
                        "italic": False,
                        "strikethrough": False,
                        "underline": False,
                        "code": False,
                        "color": "default",
                    },
                }
            )
        elif isinstance(token, Math):
            # Inline LaTeX math equation
            # Extract the expression without the delimiters
            content = token.content.strip()
            if content.startswith("$$") and content.endswith("$$"):
                # Block math ($$...$$) - extract inner content
                expression = content[2:-2].strip()
            elif content.startswith("$") and content.endswith("$"):
                # Inline math ($...$) - extract inner content
                expression = content[1:-1].strip()
            else:
                expression = content

            rich_text.append(
                {
                    "type": "equation",
                    "equation": {"expression": expression},
                    "annotations": {
                        "bold": False,
                        "italic": False,
                        "strikethrough": False,
                        "underline": False,
                        "code": False,
                        "color": "default",
                    },
                    "plain_text": expression,
                    "href": None,
                }
            )
        elif isinstance(token, span_token.Image):
            # Images cannot be inline in Notion rich text, so they are skipped
            # Future enhancement: Convert to separate image blocks after paragraph
            pass

    return rich_text


def _map_language(language: str) -> str:
    """Map markdown language names to Notion language names.

    Args:
        language: The markdown language identifier

    Returns:
        The corresponding Notion language identifier
    """
    # Notion supported languages (as of API version 2025-09-03)
    notion_languages = {
        "abap",
        "arduino",
        "bash",
        "basic",
        "c",
        "clojure",
        "coffeescript",
        "c++",
        "c#",
        "css",
        "dart",
        "diff",
        "docker",
        "elixir",
        "elm",
        "erlang",
        "flow",
        "fortran",
        "f#",
        "gherkin",
        "glsl",
        "go",
        "graphql",
        "groovy",
        "haskell",
        "html",
        "java",
        "javascript",
        "json",
        "julia",
        "kotlin",
        "latex",
        "less",
        "lisp",
        "livescript",
        "lua",
        "makefile",
        "markdown",
        "markup",
        "matlab",
        "mermaid",
        "nix",
        "objective-c",
        "ocaml",
        "pascal",
        "perl",
        "php",
        "plain text",
        "powershell",
        "prolog",
        "protobuf",
        "python",
        "r",
        "reason",
        "ruby",
        "rust",
        "sass",
        "scala",
        "scheme",
        "scss",
        "shell",
        "solidity",
        "sql",
        "swift",
        "typescript",
        "vb.net",
        "verilog",
        "vhdl",
        "visual basic",
        "webassembly",
        "xml",
        "yaml",
        "java/c/c++/c#",
    }

    # Common markdown -> Notion language mappings
    language_map = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "rb": "ruby",
        "sh": "bash",
        "yml": "yaml",
        "plaintext": "plain text",
        "text": "plain text",
        "txt": "plain text",
        # C++ variants
        "cpp": "c++",
        "c++": "c++",
        "cplusplus": "c++",
        # C# variants
        "csharp": "c#",
        "cs": "c#",
        # Other common variants
        "golang": "go",
        "objc": "objective-c",
        "objective-c++": "objective-c",
        "objectivec": "objective-c",
        "fsharp": "f#",
        "fs": "f#",
        "visualbasic": "visual basic",
        "vb": "vb.net",
        "vbnet": "vb.net",
        "proto": "protobuf",
        "make": "makefile",
        "md": "markdown",
        "tex": "latex",
        "wasm": "webassembly",
        # Solidity variants
        "sol": "solidity",
        # Mermaid variants
        "mermaid": "mermaid",
        "mmd": "mermaid",
    }

    normalized = language.lower().strip()

    # Try direct mapping first
    if normalized in language_map:
        return language_map[normalized]

    # Check if it's already a valid Notion language
    if normalized in notion_languages:
        return normalized

    # Fallback to plain text for unsupported languages
    return "plain text"
