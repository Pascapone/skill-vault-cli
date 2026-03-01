"""Windows Junction handling for Skill Vault.

Junctions are used instead of symlinks on Windows because they don't require
administrator privileges and work for directory-to-directory linking.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Union


class JunctionError(Exception):
    """Raised when junction operations fail."""
    pass


def create_junction(source: Union[str, Path], target: Union[str, Path]) -> bool:
    """Create a Windows Junction (directory symbolic link) or POSIX symlink.
    
    Junctions don't require administrator privileges on Windows.
    On POSIX systems, a standard symbolic link is created.
    
    Args:
        source: Path where the junction/symlink will be created
        target: Path to the actual directory
        
    Returns:
        True if successful, False otherwise
        
    Raises:
        JunctionError: If the operation fails with a specific error
    """
    source = Path(source).resolve()
    target = Path(target).resolve()
    
    # Validate target exists and is a directory
    if not target.exists():
        raise JunctionError(f"Target directory does not exist: {target}")
    
    if not target.is_dir():
        raise JunctionError(f"Target is not a directory: {target}")
    
    # Check if source already exists
    if source.exists():
        # On Windows, check if it's an existing junction
        if sys.platform == "win32" and is_junction(source):
            current_target = get_junction_target(source)
            if current_target == target:
                return True  # Already correct
            raise JunctionError(
                f"Junction already exists at {source} pointing to {current_target}"
            )
        # On POSIX, check if it's an existing symlink
        elif sys.platform != "win32" and source.is_symlink():
            current_target = Path(os.readlink(source)).resolve()
            if current_target == target:
                return True # Already correct
            raise JunctionError(
                f"Symlink already exists at {source} pointing to {current_target}"
            )
        raise JunctionError(f"Path already exists (not a junction/symlink): {source}")
    
    # Ensure parent directory exists
    source.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        if sys.platform == "win32":
            # Use mklink /J to create junction on Windows
            cmd = ['cmd', '/c', 'mklink', '/J', str(source), str(target)]
            result = subprocess.run(
                cmd,
                capture_output=True,
                shell=False,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode != 0:
                stderr = result.stderr if result.stderr else "Unknown error"
                raise JunctionError(f"Failed to create junction: {stderr}")
        else:
            # Use os.symlink for POSIX systems
            # Note: os.symlink(src, dst) where src is the target and dst is the link
            os.symlink(target, source)
        
        return True
        
    except (subprocess.SubprocessError, OSError) as e:
        raise JunctionError(f"Failed to create link: {e}")
    except Exception as e:
        raise JunctionError(f"Unexpected error: {e}")


def remove_junction(path: Union[str, Path]) -> bool:
    """Remove a Windows Junction or POSIX directory symlink.
    
    This only removes the junction/symlink, NOT the target directory.
    """
    path = Path(path)
    
    if not path.exists() and not path.is_symlink():
        return True
    
    if not is_junction(path):
        raise JunctionError(f"Path is not a junction: {path}")
    
    try:
        if sys.platform == 'win32':
            # For junctions on Windows, rmdir only removes the link, not the target
            os.rmdir(path)
        else:
            # On POSIX, directory symlinks are removed with unlink
            path.unlink()
        return True
    except OSError as e:
        raise JunctionError(f"Failed to remove junction: {e}")


def is_junction(path: Union[str, Path]) -> bool:
    """Check if a path is a Windows Junction or POSIX directory symlink.
    
    Args:
        path: Path to check
        
    Returns:
        True if the path is a junction or directory symlink
    """
    path = Path(path)
    
    if not path.exists() and not path.is_symlink():
        return False
    
    # On POSIX, islink is the definitive check
    if sys.platform != 'win32':
        return os.path.islink(path)
    
    # Check if it's a symbolic link (junctions are a type of reparse point)
    if os.path.islink(path):
        return True
    
    # Additional check for junctions on Windows
    try:
        import stat
        st = os.lstat(path)
        # FILE_ATTRIBUTE_REPARSE_POINT = 0x400
        return bool(st.st_file_attributes & 0x400) if hasattr(st, 'st_file_attributes') else False
    except (AttributeError, OSError):
        pass
    
    return False


def get_junction_target(path: Union[str, Path]) -> Union[Path, None]:
    """Get the target of a Windows Junction.
    
    Args:
        path: Path to the junction
        
    Returns:
        Path to the target directory, or None if not a junction
    """
    path = Path(path)
    
    if not is_junction(path):
        return None
    
    try:
        # Read the target of the symbolic link
        return Path(os.readlink(path)).resolve()
    except OSError:
        return None


def list_junctions(directory: Union[str, Path]) -> list[Path]:
    """List all junctions in a directory.
    
    Args:
        directory: Directory to search
        
    Returns:
        List of paths that are junctions
    """
    directory = Path(directory)
    
    if not directory.exists():
        return []
    
    junctions = []
    for item in directory.iterdir():
        if is_junction(item):
            junctions.append(item)
    
    return junctions


def recreate_junction(source: Union[str, Path], target: Union[str, Path]) -> bool:
    """Remove existing junction and create new one.
    
    Args:
        source: Path where the junction will be created
        target: Path to the actual directory
        
    Returns:
        True if successful
    """
    source = Path(source)
    
    # Remove existing junction if present (including dangling symlinks)
    if source.exists() or source.is_symlink():
        if is_junction(source):
            remove_junction(source)
        else:
            raise JunctionError(f"Path exists and is not a junction: {source}")
    
    return create_junction(source, target)
