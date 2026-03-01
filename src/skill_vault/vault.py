"""Vault management with Git integration."""

import git
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field, asdict

from .skills import Skill, SkillParser


@dataclass
class ProjectConfig:
    """Configuration for a project using Skill Vault."""
    name: str
    path: str
    vault_remote: str = "origin"
    vault_branch: str = "main"
    enabled_frameworks: list[str] = field(default_factory=list)
    installed_skills: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "ProjectConfig":
        return cls(**data)


class Vault:
    """Manages the Skill Vault repository."""
    
    def __init__(self, vault_path: Path):
        self.path = vault_path
        self.skills_dir = vault_path / "skills"
        self.presets_dir = vault_path / "presets"
        
        # Initialize or open Git repository
        if (vault_path / ".git").exists():
            self.repo = git.Repo(vault_path)
        else:
            self.repo = None
    
    def initialize(self, remote_url: Optional[str] = None) -> None:
        """Initialize a new Vault repository."""
        repo_was_created = False

        # Create directory structure
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Git repository
        if not self.repo:
            self.repo = git.Repo.init(self.path)
            repo_was_created = True
        
        # Create .gitignore
        gitignore = self.path / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(
                "# Project-specific installations\nprojects/*/\n\n# CLI Configuration\nconfig.yaml\n"
            )
        else:
            content = gitignore.read_text(encoding="utf-8")
            if "config.yaml" not in content:
                gitignore.write_text(content.rstrip() + "\n\n# CLI Configuration\nconfig.yaml\n", encoding="utf-8")
        
        # Create initial README
        readme = self.path / "README.md"
        if not readme.exists():
            readme.write_text(
                "# Skill Vault\n\n"
                "Central repository for Agent Skills.\n\n"
                "## Structure\n\n"
                "- `skills/` - All centralized skills\n"
            )
        
        # Add remote if provided
        if remote_url:
            try:
                self.repo.create_remote('origin', remote_url)
            except git.GitCommandError:
                pass  # Remote already exists
        
        # Initial commit
        if not self.repo.head.is_valid():
            self.repo.index.add(['.gitignore', 'README.md'])
            self.repo.index.commit("Initial commit: Skill Vault setup")

            # Enforce modern default branch for newly created vault repos.
            if repo_was_created:
                try:
                    self.repo.git.branch("-M", "main")
                except git.GitCommandError:
                    pass

    def has_remote(self, remote_name: str = "origin") -> bool:
        """Check whether a remote exists."""
        if not self.repo:
            return False
        return any(remote.name == remote_name for remote in self.repo.remotes)

    def has_local_branch(self, branch: str) -> bool:
        """Check whether a local branch exists."""
        if not self.repo:
            return False
        return any(head.name == branch for head in self.repo.heads)

    def list_remotes(self) -> dict[str, str]:
        """List configured remotes and URLs."""
        if not self.repo:
            return {}
        remotes: dict[str, str] = {}
        for remote in self.repo.remotes:
            urls = list(remote.urls)
            remotes[remote.name] = urls[0] if urls else ""
        return remotes

    def get_remote_url(self, remote_name: str = "origin") -> Optional[str]:
        """Get URL for a remote."""
        if not self.repo or not self.has_remote(remote_name):
            return None
        remote = self.repo.remote(name=remote_name)
        urls = list(remote.urls)
        return urls[0] if urls else None

    def set_remote(self, remote_url: str, remote_name: str = "origin", overwrite: bool = True) -> None:
        """Create or update a remote URL."""
        if not self.repo:
            raise ValueError("Vault repository not initialized")

        if self.has_remote(remote_name):
            if overwrite:
                self.repo.remote(name=remote_name).set_url(remote_url)
            return

        self.repo.create_remote(remote_name, remote_url)

    def remove_remote(self, remote_name: str = "origin") -> bool:
        """Remove a configured remote.

        Returns:
            True if a remote was removed, False if it did not exist.
        """
        if not self.repo:
            raise ValueError("Vault repository not initialized")

        if not self.has_remote(remote_name):
            return False

        self.repo.delete_remote(self.repo.remote(name=remote_name))
        return True

    def checkout_remote_branch(self, remote_name: str, branch: str) -> None:
        """Reset local branch to the exact remote branch state."""
        if not self.repo:
            raise ValueError("Vault repository not initialized")
        if not self.has_remote(remote_name):
            raise ValueError(f"Remote not found: {remote_name}")

        self.repo.git.fetch(remote_name, branch)
        self.repo.git.checkout("-B", branch, f"{remote_name}/{branch}")

    def is_bootstrap_history(self) -> bool:
        """Whether repository still has only the local bootstrap commit."""
        if not self.repo or not self.repo.head.is_valid():
            return False

        commits = list(self.repo.iter_commits(max_count=2))
        if len(commits) != 1:
            return False
        return commits[0].message.strip() == "Initial commit: Skill Vault setup"

    def get_current_branch(self) -> Optional[str]:
        """Get current local branch name."""
        if not self.repo:
            return None
        try:
            return self.repo.active_branch.name
        except TypeError:
            # Detached HEAD
            return None

    def get_remote_default_branch(self, remote_name: str = "origin") -> Optional[str]:
        """Resolve the default branch of a remote, if available."""
        if not self.repo or not self.has_remote(remote_name):
            return None

        try:
            output = self.repo.git.ls_remote("--symref", remote_name, "HEAD")
        except git.GitCommandError:
            return None

        for line in output.splitlines():
            if not line.startswith("ref: "):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            ref = parts[1]
            if ref.startswith("refs/heads/"):
                return ref.replace("refs/heads/", "", 1)

        return None

    def remote_branch_exists(self, branch: str, remote_name: str = "origin") -> bool:
        """Check whether a branch exists on remote."""
        if not self.repo or not self.has_remote(remote_name):
            return False

        try:
            output = self.repo.git.ls_remote("--heads", remote_name, branch)
        except git.GitCommandError:
            return False

        return bool(output.strip())

    def resolve_branch(self, branch: Optional[str] = None, remote_name: str = "origin") -> str:
        """Resolve branch to use for network operations."""
        if branch:
            return branch

        current = self.get_current_branch()
        if current:
            return current

        remote_default = self.get_remote_default_branch(remote_name=remote_name)
        if remote_default:
            return remote_default

        return "main"

    def is_clean(self, untracked_files: bool = True) -> bool:
        """Check if repository has no uncommitted changes."""
        if not self.repo:
            return True
        return not self.repo.is_dirty(untracked_files=untracked_files)

    def _has_staged_changes(self) -> bool:
        """Check whether there are staged changes."""
        if not self.repo:
            return False
        staged = self.repo.git.diff("--cached", "--name-only")
        return bool(staged.strip())
    
    def list_skills(self) -> list[Skill]:
        """List all skills in the vault."""
        return SkillParser.parse_all(self.skills_dir)
    
    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        skill_path = self.skills_dir / name
        if skill_path.exists():
            try:
                return SkillParser.parse(skill_path)
            except (FileNotFoundError, ValueError):
                pass
        
        return None
    
    def skill_exists(self, name: str) -> bool:
        """Check if a skill exists in the vault."""
        return self.get_skill(name) is not None
    
    def get_skill_version(self, name: str) -> str:
        """Get the version of a skill."""
        skill = self.get_skill(name)
        if skill:
            return skill.version
        return "0.0.0"
    
    def list_presets(self) -> list[str]:
        """List all available presets in the vault."""
        presets = []
        if not self.presets_dir.exists():
            return presets
        
        for preset_dir in self.presets_dir.iterdir():
            if preset_dir.is_dir() and (preset_dir / "PRESET.md").is_file():
                presets.append(preset_dir.name)
        
        return sorted(presets)
    
    def get_preset_content(self, name: str) -> Optional[str]:
        """Get the content of a named preset."""
        preset_file = self.presets_dir / name / "PRESET.md"
        if preset_file.is_file():
            return preset_file.read_text(encoding="utf-8")
        return None
    
    def get_preset_skills(self, name: str) -> list[str]:
        """Get list of required skills from a preset's skills.json if it exists."""
        skills_file = self.presets_dir / name / "skills.json"
        if not skills_file.is_file():
            return []
            
        try:
            with open(skills_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                skills = data.get("skills")
                if isinstance(skills, list):
                    return [str(s) for s in skills]
        except (json.JSONDecodeError, OSError):
            pass
            
        return []
    
    def commit_skill(self, skill_name: str, message: str, author_name: str = "Skill Vault", author_email: str = "vault@local") -> str:
        """Commit changes to a skill and create a tag.
        
        Returns:
            The tag name created
        """
        skill = self.get_skill(skill_name)
        if not skill:
            raise ValueError(f"Skill not found: {skill_name}")
        
        # Stage all changes in the skill directory (including deletions)
        skill_relative = skill.path.relative_to(self.path)
        self.repo.git.add("-A", str(skill_relative))

        if not self._has_staged_changes():
            raise ValueError(f"No changes to commit for skill: {skill_name}")
        
        # Create commit
        commit_message = f"{skill_name}: {message}"
        self.repo.index.commit(
            commit_message,
            author=git.Actor(author_name, author_email)
        )
        
        # Create tag
        tag_name = f"{skill_name}@v{skill.version}"
        try:
            self.repo.create_tag(tag_name)
        except git.GitCommandError:
            # Update existing tag if version is reused
            self.repo.delete_tag(tag_name)
            self.repo.create_tag(tag_name)
        
        return tag_name
    
    def commit_all_changes(self, message: str, author_name: str = "Skill Vault", author_email: str = "vault@local") -> str:
        """Commit all staged and unstaged changes in the vault.
        
        This is used for automatic commits after skill operations.
        
        Args:
            message: Commit message
            author_name: Author name for the commit
            author_email: Author email for the commit
            
        Returns:
            The commit hash
        """
        if not self.repo:
            raise ValueError("Vault repository not initialized")
        
        # Add all changes (staged and unstaged)
        self.repo.git.add('-A')
        
        # Check if there are changes to commit
        if not self._has_staged_changes():
            return ""
        
        # Create commit
        commit = self.repo.index.commit(
            message,
            author=git.Actor(author_name, author_email)
        )
        
        return str(commit.hexsha)
    
    def push(self, remote_name: str = "origin", branch: Optional[str] = None, set_upstream: bool = True) -> str:
        """Push commits and tags to remote."""
        if not self.repo:
            raise ValueError("Vault repository not initialized")
        if not self.has_remote(remote_name):
            raise ValueError(f"Remote not found: {remote_name}")

        resolved_branch = self.resolve_branch(branch=branch, remote_name=remote_name)

        if set_upstream:
            self.repo.git.push("--set-upstream", remote_name, f"{resolved_branch}:{resolved_branch}")
        else:
            self.repo.git.push(remote_name, f"{resolved_branch}:{resolved_branch}")

        self.repo.git.push(remote_name, "--tags")
        return resolved_branch
    
    def pull(self, remote_name: str = "origin", branch: Optional[str] = None) -> str:
        """Pull latest changes from remote."""
        if not self.repo:
            raise ValueError("Vault repository not initialized")
        if not self.has_remote(remote_name):
            raise ValueError(f"Remote not found: {remote_name}")

        resolved_branch = self.resolve_branch(branch=branch, remote_name=remote_name)
        self.repo.git.pull(remote_name, resolved_branch)
        return resolved_branch
    
    def get_skill_diff(self, skill_name: str) -> str:
        """Get the git diff for a skill."""
        skill = self.get_skill(skill_name)
        if not skill:
            return ""
        
        skill_relative = skill.path.relative_to(self.path)
        return self.repo.git.diff([str(skill_relative)])


class ProjectVault:
    """Manages a project's connection to the Skill Vault."""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.vault_dir = project_path / ".skill-vault"
        self.config_file = self.vault_dir / "config.yaml"
        self.installed_file = self.vault_dir / "installed.json"
        self.config: Optional[ProjectConfig] = None
    
    def is_initialized(self) -> bool:
        """Check if project has been initialized."""
        return self.vault_dir.exists() and self.config_file.exists()
    
    def initialize(self, name: str, vault_path: Path, frameworks: list[str]) -> None:
        """Initialize Skill Vault for this project."""
        self.vault_dir.mkdir(exist_ok=True)
        
        self.config = ProjectConfig(
            name=name,
            path=str(self.project_path),
            enabled_frameworks=frameworks,
            installed_skills={}
        )
        
        self._save_config()
        self._save_installed()
    
    def _save_config(self) -> None:
        """Save project configuration."""
        import yaml
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.config.to_dict(), f, default_flow_style=False)
    
    def _save_installed(self) -> None:
        """Save installed skills."""
        with open(self.installed_file, 'w', encoding='utf-8') as f:
            json.dump(self.config.installed_skills, f, indent=2)
    
    def load(self) -> None:
        """Load project configuration."""
        import yaml
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        self.config = ProjectConfig.from_dict(data)
        
        # Load installed skills
        if self.installed_file.exists():
            with open(self.installed_file, 'r', encoding='utf-8') as f:
                self.config.installed_skills = json.load(f)
    
    def install_skill(self, skill: Skill, frameworks: list[str]) -> None:
        """Record skill installation."""
        self.config.installed_skills[skill.name] = {
            "version": skill.version,
            "installed_at": datetime.now().isoformat(),
            "frameworks": frameworks
        }
        self._save_installed()
    
    def remove_skill(self, skill_name: str) -> None:
        """Remove skill from installed list."""
        if skill_name in self.config.installed_skills:
            del self.config.installed_skills[skill_name]
            self._save_installed()

    def update_enabled_frameworks(self, frameworks: list[str]) -> None:
        """Update enabled frameworks for this project."""
        if not self.config:
            raise ValueError("Project configuration not loaded")

        self.config.enabled_frameworks = frameworks
        self._save_config()
    
    def get_installed_skills(self) -> dict:
        """Get all installed skills."""
        return self.config.installed_skills.copy()
    
    def is_skill_installed(self, skill_name: str) -> bool:
        """Check if a skill is installed."""
        return skill_name in self.config.installed_skills
    
    def get_installed_version(self, skill_name: str) -> str:
        """Get installed version of a skill."""
        if skill_name in self.config.installed_skills:
            return self.config.installed_skills[skill_name].get("version", "0.0.0")
        return "0.0.0"
