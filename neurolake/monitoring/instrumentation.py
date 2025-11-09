"""
Monitoring Instrumentation

OpenTelemetry and Prometheus instrumentation for comprehensive observability.
"""

import logging
from typing import Optional
from fastapi import FastAPI
from prometheus_client import Counter, Histogram, Gauge, Info
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader

from neurolake.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# Prometheus metrics
QUERY_DURATION = Histogram(
    'neurolake_query_duration_seconds',
    'Query execution duration',
    ['query_type', 'status']
)

QUERY_COUNT = Counter(
    'neurolake_queries_total',
    'Total queries executed',
    ['query_type', 'status']
)

CACHE_OPERATIONS = Counter(
    'neurolake_cache_operations_total',
    'Cache operations',
    ['operation', 'status']
)

ACTIVE_QUERIES = Gauge(
    'neurolake_active_queries',
    'Number of currently executing queries'
)

DB_POOL_CONNECTIONS = Gauge(
    'neurolake_db_pool_connections',
    'Database connection pool status',
    ['status']
)

SYSTEM_INFO = Info(
    'neurolake_system',
    'System information'
)


def setup_tracing(app: FastAPI) -> Optional[TracerProvider]:
    """
    Setup OpenTelemetry distributed tracing.

    Args:
        app: FastAPI application instance

    Returns:
        TracerProvider instance
    """
    if not settings.monitoring.tracing_enabled:
        logger.info("Distributed tracing is disabled")
        return None

    try:
        # Create resource with service information
        resource = Resource(attributes={
            SERVICE_NAME: "neurolake-api",
            "service.version": "1.0.0",
            "deployment.environment": settings.api.environment
        })

        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)

        # Add Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=settings.monitoring.jaeger_host,
            agent_port=settings.monitoring.jaeger_port,
        )
        tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

        # Add console exporter for development
        if settings.api.debug:
            tracer_provider.add_span_processor(
                BatchSpanProcessor(ConsoleSpanExporter())
            )

        # Set global tracer provider
        trace.set_tracer_provider(tracer_provider)

        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)

        # Instrument SQLAlchemy
        SQLAlchemyInstrumentor().instrument()

        # Instrument Redis
        RedisInstrumentor().instrument()

        logger.info(f"✓ Distributed tracing enabled (Jaeger: {settings.monitoring.jaeger_host}:{settings.monitoring.jaeger_port})")
        return tracer_provider

    except Exception as e:
        logger.error(f"Failed to setup tracing: {e}")
        return None


def setup_metrics() -> Optional[MeterProvider]:
    """
    Setup OpenTelemetry metrics.

    Returns:
        MeterProvider instance
    """
    if not settings.monitoring.metrics_enabled:
        logger.info("Metrics collection is disabled")
        return None

    try:
        # Create resource
        resource = Resource(attributes={
            SERVICE_NAME: "neurolake-api",
            "service.version": "1.0.0"
        })

        # Create metric readers
        readers = []

        # Prometheus exporter
        if settings.monitoring.prometheus_enabled:
            readers.append(PrometheusMetricReader())

        # Console exporter for development
        if settings.api.debug:
            readers.append(
                PeriodicExportingMetricReader(ConsoleMetricExporter())
            )

        # Create meter provider
        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=readers
        )

        # Set global meter provider
        metrics.set_meter_provider(meter_provider)

        logger.info("✓ Metrics collection enabled")
        return meter_provider

    except Exception as e:
        logger.error(f"Failed to setup metrics: {e}")
        return None


def setup_monitoring(app: FastAPI):
    """
    Setup comprehensive monitoring and instrumentation.

    This function sets up:
    - Distributed tracing (OpenTelemetry + Jaeger)
    - Metrics collection (Prometheus)
    - Application instrumentation

    Args:
        app: FastAPI application instance
    """
    logger.info("Setting up monitoring and instrumentation...")

    # Setup distributed tracing
    tracer_provider = setup_tracing(app)

    # Setup metrics
    meter_provider = setup_metrics()

    # Set system information
    SYSTEM_INFO.info({
        "version": "1.0.0",
        "environment": settings.api.environment,
        "tracing_enabled": str(settings.monitoring.tracing_enabled),
        "metrics_enabled": str(settings.monitoring.metrics_enabled)
    })

    logger.info("✓ Monitoring setup complete")


# Convenience functions for tracking operations

def track_query_execution(query_type: str, duration: float, success: bool):
    """
    Track query execution metrics.

    Args:
        query_type: Type of query (sql, ncf, etc.)
        duration: Execution duration in seconds
        success: Whether query succeeded
    """
    status = "success" if success else "error"
    QUERY_DURATION.labels(query_type=query_type, status=status).observe(duration)
    QUERY_COUNT.labels(query_type=query_type, status=status).inc()


def track_cache_operation(operation: str, success: bool):
    """
    Track cache operation metrics.

    Args:
        operation: Operation type (get, set, delete)
        success: Whether operation succeeded
    """
    status = "success" if success else "error"
    CACHE_OPERATIONS.labels(operation=operation, status=status).inc()


def update_db_pool_metrics(active: int, idle: int):
    """
    Update database connection pool metrics.

    Args:
        active: Number of active connections
        idle: Number of idle connections
    """
    DB_POOL_CONNECTIONS.labels(status="active").set(active)
    DB_POOL_CONNECTIONS.labels(status="idle").set(idle)


class QueryTracker:
    """Context manager for tracking query execution."""

    def __init__(self, query_type: str):
        self.query_type = query_type
        self.start_time = None

    def __enter__(self):
        import time
        ACTIVE_QUERIES.inc()
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        ACTIVE_QUERIES.dec()
        duration = time.time() - self.start_time
        success = exc_type is None
        track_query_execution(self.query_type, duration, success)
