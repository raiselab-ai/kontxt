"""File loading with compression support for prompt files."""

import asyncio
import gzip
from pathlib import Path
from typing import Optional

# Optional dependencies with graceful fallbacks
try:
    import aiofiles
    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False


class PromptFileLoader:
    """Handles loading prompt files with optional compression."""
    
    def __init__(self, enable_compression: bool = False):
        """Initialize file loader.
        
        Args:
            enable_compression: Whether to enable gzip compression support
        """
        self.enable_compression = enable_compression
    
    def load_file_content(self, prompt_path: Path) -> str:
        """Load file content with optional compression support.
        
        Args:
            prompt_path: Path to the prompt file
            
        Returns:
            File content as string
            
        Raises:
            IOError: If file cannot be read
        """
        if prompt_path.suffix == '.gz':
            with gzip.open(prompt_path, 'rt', encoding='utf-8') as f:
                return f.read()
        else:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
    
    async def load_file_content_async(self, prompt_path: Path) -> str:
        """Load file content asynchronously.
        
        Args:
            prompt_path: Path to the prompt file
            
        Returns:
            File content as string
            
        Raises:
            IOError: If file cannot be read
        """
        if prompt_path.suffix == '.gz':
            # Compressed files - use thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.load_file_content, prompt_path)
        
        if HAS_AIOFILES:
            async with aiofiles.open(prompt_path, 'r', encoding='utf-8') as f:
                return await f.read()
        else:
            # Fallback to thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.load_file_content, prompt_path)
    
    def get_prompt_path(self, base_path: Path, name: str, version: str) -> Path:
        """Get the path to a specific prompt version.
        
        Args:
            base_path: Base path for prompts
            name: Prompt name
            version: Prompt version
            
        Returns:
            Path to the prompt file
        """
        path = base_path / name / "versions" / f"{version}.yaml"
        
        # Check for compressed version if compression is enabled
        if self.enable_compression and not path.exists():
            compressed_path = path.with_suffix(".yaml.gz")
            if compressed_path.exists():
                return compressed_path
        
        return path
