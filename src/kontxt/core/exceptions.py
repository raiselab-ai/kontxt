"""Core exceptions for the Kontxt library.

This module provides a hierarchy of exceptions with educational messages
to guide users from synchronous learning to asynchronous production usage.
"""

from typing import Optional, List, Any


class KontxtError(Exception):
    """Base exception for all Kontxt library errors.
    
    All custom exceptions in the Kontxt library inherit from this base class,
    allowing for unified error handling across the library.
    """
    
    def __init__(self, message: str, suggestions: Optional[List[str]] = None):
        """Initialize the KontxtError.
        
        Args:
            message: The error message
            suggestions: Optional list of suggestions for resolving the error
        """
        super().__init__(message)
        self.suggestions = suggestions or []
        
    def __str__(self) -> str:
        """Format the error message with suggestions."""
        base_msg = super().__str__()
        if self.suggestions:
            suggestions_str = "\n  - ".join([""] + self.suggestions)
            return f"{base_msg}\nSuggestions:{suggestions_str}"
        return base_msg


class AsyncContextError(KontxtError):
    """Raised when synchronous methods are called in an async context.
    
    This educational error helps users understand when they should transition
    from synchronous (learning) methods to asynchronous (production) methods.
    """
    
    def __init__(self, method_name: str, async_alternative: str):
        """Initialize the AsyncContextError with educational guidance.
        
        Args:
            method_name: The synchronous method that was called
            async_alternative: The async method that should be used instead
        """
        message = (
            f"Synchronous method '{method_name}' called in async context. "
            f"You're ready for production! Use '{async_alternative}' instead."
        )
        suggestions = [
            f"Replace '{method_name}()' with 'await {async_alternative}()'",
            "Async methods provide better performance in production environments",
            "See documentation: https://docs.kontxt.io/async-migration"
        ]
        super().__init__(message, suggestions)
        self.method_name = method_name
        self.async_alternative = async_alternative


class PromptNotFoundError(KontxtError):
    """Raised when a requested prompt cannot be found."""
    
    def __init__(self, prompt_name: str, available_prompts: Optional[List[str]] = None):
        """Initialize the PromptNotFoundError.
        
        Args:
            prompt_name: The name of the prompt that wasn't found
            available_prompts: Optional list of available prompt names
        """
        message = f"Prompt '{prompt_name}' not found in registry"
        suggestions = []
        
        if available_prompts:
            # Find similar prompts using simple string matching
            similar = [p for p in available_prompts if prompt_name.lower() in p.lower()]
            if similar:
                suggestions.append(f"Did you mean one of these? {', '.join(similar[:3])}")
            else:
                suggestions.append(f"Available prompts: {', '.join(available_prompts[:5])}")
        
        suggestions.extend([
            f"Check if the prompt exists at: .kontxt/prompts/{prompt_name}/",
            "Use PromptRegistry.list_prompts() to see all available prompts"
        ])
        
        super().__init__(message, suggestions)
        self.prompt_name = prompt_name
        self.available_prompts = available_prompts


class TemplateRenderError(KontxtError):
    """Raised when template rendering fails."""
    
    def __init__(self, 
                 template_name: str,
                 error_details: str,
                 missing_variables: Optional[List[str]] = None,
                 invalid_variables: Optional[List[str]] = None):
        """Initialize the TemplateRenderError.
        
        Args:
            template_name: The name of the template that failed to render
            error_details: Specific details about the rendering error
            missing_variables: Optional list of missing required variables
            invalid_variables: Optional list of invalid variables
        """
        message = f"Failed to render template '{template_name}': {error_details}"
        suggestions = []
        
        if missing_variables:
            suggestions.append(f"Missing required variables: {', '.join(missing_variables)}")
            suggestions.append("Provide all required variables in the 'variables' parameter")
        
        if invalid_variables:
            suggestions.append(f"Invalid variables: {', '.join(invalid_variables)}")
            suggestions.append("Check variable types and allowed values in the prompt definition")
        
        suggestions.append("Use prompt.get_variables() to see all required variables")
        
        super().__init__(message, suggestions)
        self.template_name = template_name
        self.error_details = error_details
        self.missing_variables = missing_variables
        self.invalid_variables = invalid_variables


class VariableValidationError(KontxtError):
    """Raised when variable validation fails."""
    
    def __init__(self,
                 variable_name: str,
                 expected_type: str,
                 actual_value: Any,
                 allowed_values: Optional[List[Any]] = None):
        """Initialize the VariableValidationError.
        
        Args:
            variable_name: The name of the invalid variable
            expected_type: The expected type of the variable
            actual_value: The actual value that was provided
            allowed_values: Optional list of allowed values for enum types
        """
        actual_type = type(actual_value).__name__
        message = (
            f"Variable '{variable_name}' validation failed. "
            f"Expected type '{expected_type}', got '{actual_type}'"
        )
        
        suggestions = []
        if allowed_values:
            suggestions.append(f"Allowed values: {allowed_values}")
        
        suggestions.extend([
            f"Convert the value to {expected_type} before passing",
            "Check the prompt definition for variable requirements"
        ])
        
        super().__init__(message, suggestions)
        self.variable_name = variable_name
        self.expected_type = expected_type
        self.actual_value = actual_value
        self.allowed_values = allowed_values


class PromptVersionError(KontxtError):
    """Raised when there's an issue with prompt versioning."""
    
    def __init__(self,
                 prompt_name: str,
                 version: str,
                 available_versions: Optional[List[str]] = None):
        """Initialize the PromptVersionError.
        
        Args:
            prompt_name: The name of the prompt
            version: The requested version that caused the error
            available_versions: Optional list of available versions
        """
        message = f"Version '{version}' not found for prompt '{prompt_name}'"
        suggestions = []
        
        if available_versions:
            suggestions.append(f"Available versions: {', '.join(available_versions)}")
            suggestions.append("Use 'latest' to get the most recent version")
        
        suggestions.extend([
            f"Check versions at: .kontxt/prompts/{prompt_name}/versions/",
            "Use prompt.list_versions() to see all available versions"
        ])
        
        super().__init__(message, suggestions)
        self.prompt_name = prompt_name
        self.version = version
        self.available_versions = available_versions


class PromptTypeError(KontxtError):
    """Raised when there's a mismatch in prompt types."""
    
    def __init__(self,
                 expected_type: str,
                 actual_type: str,
                 operation: str):
        """Initialize the PromptTypeError.
        
        Args:
            expected_type: The expected prompt type
            actual_type: The actual prompt type
            operation: The operation that was attempted
        """
        message = (
            f"Prompt type mismatch for operation '{operation}'. "
            f"Expected '{expected_type}', got '{actual_type}'"
        )
        suggestions = [
            f"This operation requires a '{expected_type}' prompt type",
            "Check the prompt definition to ensure it matches your use case",
            "Convert the prompt type if necessary using prompt.convert_to()"
        ]
        
        super().__init__(message, suggestions)
        self.expected_type = expected_type
        self.actual_type = actual_type
        self.operation = operation


class PerformanceWarning(KontxtError):
    """Raised when performance could be improved."""
    
    def __init__(self,
                 operation: str,
                 sync_time: float,
                 async_time: Optional[float] = None):
        """Initialize the PerformanceWarning.
        
        Args:
            operation: The operation that triggered the warning
            sync_time: Time taken by synchronous operation
            async_time: Optional time for async operation comparison
        """
        if async_time:
            improvement = ((sync_time - async_time) / sync_time) * 100
            message = (
                f"Performance warning for '{operation}': "
                f"Async version is {improvement:.1f}% faster"
            )
            suggestions = [
                f"Sync time: {sync_time:.3f}s, Async time: {async_time:.3f}s",
                "Consider switching to async methods for better performance",
                "Use prompt.get_performance_comparison() for detailed metrics"
            ]
        else:
            message = (
                f"Performance warning for '{operation}': "
                f"Operation took {sync_time:.3f}s"
            )
            suggestions = [
                "This operation could be faster with async methods",
                "Large templates or many variables may impact performance",
                "Consider caching rendered prompts for repeated use"
            ]
        
        super().__init__(message, suggestions)
        self.operation = operation
        self.sync_time = sync_time
        self.async_time = async_time