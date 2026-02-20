# Windows Junctions

Understanding junction-based linking in Skill Vault.

## What are Junctions?

Windows Junctions are a type of directory reparse point that creates a link between two directories. Unlike symlinks, junctions:

- **Don't require administrator privileges**
- **Work natively on Windows**
- **Only link directories, not files**

## Junctions vs Symlinks

| Feature | Junction | Symlink |
|---------|----------|---------|
| Admin rights required | No | Yes (usually) |
| Directory linking | Yes | Yes |
| File linking | No | Yes |
| Cross-volume support | No | Yes |
| Windows native | Yes | Yes (Vista+) |

## Why Skill Vault Uses Junctions

### No Privilege Escalation

Creating symlinks on Windows typically requires Developer Mode or administrator privileges. Junctions work without any special configuration.

### Simplicity

Skills are always directories, so file-level linking isn't needed. Junctions provide exactly what's needed.

### Compatibility

Junctions have been supported since Windows 2000 and work consistently across all modern Windows versions.

## How Skill Vault Uses Junctions

### Global Skills

Junctions connect vault skills to framework directories:

```
~/.agents/skills/my-skill/  →  ~/.skill-vault/skills/global/my-skill/
~/.claude/skills/my-skill/  →  ~/.skill-vault/skills/global/my-skill/
```

Each framework directory contains junctions pointing to the vault.

### Project Skills

Within a project, framework directories are junctioned:

```
my-project/
├── .agents/skills/     ← Real directory (primary)
├── .claude/skills/     ← Junction → .agents/skills/
└── .roo/skills/        ← Junction → .agents/skills/
```

Only one copy of each skill exists; all frameworks share it via junctions.

## Implementation

### Creating a Junction

Skill Vault uses `mklink /J`:

```python
# junction.py
def create_junction(source: Path, target: Path) -> bool:
    cmd = ['cmd', '/c', 'mklink', '/J', str(source), str(target)]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0
```

### Removing a Junction

Removing a junction doesn't affect the target:

```python
def remove_junction(path: Path) -> bool:
    os.rmdir(path)  # Only removes the junction
    return True
```

### Checking if Junction

```python
def is_junction(path: Path) -> bool:
    return os.path.islink(path) or bool(
        os.lstat(path).st_file_attributes & 0x400
    )
```

## Limitations

### Local Paths Only

Junctions must use local paths. Network paths (UNC) are not supported as targets.

### Same Volume

Junctions can only point to directories on the same volume.

### Directory Only

Cannot create junctions for individual files.

## Troubleshooting

### Junction Not Created

Check:
1. Target directory exists
2. Target is on the same volume
3. Source doesn't already exist as a real directory

### Junction Points to Wrong Location

Remove and recreate:

```bash
skill-vault framework sync
# or
skill-vault vault sync-global
```

### Can't Delete Junction

If `rmdir` fails, the path might not be a junction. Check with:

```bash
dir /AL  # List reparse points
```

## Best Practices

1. **Always use the CLI** - Don't manually create junctions; use `skill-vault` commands
2. **Sync after changes** - Run `framework sync` after changing frameworks
3. **Don't mix methods** - Either use junctions or real directories, not both
