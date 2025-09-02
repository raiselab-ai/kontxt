"""Directory discovery logic for .kontxt directories."""

import logging
import os
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class KontxtDiscovery:
    """Handles .kontxt directory discovery and validation."""
    
    @staticmethod
    def discover_kontxt_directory() -> Path:
        """Discover .kontxt directory by walking up the directory tree.
        
        Returns:
            Path to the .kontxt directory
            
        Raises:
            PermissionError: If cannot create .kontxt directory
        """
        # Check environment variable first
        if env_path := os.getenv("KONTXT_BASE_PATH"):
            kontxt_path = Path(env_path)
            if kontxt_path.exists() and kontxt_path.is_dir():
                return kontxt_path
        
        current = Path.cwd()
        
        # Walk up the directory tree
        for _ in range(10):  # Limit search depth
            kontxt_path = current / ".kontxt"
            if kontxt_path.exists() and kontxt_path.is_dir():
                return kontxt_path
            
            parent = current.parent
            if parent == current:  # Reached root
                break
            current = parent
        
        # If not found, try to create in current directory
        kontxt_path = Path.cwd() / ".kontxt"
        try:
            if not kontxt_path.exists():
                kontxt_path.mkdir(parents=True, exist_ok=True)
                (kontxt_path / "prompts").mkdir(exist_ok=True)
                (kontxt_path / "logs").mkdir(exist_ok=True)
                
                logger.info(f"Created .kontxt directory at {kontxt_path}")
        except PermissionError:
            raise PermissionError(
                f"Cannot create .kontxt directory at {kontxt_path}. "
                "Running in read-only environment? Set KONTXT_BASE_PATH to a writable location."
            )
        
        return kontxt_path
    
    @staticmethod
    def list_available_prompts(base_path: Path) -> List[str]:
        """List available prompt names.
        
        Args:
            base_path: Base path to search for prompts
            
        Returns:
            List of available prompt names
        """
        if not base_path.exists():
            return []
        
        prompts = []
        for prompt_dir in base_path.iterdir():
            if prompt_dir.is_dir() and (prompt_dir / "versions").exists():
                prompts.append(prompt_dir.name)
        
        return prompts
