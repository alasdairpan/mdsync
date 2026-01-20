"""CLI interface for mdsync.

This module defines the Click command-line interface with Rich output formatting.
Handles argument parsing, file discovery, and orchestrates converter + platform sync.
"""

from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.traceback import install as install_rich_traceback
from rich.tree import Tree

from . import __version__
from .converter import parse_markdown
from .discovery import build_file_tree, discover_markdown_files
from .platforms.notion import NotionPlatform

# Install rich traceback handler for pretty error messages
install_rich_traceback()

console = Console()


@click.group(invoke_without_command=True)
@click.option(
    "-v",
    "--version",
    is_flag=True,
    help="Show version and exit",
)
@click.pass_context
def main(ctx: click.Context, version: bool) -> None:
    """Sync markdown files to various platforms.

    Use platform-specific subcommands (e.g., 'notion') to sync to different platforms.
    """
    if version:
        click.echo(__version__)
        ctx.exit(0)
    elif ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.option(
    "--token",
    required=True,
    help="Notion integration token",
)
@click.option(
    "--parent",
    required=True,
    help="Parent page ID where files will be synced",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without actually syncing",
)
@click.option(
    "--page-icon",
    is_flag=True,
    help="Add random emoji icons to pages",
)
@click.option(
    "--page-title",
    type=click.Choice(["heading", "filename"], case_sensitive=False),
    default="filename",
    help="How to determine page titles: 'heading' (from first heading) or 'filename' (from file/folder name)",
)
@click.argument(
    "path",
    type=click.Path(exists=True, path_type=Path),
)
def notion(
    token: str,
    parent: str,
    dry_run: bool,
    page_icon: bool,
    page_title: str,
    path: Path,
) -> None:
    """Sync markdown files to Notion.

    PATH can be a single markdown file or a directory containing markdown files.
    Directories are synced recursively, preserving the folder structure.

    Examples:

    \b
    # Sync single file
    mdsync notion --token <notion_token> --parent <page_id> document.md

    \b
    # Sync directory (preserves structure)
    mdsync notion --token <notion_token> --parent <page_id> docs/

    \b
    # Dry-run preview
    mdsync notion --token <notion_token> --parent <page_id> --dry-run docs/
    """
    try:
        # File discovery
        console.print(f"\n[cyan]📄 Loading markdown file(s): {path.resolve()}[/cyan]\n")

        md_files = discover_markdown_files(path)

        if not md_files:
            console.print("[red]No markdown files to sync[/red]")
            return

        console.print(f"[green]✓ Found {len(md_files)} markdown file(s)[/green]\n")

        # Build file tree structure
        base_path = path if path.is_dir() else path.parent
        file_tree = build_file_tree(md_files, base_path)

        # Display found files
        if path.is_file():
            # Single file - just show the filename
            console.print(f"📄 {path.name}\n")
        else:
            # Directory - show tree structure
            tree = Tree(f"📁 {base_path.name}")
            _add_tree_nodes(tree, file_tree, base_path)
            console.print(tree)
            console.print()

        if dry_run:
            console.print("[yellow]🔍 Dry run mode - previewing conversion[/yellow]\n")

            # Show conversion preview for each file
            for md_file in md_files[:3]:  # Limit to first 3 for preview
                console.print(f"[cyan]📄 {md_file.relative_to(base_path)}[/cyan]")
                try:
                    parse_result = parse_markdown(md_file)
                    console.print(f"  [dim]→ {len(parse_result.blocks)} Notion block(s)[/dim]")
                except Exception as e:
                    console.print(f"  [red]✗ Error: {e}[/red]")

            if len(md_files) > 3:
                console.print(f"[dim]  ... and {len(md_files) - 3} more files[/dim]")

            console.print("\n[yellow]No changes made (dry run)[/yellow]")
        else:
            console.print(f"[green]🚀 Syncing to Notion (Parent: {parent})...[/green]\n")

            # Build directory structure map: directory path -> parent page ID
            dir_to_parent: dict[Path, str] = {base_path: parent}

            # Track file->page mappings and blocks with links for second pass
            file_to_page_id: dict[Path, str] = {}  # absolute file path -> page ID
            blocks_to_update: list[
                tuple[str, dict[str, Any], Path, str, int]
            ] = []  # (block_id, block_content, source_file, relative_link, block_idx)

            # TWO-PASS SYNC
            # Pass 1: Create all pages and collect block IDs for those with relative links
            # Pass 2: Update only blocks that have relative links with resolved URLs

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console,
            ) as progress:
                # Initialize Notion platform
                notion_platform = NotionPlatform(
                    token,
                    parent,
                    page_icon=page_icon,
                    page_title=page_title,
                    console=progress.console,
                )

                # PASS 1: Create pages
                task = progress.add_task("Creating pages...", total=len(md_files))

                results: list[dict[str, Any]] = []
                for md_file in md_files:
                    # Update progress with current file
                    relative_path = md_file.relative_to(base_path)
                    progress.update(task, description=f"Creating [cyan]{relative_path}[/cyan]")

                    try:
                        # Ensure parent containers exist for this file's directory
                        file_dir = md_file.parent
                        if file_dir not in dir_to_parent:
                            # Create container pages for all missing parent directories
                            _create_directory_containers(
                                file_dir, base_path, dir_to_parent, notion_platform
                            )

                        # Get the parent page ID for this file
                        file_parent_id = dir_to_parent[file_dir]

                        # Parse markdown WITHOUT page_map (first pass)
                        parse_result = parse_markdown(md_file)

                        # Sync to Notion with correct parent
                        page_url, page_id, block_ids = notion_platform.sync(
                            md_file, parse_result.blocks, file_parent_id
                        )

                        # Store file -> page ID mapping (use absolute path)
                        file_to_page_id[md_file.resolve()] = page_id

                        # Collect blocks that need link resolution
                        # Store: block_id, original_block (for matching), source_file, relative_link
                        for block_idx, relative_link in parse_result.blocks_with_links:
                            # Adjust for skipped heading
                            title, skip_first = notion_platform._extract_title(
                                md_file, parse_result.blocks
                            )
                            actual_idx = (
                                block_idx - 1 if skip_first and block_idx > 0 else block_idx
                            )

                            if 0 <= actual_idx < len(block_ids):
                                block_id = block_ids[actual_idx]
                                block_content = parse_result.blocks[block_idx]
                                blocks_to_update.append(
                                    (
                                        block_id,
                                        block_content,
                                        md_file,
                                        relative_link,
                                        block_idx,
                                    )
                                )

                        results.append(
                            {
                                "file": relative_path,
                                "blocks": len(parse_result.blocks),
                                "url": page_url,
                                "status": "✓",
                                "error": None,
                            }
                        )
                    except Exception as e:
                        error_msg = str(e)
                        results.append(
                            {
                                "file": relative_path,
                                "blocks": 0,
                                "url": "",
                                "status": "✗",
                                "error": error_msg,
                            }
                        )

                    progress.advance(task)

                # PASS 2: Update blocks with resolved links (only if there are links to resolve)
                if blocks_to_update:
                    task2 = progress.add_task(
                        f"Resolving {len(blocks_to_update)} link(s)...",
                        total=len(blocks_to_update),
                    )

                    # Build page_map: absolute file path -> page URL
                    page_map: dict[Path, str] = {}
                    for file_path, page_id in file_to_page_id.items():
                        page_map[file_path] = notion_platform._get_page_url(page_id)

                    for (
                        block_id,
                        _block_content,
                        source_file,
                        relative_link,
                        block_idx,
                    ) in blocks_to_update:
                        progress.update(
                            task2,
                            description=f"Updating link to [cyan]{relative_link}[/cyan]",
                        )

                        try:
                            # Resolve relative link to absolute path
                            source_dir = source_file.parent
                            target_path = (source_dir / relative_link).resolve()

                            # Check if target exists in our page_map
                            if target_path in page_map:
                                # Re-parse just the source file with page_map to get resolved links
                                parse_result_resolved = parse_markdown(
                                    source_file, page_map=page_map
                                )

                                # Get the resolved block at the same index
                                if block_idx < len(parse_result_resolved.blocks):
                                    updated_block_content = parse_result_resolved.blocks[block_idx]
                                    notion_platform.update_block(block_id, updated_block_content)

                        except Exception as e:
                            progress.console.print(
                                f"[yellow]⚠ Failed to resolve link '{relative_link}' in {source_file.name}: {e}[/yellow]"
                            )

                        progress.advance(task2)

            # Display summary table
            console.print()
            table = Table(title="Sync Summary", show_header=True)
            table.add_column("File", style="cyan")
            table.add_column("Blocks", justify="right")
            table.add_column("Status", style="green")

            for result in results:
                table.add_row(
                    str(result["file"]),
                    str(result["blocks"]),
                    result["status"],
                )

            console.print(table)

            # Show detailed errors if any
            errors = [r for r in results if r["error"]]
            if errors:
                console.print("\n[red]Detailed Error Messages:[/red]\n")
                for result in errors:
                    console.print(f"[cyan]{result['file']}[/cyan]")
                    console.print(f"  [red]{result['error']}[/red]\n")

            # Success message
            success_count = sum(1 for r in results if r["status"] == "✓")
            if success_count == len(results):
                console.print(f"\n[green]✓ Successfully synced {success_count} file(s)[/green]")
            else:
                console.print(f"\n[yellow]⚠ Synced {success_count}/{len(results)} file(s)[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise

    console.print()


def _add_tree_nodes(tree: Tree, structure: dict, base_path: Path) -> None:
    """Recursively add nodes to Rich Tree for visualization.

    Args:
        tree: Rich Tree object
        structure: Dictionary representing file/directory structure
        base_path: Base directory path
    """
    for name, value in structure.items():
        if isinstance(value, dict):
            # Directory
            branch = tree.add(f"📁 {name}")
            _add_tree_nodes(branch, value, base_path)
        else:
            # File
            tree.add(f"📄 {name}")


def _create_directory_containers(
    target_dir: Path,
    base_path: Path,
    dir_to_parent: dict[Path, str],
    notion_platform: NotionPlatform,
) -> None:
    """Create Notion container pages for directory hierarchy.

    Args:
        target_dir: The directory we need to ensure exists
        base_path: The base directory (already has a parent)
        dir_to_parent: Map of directory paths to their Notion parent page IDs
        notion_platform: NotionPlatform instance to create containers
    """
    # Build path from base to target
    try:
        relative = target_dir.relative_to(base_path)
    except ValueError:
        # target_dir is not under base_path
        return

    # Get all parent directories in order
    parts = relative.parts
    current_path = base_path

    for part in parts:
        current_path = current_path / part

        if current_path not in dir_to_parent:
            # Need to create container for this directory
            parent_path = current_path.parent
            parent_id = dir_to_parent[parent_path]

            # Create container page for this directory
            container_id = notion_platform.create_container(part, parent_id)
            dir_to_parent[current_path] = container_id


if __name__ == "__main__":
    main()
