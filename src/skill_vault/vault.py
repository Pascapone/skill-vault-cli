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
        self.global_skills_dir = self.skills_dir / "global"
        self.local_skills_dir = self.skills_dir / "local"
        
        # Initialize or open Git repository
        if (vault_path / ".git").exists():
            self.repo = git.Repo(vault_path)
        else:
            self.repo = None
    
    def initialize(self, remote_url: Optional[str] = None) -> None:
        """Initialize a new Vault repository."""
        # Create directory structure
        self.global_skills_dir.mkdir(parents=True, exist_ok=True)
        self.local_skills_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Git repository
        if not self.repo:
            self.repo = git.Repo.init(self.path)
        
        # Create .gitignore
        gitignore = self.path / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(
                "# Project-specific installations\nprojects/*/\n"
            )
        
        # Create initial README
        readme = self.path / "README.md"
        if not readme.exists():
            readme.write_text(
                "# Skill Vault\n\n"
                "Central repository for Agent Skills.\n\n"
                "## Structure\n\n"
                "- `skills/global/` - Skills available to all projects\n"
                "- `skills/local/` - Private skill templates\n"
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
    
    def list_global_skills(self) -> list[Skill]:
        """List all global skills in the vault."""
        return SkillParser.parse_all(self.global_skills_dir, is_local=False)
    
    def list_local_skills(self) -> list[Skill]:
        """List all local skills in the vault."""
        return SkillParser.parse_all(self.local_skills_dir, is_local=True)
    
    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        # Check global skills first
        skill_path = self.global_skills_dir / name
        if skill_path.exists():
            try:
                return SkillParser.parse(skill_path)
            except (FileNotFoundError, ValueError):
                pass
        
        # Check local skills
        skill_path = self.local_skills_dir / name
        if skill_path.exists():
            try:
                skill = SkillParser.parse(skill_path)
                skill.is_local = True
                return skill
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
    
    def commit_skill(self, skill_name: str, message: str, author_name: str = "Skill Vault", author_email: str = "vault@local") -> str:
        """Commit changes to a skill and create a tag.
        
        Returns:
            The tag name created
        """
        skill = self.get_skill(skill_name)
        if not skill:
            raise ValueError(f"Skill not found: {skill_name}")
        
        # Stage all files in the skill directory
        skill_files = skill.get_files()
        for file_path in skill_files:
            relative_path = file_path.relative_to(self.path)
            self.repo.index.add([str(relative_path)])
        
        # Create commit
        commit_message = f"{skill_name}: {message}"
        self.repo.index.commit(
            commit_message,
            author=git.Actor(author_name, author_email)
        )
        
        # Create tag
        tag_name = f"{skill_name}@v{skill.version}"
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
        if not self.repo.index.diff("HEAD") and not self.repo.untracked_files:
            return ""
        
        # Create commit
        commit = self.repo.index.commit(
            message,
            author=git.Actor(author_name, author_email)
        )
        
        return str(commit.hexsha)
    
    def push(self, remote_name: str = "origin") -> None:
        """Push commits and tags to remote."""
        remote = self.repo.remote(name=remote_name)
        remote.push()
        remote.push(tags=True)
    
    def pull(self, remote_name: str = "origin", branch: str = "main") -> None:
        """Pull latest changes from remote."""
        remote = self.repo.remote(name=remote_name)
        remote.pull(branch)
    
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
            "frameworks": frameworks,
            "is_local": skill.is_local
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
