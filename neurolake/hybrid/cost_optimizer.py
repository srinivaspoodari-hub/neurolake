"""
Cost Optimizer

Analyzes usage patterns and provides recommendations for cost optimization
across hybrid storage and compute.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CostOptimizer:
    """
    Provides cost optimization recommendations for hybrid deployments

    Features:
    - Cost tracking and forecasting
    - Optimization recommendations
    - ROI analysis for local vs cloud
    """

    # Cost constants (USD per month)
    COST_CLOUD_STORAGE_PER_GB = 0.023  # S3 Standard
    COST_CLOUD_TRANSFER_OUT_PER_GB = 0.09
    COST_CLOUD_COMPUTE_SMALL_PER_HOUR = 0.10
    COST_CLOUD_COMPUTE_LARGE_PER_HOUR = 0.80

    def __init__(self):
        """Initialize Cost Optimizer"""
        self.cost_history: List[Dict] = []

    def calculate_storage_cost(
        self,
        local_gb: float,
        cloud_gb: float,
        monthly_transfer_gb: float
    ) -> Dict[str, float]:
        """
        Calculate storage costs

        Args:
            local_gb: Data stored locally
            cloud_gb: Data stored in cloud
            monthly_transfer_gb: Monthly data transfer out

        Returns:
            Cost breakdown
        """
        cloud_storage_cost = cloud_gb * self.COST_CLOUD_STORAGE_PER_GB
        transfer_cost = monthly_transfer_gb * self.COST_CLOUD_TRANSFER_OUT_PER_GB

        # Local storage cost (amortized hardware)
        local_storage_cost = local_gb * 0.005  # Rough estimate for local HDD

        return {
            'local_storage_usd': local_storage_cost,
            'cloud_storage_usd': cloud_storage_cost,
            'transfer_usd': transfer_cost,
            'total_usd': local_storage_cost + cloud_storage_cost + transfer_cost
        }

    def calculate_compute_cost(
        self,
        local_hours: float,
        cloud_small_hours: float,
        cloud_large_hours: float
    ) -> Dict[str, float]:
        """
        Calculate compute costs

        Args:
            local_hours: Hours of local compute
            cloud_small_hours: Hours of small cloud compute
            cloud_large_hours: Hours of large cloud compute

        Returns:
            Cost breakdown
        """
        # Local compute cost (electricity + amortized hardware)
        local_compute_cost = local_hours * 0.02  # ~$0.02/hour estimate

        cloud_small_cost = cloud_small_hours * self.COST_CLOUD_COMPUTE_SMALL_PER_HOUR
        cloud_large_cost = cloud_large_hours * self.COST_CLOUD_COMPUTE_LARGE_PER_HOUR

        return {
            'local_compute_usd': local_compute_cost,
            'cloud_small_usd': cloud_small_cost,
            'cloud_large_usd': cloud_large_cost,
            'total_usd': local_compute_cost + cloud_small_cost + cloud_large_cost
        }

    def get_recommendations(
        self,
        storage_stats: Dict[str, Any],
        compute_stats: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Generate cost optimization recommendations

        Args:
            storage_stats: Storage usage statistics
            compute_stats: Compute usage statistics

        Returns:
            List of recommendations
        """
        recommendations = []

        # Storage recommendations
        if storage_stats.get('cloud_objects', 0) > 0:
            cache_hit_rate = storage_stats.get('cache_hit_rate', 0)
            if cache_hit_rate < 0.7:
                recommendations.append({
                    'category': 'storage',
                    'priority': 'high',
                    'recommendation': 'Increase local cache size',
                    'impact': f'Cache hit rate is {cache_hit_rate:.1%}. Increasing local storage could save 20-30% on cloud transfer costs.',
                    'estimated_savings_usd_month': 50.0
                })

        # Compute recommendations
        local_exec_pct = compute_stats.get('local_execution_pct', 0)
        if local_exec_pct < 80:
            recommendations.append({
                'category': 'compute',
                'priority': 'medium',
                'recommendation': 'Increase local compute capacity',
                'impact': f'Only {local_exec_pct:.1f}% of workloads run locally. Adding compute resources could reduce cloud costs.',
                'estimated_savings_usd_month': 100.0
            })

        # Data tiering recommendation
        if storage_stats.get('local_objects', 0) > 1000:
            recommendations.append({
                'category': 'storage',
                'priority': 'medium',
                'recommendation': 'Implement automated data tiering',
                'impact': 'Move cold data to cloud archive tier (Glacier) for 80% storage cost reduction.',
                'estimated_savings_usd_month': 30.0
            })

        return recommendations

    def forecast_monthly_cost(
        self,
        current_usage: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Forecast monthly costs based on current usage

        Args:
            current_usage: Current usage metrics

        Returns:
            Forecasted costs
        """
        # Extract usage metrics
        storage_gb = current_usage.get('storage_gb', 0)
        transfer_gb_day = current_usage.get('transfer_gb_per_day', 0)
        compute_hours_day = current_usage.get('compute_hours_per_day', 0)

        # Monthly projections
        monthly_transfer_gb = transfer_gb_day * 30
        monthly_compute_hours = compute_hours_day * 30

        storage_cost = self.calculate_storage_cost(
            local_gb=storage_gb * 0.7,  # Assume 70% local
            cloud_gb=storage_gb * 0.3,  # 30% cloud
            monthly_transfer_gb=monthly_transfer_gb
        )

        compute_cost = self.calculate_compute_cost(
            local_hours=monthly_compute_hours * 0.8,  # 80% local
            cloud_small_hours=monthly_compute_hours * 0.15,
            cloud_large_hours=monthly_compute_hours * 0.05
        )

        return {
            'storage_total_usd': storage_cost['total_usd'],
            'compute_total_usd': compute_cost['total_usd'],
            'monthly_total_usd': storage_cost['total_usd'] + compute_cost['total_usd'],
            'breakdown': {
                'storage': storage_cost,
                'compute': compute_cost
            }
        }

    def compare_deployment_models(
        self,
        monthly_data_gb: float,
        monthly_compute_hours: float
    ) -> Dict[str, Any]:
        """
        Compare costs across different deployment models

        Args:
            monthly_data_gb: Monthly data processed in GB
            monthly_compute_hours: Monthly compute hours

        Returns:
            Cost comparison
        """
        # Pure cloud deployment
        cloud_only = {
            'storage': monthly_data_gb * self.COST_CLOUD_STORAGE_PER_GB,
            'transfer': monthly_data_gb * 0.2 * self.COST_CLOUD_TRANSFER_OUT_PER_GB,  # 20% transfer out
            'compute': monthly_compute_hours * self.COST_CLOUD_COMPUTE_SMALL_PER_HOUR,
        }
        cloud_only['total'] = sum(cloud_only.values())

        # Hybrid deployment (70% local)
        hybrid = {
            'storage': (monthly_data_gb * 0.3 * self.COST_CLOUD_STORAGE_PER_GB) + (monthly_data_gb * 0.7 * 0.005),
            'transfer': monthly_data_gb * 0.05 * self.COST_CLOUD_TRANSFER_OUT_PER_GB,  # 5% transfer out
            'compute': (monthly_compute_hours * 0.8 * 0.02) + (monthly_compute_hours * 0.2 * self.COST_CLOUD_COMPUTE_SMALL_PER_HOUR),
        }
        hybrid['total'] = sum(hybrid.values())

        # Pure local deployment
        local_only = {
            'storage': monthly_data_gb * 0.005,
            'transfer': 0,  # No cloud transfer
            'compute': monthly_compute_hours * 0.02,
        }
        local_only['total'] = sum(local_only.values())

        savings_vs_cloud = cloud_only['total'] - hybrid['total']
        savings_pct = (savings_vs_cloud / cloud_only['total'] * 100) if cloud_only['total'] > 0 else 0

        return {
            'cloud_only_usd': cloud_only,
            'hybrid_usd': hybrid,
            'local_only_usd': local_only,
            'recommended': 'hybrid',
            'savings_vs_cloud_usd': savings_vs_cloud,
            'savings_vs_cloud_pct': savings_pct
        }

    def generate_cost_report(
        self,
        storage_stats: Dict,
        compute_stats: Dict
    ) -> Dict[str, Any]:
        """Generate comprehensive cost report"""
        recommendations = self.get_recommendations(storage_stats, compute_stats)

        # Calculate actual vs potential cloud-only costs
        bytes_saved = storage_stats.get('bytes_saved_locally', 0)
        gb_saved = bytes_saved / (1024 ** 3)

        actual_cost_usd = gb_saved * 0.005  # Local storage cost
        cloud_only_cost_usd = gb_saved * self.COST_CLOUD_STORAGE_PER_GB

        savings = {
            'storage_savings_usd_month': cloud_only_cost_usd - actual_cost_usd,
            'compute_savings_usd_month': compute_stats.get('estimated_cost_saved_usd', 0),
            'total_savings_usd_month': (cloud_only_cost_usd - actual_cost_usd) + compute_stats.get('estimated_cost_saved_usd', 0)
        }

        return {
            'savings': savings,
            'recommendations': recommendations,
            'roi_pct': savings['total_savings_usd_month'] / max(actual_cost_usd, 1) * 100,
            'generated_at': datetime.utcnow().isoformat()
        }
