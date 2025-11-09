#!/usr/bin/env python3
"""
E2E Testing via Docker Deployment
Tests all functionalities through the Dockerized dashboard
"""
import requests
import json
import time
import sys

BASE_URL = "http://localhost:5000"

print("="*80)
print(" NEUROLAKE DOCKER E2E TESTING")
print(" Testing all functionalities via Docker deployment")
print("="*80)
print()

# Wait for dashboard to be ready
print("[SETUP] Waiting for dashboard to be ready...")
max_retries = 30
for i in range(max_retries):
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        if response.status_code == 200:
            print(f"[OK] Dashboard is ready after {i+1} attempts!")
            break
    except:
        if i < max_retries - 1:
            print(f"[WAIT] Attempt {i+1}/{max_retries}... Dashboard not ready yet.")
            time.sleep(2)
        else:
            print(f"[ERROR] Dashboard did not become ready after {max_retries} attempts")
            sys.exit(1)

print()

# Test counter
tests_passed = 0
tests_failed = 0

def test_endpoint(name, method, url, payload=None, expected_status=200):
    """Test a single endpoint"""
    global tests_passed, tests_failed

    print(f"[TEST] {name}")
    print(f"       {method} {url}")

    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=payload, timeout=10)
        else:
            print(f"[ERROR] Unsupported method: {method}")
            tests_failed += 1
            return None

        if response.status_code == expected_status or response.status_code == 200:
            print(f"[OK] Status: {response.status_code}")
            try:
                data = response.json()
                print(f"     Response keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
                tests_passed += 1
                return data
            except:
                print(f"     Response: {response.text[:100]}")
                tests_passed += 1
                return response.text
        else:
            print(f"[WARN] Status: {response.status_code}")
            print(f"       Response: {response.text[:200]}")
            tests_failed += 1
            return None

    except Exception as e:
        print(f"[ERROR] {e}")
        tests_failed += 1
        return None

print("="*80)
print(" TEST 1: NCF (NeuroLake Common Format)")
print("="*80)
print()

# Test 1.1: List NCF tables
test_endpoint(
    "List NCF Tables",
    "GET",
    f"{BASE_URL}/api/ncf/tables"
)
print()

# Test 1.2: Create NCF table
test_endpoint(
    "Create NCF Table - employee",
    "POST",
    f"{BASE_URL}/api/ncf/tables/create",
    payload={
        "table_name": "employee",
        "schema": {
            "emp_id": "int64",
            "emp_name": "string",
            "emp_email": "string",
            "emp_phone": "string",
            "dept_id": "int64",
            "salary": "float64",
            "ssn": "string"
        }
    }
)
print()

# Test 1.3: PII Detection
test_endpoint(
    "Detect PII in employee table",
    "GET",
    f"{BASE_URL}/api/ncf/tables/employee/pii"
)
print()

# Test 1.4: Get table schema
test_endpoint(
    "Get employee table schema",
    "GET",
    f"{BASE_URL}/api/ncf/tables/employee/schema"
)
print()

# Test 1.5: PII Compliance Report
test_endpoint(
    "Get PII Compliance Report",
    "GET",
    f"{BASE_URL}/api/ncf/compliance/pii-report"
)
print()

print("="*80)
print(" TEST 2: Cloud Authentication")
print("="*80)
print()

# Test 2.1: Get cloud auth status
test_endpoint(
    "Get Cloud Auth Status",
    "GET",
    f"{BASE_URL}/api/cloud/auth/status"
)
print()

# Test 2.2: Configure AWS (mock)
test_endpoint(
    "Configure AWS Authentication",
    "POST",
    f"{BASE_URL}/api/cloud/auth/configure",
    payload={
        "provider": "aws",
        "config": {
            "region": "us-east-1",
            "use_iam_role": True
        }
    }
)
print()

print("="*80)
print(" TEST 3: NeuroLake Catalog")
print("="*80)
print()

# Test 3.1: Search catalog
test_endpoint(
    "Search Catalog for 'employee'",
    "GET",
    f"{BASE_URL}/api/neurolake/catalog/search?query=employee"
)
print()

print("="*80)
print(" TEST 4: Data Ingestion")
print("="*80)
print()

# Test 4.1: Ingest employee data
test_endpoint(
    "Ingest employee.json",
    "POST",
    f"{BASE_URL}/api/neurolake/ingestion/ingest",
    payload={
        "file_path": "/app/test_data_e2e/employee.json",
        "dataset_name": "employee",
        "use_case": "analytics"
    }
)
print()

print("="*80)
print(" TEST 5: SQL Query Execution")
print("="*80)
print()

# Test 5.1: Execute simple query
test_endpoint(
    "Execute SQL Query",
    "POST",
    f"{BASE_URL}/api/query/execute",
    payload={
        "sql": "SELECT 'Docker E2E Test' as test_message, CURRENT_TIMESTAMP as timestamp",
        "limit": 10
    }
)
print()

print("="*80)
print(" TEST 6: Data Lineage")
print("="*80)
print()

# Test 6.1: Get lineage
test_endpoint(
    "Get Lineage for employee table",
    "GET",
    f"{BASE_URL}/api/neurolake/lineage/table/employee"
)
print()

print("="*80)
print(" TEST 7: Schema Evolution")
print("="*80)
print()

# Test 7.1: Get schema history
test_endpoint(
    "Get Schema History for employee",
    "GET",
    f"{BASE_URL}/api/neurolake/schema/history/employee"
)
print()

print("="*80)
print(" TEST 8: Quality Metrics")
print("="*80)
print()

# Test 8.1: Get quality metrics
test_endpoint(
    "Get Quality Metrics for employee",
    "GET",
    f"{BASE_URL}/api/neurolake/quality/metrics/employee"
)
print()

print("="*80)
print(" TEST 9: Notebooks")
print("="*80)
print()

# Test 9.1: List notebooks
test_endpoint(
    "List Notebooks",
    "GET",
    f"{BASE_URL}/api/notebooks"
)
print()

print("="*80)
print(" TEST SUMMARY")
print("="*80)
print()
print(f"Tests Passed: {tests_passed}")
print(f"Tests Failed: {tests_failed}")
print(f"Total Tests: {tests_passed + tests_failed}")
print(f"Success Rate: {(tests_passed/(tests_passed+tests_failed)*100):.1f}%" if (tests_passed + tests_failed) > 0 else "N/A")
print()

if tests_failed == 0:
    print("[SUCCESS] All tests passed!")
    print()
    print("Dashboard is fully functional via Docker!")
    print("Access at: http://localhost:5000")
else:
    print(f"[WARN] {tests_failed} test(s) failed")
    print("Some features may need troubleshooting")

print()
print("="*80)
