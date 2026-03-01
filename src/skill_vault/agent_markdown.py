"""Agent Markdown Symlink Setup for Skill Vault."""

import os
import subprocess
from pathlib import Path
from rich.console import Console

from .config import Config

console = Console()

def elevate_command(cmd: str) -> None:
    """Run a command in an elevated cmd.exe prompt (requires UAC)."""
    # -Wait ensures we wait for the UAC prompt and execution to finish
    ps = f"Start-Process cmd.exe -Verb RunAs -Wait -ArgumentList '/c {cmd}'"
    subprocess.run(['powershell', '-Command', ps])

def ensure_agents_file(path: Path) -> tuple[bool, str]:
    """Ensure source markdown file exists as a regular file."""
    if path.exists():
        if path.is_symlink():
            return False, "is_symlink"
        if path.is_dir():
            return False, "is_directory"
        return True, "already_exists"

    try:
        path.write_text(
            f"# {path.stem}\n\n"
            "Central agent instructions for this repository.\n",
            encoding="utf-8",
        )
        return True, "created"
    except OSError as exc:
        return False, f"error: {exc}"

def get_symlink_target(link_path: Path) -> str | None:
    try:
        return os.readlink(link_path)
    except OSError:
        return None

def setup_agent_markdown_symlinks(project_root: Path, enabled_frameworks: list[str], config: Config) -> None:
    """Setup markdown symlinks for the enabled frameworks."""
    
    # Collect unique agent_markdown files for enabled frameworks
    markdown_files = []
    for fw_name in enabled_frameworks:
        fw = config.get_framework(fw_name)
        if fw and fw.agent_markdown:
            if fw.agent_markdown not in markdown_files:
                markdown_files.append(fw.agent_markdown)
                
    if not markdown_files:
        return
        
    source_file = markdown_files[0]
    source_path = project_root / source_file
    
    # Ensure source file exists
    ok, source_status = ensure_agents_file(source_path)
    if source_status == "created":
        console.print(f"[green]+[/green] Created source markdown: {source_file}")
    elif source_status != "already_exists":
        console.print(f"[yellow]![/yellow] Could not create source markdown {source_file}: {source_status}")
        return
        
    if not ok:
        return

    # Check which symlinks need to be created
    target_files = markdown_files[1:]
    links_to_create = []
    
    for file_name in target_files:
        link_path = project_root / file_name
        
        if link_path.exists() or link_path.is_symlink():
            if link_path.is_symlink():
                current_target = get_symlink_target(link_path)
                if current_target and os.path.normpath(current_target) == os.path.normpath(str(source_path)):
                    # Already correct
                    continue
                console.print(f"[yellow]![/yellow] WARNING: {file_name} is a symlink pointing to wrong target '{current_target}'. Please remove it manually.")
            else:
                console.print(f"[yellow]![/yellow] WARNING: {file_name} already exists as a real file. Please rename/remove it if you want a symlink instead.")
            continue
            
        links_to_create.append((link_path, source_path))

    if not links_to_create:
        return

    # Build cmd chain for mklink
    cmds = []
    for link_path, target_path in links_to_create:
        # mklink link target
        cmd = f'mklink "{link_path}" "{target_path}"'
        cmds.append(cmd)
        
    if cmds:
        console.print("[blue]Creating markdown symlinks (Admin rights required)...[/blue]")
        # Chain commands with &
        full_cmd = " & ".join(cmds)
        
        try:
            elevate_command(full_cmd)
            
            # Verify creation
            for link_path, _ in links_to_create:
                if link_path.exists() and link_path.is_symlink():
                    console.print(f"[green]+[/green] {link_path.name} -> {source_file}")
                else:
                    console.print(f"[red]x[/red] Failed to create symlink: {link_path.name}")
        except Exception as e:
            console.print(f"[red]Error during symlink creation: {e}[/red]")
