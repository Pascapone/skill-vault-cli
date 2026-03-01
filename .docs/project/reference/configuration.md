# Configuration Reference

Configuration files used by Skill Vault.

## frameworks.yaml

Located in `config/frameworks.yaml`. Defines supported AI frameworks.

### Structure

```yaml
frameworks:
  <key>:
    name: "Display Name"
    local_path: ".framework/skills"
    config_files: [".framework", "framework.md"]

defaults:
  auto_sync: false
  create_backups: true
  preferred_frameworks: [codex, claude]
```

### Framework Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Display name for the framework |
| `local_path` | Yes | Skills directory within a project (relative) |
| `config_files` | No | Files that indicate framework usage (for auto-detection) |

### Defaults Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `auto_sync` | bool | `false` | Auto-sync on install |
| `create_backups` | bool | `true` | Create backups before changes |
| `preferred_frameworks` | list | `[]` | Default frameworks for new projects |

### Example: Adding a Framework

```yaml
frameworks:
  # ... existing frameworks ...
  
  my-framework:
    name: "My Framework"
    local_path: ".my-framework/skills"
    config_files: [".my-framework", "my-framework.md"]
```

---

## Project config.yaml

Located in `<project>/.skill-vault/config.yaml`. Project-specific settings.

### Structure

```yaml
name: my-project
path: /path/to/project
vault_remote: origin
vault_branch: main
enabled_frameworks:
  - codex
  - claude
installed_skills: {}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Project name |
| `path` | string | Absolute project path |
| `vault_remote` | string | Git remote name (default: origin) |
| `vault_branch` | string | Git branch (default: main) |
| `enabled_frameworks` | list | Frameworks enabled for this project |
| `installed_skills` | dict | Tracked in installed.json |

---

## installed.json

Located in `<project>/.skill-vault/installed.json`. Tracks installed skills.

### Structure

```json
{
  "skill-name": {
    "version": "1.0.0",
    "installed_at": "2026-02-20T00:00:00.000000",
    "frameworks": ["codex", "claude"],
    "file_hashes": {
      "SKILL.md": "abc123def456..."
    }
  }
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Installed skill version |
| `installed_at` | string | ISO timestamp of installation |
| `frameworks` | list | Frameworks skill is installed for |
| `file_hashes` | dict | MD5 hashes of files (for change detection) |

---

## Vault config.yaml

Located in `~/.skill-vault/config.yaml`. Global vault settings.

### Structure

```yaml
vault:
  path: ~/.skill-vault
  repo_url: https://github.com/user/skill-vault
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `path` | string | Vault directory path |
| `repo_url` | string | Remote repository URL |
