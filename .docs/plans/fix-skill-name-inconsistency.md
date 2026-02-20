# Fix: Inconsistente Skill-Namen bei Promotion

## Problem

Bei der Promotion eines Skills zum Vault entstehen inkonsistente Namen:

| Ort | Wert | Quelle |
|-----|------|--------|
| Verzeichnisname im Projekt | `test` | Ordnername |
| `skill.name` (SKILL.md) | `test-skill` | YAML Frontmatter |
| Verzeichnisname im Vault | `test` | `promote_skill_to_vault` nutzt Verzeichnisnamen |
| Anzeige im Menü | `test-skill` | `select_skill_to_promote` nutzt `skill.name` |

### Folgen

1. `skill-vault skills add test-skill` → Fehler: "Skill not found in vault"
2. `skill-vault vault list` zeigt `test` (Verzeichnisname), nicht `test-skill`
3. Verwirrende UX: User wählt `test-skill`, aber Skill wird als `test` gespeichert

## Beteiligte Code-Stellen

### `sync.py`

**`discover_project_skills()`** (Zeile 600-601):
```python
skill_name = skill_dir.name  # Nutzt Verzeichnisname
discovered[skill_name] = {...}  # Key ist Verzeichnisname
```

**`promote_skill_to_vault()`** (Zeile 678-681):
```python
# Nutzt skill_name (Verzeichnisname) für Zielpfad
if is_global:
    target_path = self.vault.global_skills_dir / skill_name
else:
    target_path = self.vault.local_skills_dir / skill_name
```

### `interactive.py`

**`select_skill_to_promote()`** (Zeile 369):
```python
# Zeigt skill.name (aus SKILL.md) an
name = f"{skill.name} - {skill.description[:40]}..."
```

### `vault.py`

**`get_skill()`** (Zeile 97, 105):
```python
skill_path = self.global_skills_dir / name  # Sucht nach Verzeichnisname
```

## Lösungsansätze

### Option A: SKILL.md-Name als Quelle der Wahrheit (Empfohlen)

Der Name in `SKILL.md` (`skill.name`) wird für alles verwendet:
- Zielverzeichnis im Vault
- Suche im Vault
- Anzeige im Menü

**Änderungen:**

1. **`promote_skill_to_vault()`**: Nutze `skill.name` statt `skill_name` (Verzeichnisname)
   ```python
   target_path = self.vault.local_skills_dir / skill.name
   ```

2. **Validierung**: Warne wenn Verzeichnisname ≠ `skill.name`
   ```python
   if skill_dir.name != skill.name:
       console.print(f"[yellow]Warning: Directory name '{skill_dir.name}' differs from skill name '{skill.name}'[/yellow]")
       console.print(f"[dim]Using '{skill.name}' as the skill name in vault.[/dim]")
   ```

3. **`discover_project_skills()`**: Key sollte `skill.name` sein, nicht Verzeichnisname

### Option B: Verzeichnisname als Quelle der Wahrheit

Erzwinge dass Verzeichnisname = `skill.name` in SKILL.md

**Änderungen:**

1. Validierung bei `discover_project_skills()`:
   ```python
   if skill.name != skill_dir.name:
       discovered[skill_name]["error"] = f"Directory name '{skill_dir.name}' must match skill name '{skill.name}'"
   ```

2. User muss entweder:
   - Verzeichnis umbenennen, oder
   - `name` in SKILL.md anpassen

## Empfehlung

**Option A** ist benutzerfreundlicher:
- User kann Verzeichnis beliebigen Namen geben
- `name` in SKILL.md ist das "offizielle" Skill-Identifikator
- Konsistente Erfahrung über alle Befehle

## Implementierungsplan

1. [x] `promote_skill_to_vault()` - Nutze `skill.name` für Zielpfad
2. [x] `promote_skill_to_vault()` - Füge Warnung bei Namensabweichung hinzu
3. [x] `discover_project_skills()` - Nutze `skill.name` als Dictionary-Key
4. [x] Tests durchgeführt
5. [x] Dokumentation aktualisieren
6. [x] `promote_skill_to_vault()` - Skill zu `installed.json` hinzufügen (nach Promotion tracken)

## Status: ABGESCHLOSSEN (2026-02-20)

Die Änderungen wurden implementiert und getestet. Der Skill-Name aus SKILL.md wird jetzt konsistent verwendet. Nach der Promotion wird der Skill auch in `installed.json` getrackt, damit er mit `skills remove` verwaltet werden kann.

## Testfälle

```bash
# Setup: Skill mit abweichendem Namen
mkdir .agents/skills/test
echo '---
name: test-skill
description: Test
---' > .agents/skills/test/SKILL.md

# Test 1: Promotion
skill-vault vault create test
# Erwartung: Skill wird als "test-skill" im Vault gespeichert
# Erwartung: Warnung über Namensabweichung

# Test 2: Suche
skill-vault vault show test-skill
# Erwartung: Skill wird gefunden

# Test 3: Installation
skill-vault skills add test-skill
# Erwartung: Skill wird installiert
```
