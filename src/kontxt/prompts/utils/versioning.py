"""Version handling and comparison utilities."""

import logging
from pathlib import Path
from typing import List, Optional

# Optional dependencies with graceful fallbacks
try:
    from packaging.version import parse as parse_version
    HAS_PACKAGING = True
except ImportError:
    HAS_PACKAGING = False

try:
    import difflib
    HAS_DIFFLIB = True
except ImportError:
    HAS_DIFFLIB = False

logger = logging.getLogger(__name__)


class VersionManager:
    """Handles version comparison and diffing."""
    
    @staticmethod
    def find_latest_version(versions_dir: Path) -> str:
        """Find latest version using semantic versioning.
        
        Args:
            versions_dir: Directory containing version files
            
        Returns:
            Latest version string
            
        Raises:
            ValueError: If no versions found
        """
        if not versions_dir.exists():
            raise ValueError(f"Versions directory does not exist: {versions_dir}")
        
        versions = []
        for file in versions_dir.glob("*.yaml*"):
            version = file.stem
            if version.endswith('.yaml'):  # Handle .yaml.gz files
                version = version[:-5]
            versions.append(version)
        
        if not versions:
            raise ValueError("No versions found in directory")
        
        # Use semantic versioning if available
        if HAS_PACKAGING:
            try:
                sorted_versions = sorted(versions, key=parse_version, reverse=True)
                return sorted_versions[0]
            except Exception:
                pass  # Fall back to lexicographic sorting
        
        # Lexicographic sorting fallback
        versions.sort(reverse=True)
        return versions[0]
    
    @staticmethod
    def list_versions(versions_dir: Path) -> List[str]:
        """List and sort versions.
        
        Args:
            versions_dir: Directory containing version files
            
        Returns:
            Sorted list of version strings (latest first)
        """
        if not versions_dir.exists():
            return []
        
        versions = []
        for file in versions_dir.glob("*.yaml*"):
            version = file.stem
            if version.endswith('.yaml'):  # Handle .yaml.gz files
                version = version[:-5]
            versions.append(version)
        
        # Use semantic versioning if available
        if HAS_PACKAGING:
            try:
                return sorted(versions, key=parse_version, reverse=True)
            except Exception:
                pass
        
        return sorted(versions, reverse=True)
    
    @staticmethod
    def diff_versions(current_path: Path, other_path: Path,
                     current_version: str, other_version: str,
                     prompt_name: str) -> str:
        """Compare two prompt versions.
        
        Args:
            current_path: Path to current version file
            other_path: Path to other version file
            current_version: Current version string
            other_version: Other version string
            prompt_name: Name of the prompt
            
        Returns:
            Diff string showing changes
        """
        if not HAS_DIFFLIB:
            return "difflib not available - cannot generate diff"
        
        try:
            # Load current version content
            current_content = VersionManager._load_file_content(current_path).splitlines()
            
            # Load other version content
            if not other_path.exists():
                return f"Version {other_version} not found"
            
            other_content = VersionManager._load_file_content(other_path).splitlines()
            
            # Generate diff
            diff_lines = difflib.unified_diff(
                other_content,
                current_content,
                fromfile=f"{prompt_name} v{other_version}",
                tofile=f"{prompt_name} v{current_version}",
                lineterm=""
            )
            
            return '\n'.join(diff_lines)
            
        except Exception as e:
            return f"Error generating diff: {e}"
    
    @staticmethod
    def _load_file_content(file_path: Path) -> str:
        """Load file content with compression support.
        
        Args:
            file_path: Path to file
            
        Returns:
            File content as string
        """
        import gzip
        
        if file_path.suffix == '.gz':
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                return f.read()
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
