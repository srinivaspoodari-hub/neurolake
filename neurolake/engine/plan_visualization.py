"""
Query Plan Visualization

Visualize SQL query execution plans in a readable format.
"""

from typing import Dict, Any, List, Optional
import re


class QueryPlanVisualizer:
    """
    Visualize SQL query execution plans.

    Provides methods to format and display query plans in various formats.
    """

    def __init__(self):
        pass

    def format_plan(
        self,
        plan_info: Dict[str, Any],
        format: str = "tree"
    ) -> str:
        """
        Format query plan for display.

        Args:
            plan_info: Plan information from engine.get_query_plan()
            format: Output format ("tree", "table", "compact")

        Returns:
            Formatted plan string
        """
        if format == "tree":
            return self._format_tree(plan_info)
        elif format == "table":
            return self._format_table(plan_info)
        elif format == "compact":
            return self._format_compact(plan_info)
        else:
            return plan_info.get("plan_text", "")

    def _format_tree(self, plan_info: Dict[str, Any]) -> str:
        """Format as tree structure."""
        output = []
        output.append("=" * 60)
        output.append("QUERY EXECUTION PLAN")
        output.append("=" * 60)
        output.append(f"Backend: {plan_info.get('backend', 'unknown')}")
        output.append(f"SQL: {plan_info.get('sql', '')[:100]}...")
        output.append("")

        if "estimated_cost" in plan_info:
            output.append(f"Estimated Cost: {plan_info['estimated_cost']}")
        if "estimated_rows" in plan_info:
            output.append(f"Estimated Rows: {plan_info['estimated_rows']}")

        output.append("")
        output.append("Plan:")
        output.append("-" * 60)

        # Indent plan lines to show tree structure
        plan_lines = plan_info.get("plan_lines", [])
        for line in plan_lines:
            # Detect indentation level
            stripped = line.lstrip()
            indent_level = len(line) - len(stripped)

            # Add tree characters
            if indent_level > 0:
                prefix = "  " * (indent_level // 2) + "└─ "
            else:
                prefix = ""

            output.append(prefix + stripped)

        output.append("=" * 60)
        return "\n".join(output)

    def _format_table(self, plan_info: Dict[str, Any]) -> str:
        """Format as table."""
        output = []
        output.append("┌" + "─" * 58 + "┐")
        output.append("│" + " QUERY EXECUTION PLAN".center(58) + "│")
        output.append("├" + "─" * 58 + "┤")

        # Add metadata
        metadata = [
            ("Backend", plan_info.get("backend", "unknown")),
            ("SQL", plan_info.get("sql", "")[:40] + "..."),
        ]

        if "estimated_cost" in plan_info:
            metadata.append(("Est. Cost", str(plan_info["estimated_cost"])))
        if "estimated_rows" in plan_info:
            metadata.append(("Est. Rows", str(plan_info["estimated_rows"])))

        for key, value in metadata:
            line = f"│ {key:15s}: {value:40s} │"
            output.append(line[:60] + "│")

        output.append("├" + "─" * 58 + "┤")

        # Add plan
        plan_lines = plan_info.get("plan_lines", [])
        for line in plan_lines[:10]:  # Limit to 10 lines
            content = line[:56] if len(line) > 56 else line
            output.append(f"│ {content:56s} │")

        if len(plan_lines) > 10:
            output.append(f"│ {'... (' + str(len(plan_lines) - 10) + ' more lines)':56s} │")

        output.append("└" + "─" * 58 + "┘")
        return "\n".join(output)

    def _format_compact(self, plan_info: Dict[str, Any]) -> str:
        """Format in compact style."""
        output = []
        output.append(f"Plan [{plan_info.get('backend', 'unknown')}]:")

        if "estimated_cost" in plan_info:
            output.append(f"  Cost: {plan_info['estimated_cost']}")
        if "estimated_rows" in plan_info:
            output.append(f"  Rows: {plan_info['estimated_rows']}")

        output.append(f"  SQL: {plan_info.get('sql', '')[:80]}...")
        return "\n".join(output)

    def print_plan(
        self,
        plan_info: Dict[str, Any],
        format: str = "tree"
    ):
        """Print formatted plan to console."""
        print(self.format_plan(plan_info, format))

    def extract_operations(self, plan_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract individual operations from plan.

        Returns:
            List of operations with their details
        """
        operations = []
        plan_lines = plan_info.get("plan_lines", [])

        for line in plan_lines:
            # Try to parse operation type
            op_match = re.search(r'(SCAN|JOIN|FILTER|PROJECT|AGGREGATE|SORT|LIMIT)', line, re.IGNORECASE)
            if op_match:
                op_type = op_match.group(1).upper()

                # Try to extract table name for scans
                table_match = re.search(r'(\w+)\s*(?:\(|$)', line)
                table_name = table_match.group(1) if table_match else None

                operations.append({
                    "type": op_type,
                    "table": table_name,
                    "details": line.strip(),
                })

        return operations

    def get_plan_summary(self, plan_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary statistics from plan.

        Returns:
            Dictionary with plan statistics
        """
        operations = self.extract_operations(plan_info)

        summary = {
            "backend": plan_info.get("backend", "unknown"),
            "total_operations": len(operations),
            "operation_types": {},
            "tables_accessed": set(),
        }

        # Count operation types
        for op in operations:
            op_type = op["type"]
            summary["operation_types"][op_type] = summary["operation_types"].get(op_type, 0) + 1

            if op["table"]:
                summary["tables_accessed"].add(op["table"])

        summary["tables_accessed"] = list(summary["tables_accessed"])

        if "estimated_cost" in plan_info:
            summary["estimated_cost"] = plan_info["estimated_cost"]
        if "estimated_rows" in plan_info:
            summary["estimated_rows"] = plan_info["estimated_rows"]

        return summary


__all__ = ["QueryPlanVisualizer"]
