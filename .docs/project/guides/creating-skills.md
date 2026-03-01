# Creating Skills

Guide for creating and structuring Agent Skills.

## Directory Structure

A skill is a directory containing at minimum a `SKILL.md` file:

```
my-skill/
├── SKILL.md           # Required: Skill definition
├── scripts/           # Optional: Helper scripts
├── assets/            # Optional: Templates, files
└── references/        # Optional: Additional documentation
```

## SKILL.md Format

Every skill must have a `SKILL.md` file with YAML frontmatter:

```markdown
---
name: my-skill
version: 1.0.0
description: "Brief description of what this skill does"
author: Your Name
tags: [productivity, automation]
frameworks: [codex, claude]
---

# My Skill

## Purpose
Detailed description of what this skill helps with.

## Usage
How to use this skill.

## Examples
Example usage scenarios.
```

### Frontmatter Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `name` | Yes | - | Unique skill identifier |
| `description` | Yes | - | Brief description |
| `version` | No | `0.0.0` | Semantic version |
| `author` | No | - | Author name |
| `tags` | No | `[]` | List of categorization tags |
| `frameworks` | No | `[]` | Supported frameworks (empty = all) |

## Content Structure

The markdown content after the frontmatter should include:

### Purpose
Explain what the skill does and when to use it.

### Usage
Instructions on how to use the skill.

### Examples
Concrete examples of the skill in action.

### References (Optional)
Links to additional files in `references/` directory:

```markdown
## References

- **[references/advanced.md](references/advanced.md)** - Advanced patterns
- **[references/api.md](references/api.md)** - API reference
```

## Creating a Skill

### Method 1: Create in Project (Recommended)

1. Create skill in your project:
   ```bash
   mkdir -p .agents/skills/my-skill
   ```

2. Create `SKILL.md` with content

3. Promote to vault:
   ```bash
   skill-vault vault create my-skill
   ```

### Method 2: Create Directly in Vault

1. Create directory in vault:
   ```bash
   mkdir -p ~/.skill-vault/skills/my-skill
   ```

2. Create `SKILL.md` with content

3. Setup global junctions:
   ```bash
   skill-vault framework sync
   ```

## Best Practices

### Naming

- Use lowercase with hyphens: `my-skill-name`
- Be descriptive but concise
- Match directory name to skill name

### Description

- Keep it under 100 characters
- Start with a verb: "Build...", "Create...", "Manage..."
- Explain when to use the skill

### Version

- Use semantic versioning: `MAJOR.MINOR.PATCH`
- Increment when making changes:
  - MAJOR: Breaking changes
  - MINOR: New features
  - PATCH: Bug fixes

### Content

- Focus on practical usage
- Include code examples
- Link to reference files for detailed information

## Example Skill

```
pydantic-agents/
├── SKILL.md
└── references/
    ├── tools.md
    ├── testing.md
    └── mcp.md
```

SKILL.md:
```markdown
---
name: pydantic-agents
description: Build production-grade AI agents with Pydantic AI framework
version: 1.0.0
tags: [agents, pydantic, ai]
---

# Pydantic AI Agents

Build reliable, type-safe AI agents with structured outputs and tool calling.

## Core Concepts

An agent is a container for: **instructions**, **tools**, **output_type**, **deps_type**, and **model**.

## References

- **[references/tools.md](references/tools.md)** - Tool calling patterns
- **[references/testing.md](references/testing.md)** - Testing strategies
```
