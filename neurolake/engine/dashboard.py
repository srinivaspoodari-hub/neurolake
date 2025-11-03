"""
Simple Query Dashboard

Display query execution statistics and metrics.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd


class QueryDashboard:
    """
    Simple dashboard for query metrics and statistics.
    """
    
    def __init__(self, history_store=None):
        """Initialize dashboard with history store."""
        self.history_store = history_store
    
    def get_summary_stats(
        self, queries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get summary statistics for queries.
        
        Args:
            queries: List of query history entries
            
        Returns:
            Dict with summary statistics
        """
        if not queries:
            return {
                "total_queries": 0,
                "successful": 0,
                "failed": 0,
                "avg_execution_time": 0,
                "total_rows": 0,
            }
        
        df = pd.DataFrame(queries)
        
        stats = {
            "total_queries": len(df),
            "successful": len(df[df.get("status", df.get("query_status")) == "success"]),
            "failed": len(df[df.get("status", df.get("query_status")) == "failed"]),
            "avg_execution_time": df["execution_time"].mean() if "execution_time" in df else 0,
            "total_rows": df["row_count"].sum() if "row_count" in df else 0,
            "unique_tables": len(set([t for tables in df.get("table_names", []) if tables for t in tables])) if "table_names" in df else 0,
        }
        
        return stats
    
    def get_slow_queries(
        self, queries: List[Dict[str, Any]], threshold_seconds: float = 1.0
    ) -> List[Dict[str, Any]]:
        """Get queries slower than threshold."""
        slow = []
        for q in queries:
            exec_time = q.get("execution_time", 0)
            if exec_time > threshold_seconds:
                slow.append({
                    "query_id": q["query_id"],
                    "sql": q["sql"][:100],
                    "execution_time": exec_time,
                    "timestamp": q.get("timestamp", ""),
                })
        
        return sorted(slow, key=lambda x: x["execution_time"], reverse=True)
    
    def get_failed_queries(
        self, queries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Get failed queries."""
        failed = []
        for q in queries:
            if q.get("status", q.get("query_status")) == "failed":
                failed.append({
                    "query_id": q["query_id"],
                    "sql": q["sql"][:100],
                    "error": q.get("error", "Unknown error"),
                    "timestamp": q.get("timestamp", ""),
                })
        
        return failed
    
    def get_table_usage(
        self, queries: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Get table usage statistics."""
        table_counts = {}
        
        for q in queries:
            tables = q.get("table_names", q.get("tables_accessed", []))
            if tables:
                for table in tables:
                    table_counts[table] = table_counts.get(table, 0) + 1
        
        return dict(sorted(table_counts.items(), key=lambda x: x[1], reverse=True))
    
    def print_dashboard(self, queries: List[Dict[str, Any]]):
        """Print dashboard to console."""
        print("\n" + "=" * 60)
        print("NEUROLAKE QUERY DASHBOARD")
        print("=" * 60)
        
        # Summary
        stats = self.get_summary_stats(queries)
        print("\nSUMMARY:")
        print(f"  Total Queries: {stats['total_queries']}")
        print(f"  Successful:    {stats['successful']}")
        print(f"  Failed:        {stats['failed']}")
        print(f"  Avg Exec Time: {stats['avg_execution_time']:.3f}s")
        print(f"  Total Rows:    {stats['total_rows']}")
        
        # Slow queries
        slow = self.get_slow_queries(queries, threshold_seconds=0.5)
        if slow:
            print(f"\nSLOW QUERIES (>{0.5}s):")
            for q in slow[:5]:
                print(f"  {q['execution_time']:.3f}s - {q['sql']}...")
        
        # Failed queries
        failed = self.get_failed_queries(queries)
        if failed:
            print(f"\nFAILED QUERIES:")
            for q in failed[:5]:
                print(f"  {q['error']}: {q['sql']}...")
        
        # Table usage
        tables = self.get_table_usage(queries)
        if tables:
            print(f"\nTOP TABLES:")
            for table, count in list(tables.items())[:5]:
                print(f"  {table}: {count} queries")
        
        print("\n" + "=" * 60 + "\n")


__all__ = ["QueryDashboard"]
