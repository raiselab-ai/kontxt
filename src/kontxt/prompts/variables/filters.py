"""Custom Jinja filters for LLM processing."""

from typing import Dict, Callable, List


def get_custom_filters() -> Dict[str, Callable]:
    """Get all custom Jinja filters for LLM processing.
    
    Returns:
        Dictionary mapping filter names to filter functions
    """
    return {
        'escape_llm': escape_llm_filter,
        'format_few_shot': format_few_shot_filter,
        'truncate_words': truncate_words_filter,
        'to_upper_snake': to_upper_snake_filter,
    }


def escape_llm_filter(x: str) -> str:
    """Escape content for LLM processing.
    
    Args:
        x: Content to escape
        
    Returns:
        Escaped content
    """
    return str(x).replace('"', '\\"').replace('\n', '\\n')


def format_few_shot_filter(examples: List[Dict]) -> str:
    """Format few-shot examples for display.
    
    Args:
        examples: List of example dictionaries
        
    Returns:
        Formatted few-shot examples as string
    """
    formatted = []
    for i, example in enumerate(examples, 1):
        formatted.append(f"Example {i}:")
        formatted.append(f"Input: {example.get('input', '')}")
        formatted.append(f"Output: {example.get('output', '')}")
        if example.get('reasoning'):
            formatted.append(f"Reasoning: {example['reasoning']}")
        formatted.append("")
    return '\n'.join(formatted)


def truncate_words_filter(x: str, n: int) -> str:
    """Truncate text to a specific number of words.
    
    Args:
        x: Text to truncate
        n: Number of words to keep
        
    Returns:
        Truncated text with ellipsis if truncated
    """
    words = str(x).split()
    if len(words) <= n:
        return str(x)
    return ' '.join(words[:n]) + '...'


def to_upper_snake_filter(x: str) -> str:
    """Convert text to UPPER_SNAKE_CASE.
    
    Args:
        x: Text to convert
        
    Returns:
        Text in UPPER_SNAKE_CASE format
    """
    return str(x).upper().replace(' ', '_')
