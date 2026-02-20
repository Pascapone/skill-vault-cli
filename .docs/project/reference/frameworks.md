# Supported Frameworks

AI frameworks supported by Skill Vault.

## Framework Reference

| Key | Name | Local Path | Global Path | Config Files |
|-----|------|------------|-------------|--------------|
| `codex` | OpenAI Codex | `.agents/skills` | `~/.agents/skills` | `.codex`, `codex.md` |
| `opencode` | OpenCode | `.agents/skills` | `~/.agents/skills` | `.opencode` |
| `claude` | Claude Code | `.claude/skills` | `~/.claude/skills` | `.claude`, `CLAUDE.md` |
| `antigravity` | Antigravity (Gemini) | `.agent/skills` | `~/.gemini/antigravity/skills` | `.gemini`, `gemini.md` |
| `roo` | Roo Code | `.roo/skills` | `~/.roo/skills` | `.roo` |
| `vscode` | VS Code | `.vscode/skills` | `~/.vscode/skills` | `.vscode` |

---

## Framework Details

### OpenAI Codex

Agent framework by OpenAI.

- **Key**: `codex`
- **Skills directory**: `.agents/skills`
- **Agent instructions**: `codex.md` or `AGENTS.md`

### OpenCode

Open-source agent framework.

- **Key**: `opencode`
- **Skills directory**: `.agents/skills`
- **Agent instructions**: `.opencode`

### Claude Code

Anthropic's Claude Code agent.

- **Key**: `claude`
- **Skills directory**: `.claude/skills`
- **Agent instructions**: `CLAUDE.md`

### Antigravity (Gemini)

Google's Gemini agent framework.

- **Key**: `antigravity`
- **Skills directory**: `.agent/skills`
- **Agent instructions**: `gemini.md`

### Roo Code

VS Code extension for AI-assisted development.

- **Key**: `roo`
- **Skills directory**: `.roo/skills`
- **Agent instructions**: `.roo`

### VS Code

Visual Studio Code editor.

- **Key**: `vscode`
- **Skills directory**: `.vscode/skills`
- **Agent instructions**: `.vscode`

---

## Shared Paths

Some frameworks share the same skills directory:

| Shared Path | Frameworks |
|-------------|------------|
| `.agents/skills` | `codex`, `opencode` |

When both frameworks are enabled, only one real directory is created, with junctions between them.

---

## Auto-Detection

Skill Vault auto-detects frameworks by checking for config files:

```bash
skill-vault project init
# Checks for: .codex, .opencode, .claude, .gemini, .roo, .vscode
```

To override auto-detection:

```bash
skill-vault project init -f codex -f claude
```

---

## Adding Custom Frameworks

Edit `config/frameworks.yaml`:

```yaml
frameworks:
  my-framework:
    name: "My Framework"
    local_path: ".my-framework/skills"
    global_path: "~/.my-framework/skills"
    config_files: [".my-framework", "my-framework.md"]
```

### Fields

| Field | Description |
|-------|-------------|
| `name` | Display name |
| `local_path` | Skills directory within project |
| `global_path` | Skills directory in home |
| `config_files` | Files indicating framework usage |

---

## Framework Selection

### During Project Init

```bash
skill-vault project init
# Auto-detects or prompts for selection
```

### After Init

```bash
skill-vault framework edit
# Interactive checkbox to enable/disable frameworks
```

---

## Cross-Framework Skills

Skills with empty `frameworks` field work with all frameworks:

```yaml
---
name: my-skill
description: Works with all frameworks
frameworks: []
---
```

Skills with specific frameworks only appear for those:

```yaml
---
name: claude-specific-skill
description: Only for Claude
frameworks: [claude]
---
```
