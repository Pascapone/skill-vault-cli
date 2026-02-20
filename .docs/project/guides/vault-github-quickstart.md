# Vault + GitHub Quickstart

Kurzguide, um einen neuen Skill Vault aufzusetzen und mit GitHub zu verbinden.

## Voraussetzungen

- `git` installiert
- Python-CLI installiert: `pip install -e .`
- Optional fuer Repo-Erstellung per CLI: `gh` installiert und eingeloggt (`gh auth login`)

## 1. Vault initialisieren

```bash
skill-vault vault init
```

Optional direkt mit Remote + Auto-Push:

```bash
skill-vault vault init --repo git@github.com:<you>/<repo>.git --auto-push
```

## 2. Remote-Status pruefen

```bash
skill-vault vault repo status
```

Du siehst dort u.a. Vault-Pfad, Branch, Remote-URL und Auto-Push-Status.

## 3. Mit vorhandenem GitHub-Repo verbinden

```bash
skill-vault vault repo connect --url git@github.com:<you>/<repo>.git --push
```

Hinweis: `https://github.com/...` wird fuer GitHub automatisch in `git@github.com:...` umgewandelt.

Optional:

```bash
skill-vault vault repo connect --url git@github.com:<you>/<repo>.git --remote origin --branch main
skill-vault vault repo auto-push on
```

## 4. Neues GitHub-Repo direkt aus der CLI erstellen

```bash
skill-vault vault repo create --name my-skill-vault --private
```

Optional mit Owner/Org:

```bash
skill-vault vault repo create --owner <org-or-user> --name my-skill-vault --private
```

## 5. Skills in den Vault bringen und syncen

Skill aus Projekt promoten:

```bash
skill-vault vault create my-skill
```

Mit sofortigem Remote-Push:

```bash
skill-vault vault create my-skill --push
```

Lokalen Skill updaten/taggen:

```bash
skill-vault push my-skill -m "Update my-skill"
```

## 6. Auf anderem Rechner uebernehmen

Nach Setup auf Rechner A reichen auf Rechner B:

```bash
skill-vault vault init --path ~/.skill-vault
skill-vault vault repo connect --url git@github.com:<you>/<repo>.git
skill-vault pull
skill-vault vault sync-global
```

## Troubleshooting (kurz)

- `Remote not configured`: `skill-vault vault repo connect --url git@github.com:<you>/<repo>.git`
- `pull`-Probleme wegen Branch: `skill-vault vault repo connect --url git@github.com:<you>/<repo>.git --branch <branch>`
- `gh` fehlt: `vault repo create` geht erst nach Installation/Login von GitHub CLI
