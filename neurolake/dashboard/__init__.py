"""
NeuroLake Unified Dashboard
===========================

A comprehensive web interface that integrates all NeuroLake features:
- SQL Query Editor
- Data Explorer
- Metadata Browser
- Query History
- System Monitoring
- Performance Analytics
- AI-powered insights

Similar to Databricks unified platform.
"""

from neurolake.dashboard.app import create_dashboard_app

__all__ = ["create_dashboard_app"]
