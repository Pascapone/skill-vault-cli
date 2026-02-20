"""Command Line Interface for Skill Vault."""

import os
import sys
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .config import Config
from .vault import Vault, ProjectVault
from .sync import SkillSync
from .skills import SkillParser
from . import interactive
from .global_junctions import setup_global_junctions, sync_global_junctions


console = Console()


def get_vault_path() -> Path:
    """Get the vault path from config or default."""
    config_path = Path.home() / ".skill-vault" / "config.yaml"
    if config_path.exists():
        import yaml
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
            if 'vault' in data and 'path' in data['vault']:
                return Path(data['vault']['path']).expanduser()
    return Path.home() / ".skill-vault"


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
@click.option('--setup-global/--no-setup-global', default=True, help='Setup global junctions after init')
def vault_init(path, repo, setup_global):
    """Initialize the Skill Vault."""
    vault_path = Path(path).expanduser() if path else Path.home() / ".skill-vault"
    
    if vault_path.exists() and (vault_path / ".git").exists():
        console.print(f"[yellow]Vault already exists at {vault_path}[/yellow]")
        if not click.confirm("Reinitialize?"):
            return
    
    vault = Vault(vault_path)
    vault.initialize(remote_url=repo)
    
    # Save vault path to config
    config_file = Path.home() / ".skill-vault" / "config.yaml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    import yaml
    with open(config_file, 'w') as f:
        yaml.dump({'vault': {'path': str(vault_path), 'repo_url': repo}}, f)
    
    console.print(f"[green]+[/green] Initialized vault at {vault_path}")
    
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


@vault.command(name='create')
@click.argument('skill_name', required=False)
@click.option('--local', 'is_local', is_flag=True, help='Add as local skill instead of global')
@click.option('--global', 'is_global', is_flag=True, help='Add as global skill (default)')
@click.option('--message', '-m', default=None, help='Commit message')
def vault_create(skill_name, is_local, is_global, message):
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
    
    # Promote the skill
    sync.promote_skill_to_vault(
        skill_name=selected["name"],
        is_global=is_global_skill,
        message=message
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
        sync.install_skill(skill_name, framework_list, force=force)


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
        
        if sync.remove_skill(skill_name):
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
@click.option('--interactive', '-i', is_flag=True, help='Interactive selection')
def sync_cmd(dry_run, auto_update, interactive):
    """Synchronize skills with the vault."""
    proj = get_project()
    
    if not proj.is_initialized():
        console.print("[red]Project not initialized.[/red]")
        return
    
    proj.load()
    vault = get_vault()
    config = Config(get_vault_path())
    skill_sync = SkillSync(vault, proj, config)
    
    updates = skill_sync.get_available_updates()
    
    if not updates:
        console.print("[green]All skills are up to date![/green]")
        return
    
    if dry_run:
        skill_sync.sync_updates(dry_run=True)
        return
    
    if interactive or (not auto_update):
        # Show interactive selection
        to_update = interactive.select_updates_interactive(updates)
        for skill_name in to_update:
            skill_sync.install_skill(skill_name, force=True)
    else:
        # Update all
        skill_sync.sync_updates(auto=True)


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
    
    # Get commit message
    if not message:
        message = interactive.ask_commit_message(skill_name)
    
    # Push
    if sync.push_skill(skill_name, message):
        # Ask if push to remote
        if click.confirm("Push to remote?"):
            vault.push()
            console.print("[green]+[/green] Pushed to remote")


@cli.command(name='pull')
def pull_cmd():
    """Pull latest changes from vault."""
    vault = get_vault()
    
    if not vault.repo:
        console.print("[red]Vault not initialized.[/red]")
        return
    
    try:
        vault.pull()
        console.print("[green]+[/green] Pulled latest changes from vault")
        
        # Re-sync global junctions after pull
        console.print("[blue]Updating global junctions...[/blue]")
        config = Config(get_vault_path())
        sync_global_junctions(vault, config)
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

    if proj.config.installed_skills:
        console.print(
            "[dim]Note: Installed skills keep their current framework assignments until reinstalled or synced manually.[/dim]"
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
