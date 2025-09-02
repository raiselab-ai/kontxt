"""Output logging system for rendered prompts and LLM responses."""

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


class OutputLogger:
    """Handles logging of rendered prompts and LLM responses."""
    
    def __init__(self, log_dir: Path):
        """Initialize output logger.
        
        Args:
            log_dir: Directory to store log files
        """
        self.log_dir = log_dir
        self.logger = logging.getLogger(__name__)
    
    def log_output(self, prompt_name: str, prompt_version: str,
                   rendered_prompt: Any, llm_response: str, 
                   metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log rendered prompt and LLM response.
        
        Args:
            prompt_name: Name of the prompt
            prompt_version: Version of the prompt
            rendered_prompt: The rendered prompt output
            llm_response: The LLM's response
            metadata: Additional metadata to log
        """
        try:
            self.log_dir.mkdir(exist_ok=True)
            
            log_entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "prompt_name": prompt_name,
                "prompt_version": prompt_version,
                "rendered_prompt": rendered_prompt,
                "llm_response": llm_response,
                "metadata": metadata or {}
            }
            
            log_file = self.log_dir / f"{prompt_name}_output.yaml"
            
            # Load existing logs
            logs = []
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        logs = yaml.safe_load(f) or []
                except yaml.YAMLError as e:
                    self.logger.warning(f"Corrupted log file {log_file}, starting fresh: {e}")
                    logs = []
            
            logs.append(log_entry)
            
            # Keep only last 1000 entries
            if len(logs) > 1000:
                logs = logs[-1000:]
            
            try:
                with open(log_file, 'w', encoding='utf-8') as f:
                    yaml.dump(logs, f, default_flow_style=False)
            except yaml.YAMLError as e:
                self.logger.error(f"Failed to write log file due to YAML error: {e}")
                
        except Exception as e:
            self.logger.warning(f"Failed to log output: {e}")
