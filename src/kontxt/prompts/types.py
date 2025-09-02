"""Type definitions for the prompts module.

This module contains all dataclasses and enums used throughout the prompts system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union


class PromptType(Enum):
    """Enum for different prompt types."""
    
    STRUCTURED = "structured"  # Chat messages as list of dicts
    FREEFORM = "freeform"      # Single string template
    HYBRID = "hybrid"          # Flexible dict format


@dataclass
class PromptVariable:
    """Definition of a prompt variable with enhanced type support.
    
    Note: Validation logic is handled by variables.validator module.
    """
    
    name: str
    type: str
    default: Optional[Any] = None
    required: bool = True
    values: Optional[List[Any]] = None  # For enum types
    description: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None  # For complex types


@dataclass
class PromptMetadata:
    """Metadata for a prompt template."""
    
    name: str
    version: str
    type: PromptType
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    performance_score: Optional[float] = None
    description: Optional[str] = None
    available_sections: Set[str] = field(default_factory=set)
    variable_count: int = 0
    
    def __post_init__(self):
        """Post-initialization processing."""
        if isinstance(self.type, str):
            self.type = PromptType(self.type)


@dataclass
class FewShotExample:
    """Typed structure for few-shot examples with multi-turn support."""
    input: Union[str, List[Dict[str, str]]]  # Support multi-turn
    output: Union[str, List[Dict[str, str]]]
    reasoning: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StructuredPromptContent:
    """Typed structure for structured prompt content."""
    
    system_role: Optional[str] = None  # Consolidated role/system
    behavior: Optional[str] = None
    restrictions: Optional[str] = None
    format: Optional[str] = None
    user: Optional[str] = None
    assistant: Optional[str] = None
    few_shots: List[FewShotExample] = field(default_factory=list)
    custom_sections: Dict[str, str] = field(default_factory=dict)
    
    # Backward compatibility aliases
    @property
    def role(self) -> Optional[str]:
        """Backward compatibility alias for system_role."""
        return self.system_role
    
    @role.setter
    def role(self, value: Optional[str]) -> None:
        """Backward compatibility setter for role."""
        self.system_role = value
    
    @property
    def system(self) -> Optional[str]:
        """Backward compatibility alias for system_role."""
        return self.system_role
    
    @system.setter
    def system(self, value: Optional[str]) -> None:
        """Backward compatibility setter for system."""
        self.system_role = value
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StructuredPromptContent":
        """Create from dictionary data with enhanced logic."""
        few_shots = cls._parse_few_shots(data.get("few_shots", []))
        system_role_content = data.get("role") or data.get("system") or data.get("system_role")
        custom_sections = cls._extract_custom_sections(data)
        
        return cls(
            system_role=system_role_content,
            behavior=data.get("behavior"),
            restrictions=data.get("restrictions"),
            format=data.get("format"),
            user=data.get("user") or data.get("human"),
            assistant=data.get("assistant") or data.get("ai"),
            few_shots=few_shots,
            custom_sections=custom_sections
        )
    
    @staticmethod
    def _parse_few_shots(few_shots_data: List[Any]) -> List[FewShotExample]:
        """Parse few-shot examples with multi-turn support."""
        few_shots = []
        for example in few_shots_data:
            if isinstance(example, dict):
                # Handle multi-turn examples
                input_data = example.get("input", "")
                output_data = example.get("output", "")
                
                few_shots.append(FewShotExample(
                    input=input_data,
                    output=output_data,
                    reasoning=example.get("reasoning") or example.get("context"),
                    metadata=example.get("metadata", {})
                ))
        return few_shots
    
    @staticmethod
    def _extract_custom_sections(data: Dict[str, Any]) -> Dict[str, str]:
        """Extract custom sections, filtering out known fields."""
        known_fields = {
            "role", "system", "system_role", "behavior", "restrictions", 
            "format", "user", "human", "assistant", "ai", "few_shots"
        }
        return {
            key: str(value) for key, value in data.items() 
            if key not in known_fields
        }
    
    def get_available_sections(self) -> Set[str]:
        """Get all available sections in this prompt."""
        sections = set()
        if self.system_role:
            sections.add("system_role")
        if self.behavior:
            sections.add("behavior")
        if self.restrictions:
            sections.add("restrictions")
        if self.format:
            sections.add("format")
        if self.user:
            sections.add("user")
        if self.assistant:
            sections.add("assistant")
        if self.few_shots:
            sections.add("few_shots")
        sections.update(self.custom_sections.keys())
        return sections


@dataclass
class FreeformPromptContent:
    """Typed structure for freeform prompt content."""
    
    template: str
    sections: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FreeformPromptContent":
        """Create from dictionary data."""
        sections = {key: str(value) for key, value in data.items()}
        # Preserve order of sections as provided
        template = "\n\n".join(str(value) for value in data.values())
        
        return cls(template=template, sections=sections)
    
    def get_available_sections(self) -> Set[str]:
        """Get all available sections."""
        return set(self.sections.keys())


@dataclass
class HybridPromptContent:
    """Typed structure for hybrid prompt content with better typing."""
    
    data: Dict[str, Any]
    _typed_fields: Dict[str, type] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HybridPromptContent":
        """Create from dictionary data with type inference."""
        instance = cls(data=data)
        instance._infer_types()
        return instance
    
    def _infer_types(self) -> None:
        """Infer types for better validation."""
        for key, value in self.data.items():
            self._typed_fields[key] = type(value)
    
    def get_available_sections(self) -> Set[str]:
        """Get all available sections."""
        return set(self.data.keys())
    
    def get_typed_value(self, key: str, expected_type: type = None) -> Any:
        """Get a value with optional type checking."""
        import logging
        
        logger = logging.getLogger(__name__)
        value = self.data.get(key)
        if expected_type and value is not None:
            if not isinstance(value, expected_type):
                try:
                    return expected_type(value)
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert {key} to {expected_type.__name__}")
        return value
