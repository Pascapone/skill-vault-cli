"""Synchronization logic for pulling and pushing skills."""

import hashlib
import filecmp
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .vault import Vault, ProjectVault
from .config import Config
from .skills import Skill
from .junction import create_junction, remove_junction, is_junction, get_junction_target


console = Console()


class SyncError(Exception):
    """Raised when synchronization fails."""
    pass


class SkillSync:
    """Handles synchronization between Vault and Project."""
    
    def __init__(self, vault: Vault, project: ProjectVault, config: Config):
        self.vault = vault
        self.project = project
        self.config = config
    
    def check_skill_modifications(self, skill_name: str) -> Dict:
        """Check if installed skill has been modified compared to original installation.
        
        Uses saved file hashes from installation time to detect changes.
        
        Args:
            skill_name: Name of the skill to check
            
        Returns:
            Dictionary with modification info:
            - has_changes: bool - whether there are any changes
            - modified_files: list - list of modified file paths
            - added_files: list - list of files added since installation
            - removed_files: list - list of files removed since installation
        """
        installed_info = self.project.get_installed_skills().get(skill_name)
        if not installed_info:
            return {"has_changes": False, "error": "Skill not installed"}
        
        frameworks = installed_info.get("frameworks", [])
        if not frameworks:
            return {"has_changes": False, "error": "No frameworks found"}
        
        # Get project skill path from first framework
        framework_name = frameworks[0]
        project_skill_path = self.config.get_local_path(
            framework_name,
            self.project.project_path
        ) / skill_name
        
        if not project_skill_path.exists():
            return {"has_changes": False, "error": "Skill not found in project"}
        
        # Get saved hashes from installation
        saved_hashes = installed_info.get("file_hashes", {})
        
        if not saved_hashes:
            # No hashes saved, we can't detect changes reliably
            # Return conservative result - assume no changes
            return {
                "has_changes": False,
                "modified_files": [],
                "added_files": [],
                "removed_files": [],
                "warning": "No hash data available for this skill (installed before tracking)"
            }
        
        # Compare with current hashes
        modified_files = []
        added_files = []
        removed_files = []
        
        # Get current files
        current_files = set()
        for file_path in project_skill_path.rglob("*"):
            if file_path.is_file():
                relative = str(file_path.relative_to(project_skill_path))
                current_files.add(relative)
                current_hash = self._calculate_file_hash(file_path)
                
                if relative in saved_hashes:
                    if saved_hashes[relative] != current_hash:
                        modified_files.append(relative)
                else:
                    added_files.append(relative)
        
        # Check for removed files
        for saved_file in saved_hashes.keys():
            if saved_file not in current_files:
                removed_files.append(saved_file)
        
        return {
            "has_changes": len(modified_files) > 0 or len(added_files) > 0 or len(removed_files) > 0,
            "modified_files": modified_files,
            "added_files": added_files,
            "removed_files": removed_files,
            "project_path": str(project_skill_path)
        }
    
    def get_available_updates(self) -> list[tuple[Skill, str]]:
        """Get list of skills that can be updated.
        
        Returns:
            List of tuples (Skill, installed_version)
        """
        updates = []
        installed = self.project.get_installed_skills()
        
        for skill_name, info in installed.items():
            vault_skill = self.vault.get_skill(skill_name)
            if vault_skill:
                installed_version = info.get("version", "0.0.0")
                if vault_skill.version != installed_version:
                    updates.append((vault_skill, installed_version))
        
        return updates
    
    def show_diff(self, skill_name: str) -> None:
        """Show differences for a skill."""
        skill = self.vault.get_skill(skill_name)
        if not skill:
            console.print(f"[red]Skill not found: {skill_name}[/red]")
            return
        
        installed_version = self.project.get_installed_version(skill_name)
        vault_version = skill.version
        
        table = Table(title=f"Skill: {skill_name}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Installed Version", installed_version)
        table.add_row("Vault Version", vault_version)
        table.add_row("Description", skill.description)
        table.add_row("Author", skill.author)
        table.add_row("Tags", ", ".join(skill.tags))
        
        console.print(table)
        
        # Show git diff if available
        diff = self.vault.get_skill_diff(skill_name)
        if diff:
            console.print(Panel(diff, title="Changes", border_style="blue"))
    
    def install_skill(
        self, 
        skill_name: str, 
        frameworks: Optional[list[str]] = None,
        force: bool = False,
        auto_commit: bool = True
    ) -> bool:
        """Install a skill from vault to project.
        
        Copies skill from vault to the primary framework's skills directory.
        Other frameworks should have their entire skills directory as a junction
        to the primary (set up via ensure_framework_junctions).
        
        Args:
            skill_name: Name of the skill to install
            frameworks: List of frameworks to install for
            force: Force reinstall even if already installed
            auto_commit: Automatically commit to vault
            
        Returns:
            True if successful
        """
        skill = self.vault.get_skill(skill_name)
        if not skill:
            console.print(f"[red]Skill not found in vault: {skill_name}[/red]")
            return False
        
        # Check if already installed
        is_update = self.project.is_skill_installed(skill_name)
        if is_update and not force:
            console.print(f"[yellow]Skill already installed: {skill_name}[/yellow]")
            console.print("Use --force to reinstall")
            return False
        
        # Determine frameworks
        if frameworks is None:
            if self.project.config and hasattr(self.project.config, 'enabled_frameworks'):
                frameworks = self.project.config.enabled_frameworks
            else:
                console.print(f"[red]No frameworks configured[/red]")
                return False
        
        if not frameworks:
            console.print(f"[red]No frameworks specified[/red]")
            return False
        
        # Ensure framework junctions are set up (skills directory level)
        self.ensure_framework_junctions(frameworks)
        
        # Get primary framework path (first framework determines the primary path)
        primary_framework = frameworks[0]
        primary_skills_dir = self.config.get_local_path(
            primary_framework, 
            self.project.project_path
        ).resolve()
        primary_path = primary_skills_dir / skill_name
        
        # Remove existing if present
        if primary_path.exists():
            if is_junction(primary_path):
                remove_junction(primary_path)
            elif primary_path.is_dir():
                shutil.rmtree(primary_path)
            else:
                primary_path.unlink()
        
        # Copy skill from vault to primary framework directory
        if not skill.path or not skill.path.exists():
            console.print(f"[red]x Skill path not found: {skill.path}[/red]")
            return False
        
        try:
            shutil.copytree(skill.path, primary_path)
            
            framework_config = self.config.get_framework(primary_framework)
            if framework_config:
                console.print(
                    f"[green]+[/green] Copied skill to {framework_config.local_path}/{skill_name}"
                )
            else:
                console.print(f"[green]+[/green] Copied skill to {primary_framework}/{skill_name}")
        except Exception as e:
            console.print(f"[red]x Failed to copy skill: {e}[/red]")
            return False
        
        # Record installation with hashes
        self.project.install_skill(skill, frameworks)
        self._save_skill_hashes(skill_name, primary_path)
        
        console.print(f"[green]+[/green] Installed skill: {skill_name} v{skill.version}")
        
        # Auto-commit to vault
        if auto_commit and self.vault.repo:
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Check if this is an update (skill was already installed)
                if is_update:
                    old_version = self.project.get_installed_version(skill_name)
                    if old_version and old_version != skill.version:
                        commit_msg = f"[{timestamp}] Update skill: {skill_name} v{old_version} -> v{skill.version}"
                    else:
                        commit_msg = f"[{timestamp}] Update skill: {skill_name} v{skill.version}"
                else:
                    commit_msg = f"[{timestamp}] Install skill: {skill_name} v{skill.version}"
                
                self.vault.commit_all_changes(commit_msg)
                console.print(f"[dim]-> Auto-committed: {commit_msg}[/dim]")
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to auto-commit: {e}[/yellow]")
        
        return True
    
    def ensure_framework_junctions(self, frameworks: List[str]) -> None:
        """Ensure all framework skills directories are properly junctioned.
        
        The first unique skills directory becomes the primary (real directory).
        All other unique skills directories become junctions to the primary.
        This ensures all frameworks share the same skills automatically.
        
        Args:
            frameworks: List of framework names to set up junctions for
        """
        if not frameworks:
            return
        
        # Group frameworks by their skills directory path
        path_to_frameworks = {}
        for framework_name in frameworks:
            framework_path = self.config.get_local_path(
                framework_name,
                self.project.project_path
            ).resolve()
            if framework_path not in path_to_frameworks:
                path_to_frameworks[framework_path] = []
            path_to_frameworks[framework_path].append(framework_name)
        
        unique_paths = list(path_to_frameworks.keys())
        
        if len(unique_paths) <= 1:
            # All frameworks share the same path, no junctions needed
            return
        
        # First unique path is the primary (source of truth)
        primary_path = unique_paths[0]
        primary_frameworks = path_to_frameworks[primary_path]
        
        # Ensure primary skills directory exists
        if not primary_path.exists():
            primary_path.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]+[/green] Created primary skills directory: {primary_path}")
        
        # Create junctions for other unique paths
        for other_path in unique_paths[1:]:
            other_frameworks = path_to_frameworks[other_path]
            
            if other_path.exists():
                if is_junction(other_path):
                    # Check if it points to the right place
                    current_target = get_junction_target(other_path)
                    if current_target == primary_path:
                        continue  # Already correct
                    else:
                        # Remove and recreate
                        remove_junction(other_path)
                else:
                    # It's a real directory with contents - we need to handle this
                    # Check if it has any non-junction contents
                    has_real_content = False
                    for item in other_path.iterdir():
                        if not is_junction(item):
                            has_real_content = True
                            break
                    
                    if has_real_content:
                        console.print(f"[yellow]! {other_path} exists with real content - skipping junction creation[/yellow]")
                        console.print(f"[dim]  Remove or merge contents manually if needed.[/dim]")
                        continue
                    else:
                        # Only has junctions, safe to remove and recreate
                        for item in list(other_path.iterdir()):
                            if is_junction(item):
                                remove_junction(item)
                        other_path.rmdir()
            
            # Create junction
            try:
                other_path.parent.mkdir(parents=True, exist_ok=True)
                create_junction(other_path, primary_path)
                console.print(f"[green]+[/green] Linked {other_path} -> {primary_path}")
            except Exception as e:
                console.print(f"[red]x Failed to create junction {other_path}: {e}[/red]")
    
    def _save_skill_hashes(self, skill_name: str, skill_path: Path) -> None:
        """Save file hashes for a skill to detect modifications later.
        
        Args:
            skill_name: Name of the skill
            skill_path: Path to the skill directory
        """
        if not skill_path.exists():
            return
        
        hashes = {}
        for file_path in skill_path.rglob("*"):
            if file_path.is_file():
                relative = str(file_path.relative_to(skill_path))
                hashes[relative] = self._calculate_file_hash(file_path)
        
        # Store hashes in project config
        if self.project.config and skill_name in self.project.config.installed_skills:
            self.project.config.installed_skills[skill_name]['file_hashes'] = hashes
            self.project._save_installed()
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            MD5 hash string
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def remove_skill(self, skill_name: str, auto_commit: bool = True) -> bool:
        """Remove a skill from the project.
        
        Args:
            skill_name: Name of the skill to remove
            auto_commit: Automatically commit to vault
            
        Returns:
            True if successful
        """
        if not self.project.is_skill_installed(skill_name):
            console.print(f"[yellow]Skill not installed: {skill_name}[/yellow]")
            return False
        
        installed_info = self.project.get_installed_skills()[skill_name]
        frameworks = installed_info.get("frameworks", [])
        version = installed_info.get("version", "unknown")
        
        # Remove from all framework directories
        for framework_name in frameworks:
            project_skill_path = self.config.get_local_path(
                framework_name,
                self.project.project_path
            ) / skill_name
            
            if project_skill_path.exists():
                try:
                    if is_junction(project_skill_path):
                        remove_junction(project_skill_path)
                        console.print(
                            f"[green]+[/green] Removed link: {project_skill_path}"
                        )
                    elif project_skill_path.is_dir():
                        shutil.rmtree(project_skill_path)
                        console.print(
                            f"[green]+[/green] Removed directory: {project_skill_path}"
                        )
                    else:
                        project_skill_path.unlink()
                        console.print(
                            f"[green]+[/green] Removed file: {project_skill_path}"
                        )
                except Exception as e:
                    console.print(f"[red]x Failed to remove {project_skill_path}: {e}[/red]")
        
        # Remove from installed list
        self.project.remove_skill(skill_name)
        
        console.print(f"[green]+[/green] Removed skill: {skill_name}")
        
        # Auto-commit to vault
        if auto_commit and self.vault.repo:
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                commit_msg = f"[{timestamp}] Remove skill: {skill_name} v{version}"
                self.vault.commit_all_changes(commit_msg)
                console.print(f"[dim]→ Auto-committed: {commit_msg}[/dim]")
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to auto-commit: {e}[/yellow]")
        
        return True
    
    def sync_updates(self, dry_run: bool = False, auto: bool = False) -> list[str]:
        """Synchronize updates from vault to project.
        
        Args:
            dry_run: Only show what would be updated
            auto: Update all without asking
            
        Returns:
            List of updated skill names
        """
        updates = self.get_available_updates()
        
        if not updates:
            console.print("[green]All skills are up to date![/green]")
            return []
        
        # Show available updates
        table = Table(title="Available Updates")
        table.add_column("Skill", style="cyan")
        table.add_column("Installed", style="yellow")
        table.add_column("Vault", style="green")
        table.add_column("Description")
        
        for skill, installed_version in updates:
            table.add_row(
                skill.name,
                installed_version,
                skill.version,
                skill.description[:50] + "..." if len(skill.description) > 50 else skill.description
            )
        
        console.print(table)
        
        if dry_run:
            return []
        
        if not auto:
            # This will be handled by interactive selection in CLI
            return []
        
        # Update all
        updated = []
        for skill, _ in updates:
            if self.install_skill(skill.name, force=True):
                updated.append(skill.name)
        
        return updated
    
    def push_skill(self, skill_name: str, message: str, author: str = "User") -> bool:
        """Push a local skill to the vault.
        
        Args:
            skill_name: Name of the skill
            message: Commit message
            author: Author name
            
        Returns:
            True if successful
        """
        # Check if skill exists in project
        if not self.project.is_skill_installed(skill_name):
            console.print(f"[red]Skill not installed in project: {skill_name}[/red]")
            return False
        
        installed_info = self.project.get_installed_skills()[skill_name]
        
        if not installed_info.get("is_local", False):
            console.print(f"[yellow]Can only push local skills: {skill_name}[/yellow]")
            return False
        
        # Get the skill from project
        frameworks = installed_info.get("frameworks", [])
        if not frameworks:
            console.print(f"[red]No frameworks found for skill: {skill_name}[/red]")
            return False
        
        # Get skill path from first framework
        framework = frameworks[0]
        project_skill_path = self.config.get_local_path(
            framework,
            self.project.project_path
        ) / skill_name
        
        if not project_skill_path.exists():
            console.print(f"[red]Skill directory not found: {project_skill_path}[/red]")
            return False
        
        # Parse skill to get version
        from .skills import SkillParser
        try:
            skill = SkillParser.parse(project_skill_path)
        except Exception as e:
            console.print(f"[red]Failed to parse skill: {e}[/red]")
            return False
        
        # Copy to vault (for local skills in skills/local/)
        import shutil
        vault_skill_path = self.vault.local_skills_dir / skill_name
        
        if vault_skill_path.exists():
            # Remove old version
            shutil.rmtree(vault_skill_path)
        
        shutil.copytree(project_skill_path, vault_skill_path)
        
        # Commit to vault
        try:
            tag = self.vault.commit_skill(skill_name, message, author)
            console.print(f"[green]+[/green] Committed skill: {skill_name}")
            console.print(f"[green]+[/green] Created tag: {tag}")
            
            # Ask if push to remote
            console.print(f"[blue]Push to remote?[/blue]")
            return True
        except Exception as e:
            console.print(f"[red]x Failed to commit: {e}[/red]")
            return False
    
    def discover_project_skills(self) -> List[Dict]:
        """Discover skills in the project that are not in the vault.
        
        Scans all enabled framework directories for skills that exist locally
        but are not tracked in the vault.
        
        Returns:
            List of dicts with skill info:
            - name: skill name (from SKILL.md)
            - directory_name: original directory name
            - path: path to skill directory
            - skill: Skill object if parseable
            - frameworks: list of frameworks where this skill exists
            - error: parsing error if any
        """
        if not self.project.config:
            return []
        
        discovered = {}
        
        for framework_name in self.project.config.enabled_frameworks:
            framework_path = self.config.get_local_path(
                framework_name,
                self.project.project_path
            )
            
            if not framework_path.exists():
                continue
            
            for skill_dir in framework_path.iterdir():
                if not skill_dir.is_dir():
                    continue
                
                # Skip if this is a junction (installed from vault)
                if is_junction(skill_dir):
                    continue
                
                # Try to parse the skill first to get the actual name
                skill_file = skill_dir / "SKILL.md"
                if not skill_file.exists():
                    continue
                
                # Parse skill to get the real name
                parsed_skill = None
                parse_error = None
                try:
                    from .skills import SkillParser
                    parsed_skill = SkillParser.parse(skill_dir)
                    skill_name = parsed_skill.name  # Use name from SKILL.md
                except Exception as ex:
                    # Use directory name if parsing fails
                    skill_name = skill_dir.name
                    parse_error = str(ex)
                
                # Skip if already in vault (check by skill name, not directory name)
                if self.vault.skill_exists(skill_name):
                    continue
                
                directory_name = skill_dir.name
                
                if skill_name not in discovered:
                    discovered[skill_name] = {
                        "name": skill_name,
                        "directory_name": directory_name,
                        "path": skill_dir,
                        "skill": parsed_skill,
                        "frameworks": [],
                        "error": parse_error
                    }
                
                discovered[skill_name]["frameworks"].append(framework_name)
        
        return list(discovered.values())
    
    def promote_skill_to_vault(
        self,
        skill_name: str,
        is_global: bool = True,
        message: Optional[str] = None,
        author: str = "User"
    ) -> bool:
        """Promote a skill from the project to the vault.
        
        Takes a skill that exists in the project but not in the vault,
        copies it to the vault, and commits the changes.
        
        Args:
            skill_name: Name of the skill to promote
            is_global: If True, add to global skills; if False, add to local skills
            message: Commit message (auto-generated if not provided)
            author: Author name for commit
            
        Returns:
            True if successful
        """
        # Discover the skill in the project
        discovered = self.discover_project_skills()
        skill_info = None
        for info in discovered:
            if info["name"] == skill_name:
                skill_info = info
                break
        
        if not skill_info:
            console.print(f"[red]Skill not found in project or already in vault: {skill_name}[/red]")
            return False
        
        if skill_info["error"]:
            console.print(f"[red]Cannot promote skill: {skill_info['error']}[/red]")
            return False
        
        skill = skill_info["skill"]
        source_path = skill_info["path"]
        directory_name = skill_info.get("directory_name", skill_name)
        
        # The actual skill name (from SKILL.md)
        actual_skill_name = skill.name if skill else skill_name
        
        # Warn if directory name differs from skill name
        if directory_name != actual_skill_name:
            console.print(f"[yellow]Note: Directory name '{directory_name}' differs from skill name '{actual_skill_name}'[/yellow]")
            console.print(f"[dim]Using '{actual_skill_name}' as the skill name in vault.[/dim]")
        
        # Determine target path in vault (use skill name from SKILL.md)
        if is_global:
            target_path = self.vault.global_skills_dir / actual_skill_name
            skill_type = "global"
        else:
            target_path = self.vault.local_skills_dir / actual_skill_name
            skill_type = "local"
        
        # Check if target already exists
        if target_path.exists():
            console.print(f"[red]Skill already exists in vault: {actual_skill_name}[/red]")
            console.print("[dim]Use a different name or remove the existing skill from vault first.[/dim]")
            return False
        
        # Copy skill to vault
        try:
            shutil.copytree(source_path, target_path)
            console.print(f"[green]+[/green] Copied skill to vault ({skill_type}): {actual_skill_name}")
        except Exception as e:
            console.print(f"[red]x Failed to copy skill: {e}[/red]")
            return False
        
        # Commit to vault
        try:
            commit_msg = message or f"Add {skill_type} skill: {actual_skill_name} v{skill.version}"
            self.vault.commit_all_changes(commit_msg)
            console.print(f"[green]+[/green] Committed to vault: {commit_msg}")
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to commit: {e}[/yellow]")
        
        # Update global junctions if global skill
        if is_global:
            try:
                from .global_junctions import setup_global_junctions
                setup_global_junctions(self.vault, self.config)
                console.print(f"[green]+[/green] Updated global junctions")
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to update global junctions: {e}[/yellow]")
        
        # Track the skill in installed.json so it can be managed
        frameworks = skill_info.get("frameworks", [])
        if not frameworks and self.project.config:
            frameworks = self.project.config.enabled_frameworks
        
        skill.is_local = not is_global  # Mark as local if added to local vault
        self.project.install_skill(skill, frameworks)
        self._save_skill_hashes(actual_skill_name, source_path)
        
        console.print(f"[green]+[/green] Promoted skill to vault: {actual_skill_name}")
        return True
