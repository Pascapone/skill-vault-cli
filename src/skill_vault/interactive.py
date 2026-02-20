"""Interactive skill selection using InquirerPy for modern CLI experience."""

from typing import List, Optional, Tuple
from rich.console import Console
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.separator import Separator

from .skills import Skill
from .vault import Vault


console = Console()


def select_skills_interactive(
    vault: Vault,
    preselected: Optional[List[str]] = None,
    show_global: bool = False,
    installed_skills: Optional[List[str]] = None
) -> List[str]:
    """Show interactive multi-select for skills using modern checkbox UI.
    
    Features:
    - Navigate with arrow keys (up/down)
    - Select/deselect with spacebar
    - Visual feedback with checked/unchecked indicators
    - Confirm with Enter
    
    Args:
        vault: The vault instance
        preselected: List of skill names to preselect
        show_global: If True, show global skills; if False (default), show only local skills
        installed_skills: List of already installed skill names (will be hidden)
        
    Returns:
        List of selected skill names
    """
    preselected = preselected or []
    installed_skills = installed_skills or []
    
    global_skills = vault.list_global_skills()
    local_skills = vault.list_local_skills()
    
    if show_global:
        all_skills = global_skills + local_skills
    else:
        all_skills = local_skills
    
    all_skills = [s for s in all_skills if s.name not in installed_skills]
    
    if not all_skills:
        if installed_skills:
            console.print("[green]All skills already installed[/green]")
        elif show_global:
            console.print("[yellow]No skills available in vault[/yellow]")
        else:
            console.print("[yellow]No local skills available. Use --global to see global skills.[/yellow]")
        return []
    
    all_skills.sort(key=lambda s: s.name)
    
    choices = []
    
    if show_global:
        available_global = [s for s in global_skills if s.name not in installed_skills]
        if available_global:
            choices.append(Separator("=== Global Skills ==="))
            for skill in sorted(available_global, key=lambda s: s.name):
                is_selected = skill.name in preselected
                choices.append(Choice(
                    name=f"{skill.name} - {skill.description[:50]}{'...' if len(skill.description) > 50 else ''}",
                    value=skill.name,
                    enabled=is_selected
                ))
    
    available_local = [s for s in local_skills if s.name not in installed_skills]
    if available_local:
        if show_global:
            choices.append(Separator("=== Local Skills ==="))
        for skill in sorted(available_local, key=lambda s: s.name):
            is_selected = skill.name in preselected
            choices.append(Choice(
                name=f"{skill.name} [local] - {skill.description[:50]}{'...' if len(skill.description) > 50 else ''}",
                value=skill.name,
                enabled=is_selected
            ))
    
    console.print("\n[bold cyan]Select skills to add to your project:[/bold cyan]")
    console.print("[dim]Use arrow keys to navigate, space to select/deselect, enter to confirm[/dim]\n")
    
    try:
        selected = inquirer.checkbox(
            message="Select skills:",
            choices=choices,
            instruction="(Use space to toggle, enter to confirm)",
            cycle=True,
            transformer=lambda result: f"{len(result)} skill(s) selected",
            validate=lambda result: len(result) > 0 or True,
        ).execute()
        
        return selected if selected else []
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Selection cancelled[/yellow]")
        return []


def select_frameworks_interactive(
    available_frameworks: List[str],
    preselected: Optional[List[str]] = None
) -> List[str]:
    """Show interactive multi-select for frameworks using modern checkbox UI.
    
    Args:
        available_frameworks: List of available framework names
        preselected: List of framework names to preselect
        
    Returns:
        List of selected framework names
    """
    preselected = preselected or []
    
    if not available_frameworks:
        return []
    
    # Create choices
    choices = [
        Choice(
            name=fw,
            value=fw,
            enabled=fw in preselected
        )
        for fw in available_frameworks
    ]
    
    console.print("\n[bold cyan]Select frameworks for your project:[/bold cyan]")
    console.print("[dim]Use arrow keys to navigate, space to select/deselect, enter to confirm[/dim]\n")
    
    try:
        selected = inquirer.checkbox(
            message="Select frameworks:",
            choices=choices,
            instruction="(Use space to toggle, enter to confirm)",
            cycle=True,
            transformer=lambda result: f"{len(result)} framework(s) selected",
        ).execute()
        
        return selected if selected else []
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Selection cancelled[/yellow]")
        return preselected


def select_updates_interactive(
    updates: List[Tuple[Skill, str]]
) -> List[str]:
    """Show interactive selection for updates using modern checkbox UI.
    
    Args:
        updates: List of (skill, installed_version) tuples
        
    Returns:
        List of skill names to update
    """
    if not updates:
        return []
    
    # Create choices
    choices = []
    for skill, installed_version in updates:
        choices.append(Choice(
            name=f"{skill.name} ({installed_version} → {skill.version})",
            value=skill.name,
            enabled=True  # Pre-select all updates by default
        ))
    
    console.print("\n[bold cyan]Select updates to apply:[/bold cyan]")
    console.print("[dim]Use arrow keys to navigate, space to select/deselect, enter to confirm[/dim]\n")
    
    try:
        selected = inquirer.checkbox(
            message="Select updates:",
            choices=choices,
            instruction="(Use space to toggle, enter to confirm)",
            cycle=True,
            transformer=lambda result: f"{len(result)} update(s) selected",
        ).execute()
        
        return selected if selected else []
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Update cancelled[/yellow]")
        return []


def confirm_push(skill_name: str, diff: str = "") -> bool:
    """Confirm pushing a skill to vault.
    
    Args:
        skill_name: Name of the skill
        diff: Git diff to show
        
    Returns:
        True if user confirms
    """
    if diff:
        console.print(f"\n[blue]Changes for {skill_name}:[/blue]")
        console.print(diff)
    
    try:
        return inquirer.confirm(
            message=f"Push skill '{skill_name}' to vault?",
            default=False,
        ).execute()
    except KeyboardInterrupt:
        return False


def ask_commit_message(skill_name: str) -> str:
    """Ask for commit message.
    
    Args:
        skill_name: Name of the skill
        
    Returns:
        The commit message
    """
    default_msg = f"Update {skill_name}"
    
    try:
        message = inquirer.text(
            message=f"Commit message for {skill_name}:",
            default=default_msg,
        ).execute()
        
        return message if message else default_msg
        
    except KeyboardInterrupt:
        return default_msg


def select_skills_to_remove(
    installed_skills: List[Skill],
    modified_skills: List[str],
    preselected: Optional[List[str]] = None
) -> List[str]:
    """Show interactive multi-select for removing skills with warning indicators.
    
    Features:
    - Navigate with arrow keys (up/down)
    - Select/deselect with spacebar
    - Red indicators for skills marked for deletion
    - Warning for modified skills
    - Confirm with Enter
    
    Args:
        installed_skills: List of installed Skill objects
        modified_skills: List of skill names that have been modified
        preselected: List of skill names to preselect
        
    Returns:
        List of selected skill names to remove
    """
    preselected = preselected or []
    
    if not installed_skills:
        console.print("[yellow]No skills installed in project[/yellow]")
        return []
    
    # Sort skills alphabetically
    installed_skills.sort(key=lambda s: s.name)
    
    # Create choices for InquirerPy
    choices = []
    
    for skill in installed_skills:
        is_selected = skill.name in preselected
        is_modified = skill.name in modified_skills
        
        # Build the display name with warning indicator (plain text for InquirerPy)
        if is_modified:
            name = f"⚠ {skill.name} [MODIFIED] - {skill.description[:40]}{'...' if len(skill.description) > 40 else ''}"
        else:
            name = f"{skill.name} - {skill.description[:50]}{'...' if len(skill.description) > 50 else ''}"
        
        choices.append(Choice(
            name=name,
            value=skill.name,
            enabled=is_selected
        ))
    
    # Show warning if there are modified skills
    if modified_skills:
        console.print("\n[bold red]⚠ Warning:[/bold red] The following skills have been modified:")
        for skill_name in modified_skills:
            console.print(f"  [yellow]• {skill_name}[/yellow]")
        console.print("[dim]Modified skills may contain unsaved changes![/dim]\n")
    
    # Show the interactive checkbox selection
    console.print("\n[bold cyan]Select skills to remove from your project:[/bold cyan]")
    console.print("[dim]Use arrow keys to navigate, space to select/deselect, enter to confirm[/dim]")
    console.print("[dim]⚠ = modified skill (may contain unsaved changes)[/dim]\n")
    
    try:
        selected = inquirer.checkbox(
            message="Select skills to remove:",
            choices=choices,
            instruction="(Use space to toggle, enter to confirm)",
            cycle=True,
            transformer=lambda result: f"{len(result)} skill(s) selected for removal",
            validate=lambda result: len(result) > 0 or True,  # Allow empty selection
        ).execute()
        
        return selected if selected else []
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Removal cancelled[/yellow]")
        return []


def confirm_remove_modified(skill_name: str, modification_info: dict) -> bool:
    """Confirm removal of a modified skill with detailed warning.
    
    Args:
        skill_name: Name of the skill
        modification_info: Dictionary with modification details from check_skill_modifications
        
    Returns:
        True if user confirms removal
    """
    console.print(f"\n[bold red]⚠ Warning: Skill '{skill_name}' has been modified![/bold red]")
    console.print("[dim]This skill contains changes that differ from the vault version.[/dim]\n")
    
    # Show modification details
    if modification_info.get("modified_files"):
        console.print("[yellow]Modified files:[/yellow]")
        for f in modification_info["modified_files"]:
            console.print(f"  [red]M[/red] {f}")
    
    if modification_info.get("added_files"):
        console.print("[yellow]Added files (not in vault):[/yellow]")
        for f in modification_info.get("added_files", []):
            console.print(f"  [green]A[/green] {f}")
    
    if modification_info.get("removed_files"):
        console.print("[yellow]Removed files (deleted from project):[/yellow]")
        for f in modification_info.get("removed_files", []):
            console.print(f"  [dim]D[/dim] {f}")
    
    console.print(f"\n[dim]Project path: {modification_info.get('project_path', 'N/A')}[/dim]")
    console.print(f"[dim]Vault path: {modification_info.get('vault_path', 'N/A')}[/dim]\n")
    
    try:
        return inquirer.confirm(
            message=f"Really remove modified skill '{skill_name}'?",
            default=False,
        ).execute()
    except KeyboardInterrupt:
        return False


def select_skill_to_promote(discovered_skills: List[dict]) -> Optional[dict]:
    """Show interactive selection for promoting a skill to the vault.
    
    Args:
        discovered_skills: List of discovered skill dicts from discover_project_skills
        
    Returns:
        Selected skill dict or None if cancelled
    """
    if not discovered_skills:
        console.print("[yellow]No skills to promote[/yellow]")
        return None
    
    # Create choices
    choices = []
    for skill_info in discovered_skills:
        skill = skill_info["skill"]
        if skill:
            frameworks = ", ".join(skill_info["frameworks"])
            name = f"{skill.name} - {skill.description[:40]}{'...' if len(skill.description) > 40 else ''} [{frameworks}]"
            choices.append(Choice(
                name=name,
                value=skill_info,
            ))
    
    console.print("\n[bold cyan]Select a skill to promote to the vault:[/bold cyan]")
    console.print("[dim]Use arrow keys to navigate, enter to select[/dim]\n")
    
    try:
        selected = inquirer.select(
            message="Select skill:",
            choices=choices,
            cycle=True,
        ).execute()
        
        return selected if selected else None
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Promotion cancelled[/yellow]")
        return None


def ask_global_or_local(skill_name: str) -> bool:
    """Ask whether to add skill as global or local.
    
    Args:
        skill_name: Name of the skill
        
    Returns:
        True for global, False for local
    """
    console.print(f"\n[bold cyan]Add '{skill_name}' as:[/bold cyan]")
    
    choices = [
        Choice(name="Global skill (available to all projects)", value=True),
        Choice(name="Local skill (private/template)", value=False),
    ]
    
    try:
        return inquirer.select(
            message="Select type:",
            choices=choices,
            default=True,
            cycle=True,
        ).execute()
        
    except KeyboardInterrupt:
        return True  # Default to global
