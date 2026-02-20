# Skill Vault Documentation

A tool for managing Agent Skills across different AI frameworks (OpenCode, Claude, Codex, etc.).

## Overview

Skill Vault provides a centralized system for creating, versioning, and distributing AI agent skills across multiple frameworks. It uses Windows Junctions for efficient linking without requiring administrator privileges.

## Quick Links

| Document | Description |
|----------|-------------|
| [Architecture](architecture.md) | Module overview and system design |
| [Commands](commands.md) | Complete CLI command reference |
| [Creating Skills](guides/creating-skills.md) | How to create and structure skills |
| [Workflow](guides/workflow.md) | Typical usage workflow |
| [Windows Junctions](guides/windows-junctions.md) | Understanding junction-based linking |
| [Configuration](reference/configuration.md) | Configuration file reference |
| [Directory Structure](reference/directory-structure.md) | File system layout |
| [Frameworks](reference/frameworks.md) | Supported AI frameworks |

## Core Concepts

### Global vs Local Skills

- **Global Skills**: Shared across all projects, stored in `~/.skill-vault/skills/global/`
- **Local Skills**: Project-specific or private templates, stored in `~/.skill-vault/skills/local/`

### Vault

The vault is a Git repository that stores all skills with version control. Each skill version is tagged (e.g., `my-skill@v1.0.0`).

### Junctions

Skill Vault uses Windows Junctions instead of symlinks to link skills into framework directories. This approach:

- Requires no administrator privileges
- Works natively on Windows
- Links directories at the file system level

## Project Structure

```
~/.skill-vault/           # Global vault (Git repository)
├── skills/
│   ├── global/           # Shared skills
│   └── local/            # Private skill templates

my-project/
├── .skill-vault/         # Project metadata
│   ├── config.yaml       # Framework settings
│   └── installed.json    # Installed skills
└── .agents/skills/       # Skills directory (primary)
```

## Supported Frameworks

| Framework | Skills Path |
|-----------|-------------|
| OpenAI Codex | `.agents/skills` |
| OpenCode | `.agents/skills` |
| Claude Code | `.claude/skills` |
| Antigravity | `.agent/skills` |
| Roo Code | `.roo/skills` |
| VS Code | `.vscode/skills` |

See [Frameworks Reference](reference/frameworks.md) for complete details.
