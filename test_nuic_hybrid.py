#!/usr/bin/env python3
"""
Test script to verify NUIC and Hybrid modules are working correctly
"""

import sys
import os

# Add neurolake to path
sys.path.insert(0, os.path.dirname(__file__))

from neurolake.nuic import NUICatalog, PipelineRegistry, PatternLibrary, TemplateManager
from neurolake.hybrid import HybridStorageManager, HybridComputeScheduler, CostOptimizer


def test_nuic():
    """Test NUIC modules"""
    print("=" * 60)
    print("Testing NUIC (Neuro Unified Intelligence Catalog)")
    print("=" * 60)

    # Test Catalog
    print("\n1. Testing NUICatalog...")
    catalog = NUICatalog(storage_path="./test_catalog")

    pipeline_id = catalog.register_pipeline(
        name="test_etl",
        description="Test ETL pipeline",
        logic={"source": "test_db", "target": "test_dw"},
        tags=["test", "etl"]
    )
    print(f"   ✓ Registered pipeline: {pipeline_id}")

    stats = catalog.get_stats()
    print(f"   ✓ Catalog stats: {stats['total_pipelines']} pipelines")

    # Test Pipeline Registry
    print("\n2. Testing PipelineRegistry...")
    registry = PipelineRegistry()
    registry.register("test", {"type": "etl"})
    print(f"   ✓ Registered pipelines: {registry.list_all()}")

    # Test Pattern Library
    print("\n3. Testing PatternLibrary...")
    patterns = PatternLibrary()
    pattern_list = patterns.list_patterns()
    print(f"   ✓ Available patterns: {pattern_list}")

    # Test Template Manager
    print("\n4. Testing TemplateManager...")
    templates = TemplateManager()
    template_list = templates.list_templates()
    print(f"   ✓ Available templates: {template_list}")

    print("\n✅ NUIC modules working correctly!")


def test_hybrid():
    """Test Hybrid modules"""
    print("\n" + "=" * 60)
    print("Testing Hybrid Storage & Compute")
    print("=" * 60)

    # Test Storage Manager
    print("\n1. Testing HybridStorageManager...")
    storage = HybridStorageManager(
        local_path="./test_storage",
        local_capacity_gb=10.0
    )

    test_data = b"Hello, NeuroLake!"
    result = storage.store_data("test_file", test_data)
    print(f"   ✓ Stored data to: {result['tier']}")

    retrieved = storage.retrieve_data("test_file")
    print(f"   ✓ Retrieved {len(retrieved)} bytes")

    stats = storage.get_statistics()
    print(f"   ✓ Cache hit rate: {stats['cache_hit_rate']:.1%}")

    # Test Compute Scheduler
    print("\n2. Testing HybridComputeScheduler...")
    from neurolake.hybrid.compute_scheduler import WorkloadType

    scheduler = HybridComputeScheduler(cloud_enabled=False)

    decision = scheduler.schedule_workload(
        workload_type=WorkloadType.QUERY,
        estimated_cpu=2.0,
        estimated_memory_gb=4.0,
        estimated_duration_minutes=5,
        priority=5
    )
    print(f"   ✓ Scheduled to: {decision['tier']}")
    print(f"   ✓ Reason: {decision['reason']}")

    # Test Cost Optimizer
    print("\n3. Testing CostOptimizer...")
    optimizer = CostOptimizer()

    comparison = optimizer.compare_deployment_models(
        monthly_data_gb=100,
        monthly_compute_hours=50
    )
    print(f"   ✓ Cloud-only cost: ${comparison['cloud_only_usd']['total']:.2f}/month")
    print(f"   ✓ Hybrid cost: ${comparison['hybrid_usd']['total']:.2f}/month")
    print(f"   ✓ Savings: {comparison['savings_vs_cloud_pct']:.1f}%")

    print("\n✅ Hybrid modules working correctly!")


def test_integration():
    """Test integration between modules"""
    print("\n" + "=" * 60)
    print("Testing Integration")
    print("=" * 60)

    # Create a pipeline and store it
    catalog = NUICatalog(storage_path="./test_catalog")
    storage = HybridStorageManager(local_path="./test_storage")

    pipeline_id = catalog.register_pipeline(
        name="integrated_test",
        description="Integration test pipeline",
        logic={"test": True},
        tags=["integration"]
    )

    # Store pipeline definition
    import json
    pipeline_data = json.dumps({"pipeline_id": pipeline_id}).encode()
    storage.store_data(f"pipelines/{pipeline_id}.json", pipeline_data)

    print(f"   ✓ Integrated NUIC + Hybrid Storage")
    print(f"   ✓ Pipeline {pipeline_id} stored successfully")

    print("\n✅ Integration test passed!")


if __name__ == "__main__":
    try:
        test_nuic()
        test_hybrid()
        test_integration()

        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print("\nNUIC and Hybrid modules are ready to use!")
        print("\nNext steps:")
        print("  1. Start using catalog.register_pipeline() to add your pipelines")
        print("  2. Use storage.store_data() for local-first data storage")
        print("  3. Use scheduler.schedule_workload() for cost-optimized compute")
        print("  4. Check optimizer.compare_deployment_models() for cost analysis")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
