"""
Execution Engine for Running Migrated Jobs
Supports SQL and Spark execution with monitoring
"""

import json
import time
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class ExecutionStatus(Enum):
    """Job execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionEngine:
    """Execute migrated SQL/Spark jobs with monitoring"""

    def __init__(self):
        self.executions = {}  # Store execution history

    def execute_sql(self, sql_code: str, connection_config: Dict, execution_id: Optional[str] = None) -> Dict:
        """
        Execute SQL code

        Args:
            sql_code: SQL to execute
            connection_config: Database connection configuration
            execution_id: Optional execution ID for tracking

        Returns:
            Execution result
        """

        if not execution_id:
            execution_id = f"sql_exec_{int(time.time())}"

        execution = {
            'execution_id': execution_id,
            'type': 'sql',
            'status': ExecutionStatus.PENDING.value,
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'duration_seconds': None,
            'rows_affected': 0,
            'error': None,
            'warnings': [],
            'metrics': {}
        }

        self.executions[execution_id] = execution

        try:
            # Update status
            execution['status'] = ExecutionStatus.RUNNING.value

            # In production, would execute actual SQL
            # import psycopg2 or appropriate driver
            # connection = psycopg2.connect(**connection_config)
            # cursor = connection.cursor()
            # cursor.execute(sql_code)
            # ...

            # Simulate execution
            time.sleep(0.1)  # Simulated delay

            # Update completion
            execution['status'] = ExecutionStatus.COMPLETED.value
            execution['end_time'] = datetime.now().isoformat()
            execution['rows_affected'] = 0  # Would be actual count
            execution['message'] = 'Execution completed successfully'

        except Exception as e:
            execution['status'] = ExecutionStatus.FAILED.value
            execution['end_time'] = datetime.now().isoformat()
            execution['error'] = str(e)

        return execution

    def execute_spark(self, spark_code: str, spark_config: Dict, execution_id: Optional[str] = None) -> Dict:
        """
        Execute Spark job

        Args:
            spark_code: PySpark code to execute
            spark_config: Spark configuration
            execution_id: Optional execution ID

        Returns:
            Execution result
        """

        if not execution_id:
            execution_id = f"spark_exec_{int(time.time())}"

        execution = {
            'execution_id': execution_id,
            'type': 'spark',
            'status': ExecutionStatus.PENDING.value,
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'duration_seconds': None,
            'stages': [],
            'tasks_completed': 0,
            'tasks_total': 0,
            'error': None,
            'metrics': {
                'input_records': 0,
                'output_records': 0,
                'shuffle_read': 0,
                'shuffle_write': 0
            }
        }

        self.executions[execution_id] = execution

        try:
            execution['status'] = ExecutionStatus.RUNNING.value

            # In production:
            # from pyspark.sql import SparkSession
            # spark = SparkSession.builder.config(spark_config).getOrCreate()
            # exec(spark_code)

            # Simulate execution
            time.sleep(0.1)

            execution['status'] = ExecutionStatus.COMPLETED.value
            execution['end_time'] = datetime.now().isoformat()
            execution['message'] = 'Spark job completed successfully'

        except Exception as e:
            execution['status'] = ExecutionStatus.FAILED.value
            execution['end_time'] = datetime.now().isoformat()
            execution['error'] = str(e)

        return execution

    def get_execution_status(self, execution_id: str) -> Optional[Dict]:
        """Get status of an execution"""
        return self.executions.get(execution_id)

    def list_executions(self, limit: int = 100) -> List[Dict]:
        """List recent executions"""
        executions = list(self.executions.values())
        executions.sort(key=lambda x: x['start_time'], reverse=True)
        return executions[:limit]

    def cancel_execution(self, execution_id: str) -> Dict:
        """Cancel a running execution"""
        execution = self.executions.get(execution_id)

        if not execution:
            return {'success': False, 'error': 'Execution not found'}

        if execution['status'] != ExecutionStatus.RUNNING.value:
            return {'success': False, 'error': 'Execution is not running'}

        # In production, would cancel actual job
        execution['status'] = ExecutionStatus.CANCELLED.value
        execution['end_time'] = datetime.now().isoformat()

        return {'success': True, 'message': 'Execution cancelled'}

    def get_execution_metrics(self, execution_id: str) -> Dict:
        """Get detailed metrics for an execution"""
        execution = self.executions.get(execution_id)

        if not execution:
            return {'error': 'Execution not found'}

        # Calculate duration
        if execution['start_time'] and execution['end_time']:
            start = datetime.fromisoformat(execution['start_time'])
            end = datetime.fromisoformat(execution['end_time'])
            duration = (end - start).total_seconds()
            execution['duration_seconds'] = duration

        return {
            'execution_id': execution_id,
            'status': execution['status'],
            'duration_seconds': execution.get('duration_seconds'),
            'metrics': execution.get('metrics', {}),
            'rows_affected': execution.get('rows_affected', 0)
        }

    def compare_executions(self, original_exec_id: str, converted_exec_id: str) -> Dict:
        """
        Compare results of original vs converted execution
        For validation purposes
        """

        original = self.executions.get(original_exec_id)
        converted = self.executions.get(converted_exec_id)

        if not original or not converted:
            return {'error': 'One or both executions not found'}

        comparison = {
            'original_execution': original_exec_id,
            'converted_execution': converted_exec_id,
            'status_match': original['status'] == converted['status'],
            'rows_match': original.get('rows_affected') == converted.get('rows_affected'),
            'performance_comparison': {
                'original_duration': original.get('duration_seconds'),
                'converted_duration': converted.get('duration_seconds')
            },
            'results_equivalent': False  # Would need actual data comparison
        }

        return comparison
