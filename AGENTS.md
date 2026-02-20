# Skill Vault

A tool for managing Agent Skills across different AI frameworks (OpenCode, Claude, Codex, etc.).

## Features

- **Cross-Framework Support**: Works with OpenCode, Claude Code, OpenAI Codex, Antigravity, Roo Code, and more
- **Windows Junctions**: Uses Windows Junctions instead of Symlinks (no admin rights needed)
- **Git Integration**: Full version control for your skills with automatic tagging
- **Interactive CLI**: Easy-to-use interface for skill selection and management
- **Global & Local Skills**: Share skills globally or keep them project-specific
- **Auto-Detection**: Automatically detects which AI frameworks are used in your project
- **Framework Editing**: Update project frameworks later with interactive select/deselect

## Installation

```bash
cd skill-vault
pip install -e .
```

This installs three command aliases:
- `skill-vault` - Main command
- `sv` - Short alias
- `skill-eye` - Alternative alias

## Quick Start

### 1. Initialize the Global Vault

```bash
# Initialize vault (automatically creates global junctions)
skill-vault vault init

# Or specify custom path
skill-vault vault init --path ~/my-vault
```

### 2. Global Skills

Global skills are automatically available in your home directory for all frameworks:

```
~/.agents/skills/           # For Codex/OpenCode
~/.claude/skills/           # For Claude Code
~/.gemini/antigravity/skills/  # For Antigravity
~/.roo/skills/              # For Roo Code
```

### 3. Create a Skill

**Method A: Promote from Project (Recommended)**

Create a skill in your project's framework directory and promote it to the vault:

```bash
# Create skill in project
mkdir -p .agents/skills/my-skill

# Create SKILL.md (see format below)
# ... edit SKILL.md ...

# Promote to vault
skill-vault vault create my-skill              # Add as global skill
skill-vault vault create my-skill --local      # Add as local skill
skill-vault vault create                       # Interactive selection
```

**Method B: Manual Creation**

Create a skill directory directly in the vault:

```bash
mkdir -p ~/.skill-vault/skills/global/my-skill
```

Create a `SKILL.md` file:

```markdown
---
name: my-skill
version: 1.0.0
description: A description of what this skill does
author: Your Name
tags: [productivity, automation]
frameworks: [codex, claude, opencode]
---

# My Skill

## Purpose
This skill helps with...

## Usage
...
```

**Note**: `version` is optional and defaults to `0.0.0` if not specified.

### 4. Setup Global Junctions

After adding skills to the vault, create junctions in framework directories:

```bash
# Automatically creates junctions in ~/.agents/skills, ~/.claude/skills, etc.
skill-vault vault setup-global

# Or sync (removes obsolete, adds new)
skill-vault vault sync-global
```

### 5. Initialize a Project

```bash
cd my-project

# Auto-detect frameworks
skill-vault project init

# Or specify frameworks manually
skill-vault project init --framework codex --framework claude
```

### 6. Add Skills to Project

Interactive mode:
```bash
skill-vault skills add -i
# Enter numbers like: 1,2,3
# Or: all
```

Direct installation:
```bash
skill-vault skills add my-skill

# Force reinstall
skill-vault skills add my-skill --force
```

### 7. Edit Project Frameworks (Optional)

If you want to change enabled frameworks after initialization:

```bash
skill-vault framework edit
```

This opens a checkbox list where you can select or deselect frameworks.

### 8. Sync Updates

```bash
# Check for updates
skill-vault sync --dry-run

# Interactive update selection
skill-vault sync -i

# Update all without asking
skill-vault sync --all
```

### 9. Push Local Skills to Vault

If you modified a skill in your project:

```bash
skill-vault push my-skill
```

## Commands Reference

### Global Vault Commands

```bash
skill-vault vault init                          # Initialize vault
skill-vault vault init --no-setup-global        # Without global junctions
skill-vault vault list                          # List all skills
skill-vault vault show <skill>                  # Show skill details
skill-vault vault create                        # Interactive: promote skill from project
skill-vault vault create <name>                 # Promote specific skill as global
skill-vault vault create <name> --local         # Promote as local skill
skill-vault vault setup-global                  # Create global junctions
skill-vault vault sync-global                   # Sync global junctions
```

### Project Commands

```bash
skill-vault project init                        # Initialize project
skill-vault project init -f codex -f claude     # With specific frameworks
skill-vault project status                      # Show project status
```

### Skill Management

```bash
skill-vault skills list                         # List all skills
skill-vault skills add <name>                   # Add skill to project
skill-vault skills add <name> --force           # Force reinstall
skill-vault skills add -i                       # Interactive selection
skill-vault skills remove <name>                # Remove skill from project
skill-vault skills diff <name>                  # Show skill differences
```

### Synchronization

```bash
skill-vault sync                                # Sync updates (interactive)
skill-vault sync -i                             # Interactive selection
skill-vault sync --all                          # Update all without asking
skill-vault sync --dry-run                      # Preview updates
skill-vault push <skill>                        # Push local skill to vault
skill-vault pull                                # Pull latest vault changes
```

### Framework Management

```bash
skill-vault framework list                      # List available frameworks
skill-vault framework edit                      # Select/deselect enabled frameworks
skill-vault framework sync                      # Set up framework junctions
```

`framework edit` updates `.skill-vault/config.yaml` for the current project.
`framework sync` creates junctions so all frameworks share the same skills directory.

## Directory Structure

### Global Vault

```
~/.skill-vault/                     # Global vault (Git repository)
├── .git/                           # Version control
├── skills/
│   ├── global/                     # Global skills (shared across projects)
│   │   ├── session-handoff/
│   │   │   ├── SKILL.md            # Skill definition (REQUIRED)
│   │   │   ├── scripts/            # Optional: Helper scripts
│   │   │   └── assets/             # Optional: Templates, files
│   │   └── my-skill/
│   │       └── SKILL.md
│   └── local/                      # Local/private skill templates
├── projects/                       # Registered project metadata
└── config/
    └── frameworks.yaml             # Framework configurations
```

### Project Structure

```
my-project/
├── .skill-vault/                   # Project metadata
│   ├── config.yaml                 # Project configuration
│   └── installed.json              # Installed skills with versions
├── .agents/skills/                 # PRIMARY skills directory (real files)
│   ├── my-skill/                   # Your project skills
│   └── session-handoff/            # Skills installed from vault
├── .claude/skills/                 # Junction -> .agents/skills/
├── .agent/skills/                  # Junction -> .agents/skills/
└── src/                            # Your project files
```

**Important**: The first enabled framework's `skills/` directory becomes the primary (real directory). All other frameworks' `skills/` directories are Windows Junctions pointing to the primary. This means:
- Adding a skill to `.agents/skills/` automatically makes it available in all frameworks
- Changes are immediately synced across all framework directories
- Only one copy of each skill exists on disk

### Home Directory (Global Access)

```
~/.agents/skills/                   # Codex/OpenCode global skills (junctions to vault)
~/.claude/skills/                   # Claude Code global skills (junctions to vault)
~/.gemini/antigravity/skills/       # Antigravity global skills (junctions to vault)
~/.roo/skills/                      # Roo Code global skills (junctions to vault)
~/.vscode/skills/                   # VS Code global skills (junctions to vault)
```

## SKILL.md Format

Each skill MUST have a `SKILL.md` file in its root directory with YAML frontmatter:

```markdown
---
name: skill-name                    # REQUIRED: Unique skill identifier
version: 1.0.0                      # OPTIONAL: Defaults to 0.0.0
description: "Description here"     # REQUIRED: Brief description
author: Your Name                   # OPTIONAL: Author name
tags: [tag1, tag2]                  # OPTIONAL: Categorization tags
frameworks: [codex, claude]         # OPTIONAL: Supported frameworks
---

# Skill Title

## Purpose
Description of what this skill does...

## Usage
How to use this skill...

## Examples
Example usage...
```

## Supported Frameworks

| Framework | Local Path | Global Path | Config Files |
|-----------|-----------|-------------|--------------|
| OpenAI Codex | `.agents/skills` | `~/.agents/skills` | `.codex`, `codex.md` |
| OpenCode | `.agents/skills` | `~/.agents/skills` | `.opencode` |
| Claude Code | `.claude/skills` | `~/.claude/skills` | `.claude`, `CLAUDE.md` |
| Antigravity (Gemini) | `.agent/skills` | `~/.gemini/antigravity/skills` | `.gemini`, `gemini.md` |
| Roo Code | `.roo/skills` | `~/.roo/skills` | `.roo` |
| VS Code | `.vscode/skills` | `~/.vscode/skills` | `.vscode` |

## Configuration

Edit `config/frameworks.yaml` to add new frameworks:

```yaml
frameworks:
  my-framework:
    name: "My Framework"
    local_path: ".my-framework/skills"
    global_path: "~/.my-framework/skills"
    config_files: [".my-framework", "my-framework.md"]
    
defaults:
  auto_sync: false
  create_backups: true
  preferred_frameworks: [codex, claude, opencode]
```

## Windows Compatibility

This tool is optimized for Windows:

- **Windows Junctions**: Uses `mklink /J` instead of symlinks
  - No administrator privileges required
  - Works for directory-to-directory linking
  - Native Windows support
  
- **Git Bash Support**: Works in Git Bash, Cygwin, and Windows Terminal
  - Simple `input()` instead of complex terminal libraries
  - UTF-8 encoding with error handling
  - ASCII-only output symbols (no Unicode issues)

## Troubleshooting

### No global skills found

Make sure you have:
1. Skills in `~/.skill-vault/skills/global/`
2. Each skill has a `SKILL.md` file
3. The SKILL.md has at least `name` and `description` in the frontmatter

### Junction creation fails

```bash
# Manually setup global junctions
skill-vault vault setup-global

# Check if paths exist
ls ~/.skill-vault/skills/global/
```

### Framework not detected

```bash
# Manually specify frameworks
skill-vault project init --framework codex --framework claude
```

### Frameworks changed, but installed skills did not move

```bash
# 1) Update enabled frameworks
skill-vault framework edit

# 2) Reinstall skills so framework assignments are updated
skill-vault skills add <skill-name> --force

# 3) Recreate junctions
skill-vault framework sync
```

### Unicode/Encoding errors

If you see encoding errors, the tool now uses UTF-8 with ignore errors. Update:
```bash
cd skill-vault
pip install -e . --force-reinstall --no-deps
```

## Version Control

Skills are versioned using Git tags:

```
session-handoff@v1.0.0
my-skill@v2.1.0
```

When you push a skill:
1. Changes are committed to the vault
2. A tag is created with the version from SKILL.md
3. You can optionally push to remote

## License

MIT

## Contributing

1. Fork the repository
2. Create your skill in `skills/global/`
3. Test locally with `skill-vault vault setup-global`
4. Submit a pull request
