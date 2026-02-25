"""Command Line Interface for Skill Vault."""

import shutil
import subprocess
import re
import click
from pathlib import Path
from typing import Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .config import Config
from .vault import Vault, ProjectVault
from .sync import SkillSync
from . import interactive
from .global_junctions import setup_global_junctions, sync_global_junctions


console = Console()


GITHUB_SSH_PATTERN = re.compile(
    r"^git@github\.com:(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?/?$",
    re.IGNORECASE
)
GITHUB_SSH_URL_PATTERN = re.compile(
    r"^ssh://git@github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?/?$",
    re.IGNORECASE
)
GITHUB_HTTP_PATTERN = re.compile(
    r"^https?://github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?/?$",
    re.IGNORECASE
)


def normalize_remote_url(url: str) -> str:
    """Normalize GitHub remotes to SSH format."""
    cleaned = (url or "").strip()
    if not cleaned:
        raise click.BadParameter("Remote URL cannot be empty")

    for pattern in (GITHUB_SSH_PATTERN, GITHUB_SSH_URL_PATTERN, GITHUB_HTTP_PATTERN):
        match = pattern.match(cleaned)
        if not match:
            continue
        owner = match.group("owner")
        repo = match.group("repo")
        return f"git@github.com:{owner}/{repo}.git"

    if "github.com" in cleaned.lower():
        raise click.BadParameter(
            "Invalid GitHub URL. Use git@github.com:<owner>/<repo>.git"
        )

    return cleaned


def get_global_config_file() -> Path:
    """Get global config file path."""
    return Path.home() / ".skill-vault" / "config.yaml"


def load_global_config() -> dict[str, Any]:
    """Load global configuration with sane defaults."""
    config_file = get_global_config_file()
    default_path = str(Path.home() / ".skill-vault")

    data: dict[str, Any] = {}
    if config_file.exists():
        import yaml
        with open(config_file, 'r', encoding='utf-8') as f:
            loaded = yaml.safe_load(f) or {}
            if isinstance(loaded, dict):
                data = loaded

    vault_cfg = data.get("vault", {})
    if not isinstance(vault_cfg, dict):
        vault_cfg = {}

    auto_push_raw = vault_cfg.get("auto_push", False)
    if isinstance(auto_push_raw, str):
        auto_push_value = auto_push_raw.strip().lower() in {"1", "true", "yes", "on"}
    else:
        auto_push_value = bool(auto_push_raw)

    branch_raw = vault_cfg.get("branch")
    if isinstance(branch_raw, str):
        branch_value = branch_raw.strip() or "main"
    elif branch_raw is None:
        branch_value = "main"
    else:
        branch_value = str(branch_raw)

    data["vault"] = {
        "path": vault_cfg.get("path", default_path),
        "repo_url": vault_cfg.get("repo_url"),
        "remote_name": vault_cfg.get("remote_name", "origin"),
        "branch": branch_value,
        "auto_push": auto_push_value,
    }
    return data


def save_global_config(config_data: dict[str, Any]) -> None:
    """Persist global configuration."""
    config_file = get_global_config_file()
    config_file.parent.mkdir(parents=True, exist_ok=True)
    import yaml
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.safe_dump(config_data, f, sort_keys=False)


def get_vault_settings() -> dict[str, Any]:
    """Get normalized vault settings from global config."""
    return load_global_config().get("vault", {})


def update_vault_settings(**updates: Any) -> dict[str, Any]:
    """Update and persist vault settings."""
    cfg = load_global_config()
    vault_cfg = cfg.get("vault", {})

    for key, value in updates.items():
        if value is not None:
            vault_cfg[key] = value

    cfg["vault"] = vault_cfg
    save_global_config(cfg)
    return vault_cfg


def clear_vault_settings(*keys: str) -> dict[str, Any]:
    """Clear selected vault settings by setting them to None."""
    cfg = load_global_config()
    vault_cfg = cfg.get("vault", {})

    for key in keys:
        vault_cfg[key] = None

    cfg["vault"] = vault_cfg
    save_global_config(cfg)
    return vault_cfg


def get_vault_path() -> Path:
    """Get the vault path from config or default."""
    settings = get_vault_settings()
    return Path(settings.get("path", str(Path.home() / ".skill-vault"))).expanduser()


def get_vault_remote_name() -> str:
    """Get configured remote name for vault operations."""
    settings = get_vault_settings()
    return settings.get("remote_name", "origin")


def get_vault_branch() -> Optional[str]:
    """Get configured branch for vault operations."""
    settings = get_vault_settings()
    branch = settings.get("branch")
    return branch if branch else "main"


def get_auto_push_enabled() -> bool:
    """Whether auto-push is enabled for vault commits."""
    settings = get_vault_settings()
    return bool(settings.get("auto_push", False))


def get_effective_remote_name(override: Optional[str] = None) -> str:
    """Resolve remote name from CLI override or config."""
    return override or get_vault_remote_name()


def get_effective_branch(vault: Vault, remote_name: str, override: Optional[str] = None) -> str:
    """Resolve branch from CLI override, config, or repository state."""
    if override:
        return override

    configured = get_vault_branch()
    if configured:
        if vault.has_remote(remote_name) and not vault.remote_branch_exists(configured, remote_name=remote_name):
            remote_default = vault.get_remote_default_branch(remote_name=remote_name)
            if remote_default:
                return remote_default
        return configured

    return vault.resolve_branch(remote_name=remote_name)


def ensure_vault_repo_initialized(vault: Vault) -> bool:
    """Return True if vault repo is initialized, otherwise print error."""
    if vault.repo:
        return True
    console.print("[red]Vault not initialized. Run 'skill-vault vault init' first.[/red]")
    return False


def pull_vault_remote(
    vault: Vault,
    remote_name: str,
    branch: Optional[str] = None,
    sync_global: bool = True
) -> bool:
    """Pull from configured remote and refresh global junctions."""
    if not vault.has_remote(remote_name):
        console.print(
            f"[red]Remote '{remote_name}' not configured. Use 'skill-vault vault repo connect --url ...' first.[/red]"
        )
        return False

    resolved_branch = branch
    if not resolved_branch:
        configured = get_vault_branch()
        if configured:
            resolved_branch = configured

    if resolved_branch and not vault.remote_branch_exists(resolved_branch, remote_name=remote_name):
        remote_default = vault.get_remote_default_branch(remote_name=remote_name)
        if remote_default and remote_default != resolved_branch:
            console.print(
                f"[yellow]![/yellow] Remote branch '{resolved_branch}' not found. Using '{remote_default}' instead."
            )
            resolved_branch = remote_default

    if not resolved_branch:
        resolved_branch = vault.get_remote_default_branch(remote_name=remote_name)

    if not resolved_branch:
        resolved_branch = vault.resolve_branch(remote_name=remote_name)

    current_branch = vault.get_current_branch()
    if current_branch != resolved_branch and vault.repo:
        if vault.has_local_branch(resolved_branch):
            vault.repo.git.checkout(resolved_branch)
        elif vault.remote_branch_exists(resolved_branch, remote_name=remote_name):
            vault.repo.git.fetch(remote_name, resolved_branch)
            vault.repo.git.checkout("-B", resolved_branch, f"{remote_name}/{resolved_branch}")

    try:
        pulled_branch = vault.pull(remote_name=remote_name, branch=resolved_branch)
    except Exception as e:
        error_text = str(e)
        if "refusing to merge unrelated histories" not in error_text:
            raise

        if not vault.is_clean(untracked_files=False):
            raise click.ClickException(
                "Pull failed due to unrelated histories and local uncommitted changes. "
                "Commit/stash first, then retry."
            )

        if not vault.is_bootstrap_history():
            raise click.ClickException(
                "Pull failed due to unrelated histories. "
                "This repository already has its own commit history. "
                "Merge manually or recreate the local vault clone."
            )

        console.print(
            "[yellow]![/yellow] Local bootstrap history differs from remote. "
            "Re-aligning local branch to remote."
        )
        vault.checkout_remote_branch(remote_name=remote_name, branch=resolved_branch)
        pulled_branch = resolved_branch

    current_url = vault.get_remote_url(remote_name)
    update_vault_settings(
        remote_name=remote_name,
        repo_url=current_url,
        branch=pulled_branch
    )
    console.print(f"[green]+[/green] Pulled latest changes from {remote_name}/{pulled_branch}")

    if sync_global:
        console.print("[blue]Updating global junctions...[/blue]")
        config = Config(get_vault_path())
        sync_global_junctions(vault, config)

    return True


def get_vault() -> Vault:
    """Get vault instance."""
    vault_path = get_vault_path()
    return Vault(vault_path)


def get_project() -> ProjectVault:
    """Get project instance for current directory."""
    return ProjectVault(Path.cwd())


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Skill Vault - Manage Agent Skills across AI frameworks."""
    pass


# Global Vault Commands
@cli.group()
def vault():
    """Manage the global Skill Vault."""
    pass


@vault.command(name='init')
@click.option('--path', '-p', default=None, help='Path for the vault (default: ~/.skill-vault)')
@click.option('--repo', '-r', default=None, help='Remote repository URL')
@click.option('--remote', default="origin", show_default=True, help='Remote name')
@click.option('--branch', default=None, help='Preferred branch for pull/push (default: main)')
@click.option('--auto-push/--no-auto-push', default=False, help='Auto-push vault commits to remote')
@click.option('--setup-global/--no-setup-global', default=True, help='Setup global junctions after init')
def vault_init(path, repo, remote, branch, auto_push, setup_global):
    """Initialize the Skill Vault."""
    vault_path = Path(path).expanduser() if path else Path.home() / ".skill-vault"
    
    if vault_path.exists() and (vault_path / ".git").exists():
        console.print(f"[yellow]Vault already exists at {vault_path}[/yellow]")
        if not click.confirm("Reinitialize?"):
            return
    
    normalized_repo = normalize_remote_url(repo) if repo else None

    vault = Vault(vault_path)
    vault.initialize(remote_url=normalized_repo)
    
    if branch:
        effective_branch = branch
    elif normalized_repo:
        effective_branch = vault.get_remote_default_branch(remote_name=remote) or "main"
    else:
        effective_branch = "main"

    current_branch = vault.get_current_branch()
    if vault.repo and current_branch != effective_branch:
        try:
            if vault.has_local_branch(effective_branch):
                vault.repo.git.checkout(effective_branch)
            elif current_branch == "master" and effective_branch == "main":
                vault.repo.git.branch("-M", "main")
        except Exception:
            pass

    effective_repo_url = normalized_repo or vault.get_remote_url(remote)
    update_vault_settings(
        path=str(vault_path),
        repo_url=effective_repo_url,
        remote_name=remote,
        branch=effective_branch,
        auto_push=auto_push
    )
    
    console.print(f"[green]+[/green] Initialized vault at {vault_path}")
    if repo and normalized_repo and normalized_repo != repo.strip():
        console.print(f"[yellow]![/yellow] Converted GitHub remote to SSH: {normalized_repo}")
    if effective_repo_url:
        console.print(f"[green]+[/green] Remote configured: {remote} -> {effective_repo_url}")
    console.print(f"[green]+[/green] Auto-push: {'enabled' if auto_push else 'disabled'}")
    
    # Setup global junctions
    if setup_global:
        console.print("\n[blue]Setting up global junctions...[/blue]")
        config = Config(vault_path)
        setup_global_junctions(vault, config)


@vault.command(name='list')
def vault_list():
    """List all skills in the vault."""
    vault = get_vault()
    
    if not vault.repo:
        console.print("[red]Vault not initialized. Run 'skill-vault vault init' first.[/red]")
        return
    
    global_skills = vault.list_global_skills()
    local_skills = vault.list_local_skills()
    
    if global_skills:
        table = Table(title="Global Skills")
        table.add_column("Name", style="cyan")
        table.add_column("Version", style="green")
        table.add_column("Description")
        
        for skill in global_skills:
            table.add_row(skill.name, skill.version, skill.description)
        
        console.print(table)
    
    if local_skills:
        table = Table(title="Local Skills")
        table.add_column("Name", style="cyan")
        table.add_column("Version", style="green")
        table.add_column("Description")
        
        for skill in local_skills:
            table.add_row(skill.name, skill.version, skill.description)
        
        console.print(table)


@vault.command(name='show')
@click.argument('skill_name')
def vault_show(skill_name):
    """Show details of a skill."""
    vault = get_vault()
    skill = vault.get_skill(skill_name)
    
    if not skill:
        console.print(f"[red]Skill not found: {skill_name}[/red]")
        return
    
    console.print(Panel.fit(
        f"[bold cyan]{skill.name}[/bold cyan] v{skill.version}\n"
        f"[dim]{skill.description}[/dim]\n\n"
        f"Author: {skill.author}\n"
        f"Tags: {', '.join(skill.tags) or 'None'}\n"
        f"Frameworks: {', '.join(skill.frameworks) or 'All'}\n"
        f"Type: {'Local' if skill.is_local else 'Global'}"
    ))


@vault.command(name='setup-global')
def vault_setup_global():
    """Setup global junctions for all skills in framework directories."""
    vault = get_vault()
    
    if not vault.repo:
        console.print("[red]Vault not initialized. Run 'skill-vault vault init' first.[/red]")
        return
    
    config = Config(get_vault_path())
    setup_global_junctions(vault, config)


@vault.command(name='sync-global')
def vault_sync_global():
    """Synchronize global junctions - add new and remove obsolete."""
    vault = get_vault()
    
    if not vault.repo:
        console.print("[red]Vault not initialized. Run 'skill-vault vault init' first.[/red]")
        return
    
    config = Config(get_vault_path())
    sync_global_junctions(vault, config)


@vault.group(name='repo')
def vault_repo():
    """Manage remote repository integration for the global vault."""
    pass


@vault_repo.command(name='status')
def vault_repo_status():
    """Show Git/remote status for the global vault."""
    vault = get_vault()
    if not ensure_vault_repo_initialized(vault):
        return

    settings = get_vault_settings()
    configured_remote = settings.get("remote_name", "origin")

    table = Table(title="Vault Repository Status")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Vault Path", str(vault.path))
    table.add_row("Current Branch", vault.get_current_branch() or "(detached)")
    table.add_row("Configured Branch", str(settings.get("branch") or "(auto)"))
    table.add_row("Configured Remote", configured_remote)
    table.add_row("Configured Repo URL", str(settings.get("repo_url") or "None"))
    table.add_row("Auto Push", "enabled" if get_auto_push_enabled() else "disabled")
    table.add_row("Working Tree", "clean" if vault.is_clean() else "dirty")
    console.print(table)

    remotes = vault.list_remotes()
    if remotes:
        remote_table = Table(title="Git Remotes")
        remote_table.add_column("Name", style="cyan")
        remote_table.add_column("URL", style="green")
        for name, url in remotes.items():
            remote_table.add_row(name, url or "(no url)")
        console.print(remote_table)
    else:
        console.print("[yellow]No remotes configured. Use 'skill-vault vault repo connect --url ...'[/yellow]")


@vault_repo.command(name='connect')
@click.option(
    '--url',
    required=True,
    help='Remote repository URL (SSH). GitHub HTTPS URLs are auto-converted.'
)
@click.option('--remote', default=None, help='Remote name (default: configured remote)')
@click.option('--branch', default=None, help='Branch to track (default: configured/current)')
@click.option('--push', is_flag=True, help='Push branch and tags immediately after connecting')
@click.option(
    '--set-auto-push',
    type=click.Choice(['on', 'off', 'keep']),
    default='keep',
    show_default=True,
    help='Update auto-push setting'
)
def vault_repo_connect(url, remote, branch, push, set_auto_push):
    """Connect vault repository to a remote."""
    vault = get_vault()
    if not ensure_vault_repo_initialized(vault):
        return

    normalized_url = normalize_remote_url(url)
    remote_name = get_effective_remote_name(remote)
    vault.set_remote(normalized_url, remote_name=remote_name, overwrite=True)

    effective_branch = get_effective_branch(vault, remote_name=remote_name, override=branch)
    auto_push = get_auto_push_enabled()
    if set_auto_push == 'on':
        auto_push = True
    elif set_auto_push == 'off':
        auto_push = False

    update_vault_settings(
        repo_url=normalized_url,
        remote_name=remote_name,
        branch=effective_branch,
        auto_push=auto_push
    )

    if normalized_url != url.strip():
        console.print(f"[yellow]![/yellow] Converted GitHub remote to SSH: {normalized_url}")
    console.print(f"[green]+[/green] Connected remote: {remote_name} -> {normalized_url}")
    console.print(f"[green]+[/green] Branch: {effective_branch}")
    console.print(f"[green]+[/green] Auto-push: {'enabled' if auto_push else 'disabled'}")

    if push:
        try:
            pushed_branch = vault.push(remote_name=remote_name, branch=effective_branch)
            console.print(f"[green]+[/green] Pushed {remote_name}/{pushed_branch} (including tags)")
        except Exception as e:
            console.print(f"[red]Failed to push: {e}[/red]")


@vault_repo.command(name='disconnect')
@click.option('--remote', default=None, help='Remote name to disconnect (default: configured remote)')
@click.option(
    '--keep-auto-push',
    is_flag=True,
    help='Keep auto-push enabled even when no remotes remain'
)
def vault_repo_disconnect(remote, keep_auto_push):
    """Disconnect a remote from the vault repository."""
    vault = get_vault()
    if not ensure_vault_repo_initialized(vault):
        return

    remote_name = get_effective_remote_name(remote)
    removed = vault.remove_remote(remote_name=remote_name)
    if not removed:
        console.print(f"[yellow]Remote '{remote_name}' is not configured.[/yellow]")
        return

    console.print(f"[green]+[/green] Disconnected remote: {remote_name}")

    settings = get_vault_settings()
    configured_remote = settings.get("remote_name", "origin")
    if remote_name != configured_remote:
        return

    remaining_remotes = vault.list_remotes()
    if remaining_remotes:
        next_remote, next_url = next(iter(remaining_remotes.items()))
        update_vault_settings(remote_name=next_remote, repo_url=next_url)
        console.print(
            f"[yellow]![/yellow] Switched configured remote to {next_remote} -> {next_url or '(no url)'}"
        )
        return

    clear_vault_settings("repo_url", "branch")
    if keep_auto_push:
        console.print(
            "[yellow]![/yellow] No remotes remain. Auto-push stayed enabled due to --keep-auto-push."
        )
    else:
        update_vault_settings(auto_push=False)
        console.print("[yellow]![/yellow] Auto-push disabled because no remote is configured.")


@vault_repo.command(name='pull')
@click.option('--remote', default=None, help='Remote name (default: configured remote)')
@click.option('--branch', default=None, help='Branch to pull (default: configured/current)')
@click.option(
    '--sync-global/--no-sync-global',
    default=True,
    show_default=True,
    help='Sync global junctions after pulling'
)
def vault_repo_pull(remote, branch, sync_global):
    """Pull latest changes from configured remote."""
    vault = get_vault()
    if not ensure_vault_repo_initialized(vault):
        return

    remote_name = get_effective_remote_name(remote)
    effective_branch = branch or get_vault_branch()
    try:
        pull_vault_remote(
            vault,
            remote_name=remote_name,
            branch=effective_branch,
            sync_global=sync_global
        )
    except Exception as e:
        console.print(f"[red]Failed to pull: {e}[/red]")


@vault_repo.command(name='create')
@click.option('--name', required=True, help='GitHub repository name')
@click.option('--owner', default=None, help='GitHub owner (user/org). Omit to use authenticated user')
@click.option('--remote', default=None, help='Remote name (default: configured remote)')
@click.option('--private/--public', 'is_private', default=True, show_default=True, help='Repository visibility')
@click.option('--description', default=None, help='Optional repository description')
@click.option('--push/--no-push', default=True, show_default=True, help='Push local vault after creating repo')
@click.option(
    '--set-auto-push',
    type=click.Choice(['on', 'off', 'keep']),
    default='keep',
    show_default=True,
    help='Update auto-push setting'
)
def vault_repo_create(name, owner, remote, is_private, description, push, set_auto_push):
    """Create a GitHub repository with GitHub CLI and connect this vault."""
    vault = get_vault()
    if not ensure_vault_repo_initialized(vault):
        return

    if shutil.which("gh") is None:
        console.print("[red]GitHub CLI 'gh' not found. Install it and run 'gh auth login' first.[/red]")
        return

    remote_name = get_effective_remote_name(remote)
    repo_slug = f"{owner}/{name}" if owner else name

    command = [
        "gh", "repo", "create", repo_slug,
        "--source", str(vault.path),
        "--remote", remote_name,
    ]
    command.append("--private" if is_private else "--public")
    if description:
        command.extend(["--description", description])
    if push:
        command.append("--push")

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        error_output = (result.stderr or result.stdout or "").strip()
        console.print(f"[red]Failed to create GitHub repository: {error_output}[/red]")
        return

    repo_url = vault.get_remote_url(remote_name)
    repo_url_converted = False
    if repo_url:
        normalized_repo_url = normalize_remote_url(repo_url)
        if normalized_repo_url != repo_url:
            vault.set_remote(normalized_repo_url, remote_name=remote_name, overwrite=True)
            repo_url_converted = True
        repo_url = normalized_repo_url

    effective_branch = get_effective_branch(vault, remote_name=remote_name)
    auto_push = get_auto_push_enabled()
    if set_auto_push == 'on':
        auto_push = True
    elif set_auto_push == 'off':
        auto_push = False

    update_vault_settings(
        repo_url=repo_url,
        remote_name=remote_name,
        branch=effective_branch,
        auto_push=auto_push
    )

    console.print(f"[green]+[/green] Created GitHub repository: {repo_slug}")
    if repo_url_converted:
        console.print(f"[yellow]![/yellow] Converted GitHub remote to SSH: {repo_url}")
    if repo_url:
        console.print(f"[green]+[/green] Remote URL: {repo_url}")
    console.print(f"[green]+[/green] Branch: {effective_branch}")
    console.print(f"[green]+[/green] Auto-push: {'enabled' if auto_push else 'disabled'}")

    if push:
        try:
            pushed_branch = vault.push(
                remote_name=remote_name,
                branch=effective_branch,
                set_upstream=False
            )
            console.print(f"[green]+[/green] Pushed {remote_name}/{pushed_branch} (including tags)")
        except Exception as e:
            console.print(f"[yellow]Warning: Repository created but final push failed: {e}[/yellow]")


@vault_repo.command(name='auto-push')
@click.argument('state', type=click.Choice(['on', 'off']))
def vault_repo_auto_push(state):
    """Enable or disable automatic pushes after vault commits."""
    enabled = state == 'on'
    update_vault_settings(auto_push=enabled)
    console.print(f"[green]+[/green] Auto-push {'enabled' if enabled else 'disabled'}")


@vault.command(name='create')
@click.argument('skill_name', required=False)
@click.option('--local', 'is_local', is_flag=True, help='Add as local skill instead of global')
@click.option('--global', 'is_global', is_flag=True, help='Add as global skill (default)')
@click.option('--message', '-m', default=None, help='Commit message')
@click.option('--push', is_flag=True, help='Push to remote after commit')
def vault_create(skill_name, is_local, is_global, message, push):
    """Add a new skill from the project to the vault.
    
    Discovers skills in the current project that are not yet in the vault
    and allows you to promote them. If no skill name is provided, shows
    an interactive selection of discoverable skills.
    
    Examples:
        skill-vault vault create              # Interactive selection
        skill-vault vault create my-skill     # Add specific skill as global
        skill-vault vault create my-skill --local  # Add as local skill
    """
    vault = get_vault()
    
    if not vault.repo:
        console.print("[red]Vault not initialized. Run 'skill-vault vault init' first.[/red]")
        return
    
    proj = get_project()
    if not proj.is_initialized():
        console.print("[red]Project not initialized. Run 'skill-vault project init' first.[/red]")
        return
    
    proj.load()
    config = Config(get_vault_path())
    sync = SkillSync(vault, proj, config)
    
    # Discover skills in project
    discovered = sync.discover_project_skills()
    
    if not discovered:
        console.print("[yellow]No new skills found in project.[/yellow]")
        console.print("[dim]Skills must have a SKILL.md file and not already exist in the vault.[/dim]")
        return
    
    # Filter valid skills (no parsing errors)
    valid_skills = [s for s in discovered if s["skill"] is not None]
    invalid_skills = [s for s in discovered if s["error"]]
    
    if invalid_skills:
        console.print("[yellow]Some skills have parsing errors:[/yellow]")
        for s in invalid_skills:
            console.print(f"  [red]x[/red] {s['name']}: {s['error']}")
        console.print()
    
    if not valid_skills:
        console.print("[red]No valid skills to promote.[/red]")
        return
    
    # Select skill
    if skill_name:
        selected = next((s for s in valid_skills if s["name"] == skill_name), None)
        if not selected:
            console.print(f"[red]Skill not found or invalid: {skill_name}[/red]")
            console.print("[dim]Available skills: " + ", ".join(s["name"] for s in valid_skills))
            return
    else:
        # Interactive selection
        selected = interactive.select_skill_to_promote(valid_skills)
        if not selected:
            return
    
    # Determine global/local
    if is_local:
        is_global_skill = False
    elif is_global:
        is_global_skill = True
    else:
        # Ask interactively
        is_global_skill = interactive.ask_global_or_local(selected["name"])

    auto_push_enabled = push or get_auto_push_enabled()
    remote_name = get_effective_remote_name()
    branch = get_effective_branch(vault, remote_name=remote_name)
    
    # Promote the skill
    sync.promote_skill_to_vault(
        skill_name=selected["name"],
        is_global=is_global_skill,
        message=message,
        auto_push=auto_push_enabled,
        remote_name=remote_name,
        branch=branch
    )


# Project Commands
@cli.group()
def project():
    """Manage Skill Vault in the current project."""
    pass


@project.command(name='init')
@click.option('--name', '-n', default=None, help='Project name (default: directory name)')
@click.option('--framework', '-f', 'frameworks', multiple=True, help='Frameworks to enable (can be used multiple times)')
def project_init(name, frameworks):
    """Initialize Skill Vault for the current project."""
    proj = get_project()
    
    if proj.is_initialized():
        console.print("[yellow]Project already initialized[/yellow]")
        return
    
    # Auto-detect frameworks if not specified
    config = Config(get_vault_path())
    
    # Convert frameworks tuple to list
    framework_list = list(frameworks) if frameworks else []
    
    if not framework_list:
        detected = config.detect_frameworks(Path.cwd())
        if detected:
            console.print(f"[blue]Detected frameworks: {', '.join(detected)}[/blue]")
            framework_list = detected
        else:
            # Show interactive selection
            available = list(config.get_all_frameworks().keys())
            selected = interactive.select_frameworks_interactive(available)
            framework_list = selected
    
    if not framework_list:
        console.print("[red]No frameworks selected. Aborting.[/red]")
        return
    
    project_name = name or Path.cwd().name
    proj.initialize(project_name, get_vault_path(), framework_list)
    
    console.print(f"[green]+[/green] Initialized Skill Vault for project: {project_name}")
    console.print(f"[green]+[/green] Enabled frameworks: {', '.join(framework_list)}")
    
    # Set up framework junctions
    vault = get_vault()
    sync = SkillSync(vault, proj, config)
    sync.ensure_framework_junctions(framework_list)


@project.command(name='status')
def project_status():
    """Show project status."""
    proj = get_project()
    
    if not proj.is_initialized():
        console.print("[red]Project not initialized. Run 'skill-vault project init' first.[/red]")
        return
    
    proj.load()
    cfg = proj.config
    
    if not cfg:
        console.print("[red]Failed to load project configuration[/red]")
        return
    
    console.print(Panel.fit(
        f"[bold]Project:[/bold] {cfg.name}\n"
        f"[bold]Path:[/bold] {cfg.path}\n"
        f"[bold]Frameworks:[/bold] {', '.join(cfg.enabled_frameworks)}\n"
        f"[bold]Installed Skills:[/bold] {len(cfg.installed_skills)}"
    ))
    
    if cfg.installed_skills:
        table = Table()
        table.add_column("Skill", style="cyan")
        table.add_column("Version", style="green")
        table.add_column("Frameworks")
        
        for skill_name, info in cfg.installed_skills.items():
            table.add_row(
                skill_name,
                info.get('version', 'unknown'),
                ', '.join(info.get('frameworks', []))
            )
        
        console.print(table)


# Skill Commands
@cli.group()
def skills():
    """Manage skills in the current project."""
    pass


@skills.command(name='list')
def skills_list():
    """List all available skills and installed status."""
    vault = get_vault()
    proj = get_project()
    
    if not vault.repo:
        console.print("[red]Vault not initialized.[/red]")
        return
    
    all_skills = vault.list_global_skills() + vault.list_local_skills()
    
    if proj.is_initialized():
        proj.load()
        installed = proj.get_installed_skills()
    else:
        installed = {}
    
    table = Table(title="Available Skills")
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Status")
    table.add_column("Description")
    
    for skill in sorted(all_skills, key=lambda s: s.name):
        if skill.name in installed:
            status = f"[green]installed ({installed[skill.name]['version']})[/green]"
        else:
            status = "[dim]not installed[/dim]"
        
        table.add_row(skill.name, skill.version, status, skill.description)
    
    console.print(table)


@skills.command(name='add')
@click.argument('skill_names', nargs=-1)
@click.option('--interactive', '-i', 'use_interactive', is_flag=True, help='Force interactive mode even with skill names')
@click.option('--framework', '-f', 'frameworks', multiple=True, help='Frameworks to install for')
@click.option('--force', is_flag=True, help='Force reinstall if already installed')
@click.option('--global', 'show_global', is_flag=True, help='Show global skills instead of local skills')
def skills_add(skill_names, use_interactive, frameworks, force, show_global):
    """Add skills to the project.
    
    By default, shows only local skills. Use --global to show global skills.
    
    If no skill names are provided, opens an interactive multi-select menu
    where you can navigate with arrow keys, select with spacebar, and confirm with enter.
    """
    proj = get_project()
    
    if not proj.is_initialized():
        console.print("[red]Project not initialized. Run 'skill-vault project init' first.[/red]")
        return
    
    proj.load()
    vault = get_vault()
    config = Config(get_vault_path())
    sync = SkillSync(vault, proj, config)
    auto_push = get_auto_push_enabled()
    remote_name = get_effective_remote_name()
    branch = get_effective_branch(vault, remote_name=remote_name)
    
    if use_interactive or not skill_names:
        installed = list(proj.get_installed_skills().keys())
        skill_names = interactive.select_skills_interactive(vault, list(skill_names), show_global=show_global, installed_skills=installed)
    
    if not skill_names:
        console.print("[yellow]No skills selected[/yellow]")
        return
    
    # Get frameworks
    if frameworks:
        framework_list = list(frameworks)
    elif proj.config and hasattr(proj.config, 'enabled_frameworks'):
        framework_list = proj.config.enabled_frameworks
    else:
        console.print("[red]No frameworks configured[/red]")
        return
    
    # Install each skill
    for skill_name in skill_names:
        sync.install_skill(
            skill_name,
            framework_list,
            force=force,
            auto_push=auto_push,
            remote_name=remote_name,
            branch=branch
        )


@skills.command(name='remove')
@click.argument('skill_names', nargs=-1)
@click.option('--interactive', '-i', 'use_interactive', is_flag=True, help='Force interactive mode even with skill names')
@click.option('--force', is_flag=True, help='Force remove without confirmation for modified skills')
def skills_remove(skill_names, use_interactive, force):
    """Remove skills from the project.
    
    If no skill names are provided, opens an interactive multi-select menu
    where you can navigate with arrow keys, select skills with spacebar,
    and confirm with enter. Modified skills are marked with a warning.
    """
    proj = get_project()
    
    if not proj.is_initialized():
        console.print("[red]Project not initialized.[/red]")
        return
    
    proj.load()
    vault = get_vault()
    config = Config(get_vault_path())
    sync = SkillSync(vault, proj, config)
    auto_push = get_auto_push_enabled()
    remote_name = get_effective_remote_name()
    branch = get_effective_branch(vault, remote_name=remote_name)
    
    # Get installed skills
    installed = proj.get_installed_skills()
    
    if not installed:
        console.print("[yellow]No skills installed in project[/yellow]")
        return
    
    # Check for modifications on all installed skills
    modified_skills = []
    modification_info = {}
    
    for skill_name in installed.keys():
        info = sync.check_skill_modifications(skill_name)
        if info.get("has_changes", False):
            modified_skills.append(skill_name)
            modification_info[skill_name] = info
    
    # Get skill names to remove
    if use_interactive or not skill_names:
        # Build Skill objects for installed skills
        from .skills import Skill
        installed_skill_objects = []
        for skill_name, info in installed.items():
            skill = vault.get_skill(skill_name)
            if skill:
                installed_skill_objects.append(skill)
            else:
                # Create minimal Skill object for skills not in vault
                installed_skill_objects.append(Skill(
                    name=skill_name,
                    version=info.get("version", "unknown"),
                    description="Installed skill (not in vault)",
                    author="Unknown",
                    tags=[],
                    frameworks=info.get("frameworks", []),
                    path=None,
                    is_local=info.get("is_local", False)
                ))
        
        skill_names = interactive.select_skills_to_remove(
            installed_skill_objects,
            modified_skills,
            list(skill_names) if skill_names else []
        )
    
    if not skill_names:
        console.print("[yellow]No skills selected for removal[/yellow]")
        return
    
    # Remove each skill
    removed_count = 0
    for skill_name in skill_names:
        # Check if skill is modified and needs confirmation
        if skill_name in modified_skills and not force:
            if not interactive.confirm_remove_modified(skill_name, modification_info[skill_name]):
                console.print(f"[yellow]Skipped removal of '{skill_name}'[/yellow]")
                continue
        
        if sync.remove_skill(
            skill_name,
            auto_push=auto_push,
            remote_name=remote_name,
            branch=branch
        ):
            removed_count += 1
    
    if removed_count > 0:
        console.print(f"\n[green]+[/green] Removed {removed_count} skill(s) from project")


@skills.command(name='diff')
@click.argument('skill_name')
def skills_diff(skill_name):
    """Show differences between installed and vault version."""
    proj = get_project()
    
    if not proj.is_initialized():
        console.print("[red]Project not initialized.[/red]")
        return
    
    proj.load()
    vault = get_vault()
    config = Config(get_vault_path())
    sync = SkillSync(vault, proj, config)
    
    sync.show_diff(skill_name)


# Sync Commands
@cli.command(name='sync')
@click.option('--dry-run', is_flag=True, help='Show what would be updated')
@click.option('--all', 'auto_update', is_flag=True, help='Update all without asking')
@click.option('--interactive', '-i', 'use_interactive', is_flag=True, help='Interactive selection')
def sync_cmd(dry_run, auto_update, use_interactive):
    """Synchronize skills with the vault."""
    proj = get_project()
    
    if not proj.is_initialized():
        console.print("[red]Project not initialized.[/red]")
        return
    
    proj.load()
    vault = get_vault()
    config = Config(get_vault_path())
    skill_sync = SkillSync(vault, proj, config)
    auto_push = get_auto_push_enabled()
    remote_name = get_effective_remote_name()
    branch = get_effective_branch(vault, remote_name=remote_name)
    
    updates = skill_sync.get_available_updates()
    
    if not updates:
        console.print("[green]All skills are up to date![/green]")
        return
    
    if dry_run:
        skill_sync.sync_updates(dry_run=True)
        return
    
    if use_interactive or (not auto_update):
        # Show interactive selection
        to_update = interactive.select_updates_interactive(updates)
        for skill_name in to_update:
            skill_sync.install_skill(
                skill_name,
                force=True,
                auto_push=auto_push,
                remote_name=remote_name,
                branch=branch
            )
    else:
        # Update all
        skill_sync.sync_updates(
            auto=True,
            auto_push=auto_push,
            remote_name=remote_name,
            branch=branch
        )


@cli.command(name='push')
@click.argument('skill_name')
@click.option('--message', '-m', default=None, help='Commit message')
def push_cmd(skill_name, message):
    """Push a local skill to the vault."""
    proj = get_project()
    
    if not proj.is_initialized():
        console.print("[red]Project not initialized.[/red]")
        return
    
    proj.load()
    vault = get_vault()
    config = Config(get_vault_path())
    sync = SkillSync(vault, proj, config)
    auto_push = get_auto_push_enabled()
    remote_name = get_effective_remote_name()
    branch = get_effective_branch(vault, remote_name=remote_name)
    
    # Get commit message
    if not message:
        message = interactive.ask_commit_message(skill_name)
    
    # Push
    if sync.push_skill(
        skill_name,
        message,
        auto_push=auto_push,
        remote_name=remote_name,
        branch=branch
    ):
        if auto_push:
            return

        if not vault.has_remote(remote_name):
            console.print(
                f"[yellow]No remote '{remote_name}' configured. Use 'skill-vault vault repo connect --url ...'[/yellow]"
            )
            return

        if click.confirm("Push to remote?"):
            try:
                pushed_branch = vault.push(remote_name=remote_name, branch=branch)
                console.print(f"[green]+[/green] Pushed to {remote_name}/{pushed_branch} (including tags)")
            except Exception as e:
                console.print(f"[red]Failed to push to remote: {e}[/red]")


@cli.command(name='pull')
def pull_cmd():
    """Pull latest changes from vault."""
    vault = get_vault()
    
    if not ensure_vault_repo_initialized(vault):
        return

    remote_name = get_effective_remote_name()
    branch = get_vault_branch()

    try:
        pull_vault_remote(vault, remote_name=remote_name, branch=branch, sync_global=True)
    except Exception as e:
        console.print(f"[red]Failed to pull: {e}[/red]")


# Framework Commands
@cli.group()
def framework():
    """Manage frameworks in the project."""
    pass


@framework.command(name='edit')
def framework_edit():
    """Edit enabled frameworks for this project."""
    proj = get_project()

    if not proj.is_initialized():
        console.print("[red]Project not initialized.[/red]")
        return

    proj.load()
    if not proj.config:
        console.print("[red]Failed to load project configuration[/red]")
        return

    config = Config(get_vault_path())
    available = list(config.get_all_frameworks().keys())
    current_frameworks = list(proj.config.enabled_frameworks)

    unknown_frameworks = [fw for fw in current_frameworks if fw not in available]
    if unknown_frameworks:
        console.print(
            f"[yellow]Unknown frameworks in project config: {', '.join(unknown_frameworks)}[/yellow]"
        )
        console.print("[dim]They are not in frameworks.yaml and will be removed when you save.[/dim]")

    selected = interactive.select_frameworks_interactive(
        available_frameworks=available,
        preselected=current_frameworks
    )

    if not selected:
        console.print("[red]No frameworks selected. Aborting.[/red]")
        return

    if selected == current_frameworks:
        console.print("[yellow]No framework changes made[/yellow]")
        return

    proj.update_enabled_frameworks(selected)

    added = [fw for fw in selected if fw not in current_frameworks]
    removed = [fw for fw in current_frameworks if fw not in selected]

    console.print(f"[green]+[/green] Updated enabled frameworks: {', '.join(selected)}")
    if added:
        console.print(f"[green]+[/green] Added: {', '.join(added)}")
    if removed:
        console.print(f"[yellow]-[/yellow] Removed: {', '.join(removed)}")

    # Automatically set up junctions so the new framework sees existing skills
    if added:
        vault = get_vault()
        sync = SkillSync(vault, proj, config)
        console.print("[blue]Setting up framework junctions for new frameworks...[/blue]")
        sync.ensure_framework_junctions(selected)
        console.print("[green]+[/green] Junctions updated — new framework can see all existing skills")

    if proj.config.installed_skills:
        console.print(
            "[dim]Note: Skill records in installed.json still list old frameworks. Run 'skills add <name> --force' to update them.[/dim]"
        )


@framework.command(name='list')
def framework_list():
    """List all available frameworks."""
    config = Config(get_vault_path())
    
    table = Table(title="Available Frameworks")
    table.add_column("Name", style="cyan")
    table.add_column("Local Path")
    table.add_column("Global Path")
    
    for name, fw in config.get_all_frameworks().items():
        table.add_row(name, fw.local_path, fw.global_path)
    
    console.print(table)


@framework.command(name='sync')
def framework_sync():
    """Set up framework skills directories as junctions.
    
    Creates junctions so all frameworks share the same skills directory.
    The first enabled framework's skills directory becomes the primary (real).
    All other frameworks' skills directories become junctions to the primary.
    """
    proj = get_project()
    
    if not proj.is_initialized():
        console.print("[red]Project not initialized.[/red]")
        return
    
    proj.load()
    vault = get_vault()
    config = Config(get_vault_path())
    sync = SkillSync(vault, proj, config)
    
    if not proj.config or not hasattr(proj.config, 'enabled_frameworks'):
        console.print("[red]No frameworks configured in project[/red]")
        return
    
    console.print("[blue]Setting up framework junctions...[/blue]")
    sync.ensure_framework_junctions(proj.config.enabled_frameworks)
    console.print("[green]+[/green] Framework junctions synchronized")


def main():
    """Entry point for the CLI."""
    cli()
