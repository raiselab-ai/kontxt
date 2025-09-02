"""Variable validation logic for prompt variables."""

import json
import logging
from datetime import datetime
from typing import Any, Dict

from ..types import PromptVariable
from ...core.exceptions import VariableValidationError

# Optional dependencies with graceful fallbacks
try:
    import pydantic
    from pydantic import BaseModel, ValidationError
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    pydantic = None
    BaseModel = object
    ValidationError = Exception

logger = logging.getLogger(__name__)


class VariableValidator:
    """Handles variable validation with enhanced type support."""
    
    @staticmethod
    def validate_variable(var_def: PromptVariable, value: Any) -> Any:
        """Validate a single variable.
        
        Args:
            var_def: Variable definition with validation rules
            value: The value to validate
            
        Returns:
            The validated (and potentially coerced) value
            
        Raises:
            VariableValidationError: If validation fails
        """
        # Use default if value is None and default exists
        if value is None:
            if var_def.default is not None:
                return var_def.default
            elif var_def.required:
                raise VariableValidationError(
                    var_def.name, 
                    var_def.type,
                    value,
                    var_def.values
                )
            else:
                return None
        
        # Enhanced type validation with new types
        try:
            if var_def.type == "string":
                return str(value) if not isinstance(value, str) else value
            elif var_def.type == "integer":
                return int(value) if not isinstance(value, int) else value
            elif var_def.type == "float":
                return float(value) if not isinstance(value, (int, float)) else value
            elif var_def.type == "boolean":
                if isinstance(value, bool):
                    return value
                return value in ("true", "True", "1", 1)
            elif var_def.type == "list":
                if not isinstance(value, list):
                    # Try to parse as comma-separated string
                    if isinstance(value, str):
                        return [item.strip() for item in value.split(',')]
                    return [value]  # Single item list
                return value
            elif var_def.type == "dict":
                if isinstance(value, dict):
                    return value
                elif isinstance(value, str):
                    # Try to parse as JSON
                    return json.loads(value)
                else:
                    raise ValueError("Cannot convert to dict")
            elif var_def.type == "date":
                if isinstance(value, str):
                    # Try common date formats
                    for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"]:
                        try:
                            return datetime.strptime(value, fmt)
                        except ValueError:
                            continue
                    raise ValueError("Invalid date format")
                return value
            elif var_def.type == "enum":
                if var_def.values and value not in var_def.values:
                    raise VariableValidationError(
                        var_def.name, var_def.type, value, var_def.values
                    )
                return value
            else:
                # Try Pydantic validation if available and schema provided
                if HAS_PYDANTIC and var_def.schema:
                    return VariableValidator._validate_with_pydantic(value, var_def.schema)
                return value
                
        except Exception as e:
            raise VariableValidationError(
                var_def.name, var_def.type, value, var_def.values
            ) from e
    
    @staticmethod
    def _validate_with_pydantic(value: Any, schema: Dict[str, Any]) -> Any:
        """Validate using Pydantic schema if available.
        
        Args:
            value: Value to validate
            schema: Pydantic schema definition
            
        Returns:
            Validated value
        """
        if not HAS_PYDANTIC or not schema:
            return value
        
        try:
            # Create a dynamic Pydantic model
            model_dict = {"value": (Any, ...)}
            if "type" in schema:
                model_dict["value"] = (eval(schema["type"]), ...)
            
            DynamicModel = pydantic.create_model("DynamicModel", **model_dict)
            validated = DynamicModel(value=value)
            return validated.value
        except Exception:
            return value
    
    @staticmethod
    def validate_all_variables(variables_def: Dict[str, PromptVariable], 
                              input_vars: Dict[str, Any]) -> Dict[str, Any]:
        """Validate all variables for a prompt.
        
        Args:
            variables_def: Dictionary of variable definitions
            input_vars: Input variables to validate
            
        Returns:
            Dictionary of validated variables
            
        Raises:
            VariableValidationError: If any variable validation fails
        """
        validated = {}
        
        # Check all defined variables
        for var_name, var_def in variables_def.items():
            if var_name in input_vars:
                validated[var_name] = VariableValidator.validate_variable(var_def, input_vars[var_name])
            else:
                validated[var_name] = VariableValidator.validate_variable(var_def, None)
        
        # Add any extra variables not in definition (for flexibility)
        for var_name, value in input_vars.items():
            if var_name not in validated:
                validated[var_name] = value
        
        return validated
