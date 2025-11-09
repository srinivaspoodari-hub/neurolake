"""
Dynamic Memory Allocation Demo

Shows real-time dynamic memory allocation with 40% overhead.
Demonstrates how the system automatically adjusts based on current availability.
"""

from neurolake.compute import LocalComputeEngine, ComputeOrchestrator
import time


def demo_dynamic_memory():
    """Demonstrate dynamic memory allocation"""
    print("=" * 80)
    print("DYNAMIC MEMORY ALLOCATION DEMO")
    print("=" * 80)
    print()

    # Initialize engine
    engine = LocalComputeEngine()

    # Get current state
    resources = engine.get_resources()

    print("CURRENT SYSTEM STATE:")
    print("-" * 80)
    print(f"Total RAM:        {resources.memory_total_gb:.2f} GB")
    print(f"Currently Used:   {resources.memory_used_gb:.2f} GB ({resources.memory_percent:.1f}%)")
    print(f"Currently Free:   {resources.memory_available_gb:.2f} GB")
    print()

    # Test different overhead percentages
    overhead_options = [20, 30, 40, 50]

    print("MEMORY ALLOCATION WITH DIFFERENT OVERHEADS:")
    print("-" * 80)
    print(f"{'Overhead':<12} {'Reserved':<15} {'Usable':<15} {'Note'}")
    print("-" * 80)

    for overhead in overhead_options:
        allocation = engine.get_dynamic_memory_allocation(overhead_percent=overhead)

        note = ""
        if overhead < 30:
            note = "⚠️  Risky - low buffer"
        elif overhead == 40:
            note = "✅ Recommended"
        elif overhead > 40:
            note = "Safe but conservative"

        print(f"{overhead}%{'':<8} "
              f"{allocation['reserved_for_system_gb']:>6.2f} GB{'':<6} "
              f"{allocation['usable_for_workload_gb']:>6.2f} GB{'':<6} "
              f"{note}")

    print()

    # Show default 40% overhead in detail
    print("DETAILED BREAKDOWN (40% OVERHEAD - RECOMMENDED):")
    print("-" * 80)
    allocation = engine.get_dynamic_memory_allocation(overhead_percent=40.0)

    print(f"Total System Memory:    {allocation['total_memory_gb']:.2f} GB")
    print(f"Currently Available:    {allocation['current_available_gb']:.2f} GB")
    print(f"")
    print(f"Reserved for System:    {allocation['reserved_for_system_gb']:.2f} GB (40% overhead)")
    print(f"Usable for Workloads:   {allocation['usable_for_workload_gb']:.2f} GB (60% of available)")
    print()

    # Check workload capacities
    print("WORKLOAD CAPACITY CHECKS:")
    print("-" * 80)

    workloads = [
        ("Small Query", 1.0, 2.0, False),
        ("Medium ETL", 4.0, 8.0, False),
        ("Large Analytics", 8.0, 16.0, False),
        ("ML Training (GPU)", 4.0, 32.0, True),
    ]

    for name, cpu, mem, gpu in workloads:
        capacity = engine.can_handle_workload(
            required_cpu_cores=cpu,
            required_memory_gb=mem,
            required_gpu=gpu,
            memory_overhead_percent=40.0
        )

        status = "✅ Can Handle" if capacity['can_handle'] else "❌ Cannot Handle"
        print(f"{name:<25} {cpu} CPU, {mem:>5.1f}GB RAM: {status}")
        if not capacity['can_handle']:
            if not capacity['cpu_ok']:
                print(f"  → CPU insufficient: need {cpu}, have {capacity['cpu_available_cores']:.1f}")
            if not capacity['memory_ok']:
                print(f"  → Memory insufficient: need {mem:.1f}GB, have {capacity['memory_usable_after_overhead_gb']:.1f}GB after overhead")
            if not capacity['gpu_ok']:
                print(f"  → GPU required but not available")

    print()

    # Show orchestrator with 40% overhead
    print("COMPUTE ORCHESTRATOR WITH 40% OVERHEAD:")
    print("-" * 80)
    orchestrator = ComputeOrchestrator(
        enable_cloud=False,
        enable_distributed=False,
        memory_overhead_percent=40.0
    )

    dynamic_allocation = orchestrator.get_dynamic_memory_allocation()
    print(f"Configured with 40% memory overhead")
    print(f"Safe usable memory: {dynamic_allocation['usable_for_workload_gb']:.2f} GB")
    print()

    # Practical example
    print("PRACTICAL EXAMPLE:")
    print("-" * 80)
    print("If you have 16GB total RAM and 12GB currently available:")
    print()
    print("Without overhead (risky):")
    print("  → Would try to use all 12GB")
    print("  → Could cause system freeze/crash")
    print()
    print("With 40% overhead (safe):")
    print("  → Reserves 4.8GB for system (40% of 12GB)")
    print("  → Uses only 7.2GB for workloads (60% of 12GB)")
    print("  → System remains stable and responsive")
    print()

    print("=" * 80)
    print("✅ DYNAMIC MEMORY ALLOCATION READY!")
    print("=" * 80)
    print()
    print("Key Benefits:")
    print("  • Real-time adjustment based on current availability")
    print("  • Configurable overhead (default 40%)")
    print("  • Prevents system crashes")
    print("  • Automatic routing to cloud if local insufficient")
    print()


def demo_api_usage():
    """Show API usage examples"""
    print("=" * 80)
    print("API USAGE EXAMPLES")
    print("=" * 80)
    print()

    print("1. Get dynamic memory allocation (40% overhead):")
    print("   GET http://localhost:5000/api/compute/memory/dynamic")
    print()

    print("2. Get with custom overhead (e.g., 30%):")
    print("   GET http://localhost:5000/api/compute/memory/dynamic?overhead_percent=30")
    print()

    print("3. Python API:")
    print("   from neurolake.compute import LocalComputeEngine")
    print("   engine = LocalComputeEngine()")
    print("   allocation = engine.get_dynamic_memory_allocation(overhead_percent=40)")
    print("   print(f'Usable: {allocation[\"usable_for_workload_gb\"]:.2f} GB')")
    print()

    print("4. Orchestrator with custom overhead:")
    print("   orchestrator = ComputeOrchestrator(memory_overhead_percent=40)")
    print("   allocation = orchestrator.get_dynamic_memory_allocation()")
    print()


if __name__ == "__main__":
    try:
        demo_dynamic_memory()
        print()
        demo_api_usage()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
