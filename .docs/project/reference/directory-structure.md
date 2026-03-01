# Directory Structure

File system layout for Skill Vault.

## Global Vault

```
~/.skill-vault/                     # Global vault (Git repository)
├── .git/                           # Version control
├── .gitignore                      # Ignores projects/ subdirectories
├── README.md                       # Vault README
├── presets/                        # Agent configuration presets
│   └── Agent1/
│       ├── PRESET.md
│       └── skills.json             # Optional dependencies
├── skills/                         # All skills
│   ├── session-handoff/
│   │   ├── SKILL.md                # Skill definition (REQUIRED)
│   │   ├── scripts/                # Optional: Helper scripts
│   │   └── assets/                 # Optional: Templates, files
│   └── my-skill/
│       └── SKILL.md
├── projects/                       # Registered project metadata (gitignored)
└── config/
    └── frameworks.yaml             # Framework configurations
```

### Global Vault Purpose

- Central storage for all skills and presets
- Git version control with tagging
- Single source of truth for skill versions

---

## Project Structure

```
my-project/
├── .skill-vault/                   # Project metadata
│   ├── config.yaml                 # Project configuration
│   └── installed.json              # Installed skills with versions
├── .agents/                        # Codex/OpenCode (PRIMARY - real directory)
│   └── skills/
│       ├── my-skill/               # Real skill files (copied from vault)
│       └── session-handoff/        # Real skill files
├── .claude/                        # Claude Code
│   └── skills/                     # Junction → .agents/skills/
├── .agent/                         # Antigravity
│   └── skills/                     # Junction → .agents/skills/
├── .roo/                           # Roo Code
│   └── skills/                     # Junction → .agents/skills/
└── src/                            # Your project files
```

### Primary Framework

The **first enabled framework's** skills directory becomes the primary (real) directory. All other frameworks' directories are junctions to this primary.

Example with frameworks `[codex, claude, roo]`:
- `.agents/skills/` - Real directory (primary)
- `.claude/skills/` - Junction → `.agents/skills/`
- `.roo/skills/` - Junction → `.agents/skills/`

---

## Home Directory (Global Access)

Global skills are accessible via junctions in framework home directories:

```
~/.agents/skills/                   # Codex/OpenCode
│   └── my-skill/                   # Junction → ~/.skill-vault/skills/my-skill/
├── .claude/skills/                 # Claude Code
│   └── my-skill/                   # Junction → ~/.skill-vault/skills/my-skill/
├── .gemini/antigravity/skills/     # Antigravity
│   └── my-skill/                   # Junction → ~/.skill-vault/skills/my-skill/
├── .roo/skills/                    # Roo Code
│   └── my-skill/                   # Junction → ~/.skill-vault/skills/my-skill/
└── .vscode/skills/                 # VS Code
    └── my-skill/                   # Junction → ~/.skill-vault/skills/my-skill/
```

### Global Access Purpose

- Skills available without project initialization
- AI frameworks can discover skills from standard locations
- Automatic sharing across all projects

---

## Key Files

### SKILL.md

Required file in every skill directory. Contains YAML frontmatter and skill content.

### config.yaml

- Vault: `~/.skill-vault/config.yaml` - Vault settings
- Project: `<project>/.skill-vault/config.yaml` - Project settings

### installed.json

Project-specific tracking of installed skills with versions and hashes.

### frameworks.yaml

Framework definitions used by Skill Vault.

---

## Junction Flow

```
Vault                    Home Directories              Project
------                   ---------------              -------
~/.skill-vault/
└── skills/
    └── my-skill/ ────────┬─→ ~/.agents/skills/my-skill/
                          ├──→ ~/.claude/skills/my-skill/
                          └──→ ~/.gemini/antigravity/skills/my-skill/
                                                       
                                 (when installed in project)
                                                       
                          └──→ my-project/.agents/skills/my-skill/
                                   ↑
                                   └── my-project/.claude/skills/ (junction)
```
