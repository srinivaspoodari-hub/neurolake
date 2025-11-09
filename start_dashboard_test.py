#!/usr/bin/env python3
"""
Quick test script to start dashboard on port 5001 to avoid conflicts
"""
import sys
import os

# Add neurolake to path
sys.path.insert(0, os.path.dirname(__file__))

# Import and modify the dashboard
import importlib.util

# Load the dashboard module
spec = importlib.util.spec_from_file_location("dashboard", "advanced_databricks_dashboard.py")
dashboard = importlib.util.module_from_spec(spec)

# Execute the module but intercept uvicorn.run
original_run = None

def custom_run(app, **kwargs):
    """Run on port 5001 instead"""
    kwargs['port'] = 5001
    print(f"\n{'='*80}")
    print("[CUSTOM] Starting dashboard on port 5001 to avoid conflicts")
    print(f"{'='*80}\n")
    import uvicorn
    return uvicorn.run(app, **kwargs)

# Monkey patch uvicorn.run before loading
import uvicorn
original_run = uvicorn.run
uvicorn.run = custom_run

# Now execute the dashboard
spec.loader.exec_module(dashboard)
