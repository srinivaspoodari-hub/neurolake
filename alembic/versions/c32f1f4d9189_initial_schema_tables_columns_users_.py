"""initial_schema_tables_columns_users_queries_audits_pipelines

Revision ID: c32f1f4d9189
Revises:
Create Date: 2025-11-01

Comprehensive initial schema for NeuroLake including:
- tables: Metadata catalog for datasets/tables
- columns: Column-level metadata
- users: User management
- query_history: Query execution tracking
- audit_logs: System audit trail
- pipelines: Data pipeline definitions
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c32f1f4d9189'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =================================================================
    # 1. USERS TABLE - User management and authentication
    # =================================================================
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('username', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(512), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_admin', sa.Boolean(), nullable=False, default=False),
        sa.Column('api_key', sa.String(512), nullable=True, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
    )
    op.create_index('idx_users_active', 'users', ['is_active'])
    op.create_index('idx_users_created', 'users', ['created_at'])

    # =================================================================
    # 2. TABLES TABLE - Metadata catalog for datasets/tables
    # =================================================================
    op.create_table(
        'tables',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('table_name', sa.String(255), nullable=False, index=True),
        sa.Column('schema_name', sa.String(255), nullable=False, default='public', index=True),
        sa.Column('table_type', sa.String(50), nullable=False),  # ncf, parquet, csv, external
        sa.Column('storage_format', sa.String(50), nullable=False),  # ncf, parquet, etc.
        sa.Column('storage_location', sa.Text(), nullable=False),  # S3 path, MinIO path, file path
        sa.Column('row_count', sa.BigInteger(), nullable=True),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('compression_ratio', sa.Float(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('owner_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),  # Additional custom metadata
        sa.Column('schema_version', sa.Integer(), nullable=False, default=1),
        sa.Column('partitioning_info', postgresql.JSONB(), nullable=True),
    )
    op.create_index('idx_tables_name_schema', 'tables', ['table_name', 'schema_name'], unique=True)
    op.create_index('idx_tables_type', 'tables', ['table_type'])
    op.create_index('idx_tables_format', 'tables', ['storage_format'])
    op.create_index('idx_tables_active', 'tables', ['is_active'])
    op.create_index('idx_tables_created', 'tables', ['created_at'])
    op.create_index('idx_tables_tags', 'tables', ['tags'], postgresql_using='gin')

    # =================================================================
    # 3. COLUMNS TABLE - Column-level metadata
    # =================================================================
    op.create_table(
        'columns',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('table_id', sa.Integer(), sa.ForeignKey('tables.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('column_name', sa.String(255), nullable=False, index=True),
        sa.Column('column_position', sa.Integer(), nullable=False),
        sa.Column('data_type', sa.String(100), nullable=False),  # NCFDataType enum values
        sa.Column('semantic_type', sa.String(100), nullable=True),  # email, phone, address, etc.
        sa.Column('is_nullable', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_primary_key', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_indexed', sa.Boolean(), nullable=False, default=False),
        sa.Column('default_value', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('statistics', postgresql.JSONB(), nullable=True),  # min, max, distinct_count, null_count
        sa.Column('constraints', postgresql.JSONB(), nullable=True),  # validation rules
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
    )
    op.create_index('idx_columns_table_name', 'columns', ['table_id', 'column_name'], unique=True)
    op.create_index('idx_columns_position', 'columns', ['table_id', 'column_position'])
    op.create_index('idx_columns_type', 'columns', ['data_type'])

    # =================================================================
    # 4. QUERY_HISTORY TABLE - Query execution tracking
    # =================================================================
    op.create_table(
        'query_history',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('query_id', sa.String(255), nullable=False, unique=True, index=True),  # UUID
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True, index=True),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('query_type', sa.String(50), nullable=False),  # SELECT, INSERT, UPDATE, DELETE, CREATE
        sa.Column('query_status', sa.String(50), nullable=False),  # pending, running, success, failed, cancelled
        sa.Column('tables_accessed', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('rows_read', sa.BigInteger(), nullable=True),
        sa.Column('rows_written', sa.BigInteger(), nullable=True),
        sa.Column('bytes_read', sa.BigInteger(), nullable=True),
        sa.Column('bytes_written', sa.BigInteger(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_type', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),  # execution plan, cache hit, etc.
    )
    op.create_index('idx_query_history_user', 'query_history', ['user_id'])
    op.create_index('idx_query_history_status', 'query_history', ['query_status'])
    op.create_index('idx_query_history_type', 'query_history', ['query_type'])
    op.create_index('idx_query_history_started', 'query_history', ['started_at'])
    op.create_index('idx_query_history_created', 'query_history', ['created_at'])

    # =================================================================
    # 5. AUDIT_LOGS TABLE - System audit trail
    # =================================================================
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True, index=True),
        sa.Column('action', sa.String(100), nullable=False, index=True),  # CREATE, READ, UPDATE, DELETE
        sa.Column('resource_type', sa.String(100), nullable=False, index=True),  # table, column, user, pipeline
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('resource_name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),  # success, failure
        sa.Column('ip_address', sa.String(45), nullable=True),  # IPv4/IPv6
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('changes', postgresql.JSONB(), nullable=True),  # before/after values
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, index=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
    )
    op.create_index('idx_audit_logs_user_action', 'audit_logs', ['user_id', 'action'])
    op.create_index('idx_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('idx_audit_logs_status', 'audit_logs', ['status'])

    # =================================================================
    # 6. PIPELINES TABLE - Data pipeline definitions
    # =================================================================
    op.create_table(
        'pipelines',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('pipeline_name', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('pipeline_type', sa.String(50), nullable=False),  # ETL, ELT, streaming, batch
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('schedule_cron', sa.String(255), nullable=True),  # Cron expression
        sa.Column('source_config', postgresql.JSONB(), nullable=False),  # Source connection/config
        sa.Column('destination_config', postgresql.JSONB(), nullable=False),  # Destination config
        sa.Column('transformation_config', postgresql.JSONB(), nullable=True),  # Transformation rules
        sa.Column('status', sa.String(50), nullable=False, default='draft'),  # draft, active, paused, failed
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_run_status', sa.String(50), nullable=True),  # success, failure
        sa.Column('last_run_duration_ms', sa.Integer(), nullable=True),
        sa.Column('last_run_rows_processed', sa.BigInteger(), nullable=True),
        sa.Column('last_run_error', sa.Text(), nullable=True),
        sa.Column('total_runs', sa.Integer(), nullable=False, default=0),
        sa.Column('successful_runs', sa.Integer(), nullable=False, default=0),
        sa.Column('failed_runs', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
    )
    op.create_index('idx_pipelines_type', 'pipelines', ['pipeline_type'])
    op.create_index('idx_pipelines_status', 'pipelines', ['status'])
    op.create_index('idx_pipelines_active', 'pipelines', ['is_active'])
    op.create_index('idx_pipelines_owner', 'pipelines', ['owner_user_id'])
    op.create_index('idx_pipelines_last_run', 'pipelines', ['last_run_at'])
    op.create_index('idx_pipelines_tags', 'pipelines', ['tags'], postgresql_using='gin')


def downgrade() -> None:
    # Drop tables in reverse order (respect foreign keys)
    op.drop_table('pipelines')
    op.drop_table('audit_logs')
    op.drop_table('query_history')
    op.drop_table('columns')
    op.drop_table('tables')
    op.drop_table('users')
