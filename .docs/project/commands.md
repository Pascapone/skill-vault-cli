# Commands Reference

Complete reference for all Skill Vault CLI commands.

## Command Aliases

The tool can be invoked as:
- `skill-vault` - Main command
- `sv` - Short alias
- `skill-eye` - Alternative alias

---

## Vault Commands

Manage the global Skill Vault repository.

### vault init

Initialize the global vault.

```bash
skill-vault vault init                    # Default: ~/.skill-vault
skill-vault vault init --path ~/my-vault  # Custom path
skill-vault vault init --repo <url>       # With remote repository
skill-vault vault init --no-setup-global  # Skip global junctions
```

### vault list

List all skills in the vault.

```bash
skill-vault vault list
```

### vault show

Show details of a specific skill.

```bash
skill-vault vault show <skill-name>
```

### vault create

Promote a skill from project to vault.

```bash
skill-vault vault create                  # Interactive selection
skill-vault vault create <name>           # Add as global skill
skill-vault vault create <name> --local   # Add as local skill
skill-vault vault create <name> --global  # Explicitly global
```

### vault setup-global

Create junctions in all framework home directories (~/.agents/skills, ~/.claude/skills, etc.).

```bash
skill-vault vault setup-global
```

### vault sync-global

Synchronize global junctions - add new and remove obsolete.

```bash
skill-vault vault sync-global
```

### vault repo

Manage the remote repository connection for the vault.

```bash
skill-vault vault repo status                   # Show vault git/remote status
skill-vault vault repo connect --url <ssh-url>  # Connect/update remote
skill-vault vault repo disconnect               # Disconnect configured remote
skill-vault vault repo create --name <name>     # Create GitHub repo via gh CLI
skill-vault vault repo pull                     # Pull latest from configured remote
skill-vault vault repo auto-push on|off         # Toggle auto-push behavior
```

---

## Project Commands

Manage Skill Vault in the current project.

### project init

Initialize a project to use Skill Vault.

```bash
skill-vault project init                          # Auto-detect frameworks
skill-vault project init -f codex -f claude       # Specify frameworks
```

### project status

Show project status and installed skills.

```bash
skill-vault project status
```

---

## Skills Commands

Manage skills in the current project.

### skills list

List all available skills and installation status.

```bash
skill-vault skills list
```

### skills add

Add skills to the project.

```bash
skill-vault skills add                     # Interactive (local skills only)
skill-vault skills add --global            # Interactive (show global skills)
skill-vault skills add <name>              # Direct install
skill-vault skills add <name> --force      # Force reinstall
skill-vault skills add -f codex <name>     # For specific framework
```

### skills remove

Remove skills from the project.

```bash
skill-vault skills remove                  # Interactive selection
skill-vault skills remove <name>           # Direct remove
skill-vault skills remove <name> --force   # Skip confirmation for modified
```

### skills diff

Show differences between installed and vault version.

```bash
skill-vault skills diff <name>
```

---

## Sync Commands

Synchronize between project and vault.

### sync

Check for and apply skill updates.

```bash
skill-vault sync                # Interactive selection
skill-vault sync --dry-run      # Preview updates
skill-vault sync --all          # Update all without asking
skill-vault sync -i             # Interactive mode
```

### push

Push a local skill from project to vault.

```bash
skill-vault push <name>
skill-vault push <name> -m "Update message"
```

### pull

Pull latest changes from vault remote.

```bash
skill-vault pull
```

---

## Framework Commands

Manage frameworks in the project.

### framework list

List all available frameworks.

```bash
skill-vault framework list
```

### framework edit

Interactively select/deselect enabled frameworks.

```bash
skill-vault framework edit
```

### framework sync

Recreate framework directory junctions.

```bash
skill-vault framework sync
```

---

## Global Options

```bash
skill-vault --version          # Show version
skill-vault --help             # Show help
skill-vault <command> --help   # Command-specific help
```
