#!/usr/bin/env python3
"""Performance profiling script for Sequel.

This script profiles key operations to establish baseline metrics and detect
performance regressions.

Usage:
    python scripts/profile.py [--operation OPERATION] [--verbose]

Operations:
    project_loading    - Profile project loading time
    cache_stats        - Show cache hit rates and statistics
    memory             - Profile memory usage over time
    all                - Run all profiling operations (default)
"""

import argparse
import asyncio
import cProfile
import pstats
import sys
import time
from io import StringIO
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sequel.cache.memory import get_cache
from sequel.services.projects import get_project_service


async def profile_project_loading() -> dict[str, float]:
    """Profile project loading time.

    Returns:
        Dictionary with timing metrics
    """
    print("\n=== Profiling Project Loading ===")

    project_service = await get_project_service()

    # Clear cache for accurate measurement
    cache = get_cache()
    await cache.clear()

    # Profile with cProfile
    profiler = cProfile.Profile()

    start_time = time.time()
    profiler.enable()

    projects = await project_service.list_projects(use_cache=False)

    profiler.disable()
    elapsed_time = time.time() - start_time

    # Print results
    print(f"✓ Loaded {len(projects)} projects in {elapsed_time:.2f}s")

    # Show top 10 time-consuming functions
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
    ps.print_stats(10)
    print("\nTop 10 time-consuming functions:")
    print(s.getvalue())

    # Test cached loading
    start_time_cached = time.time()
    cached_projects = await project_service.list_projects(use_cache=True)
    elapsed_time_cached = time.time() - start_time_cached

    print(f"\n✓ Cached load: {elapsed_time_cached:.4f}s")
    print(f"  Speedup: {elapsed_time / elapsed_time_cached:.1f}x faster")

    return {
        "uncached_time": elapsed_time,
        "cached_time": elapsed_time_cached,
        "project_count": len(projects),
        "speedup": elapsed_time / elapsed_time_cached if elapsed_time_cached > 0 else 0,
    }


async def profile_cache_stats() -> dict[str, int]:
    """Show cache statistics.

    Returns:
        Dictionary with cache metrics
    """
    print("\n=== Cache Statistics ===")

    cache = get_cache()
    stats = cache.get_stats()
    size_bytes = cache.get_size_bytes()
    entry_count = cache.size()

    print(f"Cache entries: {entry_count}")
    print(f"Cache size: {size_bytes / 1024:.2f} KB")
    print(f"Hits: {stats['hits']}")
    print(f"Misses: {stats['misses']}")
    print(f"Evictions: {stats['evictions']}")
    print(f"Expirations: {stats['expirations']}")

    total_requests = stats["hits"] + stats["misses"]
    if total_requests > 0:
        hit_rate = (stats["hits"] / total_requests) * 100
        print(f"Hit rate: {hit_rate:.1f}%")

        # Success criteria: > 70% hit rate
        if hit_rate > 70:
            print("✓ Cache hit rate exceeds 70% target")
        else:
            print("⚠ Cache hit rate below 70% target")
    else:
        hit_rate = 0.0
        print("No cache requests yet")

    return {**stats, "size_bytes": size_bytes, "entry_count": entry_count, "hit_rate": hit_rate}


async def profile_memory() -> dict[str, int]:
    """Profile memory usage over time.

    Returns:
        Dictionary with memory metrics
    """
    print("\n=== Memory Usage Profiling ===")

    try:
        import psutil
        process = psutil.Process()

        # Measure baseline memory
        baseline_mb = process.memory_info().rss / 1024 / 1024
        print(f"Baseline memory: {baseline_mb:.2f} MB")

        # Load projects multiple times
        project_service = await get_project_service()

        memory_samples = []
        for i in range(5):
            await project_service.list_projects(use_cache=False)
            current_mb = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_mb)
            print(f"  After iteration {i+1}: {current_mb:.2f} MB")
            await asyncio.sleep(0.5)

        final_mb = memory_samples[-1]
        delta_mb = final_mb - baseline_mb

        print(f"\nMemory delta: {delta_mb:+.2f} MB")

        # Check for memory stability (growth should be < 20MB)
        if delta_mb < 20:
            print("✓ Memory usage is stable")
        else:
            print("⚠ Memory usage increased significantly")

        return {
            "baseline_mb": int(baseline_mb),
            "final_mb": int(final_mb),
            "delta_mb": int(delta_mb),
            "samples": [int(s) for s in memory_samples],
        }

    except ImportError:
        print("⚠ psutil not installed. Install with: pip install psutil")
        return {}


async def run_all_profiles() -> dict[str, dict]:
    """Run all profiling operations.

    Returns:
        Dictionary with all metrics
    """
    results = {}

    try:
        results["project_loading"] = await profile_project_loading()
    except Exception as e:
        print(f"✗ Project loading profiling failed: {e}")
        results["project_loading"] = {}

    try:
        results["cache_stats"] = await profile_cache_stats()
    except Exception as e:
        print(f"✗ Cache stats profiling failed: {e}")
        results["cache_stats"] = {}

    try:
        results["memory"] = await profile_memory()
    except Exception as e:
        print(f"✗ Memory profiling failed: {e}")
        results["memory"] = {}

    return results


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Profile Sequel performance")
    parser.add_argument(
        "--operation",
        choices=["project_loading", "cache_stats", "memory", "all"],
        default="all",
        help="Operation to profile (default: all)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output",
    )
    args = parser.parse_args()

    print("Sequel Performance Profiler")
    print("=" * 50)

    if args.operation == "all":
        asyncio.run(run_all_profiles())
    elif args.operation == "project_loading":
        asyncio.run(profile_project_loading())
    elif args.operation == "cache_stats":
        asyncio.run(profile_cache_stats())
    elif args.operation == "memory":
        asyncio.run(profile_memory())

    print("\n" + "=" * 50)
    print("Profiling complete!")


if __name__ == "__main__":
    main()
