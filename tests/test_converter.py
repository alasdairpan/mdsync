"""Unit tests for mdsync.converter module.

Tests markdown parsing and conversion to Notion blocks without requiring Notion connection.
"""

from pathlib import Path

import pytest

from mdsync.converter import ParseResult, parse_markdown


class TestParseMarkdown:
    """Tests for parse_markdown function."""

    def test_parse_simple_paragraph(self, tmp_path: Path) -> None:
        """Test parsing a simple paragraph."""
        md_file = tmp_path / "test.md"
        md_file.write_text("This is a simple paragraph.")

        result = parse_markdown(md_file)

        assert isinstance(result, ParseResult)
        assert len(result.blocks) == 1
        assert result.blocks[0]["type"] == "paragraph"
        assert (
            result.blocks[0]["paragraph"]["rich_text"][0]["text"]["content"]
            == "This is a simple paragraph."
        )

    def test_parse_heading_level_1(self, tmp_path: Path) -> None:
        """Test parsing heading level 1."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Heading 1")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 1
        assert result.blocks[0]["type"] == "heading_1"
        assert result.blocks[0]["heading_1"]["rich_text"][0]["text"]["content"] == "Heading 1"

    def test_parse_heading_level_2(self, tmp_path: Path) -> None:
        """Test parsing heading level 2."""
        md_file = tmp_path / "test.md"
        md_file.write_text("## Heading 2")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 1
        assert result.blocks[0]["type"] == "heading_2"
        assert result.blocks[0]["heading_2"]["rich_text"][0]["text"]["content"] == "Heading 2"

    def test_parse_heading_level_3(self, tmp_path: Path) -> None:
        """Test parsing heading level 3."""
        md_file = tmp_path / "test.md"
        md_file.write_text("### Heading 3")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 1
        assert result.blocks[0]["type"] == "heading_3"
        assert result.blocks[0]["heading_3"]["rich_text"][0]["text"]["content"] == "Heading 3"

    def test_parse_heading_level_4_becomes_3(self, tmp_path: Path) -> None:
        """Test that heading level 4+ is converted to level 3."""
        md_file = tmp_path / "test.md"
        md_file.write_text("#### Heading 4")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 1
        assert result.blocks[0]["type"] == "heading_3"

    def test_parse_bold_text(self, tmp_path: Path) -> None:
        """Test parsing bold text."""
        md_file = tmp_path / "test.md"
        md_file.write_text("This is **bold** text.")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 1
        rich_text = result.blocks[0]["paragraph"]["rich_text"]
        # Find the bold text element
        bold_elem = next(rt for rt in rich_text if rt["annotations"]["bold"])
        assert bold_elem["text"]["content"] == "bold"

    def test_parse_italic_text(self, tmp_path: Path) -> None:
        """Test parsing italic text."""
        md_file = tmp_path / "test.md"
        md_file.write_text("This is *italic* text.")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 1
        rich_text = result.blocks[0]["paragraph"]["rich_text"]
        # Find the italic text element
        italic_elem = next(rt for rt in rich_text if rt["annotations"]["italic"])
        assert italic_elem["text"]["content"] == "italic"

    def test_parse_strikethrough_text(self, tmp_path: Path) -> None:
        """Test parsing strikethrough text."""
        md_file = tmp_path / "test.md"
        md_file.write_text("This is ~~strikethrough~~ text.")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 1
        rich_text = result.blocks[0]["paragraph"]["rich_text"]
        # Find the strikethrough text element
        strike_elem = next(rt for rt in rich_text if rt["annotations"]["strikethrough"])
        assert strike_elem["text"]["content"] == "strikethrough"

    def test_parse_inline_code(self, tmp_path: Path) -> None:
        """Test parsing inline code."""
        md_file = tmp_path / "test.md"
        md_file.write_text("This is `code` inline.")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 1
        rich_text = result.blocks[0]["paragraph"]["rich_text"]
        # Find the code element
        code_elem = next(rt for rt in rich_text if rt["annotations"]["code"])
        assert code_elem["text"]["content"] == "code"

    def test_parse_link(self, tmp_path: Path) -> None:
        """Test parsing a link."""
        md_file = tmp_path / "test.md"
        md_file.write_text("Check out [GitHub](https://github.com).")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 1
        rich_text = result.blocks[0]["paragraph"]["rich_text"]
        # Find the link element
        link_elem = next(rt for rt in rich_text if rt["text"].get("link"))
        assert link_elem["text"]["content"] == "GitHub"
        assert link_elem["text"]["link"]["url"] == "https://github.com"

    def test_parse_code_block(self, tmp_path: Path) -> None:
        """Test parsing a code block."""
        md_file = tmp_path / "test.md"
        md_file.write_text("```python\nprint('hello')\n```")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 1
        assert result.blocks[0]["type"] == "code"
        assert result.blocks[0]["code"]["language"] == "python"
        assert "print('hello')" in result.blocks[0]["code"]["rich_text"][0]["text"]["content"]

    def test_parse_solidity_code_block(self, tmp_path: Path) -> None:
        """Test parsing a Solidity code block."""
        md_file = tmp_path / "test.md"
        md_file.write_text("```solidity\npragma solidity ^0.8.20;\n```")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 1
        assert result.blocks[0]["type"] == "code"
        assert result.blocks[0]["code"]["language"] == "solidity"
        assert "pragma solidity" in result.blocks[0]["code"]["rich_text"][0]["text"]["content"]

    def test_parse_solidity_code_block_with_sol_alias(self, tmp_path: Path) -> None:
        """Test parsing a Solidity code block using 'sol' alias."""
        md_file = tmp_path / "test.md"
        md_file.write_text("```sol\ncontract Governor {}\n```")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 1
        assert result.blocks[0]["type"] == "code"
        assert result.blocks[0]["code"]["language"] == "solidity"
        assert "contract Governor" in result.blocks[0]["code"]["rich_text"][0]["text"]["content"]

    def test_parse_bulleted_list(self, tmp_path: Path) -> None:
        """Test parsing a bulleted list."""
        md_file = tmp_path / "test.md"
        md_file.write_text("- Item 1\n- Item 2\n- Item 3")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 3
        assert all(block["type"] == "bulleted_list_item" for block in result.blocks)
        assert result.blocks[0]["bulleted_list_item"]["rich_text"][0]["text"]["content"] == "Item 1"
        assert result.blocks[1]["bulleted_list_item"]["rich_text"][0]["text"]["content"] == "Item 2"
        assert result.blocks[2]["bulleted_list_item"]["rich_text"][0]["text"]["content"] == "Item 3"

    def test_parse_numbered_list(self, tmp_path: Path) -> None:
        """Test parsing a numbered list."""
        md_file = tmp_path / "test.md"
        md_file.write_text("1. First\n2. Second\n3. Third")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 3
        assert all(block["type"] == "numbered_list_item" for block in result.blocks)

    def test_parse_task_list_unchecked(self, tmp_path: Path) -> None:
        """Test parsing an unchecked task list item."""
        md_file = tmp_path / "test.md"
        md_file.write_text("- [ ] Unchecked task")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 1
        assert result.blocks[0]["type"] == "to_do"
        assert result.blocks[0]["to_do"]["checked"] is False
        assert "Unchecked task" in result.blocks[0]["to_do"]["rich_text"][0]["text"]["content"]

    def test_parse_task_list_checked(self, tmp_path: Path) -> None:
        """Test parsing a checked task list item."""
        md_file = tmp_path / "test.md"
        md_file.write_text("- [x] Checked task")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 1
        assert result.blocks[0]["type"] == "to_do"
        assert result.blocks[0]["to_do"]["checked"] is True
        assert "Checked task" in result.blocks[0]["to_do"]["rich_text"][0]["text"]["content"]

    def test_parse_blockquote(self, tmp_path: Path) -> None:
        """Test parsing a blockquote."""
        md_file = tmp_path / "test.md"
        md_file.write_text("> This is a quote")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 1
        assert result.blocks[0]["type"] == "quote"
        assert result.blocks[0]["quote"]["rich_text"][0]["text"]["content"] == "This is a quote"

    def test_parse_divider(self, tmp_path: Path) -> None:
        """Test parsing a horizontal rule (divider)."""
        md_file = tmp_path / "test.md"
        md_file.write_text("---")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 1
        assert result.blocks[0]["type"] == "divider"

    def test_parse_inline_math(self, tmp_path: Path) -> None:
        """Test parsing inline math equation."""
        md_file = tmp_path / "test.md"
        md_file.write_text("The equation is $E=mc^2$ inline.")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 1
        rich_text = result.blocks[0]["paragraph"]["rich_text"]
        # Find the equation element
        eq_elem = next(rt for rt in rich_text if rt["type"] == "equation")
        assert "E=mc^2" in eq_elem["equation"]["expression"]

    def test_parse_block_math(self, tmp_path: Path) -> None:
        """Test parsing block math equation."""
        md_file = tmp_path / "test.md"
        md_file.write_text("$$\nE=mc^2\n$$")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 1
        assert result.blocks[0]["type"] == "equation"
        assert "E=mc^2" in result.blocks[0]["equation"]["expression"]

    def test_parse_multiple_blocks(self, tmp_path: Path) -> None:
        """Test parsing multiple blocks."""
        md_file = tmp_path / "test.md"
        content = """# Title

This is a paragraph.

## Subtitle

- Item 1
- Item 2
"""
        md_file.write_text(content)

        result = parse_markdown(md_file)

        assert len(result.blocks) >= 4
        assert result.blocks[0]["type"] == "heading_1"
        assert result.blocks[1]["type"] == "paragraph"
        assert result.blocks[2]["type"] == "heading_2"

    def test_parse_empty_file(self, tmp_path: Path) -> None:
        """Test parsing an empty file."""
        md_file = tmp_path / "test.md"
        md_file.write_text("")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 0

    def test_parse_file_not_found(self, tmp_path: Path) -> None:
        """Test that parsing non-existent file raises FileNotFoundError."""
        md_file = tmp_path / "nonexistent.md"

        with pytest.raises(FileNotFoundError):
            parse_markdown(md_file)

    def test_parse_relative_link_tracking(self, tmp_path: Path) -> None:
        """Test that relative links are tracked."""
        md_file = tmp_path / "test.md"
        md_file.write_text("See [other page](./other.md) for more.")

        result = parse_markdown(md_file)

        # Should have at least one block with a relative link
        assert len(result.blocks_with_links) > 0
        assert any("other.md" in link for _, link in result.blocks_with_links)

    def test_parse_absolute_link_not_tracked(self, tmp_path: Path) -> None:
        """Test that absolute links are not tracked as relative."""
        md_file = tmp_path / "test.md"
        md_file.write_text("See [GitHub](https://github.com) for more.")

        result = parse_markdown(md_file)

        # Should not track absolute URLs as relative links
        assert len(result.blocks_with_links) == 0

    def test_parse_combined_formatting(self, tmp_path: Path) -> None:
        """Test parsing text with combined formatting."""
        md_file = tmp_path / "test.md"
        md_file.write_text("This is **bold and _italic_** text.")

        result = parse_markdown(md_file)

        assert len(result.blocks) == 1
        rich_text = result.blocks[0]["paragraph"]["rich_text"]
        # Should have elements with different formatting
        assert any(rt["annotations"]["bold"] for rt in rich_text)
        assert any(rt["annotations"]["italic"] for rt in rich_text)

    def test_parse_table(self, tmp_path: Path) -> None:
        """Test parsing a markdown table."""
        md_file = tmp_path / "test.md"
        content = """| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |
"""
        md_file.write_text(content)

        result = parse_markdown(md_file)

        # Tables should be converted to table blocks
        assert len(result.blocks) >= 1
        assert result.blocks[0]["type"] == "table"

    def test_parse_nested_list(self, tmp_path: Path) -> None:
        """Test parsing nested lists."""
        md_file = tmp_path / "test.md"
        content = """- Item 1
  - Nested 1
  - Nested 2
- Item 2
"""
        md_file.write_text(content)

        result = parse_markdown(md_file)

        # Should have list items, and nested items as children
        assert len(result.blocks) >= 2
        assert result.blocks[0]["type"] == "bulleted_list_item"


class TestParseResultDataclass:
    """Tests for ParseResult dataclass."""

    def test_parse_result_creation(self) -> None:
        """Test creating a ParseResult instance."""
        blocks = [{"type": "paragraph", "paragraph": {"rich_text": []}}]
        blocks_with_links = [(0, "./other.md")]

        result = ParseResult(blocks=blocks, blocks_with_links=blocks_with_links)

        assert result.blocks == blocks
        assert result.blocks_with_links == blocks_with_links

    def test_parse_result_empty(self) -> None:
        """Test creating an empty ParseResult."""
        result = ParseResult(blocks=[], blocks_with_links=[])

        assert result.blocks == []
        assert result.blocks_with_links == []
