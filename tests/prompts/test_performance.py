"""Performance and async functionality tests.

Tests comprehensive performance tracking, async patterns, educational features,
and integration with the AsyncBase class.
"""

import asyncio
import time
import warnings
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

from kontxt.core.async_base import AsyncBase, PerformanceMetrics
from kontxt.core.exceptions import AsyncContextError, PerformanceWarning
from kontxt.prompts import Prompt
from .fixtures import TestData


class TestPerformanceMetrics:
    """Test the PerformanceMetrics dataclass."""
    
    def test_empty_metrics(self):
        """Test metrics with no data."""
        metrics = PerformanceMetrics("test_op")
        
        assert metrics.operation == "test_op"
        assert metrics.avg_sync_time == 0.0
        assert metrics.avg_async_time == 0.0
        assert metrics.performance_gain == 0.0
    
    def test_sync_only_metrics(self):
        """Test metrics with only sync times."""
        metrics = PerformanceMetrics("test_op")
        metrics.sync_times = [0.1, 0.2, 0.3]
        
        assert metrics.avg_sync_time == 0.2
        assert metrics.avg_async_time == 0.0
        assert metrics.performance_gain == 0.0
    
    def test_async_only_metrics(self):
        """Test metrics with only async times."""
        metrics = PerformanceMetrics("test_op")
        metrics.async_times = [0.05, 0.1, 0.15]
        
        assert metrics.avg_sync_time == 0.0
        assert metrics.avg_async_time == 0.1
        assert metrics.performance_gain == 0.0
    
    def test_performance_gain_calculation(self):
        """Test performance gain calculation."""
        metrics = PerformanceMetrics("test_op")
        metrics.sync_times = [0.2, 0.2, 0.2]  # avg = 0.2
        metrics.async_times = [0.1, 0.1, 0.1]  # avg = 0.1
        
        assert metrics.avg_sync_time == 0.2
        assert metrics.avg_async_time == 0.1
        assert metrics.performance_gain == 50.0  # 50% improvement
    
    def test_get_comparison(self):
        """Test comprehensive comparison output."""
        metrics = PerformanceMetrics("test_op")
        metrics.sync_times = [0.2, 0.3]
        metrics.async_times = [0.1, 0.15]
        
        comparison = metrics.get_comparison()
        
        assert comparison["operation"] == "test_op"
        assert "sync" in comparison
        assert "async" in comparison
        assert "performance_gain" in comparison
        assert "recommendation" in comparison
        assert comparison["sync"]["total_calls"] == 2
        assert comparison["async"]["total_calls"] == 2
    
    def test_recommendation_messages(self):
        """Test different recommendation messages."""
        # No async data
        metrics1 = PerformanceMetrics("test1")
        metrics1.sync_times = [0.2]
        assert "Try async methods" in metrics1._get_recommendation()
        
        # High gain (>20%)
        metrics2 = PerformanceMetrics("test2")
        metrics2.sync_times = [0.3]
        metrics2.async_times = [0.1]
        assert "Switch to async!" in metrics2._get_recommendation()
        
        # Moderate gain
        metrics3 = PerformanceMetrics("test3")
        metrics3.sync_times = [0.2]
        metrics3.async_times = [0.18]
        assert "moderate performance" in metrics3._get_recommendation()
        
        # No gain
        metrics4 = PerformanceMetrics("test4")
        metrics4.sync_times = [0.1]
        metrics4.async_times = [0.12]
        assert "similar" in metrics4._get_recommendation()


class MockAsyncBase(AsyncBase):
    """Mock implementation of AsyncBase for testing."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def sync_method(self):
        """Mock sync method."""
        return self._run_sync_with_tracking("test_op", lambda: "sync_result")
    
    async def async_method(self):
        """Mock async method."""
        return await self._run_async_with_tracking("test_op", lambda: "async_result")


class TestAsyncBase:
    """Test the AsyncBase class functionality."""
    
    def test_initialization(self):
        """Test AsyncBase initialization."""
        base = MockAsyncBase(enable_performance_tracking=True)
        
        assert base._enable_performance_tracking is True
        assert base._education_mode is True
        assert base._async_context_detected is False
        assert len(base._performance_metrics) == 0
    
    def test_detect_async_context_outside_loop(self):
        """Test async context detection outside event loop."""
        base = MockAsyncBase()
        
        assert base._detect_async_context() is False
    
    async def test_detect_async_context_inside_loop(self):
        """Test async context detection inside event loop."""
        base = MockAsyncBase()
        
        assert base._detect_async_context() is True
    
    def test_check_async_context_sync_call(self):
        """Test async context check in sync context."""
        base = MockAsyncBase()
        
        # Should not raise in sync context
        base._check_async_context("test_method", "async_test_method")
        assert base._async_context_detected is False
    
    async def test_check_async_context_async_call(self):
        """Test async context check in async context."""
        base = MockAsyncBase()
        
        # Should raise AsyncContextError in async context
        with pytest.raises(AsyncContextError) as exc_info:
            base._check_async_context("test_method", "async_test_method")
        
        assert "test_method" in str(exc_info.value)
        assert "async_test_method" in str(exc_info.value)
        assert base._async_context_detected is True
    
    def test_track_performance_disabled(self):
        """Test performance tracking when disabled."""
        base = MockAsyncBase(enable_performance_tracking=False)
        
        base._track_performance("test_op", 0.1, is_async=False)
        
        assert len(base._performance_metrics) == 0
    
    def test_track_performance_sync(self):
        """Test performance tracking for sync operations."""
        base = MockAsyncBase(enable_performance_tracking=True)
        
        base._track_performance("test_op", 0.1, is_async=False)
        base._track_performance("test_op", 0.2, is_async=False)
        
        assert "test_op" in base._performance_metrics
        metrics = base._performance_metrics["test_op"]
        assert len(metrics.sync_times) == 2
        assert metrics.sync_times == [0.1, 0.2]
        assert len(metrics.async_times) == 0
    
    def test_track_performance_async(self):
        """Test performance tracking for async operations."""
        base = MockAsyncBase(enable_performance_tracking=True)
        
        base._track_performance("test_op", 0.05, is_async=True)
        base._track_performance("test_op", 0.08, is_async=True)
        
        metrics = base._performance_metrics["test_op"]
        assert len(metrics.async_times) == 2
        assert metrics.async_times == [0.05, 0.08]
        assert len(metrics.sync_times) == 0
    
    def test_performance_warning(self):
        """Test performance warning when sync is significantly slower."""
        base = MockAsyncBase(enable_performance_tracking=True)
        
        # Add async times (fast)
        for _ in range(3):
            base._track_performance("test_op", 0.05, is_async=True)
        
        # Add sync times (slow) - should trigger warning on 3rd call
        base._track_performance("test_op", 0.3, is_async=False)
        base._track_performance("test_op", 0.3, is_async=False)
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            base._track_performance("test_op", 0.3, is_async=False)
            
            assert len(w) == 1
            assert issubclass(w[0].category, PerformanceWarning)
            assert "faster with async" in str(w[0].message)
    
    def test_sync_method_tracking(self):
        """Test sync method with performance tracking."""
        base = MockAsyncBase()
        
        with patch('time.perf_counter', side_effect=[0.0, 0.1]):
            result = base.sync_method()
        
        assert result == "sync_result"
        assert "test_op" in base._performance_metrics
        assert base._performance_metrics["test_op"].sync_times == [0.1]
    
    async def test_async_method_tracking(self):
        """Test async method with performance tracking."""
        base = MockAsyncBase()
        
        with patch('time.perf_counter', side_effect=[0.0, 0.05]):
            result = await base.async_method()
        
        assert result == "async_result"
        assert "test_op" in base._performance_metrics
        assert base._performance_metrics["test_op"].async_times == [0.05]
    
    def test_get_performance_comparison_single(self):
        """Test getting performance comparison for single operation."""
        base = MockAsyncBase()
        base._track_performance("test_op", 0.2, is_async=False)
        base._track_performance("test_op", 0.1, is_async=True)
        
        comparison = base.get_performance_comparison("test_op")
        
        assert comparison["operation"] == "test_op"
        assert "sync" in comparison
        assert "async" in comparison
        assert "performance_gain" in comparison
    
    def test_get_performance_comparison_all(self):
        """Test getting performance comparison for all operations."""
        base = MockAsyncBase()
        base._track_performance("op1", 0.2, is_async=False)
        base._track_performance("op2", 0.3, is_async=False)
        
        comparison = base.get_performance_comparison()
        
        assert "op1" in comparison
        assert "op2" in comparison
        assert comparison["op1"]["operation"] == "op1"
        assert comparison["op2"]["operation"] == "op2"
    
    def test_get_performance_comparison_missing(self):
        """Test getting performance comparison for non-existent operation."""
        base = MockAsyncBase()
        
        comparison = base.get_performance_comparison("missing_op")
        
        assert "error" in comparison
        assert "missing_op" in comparison["error"]
    
    def test_education_mode_toggle(self):
        """Test toggling education mode."""
        base = MockAsyncBase()
        
        assert base._education_mode is True
        
        base.enable_education_mode(False)
        assert base._education_mode is False
        
        base.enable_education_mode(True)
        assert base._education_mode is True
    
    def test_get_async_guidance_basic(self):
        """Test basic async guidance."""
        base = MockAsyncBase()
        
        guidance = base.get_async_guidance()
        
        assert "async_context_detected" in guidance
        assert "education_mode" in guidance
        assert "migration_steps" in guidance
        assert "benefits" in guidance
        assert "recommendation" in guidance
        assert len(guidance["migration_steps"]) == 5
    
    def test_get_async_guidance_with_metrics(self):
        """Test async guidance with performance metrics."""
        base = MockAsyncBase()
        
        # Add some metrics showing async is much faster
        for _ in range(3):
            base._track_performance("test_op", 0.5, is_async=False)
            base._track_performance("test_op", 0.1, is_async=True)
        
        guidance = base.get_async_guidance()
        
        assert "performance_metrics" in guidance
        assert "would benefit from async" in guidance["recommendation"]
    
    async def test_get_async_guidance_context_detected(self):
        """Test async guidance when async context is detected."""
        base = MockAsyncBase()
        
        # Trigger async context detection
        try:
            base._check_async_context("test", "async_test")
        except AsyncContextError:
            pass
        
        guidance = base.get_async_guidance()
        
        assert guidance["async_context_detected"] is True
        assert "already using async context" in guidance["recommendation"]
    
    def test_create_async_wrapper(self):
        """Test creating async wrapper for sync function."""
        def sync_func(x, y=10):
            return x + y
        
        async_func = AsyncBase.create_async_wrapper(sync_func)
        
        assert async_func.__name__ == "async_sync_func"
        assert AsyncBase.is_coroutine_function(async_func)
        
        # Test the wrapper works
        result = asyncio.run(async_func(5, y=15))
        assert result == 20
    
    def test_is_coroutine_function(self):
        """Test coroutine function detection."""
        def sync_func():
            return "sync"
        
        async def async_func():
            return "async"
        
        assert AsyncBase.is_coroutine_function(sync_func) is False
        assert AsyncBase.is_coroutine_function(async_func) is True
    
    def test_reset_performance_metrics_single(self):
        """Test resetting single operation metrics."""
        base = MockAsyncBase()
        base._track_performance("op1", 0.1, is_async=False)
        base._track_performance("op2", 0.2, is_async=False)
        
        assert len(base._performance_metrics) == 2
        
        base.reset_performance_metrics("op1")
        
        assert len(base._performance_metrics) == 1
        assert "op2" in base._performance_metrics
    
    def test_reset_performance_metrics_all(self):
        """Test resetting all metrics."""
        base = MockAsyncBase()
        base._track_performance("op1", 0.1, is_async=False)
        base._track_performance("op2", 0.2, is_async=False)
        
        assert len(base._performance_metrics) == 2
        
        base.reset_performance_metrics()
        
        assert len(base._performance_metrics) == 0


class TestPromptPerformance:
    """Test performance aspects specific to Prompt class."""
    
    def test_prompt_performance_tracking(self, sample_structured_prompt):
        """Test prompt-specific performance tracking."""
        prompt = Prompt.from_data("test", sample_structured_prompt, enable_performance_tracking=True)
        
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        
        # Render multiple times to build metrics
        with patch('time.perf_counter', side_effect=[0.0, 0.1, 0.0, 0.08, 0.0, 0.12]):
            prompt.render(variables)
            prompt.render(variables)
            prompt.render(variables)
        
        metrics = prompt.get_performance_comparison(f"render_{prompt.name}")
        
        assert "sync" in metrics
        assert metrics["sync"]["total_calls"] == 3
        assert "prompt_specific" in prompt.get_performance_comparison()
    
    async def test_prompt_async_performance_tracking(self, sample_structured_prompt):
        """Test async performance tracking for prompts."""
        prompt = Prompt.from_data("test", sample_structured_prompt, 
                                enable_performance_tracking=True,
                                enable_educational_tips=False)
        
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        
        # Async renders
        with patch('time.perf_counter', side_effect=[0.0, 0.05, 0.0, 0.04]):
            await prompt.async_render(variables)
            await prompt.async_render(variables)
        
        metrics = prompt.get_performance_comparison(f"render_{prompt.name}")
        
        assert "async" in metrics
        assert metrics["async"]["total_calls"] == 2
    
    def test_prompt_performance_comparison_integration(self, sample_structured_prompt):
        """Test integration of performance comparison with prompt-specific data."""
        prompt = Prompt.from_data("test", sample_structured_prompt, 
                                enable_performance_tracking=True,
                                performance_threshold=0.05)
        
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        
        # Simulate slow render
        with patch('time.perf_counter', side_effect=[0.0, 0.1]):
            prompt.render(variables)
        
        comparison = prompt.get_performance_comparison()
        
        assert "prompt_specific" in comparison
        prompt_specific = comparison["prompt_specific"]
        
        assert "last_render_time" in prompt_specific
        assert "performance_threshold" in prompt_specific
        assert "sections_available" in prompt_specific
        assert "variable_count" in prompt_specific
        assert "recommendation" in prompt_specific
        assert "Use async_render() for production" in prompt_specific["recommendation"]
    
    def test_prompt_async_guidance(self, sample_structured_prompt):
        """Test prompt-specific async guidance."""
        prompt = Prompt.from_data("test", sample_structured_prompt)
        
        guidance = prompt.get_async_guidance()
        
        assert "prompt_specific" in guidance
        prompt_guidance = guidance["prompt_specific"]
        
        assert "current_prompt" in prompt_guidance
        assert "tips" in prompt_guidance
        assert len(prompt_guidance["tips"]) > 5
        assert any("async_render()" in tip for tip in prompt_guidance["tips"])
        assert any("sections parameter" in tip for tip in prompt_guidance["tips"])
    
    def test_educational_tips_performance_threshold(self, sample_structured_prompt, caplog):
        """Test educational tips based on performance threshold."""
        prompt = Prompt.from_data("test", sample_structured_prompt,
                                enable_educational_tips=True,
                                performance_threshold=0.05)
        
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        
        # Fast execution - no tip
        with patch('time.perf_counter', side_effect=[0.0, 0.03]):
            prompt.render(variables)
        
        # Should not log tip for fast execution
        assert not any("Consider using async_render" in record.message for record in caplog.records)
        
        caplog.clear()
        
        # Slow execution - should show tip
        with patch('time.perf_counter', side_effect=[0.0, 0.1]):
            prompt.render(variables)
        
        # Should log tip for slow execution
        assert any("Consider using async_render" in record.message for record in caplog.records)


class TestConcurrentAsyncOperations:
    """Test concurrent async operations and thread safety."""
    
    async def test_concurrent_prompt_renders(self, sample_structured_prompt):
        """Test concurrent async rendering."""
        prompt = Prompt.from_data("test", sample_structured_prompt, enable_educational_tips=False)
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        
        # Create multiple concurrent render tasks
        tasks = [prompt.async_render(variables) for _ in range(10)]
        
        # Execute concurrently
        results = await asyncio.gather(*tasks)
        
        # All results should be identical
        assert len(results) == 10
        assert all(isinstance(r, list) for r in results)
        assert all(r == results[0] for r in results)
    
    async def test_concurrent_different_variables(self, sample_structured_prompt):
        """Test concurrent rendering with different variables."""
        prompt = Prompt.from_data("test", sample_structured_prompt, enable_educational_tips=False)
        
        # Different variable sets
        var_sets = [
            {"role": "sales_rep", "customer_name": f"Customer{i}"}
            for i in range(5)
        ]
        
        # Create concurrent tasks
        tasks = [prompt.async_render(vars) for vars in var_sets]
        results = await asyncio.gather(*tasks)
        
        # Each result should contain the respective customer name
        for i, result in enumerate(results):
            assert f"Customer{i}" in str(result)
    
    async def test_concurrent_version_creation(self, sample_structured_prompt):
        """Test concurrent version creation."""
        prompt = Prompt.from_data("test", sample_structured_prompt)
        
        with patch.object(prompt, '_load_prompt_async', new_callable=AsyncMock) as mock_load:
            # Create multiple versions concurrently
            tasks = [
                prompt.async_create_version(f"v{i}")
                for i in range(3)
            ]
            
            versions = await asyncio.gather(*tasks)
            
            assert len(versions) == 3
            for i, version in enumerate(versions):
                assert version.version == f"v{i}"
            
            # Each version should have attempted to load
            assert mock_load.call_count == 3
    
    def test_thread_safety_sync_renders(self, sample_structured_prompt):
        """Test thread safety of synchronous renders."""
        prompt = Prompt.from_data("test", sample_structured_prompt, enable_educational_tips=False)
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        
        results = []
        exceptions = []
        
        def render_in_thread():
            try:
                result = prompt.render(variables)
                results.append(result)
            except Exception as e:
                exceptions.append(e)
        
        # Create multiple threads
        threads = [threading.Thread(target=render_in_thread) for _ in range(5)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"
        assert len(results) == 5
        assert all(r == results[0] for r in results)
    
    async def test_mixed_sync_async_operations(self, sample_structured_prompt):
        """Test mixing sync operations in thread pool with async operations."""
        prompt = Prompt.from_data("test", sample_structured_prompt, enable_educational_tips=False)
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        
        # Async operations
        async_tasks = [prompt.async_render(variables) for _ in range(3)]
        
        # Sync operations in thread pool
        loop = asyncio.get_event_loop()
        sync_tasks = [
            loop.run_in_executor(None, prompt.render, variables)
            for _ in range(3)
        ]
        
        # Execute all concurrently
        all_tasks = async_tasks + sync_tasks
        results = await asyncio.gather(*all_tasks)
        
        # All results should be identical
        assert len(results) == 6
        assert all(r == results[0] for r in results)


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    def test_render_performance_benchmark(self, sample_structured_prompt):
        """Benchmark render performance."""
        prompt = Prompt.from_data("test", sample_structured_prompt)
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        
        # Warmup
        for _ in range(5):
            prompt.render(variables)
        
        # Benchmark sync rendering
        start_time = time.perf_counter()
        for _ in range(100):
            prompt.render(variables)
        sync_time = time.perf_counter() - start_time
        
        # Should be reasonably fast (adjust threshold as needed)
        assert sync_time < 1.0, f"Sync rendering too slow: {sync_time:.3f}s for 100 renders"
    
    async def test_async_render_performance_benchmark(self, sample_structured_prompt):
        """Benchmark async render performance."""
        prompt = Prompt.from_data("test", sample_structured_prompt, enable_educational_tips=False)
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        
        # Warmup
        for _ in range(5):
            await prompt.async_render(variables)
        
        # Benchmark async rendering
        start_time = time.perf_counter()
        tasks = [prompt.async_render(variables) for _ in range(100)]
        await asyncio.gather(*tasks)
        async_time = time.perf_counter() - start_time
        
        # Should be reasonably fast
        assert async_time < 2.0, f"Async rendering too slow: {async_time:.3f}s for 100 concurrent renders"
    
    def test_memory_usage_stability(self, sample_structured_prompt):
        """Test memory usage remains stable during repeated operations."""
        import gc
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        prompt = Prompt.from_data("test", sample_structured_prompt, enable_educational_tips=False)
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        
        # Initial memory
        initial_memory = process.memory_info().rss
        
        # Perform many operations
        for _ in range(1000):
            result = prompt.render(variables)
            # Ensure result is used to prevent optimization
            assert result is not None
        
        # Force garbage collection
        gc.collect()
        
        # Final memory
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be minimal (less than 10MB for 1000 operations)
        assert memory_growth < 10 * 1024 * 1024, f"Excessive memory growth: {memory_growth / 1024 / 1024:.1f}MB"
    
    def test_cache_effectiveness(self, sample_structured_prompt):
        """Test template caching effectiveness."""
        prompt = Prompt.from_data("test", sample_structured_prompt)
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        
        # First render (cold cache)
        start_time = time.perf_counter()
        result1 = prompt.render(variables)
        cold_time = time.perf_counter() - start_time
        
        # Second render (warm cache)
        start_time = time.perf_counter()
        result2 = prompt.render(variables)
        warm_time = time.perf_counter() - start_time
        
        # Results should be identical
        assert result1 == result2
        
        # Warm cache should be faster (or at least not significantly slower)
        assert warm_time <= cold_time * 1.5, f"Cache not effective: cold={cold_time:.3f}s, warm={warm_time:.3f}s"


class TestAsyncContextDetection:
    """Test async context detection edge cases."""
    
    async def test_nested_async_context_detection(self):
        """Test async context detection in nested async calls."""
        prompt = Prompt.from_data("test", TestData.get_structured_prompt(), enable_educational_tips=True)
        
        async def nested_call():
            with pytest.raises(AsyncContextError):
                prompt.render({"role": "test", "customer_name": "test"})
        
        # Should detect async context even in nested calls
        await nested_call()
    
    def test_async_context_in_thread(self, sample_structured_prompt):
        """Test async context detection in threads."""
        prompt = Prompt.from_data("test", sample_structured_prompt)
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        
        results = []
        
        def thread_render():
            # Should NOT detect async context in thread
            result = prompt.render(variables)
            results.append(result)
        
        thread = threading.Thread(target=thread_render)
        thread.start()
        thread.join()
        
        assert len(results) == 1
        assert results[0] is not None
    
    async def test_sync_method_in_executor(self, sample_structured_prompt):
        """Test sync method called via executor in async context."""
        prompt = Prompt.from_data("test", sample_structured_prompt)
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        
        # This should work - executor runs in different thread
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, prompt.render, variables)
        
        assert result is not None
        assert isinstance(result, list)


class TestEducationalFeatures:
    """Test educational and guidance features."""
    
    def test_performance_tips_integration(self, sample_structured_prompt, caplog):
        """Test integration of performance tips with actual usage patterns."""
        prompt = Prompt.from_data("test", sample_structured_prompt,
                                enable_educational_tips=True,
                                enable_performance_tracking=True,
                                performance_threshold=0.05)
        
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        
        # Simulate mixed sync/async usage with performance difference
        # Fast async calls
        with patch('time.perf_counter', side_effect=[0.0, 0.03]):
            prompt._track_performance("render_test", 0.03, is_async=True)
        
        # Slow sync call
        with patch('time.perf_counter', side_effect=[0.0, 0.15]):
            prompt.render(variables)
        
        # Should log educational tip about async performance
        log_messages = [record.message for record in caplog.records]
        assert any("Consider using async_render" in msg for msg in log_messages)
    
    def test_guidance_with_historical_data(self, sample_structured_prompt):
        """Test guidance generation with historical performance data."""
        prompt = Prompt.from_data("test", sample_structured_prompt, enable_performance_tracking=True)
        
        # Build up performance history
        operation_name = f"render_{prompt.name}"
        for _ in range(5):
            prompt._track_performance(operation_name, 0.2, is_async=False)  # Slow sync
            prompt._track_performance(operation_name, 0.05, is_async=True)  # Fast async
        
        guidance = prompt.get_async_guidance()
        
        assert "prompt_specific" in guidance
        # Should recommend async based on significant performance difference
        assert "faster" in guidance["recommendation"] or "benefit" in guidance["recommendation"]
    
    def test_educational_tip_frequency_limiting(self, sample_structured_prompt, caplog):
        """Test that educational tips aren't spammed."""
        prompt = Prompt.from_data("test", sample_structured_prompt,
                                enable_educational_tips=True,
                                performance_threshold=0.01)  # Very low threshold
        
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        
        # Multiple slow renders
        for i in range(5):
            caplog.clear()
            with patch('time.perf_counter', side_effect=[0.0, 0.1]):
                prompt.render(variables)
            
            # Tips should appear, but implementation may limit frequency
            tip_count = sum(1 for record in caplog.records 
                          if "Consider using async_render" in record.message)
            
            # Each call should generate at most one tip
            assert tip_count <= 1