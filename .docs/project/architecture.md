# Architecture

Skill Vault consists of 6 core modules that work together to manage skills across AI frameworks.

## Module Overview

```
┌─────────────────────────────────────────────────────────┐
│                        CLI (cli.py)                      │
│  Command-line interface using Click + Rich + InquirerPy │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│    Vault      │   │     Sync      │   │   Interactive │
│  (vault.py)   │   │  (sync.py)    │   │(interactive.py)│
└───────────────┘   └───────────────┘   └───────────────┘
        │                   │
        ▼                   ▼
┌───────────────┐   ┌───────────────┐
│    Skills     │   │   Junction    │
│  (skills.py)  │   │ (junction.py) │
└───────────────┘   └───────────────┘
        │
        ▼
┌───────────────┐
│    Config     │
│  (config.py)  │
└───────────────┘
```

## Modules

### cli.py

Command-line interface entry point. Defines all commands using Click decorators.

**Responsibilities:**
- Parse command arguments
- Initialize vault and project instances
- Route commands to appropriate modules
- Format output with Rich

**Key Commands:**
- `vault init`, `vault list`, `vault show`, `vault create`
- `project init`, `project status`
- `skills list`, `skills add`, `skills remove`, `skills diff`
- `sync`, `push`, `pull`
- `framework list`, `framework edit`, `framework sync`

### config.py

Configuration management for frameworks and defaults.

**Classes:**
- `FrameworkConfig`: Settings for a single framework (paths, config files)
- `DefaultsConfig`: Default settings (auto_sync, create_backups)
- `Config`: Loads and manages framework configurations

**Key Methods:**
- `detect_frameworks()`: Auto-detect frameworks in a project
- `get_local_path()`: Get framework's local skills path
- `get_global_path()`: Get framework's global skills path

### vault.py

Git-integrated vault management.

**Classes:**
- `Vault`: Manages the global skill repository
- `ProjectVault`: Manages project-specific settings
- `ProjectConfig`: Project configuration dataclass

**Key Methods:**
- `initialize()`: Create new vault with Git
- `list_global_skills()`, `list_local_skills()`: List available skills
- `get_skill()`: Retrieve skill by name
- `commit_skill()`: Commit and tag a skill version
- `push()`, `pull()`: Sync with remote

### skills.py

Skill parsing and representation.

**Classes:**
- `Skill`: Dataclass representing a skill
- `SkillParser`: Parse SKILL.md files with YAML frontmatter

**Key Methods:**
- `parse()`: Parse a single SKILL.md file
- `parse_all()`: Parse all skills in a directory
- `get_skill_version()`: Quick version extraction

### sync.py

Synchronization logic between vault and projects.

**Class:** `SkillSync`

**Key Methods:**
- `install_skill()`: Copy skill from vault to project
- `remove_skill()`: Remove skill from project
- `get_available_updates()`: Check for newer versions
- `push_skill()`: Push local skill to vault
- `promote_skill_to_vault()`: Add new skill from project
- `discover_project_skills()`: Find untracked skills
- `ensure_framework_junctions()`: Set up framework directory junctions

### junction.py

Windows Junction operations.

**Functions:**
- `create_junction()`: Create a directory junction
- `remove_junction()`: Remove a junction (preserves target)
- `is_junction()`: Check if path is a junction
- `get_junction_target()`: Get junction target path

### interactive.py

Interactive CLI elements using InquirerPy.

**Functions:**
- `select_skills_interactive()`: Multi-select for skills
- `select_frameworks_interactive()`: Multi-select for frameworks
- `select_updates_interactive()`: Select updates to apply
- `confirm_remove_modified()`: Confirm removal of modified skills

### global_junctions.py

Global skill junction management.

**Functions:**
- `setup_global_junctions()`: Create junctions in all framework home directories
- `sync_global_junctions()`: Add new and remove obsolete junctions
- `remove_global_junction()`: Remove skill from all global directories

## Data Flow

### Installing a Skill

```
1. CLI: skills add my-skill
2. SkillSync.install_skill()
   ├── Check if already installed
   ├── ensure_framework_junctions()
   ├── Copy skill files to primary framework
   ├── Record in installed.json
   └── Save file hashes for modification tracking
3. Auto-commit to vault
```

### Promoting a Skill to Vault

```
1. CLI: vault create my-skill
2. SkillSync.discover_project_skills()
   ├── Scan framework directories
   ├── Filter out vault-tracked skills
   └── Return untracked skills
3. SkillSync.promote_skill_to_vault()
   ├── Copy to vault (global/ or local/)
   ├── Commit to vault
   ├── Update global junctions
   └── Track in installed.json
```

## File Formats

### SKILL.md

```markdown
---
name: skill-name        # Required
version: 1.0.0          # Optional (default: 0.0.0)
description: "..."      # Required
author: Name            # Optional
tags: [tag1, tag2]      # Optional
frameworks: [codex]     # Optional
---

# Skill content...
```

### installed.json

```json
{
  "skill-name": {
    "version": "1.0.0",
    "installed_at": "2026-02-20T00:00:00",
    "frameworks": ["codex", "claude"],
    "is_local": false,
    "file_hashes": {
      "SKILL.md": "abc123..."
    }
  }
}
```
