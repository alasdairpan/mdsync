# mdsync

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue)](https://mypy-lang.org/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen)](tests/)

A Python CLI package to sync markdown files to Notion (and potentially other platforms in the future). One-way sync from markdown to platform with focus on simplicity and excellent markdown parsing.

## Features

- One-way sync (markdown → platform)
- Dry-run mode to preview changes
- Command-line focused (simple args, no config files)
- Excellent markdown parsing with LaTeX support
- Preserve directory structure as nested pages

## Installation

### From PyPI

```bash
pip install mdsync
```

## Quick Start

### Prerequisites

1. Create a Notion integration at https://www.notion.so/my-integrations
2. Copy the integration token (starts with `ntn_`)
3. Share a Notion page with your integration
4. Copy the page ID from the URL (the last part after the page name)

### Usage

Sync a single markdown file:

```bash
mdsync notion --token ntn_... --parent PAGE_ID document.md
```

Sync an entire directory (preserves folder structure):

```bash
mdsync notion --token ntn_... --parent PAGE_ID docs/
```

Preview changes without syncing (dry-run):

```bash
mdsync notion --token ntn_... --parent PAGE_ID --dry-run docs/
```

## Command-Line Options

```
Usage: mdsync [OPTIONS] COMMAND [ARGS]...

  Sync markdown files to various platforms.

  Use platform-specific subcommands (e.g., 'notion') to sync to different
  platforms.

Commands:
  notion  Sync markdown files to Notion

Usage: mdsync notion [OPTIONS] PATH

  Sync markdown files to Notion.

  PATH can be a single markdown file or a directory containing markdown
  files. Directories are synced recursively, preserving the folder structure.

Options:
  --token TEXT       Notion integration token  [required]
  --parent TEXT      Parent page ID where files will be synced  [required]
  --dry-run          Preview changes without actually syncing
  --page-icon        Add random emoji icons to pages
  --page-title TEXT  How to determine page titles: 'heading' (from first heading) or 'filename' (from file/folder name)  [default: filename]
  --help             Show this message and exit.
```

## Supported Markdown Features

- Headings (H1, H2, H3, H4+ mapped to H3)
- Paragraphs with inline formatting:
  - **Bold**
  - _Italic_
  - ~~Strikethrough~~
  - `Inline code`
  - [Links](https://example.com)
  - Relative links between markdown files (auto-resolved to Notion pages)
- Code blocks with syntax highlighting
- Bulleted lists
- Numbered lists
- Nested lists
- Task lists (- [ ] and - [x])
- Blockquotes
- Tables with header detection
- Dividers/Horizontal rules
- LaTeX equations (`$...$` inline, `$$...$$` block)
  - **Note**: Dollar signs are treated as math delimiters. To use `$` for currency, escape it: `\$4000`
- Line breaks

## How It Works

1. **File Discovery**: Finds all `.md` and `.markdown` files in the specified path
2. **Parsing**: Uses `mistletoe` to parse markdown into an AST
3. **Conversion**: Transforms AST nodes to Notion block format
4. **Sync**: Creates pages in Notion with proper hierarchy
5. **Link Resolution**: Two-pass sync automatically resolves relative links between markdown files to Notion page URLs
6. **Output**: Shows progress and summary with beautiful terminal output

### Directory Structure Mapping

Folders are converted to nested pages in Notion:

```
docs/
├── Getting Started.md       →  Page: "Getting Started"
├── guides/                  →  Page: "Guides" (container)
│   ├── Installation.md      →    └─ Page: "Installation"
│   └── Configuration.md     →    └─ Page: "Configuration"
└── api/                     →  Page: "Api" (container)
    ├── Authentication.md    →    └─ Page: "Authentication"
    └── Endpoints.md         →    └─ Page: "Endpoints"
```

## Roadmap

### Implemented Features

- [x] LaTeX math equation support (inline and block)
- [x] Relative link resolution between markdown files
- [x] Task list support
- [x] Strikethrough text support
- [x] Nested lists
- [x] Custom page icons (emoji)
- [x] Configurable page title source (heading vs filename)

### Future Features

- [ ] Additional platforms (Confluence, WordPress, Medium)
- [ ] Incremental sync / update detection
- [ ] Image upload support

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [mistletoe](https://github.com/miyuchina/mistletoe) - Excellent markdown parser
- [click](https://click.palletsprojects.com/) - Beautiful CLI framework
- [rich](https://rich.readthedocs.io/) - Terminal output formatting
