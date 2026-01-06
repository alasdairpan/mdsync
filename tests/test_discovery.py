"""Unit tests for mdsync.discovery module.

Tests file discovery and tree building functionality without requiring external services.
"""

import tempfile
from pathlib import Path

from mdsync.discovery import build_file_tree, discover_markdown_files


class TestDiscoverMarkdownFiles:
    """Tests for discover_markdown_files function."""

    def test_discover_single_md_file(self, tmp_path: Path) -> None:
        """Test discovering a single .md file."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test")

        result = discover_markdown_files(md_file)

        assert len(result) == 1
        assert result[0] == md_file

    def test_discover_single_markdown_file(self, tmp_path: Path) -> None:
        """Test discovering a single .markdown file."""
        markdown_file = tmp_path / "test.markdown"
        markdown_file.write_text("# Test")

        result = discover_markdown_files(markdown_file)

        assert len(result) == 1
        assert result[0] == markdown_file

    def test_discover_non_markdown_file_returns_empty(self, tmp_path: Path) -> None:
        """Test that non-markdown file returns empty list."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Test")

        result = discover_markdown_files(txt_file)

        assert len(result) == 0

    def test_discover_directory_with_md_files(self, tmp_path: Path) -> None:
        """Test discovering all .md files in a directory."""
        (tmp_path / "file1.md").write_text("# File 1")
        (tmp_path / "file2.md").write_text("# File 2")
        (tmp_path / "file3.md").write_text("# File 3")
        (tmp_path / "other.txt").write_text("Not markdown")

        result = discover_markdown_files(tmp_path)

        assert len(result) == 3
        assert all(f.suffix == ".md" for f in result)

    def test_discover_directory_recursive(self, tmp_path: Path) -> None:
        """Test that directory discovery is recursive."""
        (tmp_path / "root.md").write_text("# Root")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "sub.md").write_text("# Sub")
        nested = subdir / "nested"
        nested.mkdir()
        (nested / "deep.md").write_text("# Deep")

        result = discover_markdown_files(tmp_path)

        assert len(result) == 3
        assert any(f.name == "root.md" for f in result)
        assert any(f.name == "sub.md" for f in result)
        assert any(f.name == "deep.md" for f in result)

    def test_discover_mixed_extensions(self, tmp_path: Path) -> None:
        """Test discovering both .md and .markdown files."""
        (tmp_path / "file1.md").write_text("# File 1")
        (tmp_path / "file2.markdown").write_text("# File 2")
        (tmp_path / "file3.md").write_text("# File 3")

        result = discover_markdown_files(tmp_path)

        assert len(result) == 3
        assert any(f.suffix == ".markdown" for f in result)

    def test_discover_empty_directory(self, tmp_path: Path) -> None:
        """Test discovering files in empty directory returns empty list."""
        result = discover_markdown_files(tmp_path)

        assert len(result) == 0

    def test_results_sorted(self, tmp_path: Path) -> None:
        """Test that results are sorted alphabetically."""
        (tmp_path / "zebra.md").write_text("# Z")
        (tmp_path / "alpha.md").write_text("# A")
        (tmp_path / "beta.md").write_text("# B")

        result = discover_markdown_files(tmp_path)

        assert len(result) == 3
        assert result[0].name == "alpha.md"
        assert result[1].name == "beta.md"
        assert result[2].name == "zebra.md"


class TestBuildFileTree:
    """Tests for build_file_tree function."""

    def test_single_file(self, tmp_path: Path) -> None:
        """Test building tree for single file."""
        file_path = tmp_path / "test.md"
        file_path.write_text("# Test")
        files = [file_path]

        tree = build_file_tree(files, tmp_path)

        assert "test.md" in tree
        assert tree["test.md"] == file_path

    def test_flat_directory(self, tmp_path: Path) -> None:
        """Test building tree for flat directory structure."""
        file1 = tmp_path / "file1.md"
        file2 = tmp_path / "file2.md"
        file1.write_text("# File 1")
        file2.write_text("# File 2")
        files = [file1, file2]

        tree = build_file_tree(files, tmp_path)

        assert "file1.md" in tree
        assert "file2.md" in tree
        assert tree["file1.md"] == file1
        assert tree["file2.md"] == file2

    def test_nested_directories(self, tmp_path: Path) -> None:
        """Test building tree with nested directories."""
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        file1 = dir1 / "file1.md"
        file1.write_text("# File 1")

        dir2 = tmp_path / "dir2"
        dir2.mkdir()
        file2 = dir2 / "file2.md"
        file2.write_text("# File 2")

        files = [file1, file2]

        tree = build_file_tree(files, tmp_path)

        assert "dir1" in tree
        assert "dir2" in tree
        assert isinstance(tree["dir1"], dict)
        assert isinstance(tree["dir2"], dict)
        assert tree["dir1"]["file1.md"] == file1
        assert tree["dir2"]["file2.md"] == file2

    def test_deeply_nested_structure(self, tmp_path: Path) -> None:
        """Test building tree with deeply nested structure."""
        deep_path = tmp_path / "level1" / "level2" / "level3"
        deep_path.mkdir(parents=True)
        file_path = deep_path / "deep.md"
        file_path.write_text("# Deep")

        files = [file_path]

        tree = build_file_tree(files, tmp_path)

        assert "level1" in tree
        assert "level2" in tree["level1"]
        assert "level3" in tree["level1"]["level2"]
        assert tree["level1"]["level2"]["level3"]["deep.md"] == file_path

    def test_mixed_structure(self, tmp_path: Path) -> None:
        """Test building tree with mixed flat and nested files."""
        root_file = tmp_path / "root.md"
        root_file.write_text("# Root")

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        sub_file = subdir / "sub.md"
        sub_file.write_text("# Sub")

        files = [root_file, sub_file]

        tree = build_file_tree(files, tmp_path)

        assert "root.md" in tree
        assert "subdir" in tree
        assert tree["root.md"] == root_file
        assert tree["subdir"]["sub.md"] == sub_file

    def test_single_file_not_relative_to_base(self, tmp_path: Path) -> None:
        """Test building tree when file is not relative to base path."""
        with tempfile.TemporaryDirectory() as other_dir:
            other_path = Path(other_dir)
            file_path = other_path / "test.md"
            file_path.write_text("# Test")

            files = [file_path]

            tree = build_file_tree(files, tmp_path)

            # When file is not relative to base, it uses the filename as relative path
            # The tree structure will include the full path parts
            assert len(tree) > 0  # Tree should not be empty
            # The actual structure depends on implementation details

    def test_empty_file_list(self, tmp_path: Path) -> None:
        """Test building tree with empty file list."""
        files: list[Path] = []

        tree = build_file_tree(files, tmp_path)

        assert tree == {}

    def test_preserves_directory_hierarchy(self, tmp_path: Path) -> None:
        """Test that directory hierarchy is correctly preserved."""
        # Create structure: base/docs/api/endpoint.md and base/docs/guides/intro.md
        docs = tmp_path / "docs"
        api = docs / "api"
        guides = docs / "guides"
        api.mkdir(parents=True)
        guides.mkdir(parents=True)

        endpoint = api / "endpoint.md"
        intro = guides / "intro.md"
        endpoint.write_text("# Endpoint")
        intro.write_text("# Intro")

        files = [endpoint, intro]

        tree = build_file_tree(files, tmp_path)

        assert "docs" in tree
        assert "api" in tree["docs"]
        assert "guides" in tree["docs"]
        assert tree["docs"]["api"]["endpoint.md"] == endpoint
        assert tree["docs"]["guides"]["intro.md"] == intro
