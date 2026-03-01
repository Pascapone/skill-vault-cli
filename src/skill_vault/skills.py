"""Skill models and parsing logic."""

import re
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Skill:
    """Represents an Agent Skill."""
    
    name: str
    version: str
    description: str
    author: str
    tags: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    path: Optional[Path] = None
    installed_at: Optional[datetime] = None
    
    @property
    def skill_file(self) -> Path:
        """Get the path to SKILL.md."""
        if not self.path:
            raise ValueError("Skill path not set")
        return self.path / "SKILL.md"
    
    @property
    def exists(self) -> bool:
        """Check if the skill exists on disk."""
        return self.path is not None and self.skill_file.exists()
    
    def get_content(self) -> str:
        """Get the content of SKILL.md."""
        if not self.exists:
            raise FileNotFoundError(f"Skill not found: {self.name}")
        return self.skill_file.read_text(encoding='utf-8')
    
    def get_files(self) -> list[Path]:
        """Get all files in the skill directory."""
        if not self.path:
            return []
        
        files = []
        for item in self.path.rglob('*'):
            if item.is_file():
                files.append(item)
        return files


class SkillParser:
    """Parser for SKILL.md files."""
    
    @staticmethod
    def parse(skill_path: Path) -> Skill:
        """Parse a SKILL.md file and return a Skill object.
        
        Args:
            skill_path: Path to the skill directory or SKILL.md file
            
        Returns:
            Skill object
            
        Raises:
            FileNotFoundError: If SKILL.md doesn't exist
            ValueError: If SKILL.md is malformed
        """
        # Handle both directory and file paths
        if skill_path.is_dir():
            skill_file = skill_path / "SKILL.md"
        else:
            skill_file = skill_path
            skill_path = skill_path.parent
        
        if not skill_file.exists():
            raise FileNotFoundError(f"SKILL.md not found in {skill_path}")
        
        content = skill_file.read_text(encoding='utf-8')
        
        # Parse YAML frontmatter
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        
        if not frontmatter_match:
            raise ValueError(f"No YAML frontmatter found in {skill_file}")
        
        try:
            metadata = yaml.safe_load(frontmatter_match.group(1))
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML frontmatter in {skill_file}: {e}")
        
        # Validate required fields (version is optional, defaults to 0.0.0)
        required_fields = ['name', 'description']
        for field_name in required_fields:
            if field_name not in metadata:
                raise ValueError(f"Missing required field '{field_name}' in {skill_file}")
        
        # Create Skill object (version defaults to 0.0.0 if not specified)
        skill = Skill(
            name=metadata['name'],
            version=metadata.get('version', '0.0.0'),
            description=metadata['description'],
            author=metadata.get('author', 'Unknown'),
            tags=metadata.get('tags', []),
            frameworks=metadata.get('frameworks', []),
            path=skill_path,
        )
        
        return skill
    
    @staticmethod
    def parse_all(skills_dir: Path) -> list[Skill]:
        """Parse all skills in a directory.
        
        Args:
            skills_dir: Directory containing skill directories
            
        Returns:
            List of Skill objects
        """
        skills = []
        
        if not skills_dir.exists():
            return skills
        
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                try:
                    skill = SkillParser.parse(skill_dir)
                    skills.append(skill)
                except (FileNotFoundError, ValueError):
                    continue
        
        return skills
    
    @staticmethod
    def get_skill_version(skill_path: Path) -> str:
        """Quickly get just the version from a skill.
        
        Args:
            skill_path: Path to skill directory
            
        Returns:
            Version string
        """
        skill_file = skill_path / "SKILL.md"
        if not skill_file.exists():
            raise FileNotFoundError(f"SKILL.md not found in {skill_path}")
        
        content = skill_file.read_text(encoding='utf-8')
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        
        if not frontmatter_match:
            raise ValueError(f"No YAML frontmatter found in {skill_file}")
        
        metadata = yaml.safe_load(frontmatter_match.group(1))
        return metadata.get('version', '0.0.0')
