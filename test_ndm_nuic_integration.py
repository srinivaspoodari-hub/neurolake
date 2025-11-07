#!/usr/bin/env python3
"""
Test script for NDM + NUIC integration
Verifies all components are working together
"""

import asyncio
import sys
from pathlib import Path

# Add neurolake to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_imports():
    """Test that all required modules can be imported"""
    print("=" * 80)
    print("TEST 1: Import Verification")
    print("=" * 80)

    try:
        from neurolake.ingestion import SmartIngestor, IngestionConfig
        print("[OK] Ingestion module imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import ingestion module: {e}")
        return False

    try:
        from neurolake.nuic import (
            NUICEngine,
            CatalogQueryAPI,
            LineageGraph,
            SchemaEvolutionTracker
        )
        print("[OK] NUIC modules imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import NUIC modules: {e}")
        return False

    try:
        from neurolake_api_integration import router
        print("[OK] API integration router imported successfully")
    except ImportError as e:
        print(f"[FAIL] Failed to import API router: {e}")
        return False

    try:
        from fastapi import FastAPI
        from uvicorn import Config
        print("[OK] FastAPI and Uvicorn available")
    except ImportError as e:
        print(f"[FAIL] Failed to import FastAPI/Uvicorn: {e}")
        return False

    print("\n[OK] All imports successful!\n")
    return True


async def test_api_routes():
    """Test that all API routes are properly registered"""
    print("=" * 80)
    print("TEST 2: API Routes Verification")
    print("=" * 80)

    try:
        from neurolake_api_integration import router
        from fastapi import FastAPI

        # Create test app
        app = FastAPI()
        app.include_router(router)

        # Get all routes
        routes = [route.path for route in app.routes]

        expected_routes = [
            "/api/neurolake/ingestion/upload",
            "/api/neurolake/ingestion/statistics",
            "/api/neurolake/catalog/search",
            "/api/neurolake/catalog/dataset/{dataset_id}",
            "/api/neurolake/catalog/insights/{dataset_id}",
            "/api/neurolake/catalog/popular",
            "/api/neurolake/catalog/quality-leaders",
            "/api/neurolake/lineage/downstream/{dataset_id}",
            "/api/neurolake/lineage/upstream/{dataset_id}",
            "/api/neurolake/lineage/impact/{dataset_id}",
            "/api/neurolake/schema/history/{dataset_id}",
            "/api/neurolake/schema/compare/{dataset_id}",
            "/api/neurolake/quality/time-series/{dataset_id}",
            "/api/neurolake/quality/current/{dataset_id}",
            "/api/neurolake/system/status",
            "/api/neurolake/system/health"
        ]

        print(f"Total routes registered: {len(routes)}")

        missing_routes = []
        for expected in expected_routes:
            if expected not in routes:
                missing_routes.append(expected)

        if missing_routes:
            print("\n[FAIL] Missing routes:")
            for route in missing_routes:
                print(f"  - {route}")
            return False
        else:
            print("\n[OK] All expected API routes are registered!")
            print("\nRegistered routes:")
            for route in sorted([r for r in routes if r.startswith("/api/neurolake")]):
                print(f"  - {route}")

        print()
        return True

    except Exception as e:
        print(f"\n[FAIL] Failed to verify API routes: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_ui_files():
    """Test that all UI files exist"""
    print("=" * 80)
    print("TEST 3: UI Files Verification")
    print("=" * 80)

    base_path = Path(__file__).parent

    required_files = [
        "advanced_databricks_dashboard.py",
        "neurolake_api_integration.py",
        "neurolake_ui_integration.html"
    ]

    all_exist = True
    for file in required_files:
        file_path = base_path / file
        if file_path.exists():
            print(f"[OK] {file} exists ({file_path.stat().st_size:,} bytes)")
        else:
            print(f"[FAIL] {file} NOT FOUND")
            all_exist = False

    print()
    return all_exist


async def test_ndm_components():
    """Test NDM (NeuroLake Data Management) components"""
    print("=" * 80)
    print("TEST 4: NDM Components")
    print("=" * 80)

    try:
        from neurolake.ingestion import SmartIngestor

        # Try to instantiate SmartIngestor
        print("Creating SmartIngestor instance...")
        ingestor = SmartIngestor()
        print("[OK] SmartIngestor instantiated successfully")

        # Check if statistics method exists
        if hasattr(ingestor, 'get_statistics'):
            print("[OK] get_statistics method available")
        else:
            print("[FAIL] get_statistics method not found")
            return False

        if hasattr(ingestor, 'ingest'):
            print("[OK] ingest method available")
        else:
            print("[FAIL] ingest method not found")
            return False

        print("\n[OK] NDM components verified!\n")
        return True

    except Exception as e:
        print(f"\n[FAIL] NDM component test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_nuic_components():
    """Test NUIC (NeuroLake Unified Intelligence Catalog) components"""
    print("=" * 80)
    print("TEST 5: NUIC Components")
    print("=" * 80)

    try:
        from neurolake.nuic import NUICEngine, CatalogQueryAPI, LineageGraph

        print("Creating NUIC engine...")
        nuic = NUICEngine()
        print("[OK] NUIC engine instantiated successfully")

        print("Creating Catalog API...")
        catalog = CatalogQueryAPI(nuic)
        print("[OK] Catalog API instantiated successfully")

        print("Creating Lineage Graph...")
        lineage = LineageGraph(nuic)
        print("[OK] Lineage Graph instantiated successfully")

        # Check methods
        methods = [
            ('nuic', 'get_dataset'),
            ('nuic', 'search_datasets'),
            ('catalog', 'search'),
            ('lineage', 'get_downstream_lineage'),
            ('lineage', 'get_upstream_lineage')
        ]

        print("\nVerifying methods:")
        for obj_name, method in methods:
            obj = locals()[obj_name]
            if hasattr(obj, method):
                print(f"  [OK] {obj_name}.{method} available")
            else:
                print(f"  [FAIL] {obj_name}.{method} NOT FOUND")
                return False

        print("\n[OK] NUIC components verified!\n")
        return True

    except Exception as e:
        print(f"\n[FAIL] NUIC component test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_dashboard_integration():
    """Test that dashboard has the integration"""
    print("=" * 80)
    print("TEST 6: Dashboard Integration")
    print("=" * 80)

    try:
        # Read dashboard file
        dashboard_path = Path(__file__).parent / "advanced_databricks_dashboard.py"
        with open(dashboard_path, 'r') as f:
            dashboard_content = f.read()

        # Check for API router integration
        if 'from neurolake_api_integration import router as neurolake_router' in dashboard_content:
            print("[OK] API router imported in dashboard")
        else:
            print("[FAIL] API router NOT imported in dashboard")
            return False

        if 'app.include_router(neurolake_router)' in dashboard_content:
            print("[OK] API router included in app")
        else:
            print("[FAIL] API router NOT included in app")
            return False

        if '@app.get("/ndm-nuic"' in dashboard_content:
            print("[OK] NDM-NUIC UI route registered")
        else:
            print("[FAIL] NDM-NUIC UI route NOT registered")
            return False

        if 'Data Ingestion & Catalog' in dashboard_content:
            print("[OK] Navigation link added to dashboard")
        else:
            print("[FAIL] Navigation link NOT found")
            return False

        print("\n[OK] Dashboard integration verified!\n")
        return True

    except Exception as e:
        print(f"\n[FAIL] Dashboard integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n")
    print("=" * 80)
    print(" NDM + NUIC INTEGRATION TEST SUITE")
    print("=" * 80)
    print()

    tests = [
        ("Import Verification", test_imports),
        ("API Routes Verification", test_api_routes),
        ("UI Files Verification", test_ui_files),
        ("NDM Components", test_ndm_components),
        ("NUIC Components", test_nuic_components),
        ("Dashboard Integration", test_dashboard_integration)
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n[FAIL] Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n")
    print("=" * 80)
    print(" TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"{status}  {test_name}")

    print()
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] ALL TESTS PASSED! Integration is complete and working!")
        print("\nNext steps:")
        print("1. Start the dashboard: python advanced_databricks_dashboard.py")
        print("2. Open browser: http://localhost:8000")
        print("3. Navigate to 'Data Ingestion & Catalog' from top menu")
        print("4. Test file upload and catalog browsing")
        return 0
    else:
        print(f"\n[WARNING]  {total - passed} test(s) failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
