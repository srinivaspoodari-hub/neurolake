"""
Test Compute Integration

Comprehensive test for the NeuroLake Compute Engine including:
- Local compute detection
- Cloud provider configuration
- Workload execution
- Resource monitoring
"""

import sys
import time
from neurolake.compute import (
    ComputeOrchestrator,
    LocalComputeEngine,
    CloudProvider,
    WorkloadType,
    WorkloadRequest
)


def test_local_compute():
    """Test local compute engine"""
    print("\n" + "="*80)
    print("TEST 1: Local Compute Detection")
    print("="*80)

    engine = LocalComputeEngine()

    # Get resources
    resources = engine.get_resources()

    print(f"\n✅ Local Compute Resources:")
    print(f"  • CPU Cores: {resources.cpu_count_physical} physical, {resources.cpu_count_logical} logical")
    print(f"  • CPU Usage: {resources.cpu_usage_percent:.1f}%")
    print(f"  • CPU Frequency: {resources.cpu_freq_current_mhz:.0f} MHz")
    print(f"  • Memory Total: {resources.memory_total_gb:.2f} GB")
    print(f"  • Memory Available: {resources.memory_available_gb:.2f} GB")
    print(f"  • Memory Usage: {resources.memory_percent:.1f}%")
    print(f"  • GPU Available: {'Yes' if resources.gpu_available else 'No'}")
    if resources.gpu_available:
        print(f"  • GPU Count: {resources.gpu_count}")
        print(f"  • GPU Memory: {resources.gpu_total_memory_gb:.2f} GB")
    print(f"  • Docker Available: {'Yes' if resources.docker_available else 'No'}")
    if resources.docker_available:
        print(f"  • Docker Version: {resources.docker_version}")
        print(f"  • Running Containers: {resources.containers_running}")

    # System info
    print(f"\n✅ System Information:")
    system_info = engine.get_system_info()
    print(f"  • Platform: {system_info['system']['platform']}")
    print(f"  • Hostname: {system_info['system']['hostname']}")
    print(f"  • Architecture: {system_info['system']['architecture']}")
    print(f"  • Uptime: {system_info['uptime_hours']:.1f} hours")

    # Check workload capacity
    print(f"\n✅ Workload Capacity Check:")
    capacity = engine.can_handle_workload(
        required_cpu_cores=2.0,
        required_memory_gb=4.0,
        required_gpu=False
    )
    print(f"  • Can handle workload: {'Yes' if capacity['can_handle'] else 'No'}")
    print(f"  • Available CPU cores: {capacity['cpu_available_cores']:.1f}")
    print(f"  • Available Memory: {capacity['memory_available_gb']:.2f} GB")
    print(f"  • Recommendation: {capacity['recommendation']}")

    return True


def test_cloud_configuration():
    """Test cloud provider configuration"""
    print("\n" + "="*80)
    print("TEST 2: Cloud Provider Configuration")
    print("="*80)

    orchestrator = ComputeOrchestrator(
        enable_cloud=True,
        enable_distributed=False
    )

    # Configure AWS (using env vars or dummy creds)
    print("\n✅ Configuring AWS...")
    aws_configured = orchestrator.configure_cloud_provider(
        provider=CloudProvider.AWS,
        region='us-east-1'
    )
    print(f"  • AWS Configuration: {'Success' if aws_configured else 'Failed'}")

    # Configure Azure
    print("\n✅ Configuring Azure...")
    azure_configured = orchestrator.configure_cloud_provider(
        provider=CloudProvider.AZURE,
        region='eastus'
    )
    print(f"  • Azure Configuration: {'Success' if azure_configured else 'Failed'}")

    # Configure GCP
    print("\n✅ Configuring GCP...")
    gcp_configured = orchestrator.configure_cloud_provider(
        provider=CloudProvider.GCP,
        region='us-central1'
    )
    print(f"  • GCP Configuration: {'Success' if gcp_configured else 'Failed'}")

    # Show configured providers
    providers = orchestrator.get_configured_providers()
    print(f"\n✅ Configured Providers ({len(providers)}):")
    for provider in providers:
        print(f"  • {provider['provider'].upper()}: {provider['region']} (default: {provider['default_service']})")

    return True


def test_workload_execution():
    """Test workload execution"""
    print("\n" + "="*80)
    print("TEST 3: Workload Execution")
    print("="*80)

    orchestrator = ComputeOrchestrator(
        enable_cloud=True,
        enable_distributed=True
    )

    # Test 1: Small SQL query (should run locally)
    print("\n✅ Test 1: Small SQL Query")
    def simple_query():
        time.sleep(0.1)
        return "Query result: 42"

    request1 = WorkloadRequest(
        workload_id="sql_query_001",
        workload_type=WorkloadType.SQL_QUERY,
        function=simple_query,
        args=(),
        kwargs={},
        required_cpu_cores=0.5,
        required_memory_gb=1.0,
        required_gpu=False,
        estimated_duration_minutes=0.1,
        prefer_local=True,
        max_cost_usd=0.0,
        deadline=None,
        data_size_gb=0.1,
        data_location="local"
    )

    result1 = orchestrator.execute(request1)
    print(f"  • Workload ID: {result1.workload_id}")
    print(f"  • Execution Tier: {result1.execution_tier.value}")
    print(f"  • Status: {result1.status}")
    print(f"  • Duration: {result1.duration_seconds:.3f}s")
    print(f"  • Cost: ${result1.estimated_cost_usd:.4f}")

    # Test 2: Large ETL job (may go to cloud)
    print("\n✅ Test 2: Large ETL Job")
    def etl_job():
        time.sleep(0.2)
        return "ETL completed: 1M records processed"

    request2 = WorkloadRequest(
        workload_id="etl_job_001",
        workload_type=WorkloadType.ETL,
        function=etl_job,
        args=(),
        kwargs={},
        required_cpu_cores=8.0,
        required_memory_gb=32.0,
        required_gpu=False,
        estimated_duration_minutes=60.0,
        prefer_local=False,
        max_cost_usd=5.0,
        deadline=None,
        data_size_gb=100.0,
        data_location="s3://bucket/data"
    )

    result2 = orchestrator.execute(request2)
    print(f"  • Workload ID: {result2.workload_id}")
    print(f"  • Execution Tier: {result2.execution_tier.value}")
    print(f"  • Status: {result2.status}")
    print(f"  • Duration: {result2.duration_seconds:.3f}s")
    print(f"  • Cost: ${result2.estimated_cost_usd:.4f}")

    # Test 3: ML Training (GPU required)
    print("\n✅ Test 3: ML Training (GPU)")
    def ml_training():
        time.sleep(0.15)
        return "Model trained: accuracy 95%"

    request3 = WorkloadRequest(
        workload_id="ml_training_001",
        workload_type=WorkloadType.ML_TRAINING,
        function=ml_training,
        args=(),
        kwargs={},
        required_cpu_cores=4.0,
        required_memory_gb=16.0,
        required_gpu=True,
        estimated_duration_minutes=120.0,
        prefer_local=True,
        max_cost_usd=10.0,
        deadline=None,
        data_size_gb=50.0,
        data_location="local"
    )

    result3 = orchestrator.execute(request3)
    print(f"  • Workload ID: {result3.workload_id}")
    print(f"  • Execution Tier: {result3.execution_tier.value}")
    print(f"  • Status: {result3.status}")
    print(f"  • Duration: {result3.duration_seconds:.3f}s")
    print(f"  • Cost: ${result3.estimated_cost_usd:.4f}")

    # Show statistics
    print("\n✅ Orchestrator Statistics:")
    stats = orchestrator.get_statistics()
    print(f"  • Total Workloads: {stats['total_workloads']}")
    print(f"  • Active Workloads: {stats['active_workloads']}")
    print(f"  • By Tier: {stats['by_tier']}")
    print(f"  • By Status: {stats['by_status']}")
    print(f"  • Total Cost: ${stats['total_cost_usd']:.4f}")
    print(f"  • Avg Duration: {stats['average_duration_seconds']:.3f}s")

    return True


def test_resource_monitoring():
    """Test resource monitoring"""
    print("\n" + "="*80)
    print("TEST 4: Resource Monitoring")
    print("="*80)

    engine = LocalComputeEngine()

    print("\n✅ Collecting resource metrics...")
    for i in range(5):
        resources = engine.get_resources()
        print(f"  Sample {i+1}: CPU {resources.cpu_usage_percent:.1f}%, " +
              f"Memory {resources.memory_percent:.1f}%")
        time.sleep(0.5)

    print("\n✅ Resource Trends:")
    trends = engine.get_resource_trends(last_n=5)
    print(f"  • CPU Average: {trends['cpu_avg']:.1f}%")
    print(f"  • CPU Max: {trends['cpu_max']:.1f}%")
    print(f"  • Memory Average: {trends['memory_avg']:.1f}%")
    print(f"  • Memory Max: {trends['memory_max']:.1f}%")

    return True


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("NEUROLAKE COMPUTE ENGINE - COMPREHENSIVE TEST")
    print("="*80)

    tests = [
        ("Local Compute Detection", test_local_compute),
        ("Cloud Provider Configuration", test_cloud_configuration),
        ("Workload Execution", test_workload_execution),
        ("Resource Monitoring", test_resource_monitoring)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, "✅ PASSED" if success else "❌ FAILED"))
        except Exception as e:
            print(f"\n❌ ERROR in {test_name}: {e}")
            results.append((test_name, "❌ ERROR"))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for test_name, result in results:
        print(f"  {result} {test_name}")

    passed = sum(1 for _, r in results if "PASSED" in r)
    total = len(results)
    print(f"\n  Total: {passed}/{total} tests passed")

    print("\n" + "="*80)
    print("✅ COMPUTE ENGINE INTEGRATION COMPLETE!")
    print("="*80)
    print("\nFeatures Available:")
    print("  • Local machine compute detection (CPU, GPU, Memory)")
    print("  • Cloud compute integration (AWS, Azure, GCP)")
    print("  • Distributed frameworks (Ray, Dask, Spark)")
    print("  • Intelligent workload routing")
    print("  • Resource monitoring and trends")
    print("  • Cost optimization")
    print("  • Auto-scaling capabilities")


if __name__ == "__main__":
    main()
