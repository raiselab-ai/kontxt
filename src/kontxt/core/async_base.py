"""Async base class for common async patterns in Kontxt library.

This module provides a base class with shared async patterns, performance
tracking, and educational guidance to help users transition from sync to async.
"""

import asyncio
import inspect
import time
import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from .exceptions import AsyncContextError, PerformanceWarning

T = TypeVar('T')


@dataclass
class PerformanceMetrics:
    """Track performance metrics for sync vs async operations."""
    
    operation: str
    sync_times: List[float] = field(default_factory=list)
    async_times: List[float] = field(default_factory=list)
    
    @property
    def avg_sync_time(self) -> float:
        """Calculate average sync execution time."""
        return sum(self.sync_times) / len(self.sync_times) if self.sync_times else 0.0
    
    @property
    def avg_async_time(self) -> float:
        """Calculate average async execution time."""
        return sum(self.async_times) / len(self.async_times) if self.async_times else 0.0
    
    @property
    def performance_gain(self) -> float:
        """Calculate percentage performance improvement with async."""
        if self.avg_sync_time > 0 and self.avg_async_time > 0:
            return ((self.avg_sync_time - self.avg_async_time) / self.avg_sync_time) * 100
        return 0.0
    
    def get_comparison(self) -> Dict[str, Any]:
        """Get detailed performance comparison."""
        return {
            "operation": self.operation,
            "sync": {
                "avg_time": f"{self.avg_sync_time:.3f}s",
                "total_calls": len(self.sync_times),
                "total_time": f"{sum(self.sync_times):.3f}s"
            },
            "async": {
                "avg_time": f"{self.avg_async_time:.3f}s",
                "total_calls": len(self.async_times),
                "total_time": f"{sum(self.async_times):.3f}s"
            },
            "performance_gain": f"{self.performance_gain:.1f}%",
            "recommendation": self._get_recommendation()
        }
    
    def _get_recommendation(self) -> str:
        """Get performance-based recommendation."""
        if not self.async_times:
            return "Try async methods for better performance"
        elif self.performance_gain > 20:
            return f"Switch to async! You'll save {self.performance_gain:.1f}% execution time"
        elif self.performance_gain > 0:
            return "Async provides moderate performance improvement"
        else:
            return "Performance is similar - choose based on your application architecture"


class AsyncBase(ABC):
    """Base class providing common async patterns and educational guidance.
    
    This class helps users transition from synchronous (learning) code to
    asynchronous (production) code with helpful error messages and performance tracking.
    """
    
    def __init__(self, enable_performance_tracking: bool = True):
        """Initialize the AsyncBase.
        
        Args:
            enable_performance_tracking: Whether to track performance metrics
        """
        self._performance_metrics: Dict[str, PerformanceMetrics] = {}
        self._enable_performance_tracking = enable_performance_tracking
        self._async_context_detected = False
        self._education_mode = True  # Enable educational messages by default
    
    def _detect_async_context(self) -> bool:
        """Detect if we're running in an async context.
        
        Returns:
            True if in async context, False otherwise
        """
        try:
            # Check if there's a running event loop
            loop = asyncio.get_running_loop()
            return loop is not None
        except RuntimeError:
            # No running loop means we're not in async context
            return False
    
    def _check_async_context(self, method_name: str, async_alternative: str) -> None:
        """Check if sync method is called in async context and raise educational error.
        
        Args:
            method_name: The synchronous method being called
            async_alternative: The async method that should be used instead
            
        Raises:
            AsyncContextError: If called in async context with educational message
        """
        if self._detect_async_context():
            self._async_context_detected = True
            if self._education_mode:
                raise AsyncContextError(method_name, async_alternative)
    
    def _track_performance(self, 
                          operation: str, 
                          execution_time: float,
                          is_async: bool = False) -> None:
        """Track performance metrics for operations.
        
        Args:
            operation: The operation being tracked
            execution_time: Time taken for the operation
            is_async: Whether this was an async operation
        """
        if not self._enable_performance_tracking:
            return
        
        if operation not in self._performance_metrics:
            self._performance_metrics[operation] = PerformanceMetrics(operation)
        
        metrics = self._performance_metrics[operation]
        if is_async:
            metrics.async_times.append(execution_time)
        else:
            metrics.sync_times.append(execution_time)
        
        # Emit performance warning if sync is significantly slower
        if (not is_async and 
            len(metrics.sync_times) >= 3 and 
            metrics.performance_gain > 30):
            warnings.warn(
                f"Performance tip: {operation} is {metrics.performance_gain:.1f}% "
                f"faster with async methods",
                PerformanceWarning,
                stacklevel=3
            )
    
    async def _run_async_with_tracking(self, 
                                       operation: str,
                                       async_func: Callable,
                                       *args, 
                                       **kwargs) -> Any:
        """Run an async function with performance tracking.
        
        Args:
            operation: The operation name for tracking
            async_func: The async function to run
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            The result of the async function
        """
        start_time = time.perf_counter()
        try:
            result = await async_func(*args, **kwargs)
            return result
        finally:
            execution_time = time.perf_counter() - start_time
            self._track_performance(operation, execution_time, is_async=True)
    
    def _run_sync_with_tracking(self,
                                operation: str,
                                sync_func: Callable,
                                *args,
                                **kwargs) -> Any:
        """Run a sync function with performance tracking.
        
        Args:
            operation: The operation name for tracking
            sync_func: The sync function to run
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            The result of the sync function
        """
        start_time = time.perf_counter()
        try:
            result = sync_func(*args, **kwargs)
            return result
        finally:
            execution_time = time.perf_counter() - start_time
            self._track_performance(operation, execution_time, is_async=False)
    
    def get_performance_comparison(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get performance comparison between sync and async methods.
        
        Args:
            operation: Optional specific operation to get metrics for.
                      If None, returns all operations.
        
        Returns:
            Dictionary with performance comparison data
        """
        if operation:
            if operation in self._performance_metrics:
                return self._performance_metrics[operation].get_comparison()
            return {"error": f"No metrics found for operation: {operation}"}
        
        # Return all metrics
        return {
            op: metrics.get_comparison() 
            for op, metrics in self._performance_metrics.items()
        }
    
    def enable_education_mode(self, enabled: bool = True) -> None:
        """Enable or disable educational error messages.
        
        Args:
            enabled: Whether to enable educational mode
        """
        self._education_mode = enabled
    
    def get_async_guidance(self) -> Dict[str, Any]:
        """Get guidance on transitioning to async methods.
        
        Returns:
            Dictionary with async migration guidance
        """
        metrics_summary = self.get_performance_comparison()
        
        guidance = {
            "async_context_detected": self._async_context_detected,
            "education_mode": self._education_mode,
            "performance_metrics": metrics_summary,
            "migration_steps": [
                "1. Start with sync methods for learning and prototyping",
                "2. Monitor performance metrics with get_performance_comparison()",
                "3. When you see AsyncContextError, you're ready for async",
                "4. Replace sync methods with their async equivalents",
                "5. Use 'await' keyword with async methods"
            ],
            "benefits": {
                "concurrency": "Handle multiple operations simultaneously",
                "performance": "Better resource utilization and response times",
                "scalability": "Handle more concurrent requests",
                "non_blocking": "Prevent I/O operations from blocking execution"
            }
        }
        
        # Add specific recommendations based on usage
        if self._async_context_detected:
            guidance["recommendation"] = (
                "You're already using async context! "
                "Switch to async methods for optimal performance."
            )
        elif metrics_summary:
            total_gain = sum(
                m.performance_gain 
                for m in self._performance_metrics.values()
            ) / len(self._performance_metrics)
            if total_gain > 20:
                guidance["recommendation"] = (
                    f"Your workload would benefit from async methods "
                    f"(average {total_gain:.1f}% performance gain)"
                )
            else:
                guidance["recommendation"] = (
                    "Continue with sync methods for now. "
                    "Consider async when handling concurrent operations."
                )
        else:
            guidance["recommendation"] = (
                "Keep using sync methods while learning. "
                "Performance metrics will guide your async transition."
            )
        
        return guidance
    
    @staticmethod
    def create_async_wrapper(sync_func: Callable) -> Callable:
        """Create an async wrapper for a synchronous function.
        
        Args:
            sync_func: The synchronous function to wrap
            
        Returns:
            An async function that wraps the sync function
        """
        async def async_wrapper(*args, **kwargs):
            """Async wrapper for synchronous function."""
            # Run sync function in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, sync_func, *args, **kwargs)
        
        async_wrapper.__name__ = f"async_{sync_func.__name__}"
        async_wrapper.__doc__ = f"Async wrapper for {sync_func.__name__}"
        return async_wrapper
    
    @staticmethod
    def is_coroutine_function(func: Callable) -> bool:
        """Check if a function is a coroutine function.
        
        Args:
            func: The function to check
            
        Returns:
            True if the function is a coroutine function
        """
        return inspect.iscoroutinefunction(func)
    
    def reset_performance_metrics(self, operation: Optional[str] = None) -> None:
        """Reset performance metrics.
        
        Args:
            operation: Optional specific operation to reset.
                      If None, resets all metrics.
        """
        if operation:
            if operation in self._performance_metrics:
                del self._performance_metrics[operation]
        else:
            self._performance_metrics.clear()