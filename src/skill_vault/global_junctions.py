"""Global junction management for system-wide skill access."""

from pathlib import Path
from typing import List
from rich.console import Console

from .config import Config
from .junction import create_junction, remove_junction, is_junction
from .vault import Vault


console = Console()


def setup_global_junctions(vault: Vault, config: Config) -> None:
    """Create junctions for all global skills in framework home directories.
    
    This creates junctions in:
    - ~/.agents/skills/ (for Codex/OpenCode)
    - ~/.claude/skills/ (for Claude)
    - ~/.gemini/antigravity/skills/ (for Antigravity)
    - etc.
    
    Args:
        vault: The vault instance
        config: Configuration with framework paths
    """
    global_skills = vault.list_global_skills()
    
    if not global_skills:
        console.print("[yellow]No global skills found in vault[/yellow]")
        return
    
    console.print(f"[blue]Setting up global junctions for {len(global_skills)} skills...[/blue]")
    
    for framework_name, framework in config.get_all_frameworks().items():
        # Get global path for this framework
        global_path = Path(framework.global_path).expanduser()
        global_path.mkdir(parents=True, exist_ok=True)
        
        console.print(f"\n[dim]Framework: {framework.name}[/dim]")
        console.print(f"[dim]  Path: {global_path}[/dim]")
        
        # Create junction for each global skill
        for skill in global_skills:
            skill_junction_path = global_path / skill.name
            
            # Check if already exists
            if skill_junction_path.exists():
                if is_junction(skill_junction_path):
                    # Check if it points to the right place
                    from .junction import get_junction_target
                    current_target = get_junction_target(skill_junction_path)
                    if current_target == skill.path:
                        console.print(f"  [dim]o {skill.name} (already exists)[/dim]")
                        continue
                    else:
                        # Remove and recreate
                        remove_junction(skill_junction_path)
                else:
                    console.print(f"  [yellow]! {skill.name} exists as folder (not junction)[/yellow]")
                    continue
            
            # Create junction
            try:
                if skill.path:
                    create_junction(skill_junction_path, skill.path)
                    console.print(f"  [green]+ {skill.name}[/green]")
                else:
                    console.print(f"  [yellow]! {skill.name} (no path)[/yellow]")
            except Exception as e:
                console.print(f"  [red]x {skill.name}: {e}[/red]")


def sync_global_junctions(vault: Vault, config: Config) -> None:
    """Synchronize global junctions - add new, remove obsolete.
    
    Args:
        vault: The vault instance
        config: Configuration with framework paths
    """
    global_skills = vault.list_global_skills()
    skill_names = {s.name for s in global_skills}
    
    console.print(f"[blue]Syncing global junctions for {len(global_skills)} skills...[/blue]")
    
    for framework_name, framework in config.get_all_frameworks().items():
        global_path = Path(framework.global_path).expanduser()
        
        if not global_path.exists():
            global_path.mkdir(parents=True, exist_ok=True)
        
        console.print(f"\n[dim]Framework: {framework.name}[/dim]")
        console.print(f"[dim]  Path: {global_path}[/dim]")
        
        # Check for obsolete junctions (skills that no longer exist in vault)
        for item in global_path.iterdir():
            if is_junction(item):
                skill_name = item.name
                if skill_name not in skill_names:
                    try:
                        remove_junction(item)
                        console.print(f"  [yellow]- {skill_name} (removed obsolete)[/yellow]")
                    except Exception as e:
                        console.print(f"  [red]x {skill_name}: {e}[/red]")
        
        # Create missing junctions
        for skill in global_skills:
            skill_junction_path = global_path / skill.name
            
            if skill_junction_path.exists():
                if is_junction(skill_junction_path):
                    from .junction import get_junction_target
                    current_target = get_junction_target(skill_junction_path)
                    if current_target == skill.path:
                        console.print(f"  [dim]o {skill.name} (already exists)[/dim]")
                        continue
                    else:
                        remove_junction(skill_junction_path)
                else:
                    console.print(f"  [yellow]! {skill.name} exists as folder (not junction)[/yellow]")
                    continue
            
            try:
                if skill.path:
                    create_junction(skill_junction_path, skill.path)
                    console.print(f"  [green]+ {skill.name}[/green]")
                else:
                    console.print(f"  [yellow]! {skill.name} (no path)[/yellow]")
            except Exception as e:
                console.print(f"  [red]x {skill.name}: {e}[/red]")


def remove_global_junction(skill_name: str, config: Config) -> None:
    """Remove junctions for a specific skill from all framework directories.
    
    Args:
        skill_name: Name of the skill
        config: Configuration with framework paths
    """
    for framework_name, framework in config.get_all_frameworks().items():
        global_path = Path(framework.global_path).expanduser()
        skill_junction = global_path / skill_name
        
        if skill_junction.exists() and is_junction(skill_junction):
            try:
                remove_junction(skill_junction)
                console.print(f"[green]+[/green] Removed {skill_name} from {framework.name}")
            except Exception as e:
                console.print(f"[red]x[/red] Failed to remove {skill_name} from {framework.name}: {e}")
