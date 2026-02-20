"""Configuration management for Skill Vault."""

import os
import yaml
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field


@dataclass
class FrameworkConfig:
    """Configuration for a specific AI framework."""
    name: str
    local_path: str
    global_path: str
    config_files: list[str] = field(default_factory=list)


@dataclass
class DefaultsConfig:
    """Default settings."""
    auto_sync: bool = False
    create_backups: bool = True
    preferred_frameworks: list[str] = field(default_factory=lambda: ["codex", "claude"])


class Config:
    """Manages Skill Vault configuration."""
    
    def __init__(self, vault_path: Optional[Path] = None):
        self.vault_path = vault_path or self._get_default_vault_path()
        self.frameworks: dict[str, FrameworkConfig] = {}
        self.defaults = DefaultsConfig()
        self._load_frameworks()
    
    @staticmethod
    def _get_default_vault_path() -> Path:
        """Get the default vault path."""
        return Path.home() / ".skill-vault"
    
    def _load_frameworks(self) -> None:
        """Load framework configurations from YAML file."""
        # Look for frameworks.yaml in multiple locations
        possible_paths = [
            Path(__file__).parent.parent.parent / "config" / "frameworks.yaml",
            self.vault_path / "config" / "frameworks.yaml",
            Path.cwd() / "config" / "frameworks.yaml",
        ]
        
        frameworks_file = None
        for path in possible_paths:
            if path.exists():
                frameworks_file = path
                break
        
        if not frameworks_file:
            raise FileNotFoundError(
                "frameworks.yaml not found. Please ensure it exists in config/ directory."
            )
        
        with open(frameworks_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Parse frameworks
        for key, value in data.get('frameworks', {}).items():
            self.frameworks[key] = FrameworkConfig(
                name=value['name'],
                local_path=value['local_path'],
                global_path=value['global_path'],
                config_files=value.get('config_files', [])
            )
        
        # Parse defaults
        defaults = data.get('defaults', {})
        self.defaults = DefaultsConfig(
            auto_sync=defaults.get('auto_sync', False),
            create_backups=defaults.get('create_backups', True),
            preferred_frameworks=defaults.get(
                'preferred_frameworks', 
                ["codex", "claude"]
            )
        )
    
    def get_framework(self, name: str) -> Optional[FrameworkConfig]:
        """Get configuration for a specific framework."""
        return self.frameworks.get(name)
    
    def get_all_frameworks(self) -> dict[str, FrameworkConfig]:
        """Get all framework configurations."""
        return self.frameworks.copy()
    
    def detect_frameworks(self, project_path: Path) -> list[str]:
        """Auto-detect which frameworks are used in a project."""
        detected = []
        
        for framework_name, framework in self.frameworks.items():
            for config_file in framework.config_files:
                config_path = project_path / config_file
                if config_path.exists():
                    detected.append(framework_name)
                    break
        
        return detected
    
    def get_local_path(self, framework_name: str, project_path: Path) -> Path:
        """Get the local path for a framework in a project."""
        framework = self.get_framework(framework_name)
        if not framework:
            raise ValueError(f"Unknown framework: {framework_name}")
        
        return project_path / framework.local_path
    
    def get_global_path(self, framework_name: str) -> Path:
        """Get the global path for a framework."""
        framework = self.get_framework(framework_name)
        if not framework:
            raise ValueError(f"Unknown framework: {framework_name}")
        
        return Path(framework.global_path).expanduser()
