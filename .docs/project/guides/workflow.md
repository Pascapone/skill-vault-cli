# Workflow

Typical usage workflow for Skill Vault.

## Initial Setup

### 1. Initialize Global Vault

```bash
skill-vault vault init
```

This creates:
- `~/.skill-vault/` - Global vault with Git
- Junctions in `~/.agents/skills`, `~/.claude/skills`, etc.

### 2. Initialize Project

```bash
cd my-project
skill-vault project init
```

Auto-detects frameworks or prompts for selection. Creates:
- `.skill-vault/config.yaml` - Project settings
- `.skill-vault/installed.json` - Installed skills
- Framework skill directories with junctions

---

## Daily Usage

### Adding Skills

```bash
# Interactive selection (local skills by default)
skill-vault skills add

# Show global skills
skill-vault skills add --global

# Direct install
skill-vault skills add my-skill
```

### Checking for Updates

```bash
skill-vault sync --dry-run
```

### Updating Skills

```bash
skill-vault sync          # Interactive
skill-vault sync --all    # Update all
```

### Removing Skills

```bash
skill-vault skills remove
```

---

## Creating New Skills

### 1. Create in Project

```bash
mkdir -p .agents/skills/my-new-skill
# Edit SKILL.md
```

### 2. Test Locally

Use the skill in your project to verify it works.

### 3. Promote to Vault

```bash
skill-vault vault create my-new-skill
```

Choose global (shared) or local (private) when prompted.

---

## Collaborating

### Pulling Changes

```bash
skill-vault pull
```

Pulls latest vault changes and updates global junctions.

### Pushing Changes

After modifying a skill in your project:

```bash
skill-vault push my-skill -m "Update description"
```

Then push to remote:

```bash
skill-vault vault push  # If prompted
```

---

## Framework Management

### Adding a Framework

```bash
skill-vault framework edit
```

Select additional frameworks from the list.

**Note:** Existing skills keep their framework assignments. Reinstall to update:

```bash
skill-vault skills add my-skill --force
skill-vault framework sync
```

### Removing a Framework

```bash
skill-vault framework edit
```

Deselect unwanted frameworks.

---

## Troubleshooting

### Skill Not Found

Ensure:
1. Skill exists in `~/.skill-vault/skills/global/` or `local/`
2. SKILL.md has valid frontmatter with `name` and `description`
3. Global junctions are set up: `skill-vault vault setup-global`

### Junction Issues

Recreate junctions:

```bash
skill-vault framework sync        # Project level
skill-vault vault sync-global     # Global level
```

### Modified Skills

When removing a modified skill, you'll be warned about unsaved changes. Use `--force` to skip confirmation.
