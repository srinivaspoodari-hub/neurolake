"""add_rbac_tables

Revision ID: d4e8b9f2a5c1
Revises: c32f1f4d9189
Create Date: 2025-11-09

Add RBAC (Role-Based Access Control) tables:
- roles: User roles (admin, analyst, viewer, etc.)
- permissions: Granular permissions (query:execute, data:write, etc.)
- user_roles: Many-to-many relationship between users and roles
- role_permissions: Many-to-many relationship between roles and permissions

Also adds missing fields to users table:
- is_superuser (replacing is_admin)
- is_verified
- require_password_change
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd4e8b9f2a5c1'
down_revision: Union[str, None] = 'c32f1f4d9189'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =================================================================
    # 1. UPDATE USERS TABLE - Add missing fields
    # =================================================================

    # Add is_superuser column
    op.add_column('users', sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'))

    # Add is_verified column
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'))

    # Add require_password_change column
    op.add_column('users', sa.Column('require_password_change', sa.Boolean(), nullable=False, server_default='false'))

    # Migrate is_admin to is_superuser (for existing data)
    op.execute('UPDATE users SET is_superuser = is_admin')

    # Create index on is_superuser
    op.create_index('idx_users_superuser', 'users', ['is_superuser'])
    op.create_index('idx_users_verified', 'users', ['is_verified'])

    # =================================================================
    # 2. ROLES TABLE
    # =================================================================
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, default=0),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_system', sa.Boolean(), nullable=False, default=False),  # System roles can't be deleted
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
    )
    op.create_index('idx_roles_active', 'roles', ['is_active'])
    op.create_index('idx_roles_system', 'roles', ['is_system'])
    op.create_index('idx_roles_priority', 'roles', ['priority'])

    # =================================================================
    # 3. PERMISSIONS TABLE
    # =================================================================
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True, index=True),  # e.g., "query:execute"
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('resource', sa.String(100), nullable=False, index=True),  # e.g., "query", "data", "catalog"
        sa.Column('action', sa.String(100), nullable=False, index=True),   # e.g., "execute", "read", "write"
        sa.Column('scope', sa.String(100), nullable=True),  # Optional scope: "table", "schema", "global"
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
    )
    op.create_index('idx_permissions_resource', 'permissions', ['resource'])
    op.create_index('idx_permissions_action', 'permissions', ['action'])
    op.create_index('idx_permissions_resource_action', 'permissions', ['resource', 'action'])
    op.create_index('idx_permissions_active', 'permissions', ['is_active'])

    # =================================================================
    # 4. USER_ROLES TABLE (Many-to-Many)
    # =================================================================
    op.create_table(
        'user_roles',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('granted_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),  # Optional expiration
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
    )
    op.create_index('idx_user_roles_user', 'user_roles', ['user_id'])
    op.create_index('idx_user_roles_role', 'user_roles', ['role_id'])
    op.create_index('idx_user_roles_user_role', 'user_roles', ['user_id', 'role_id'], unique=True)
    op.create_index('idx_user_roles_expires', 'user_roles', ['expires_at'])

    # =================================================================
    # 5. ROLE_PERMISSIONS TABLE (Many-to-Many)
    # =================================================================
    op.create_table(
        'role_permissions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('permission_id', sa.Integer(), sa.ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('granted_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
    )
    op.create_index('idx_role_permissions_role', 'role_permissions', ['role_id'])
    op.create_index('idx_role_permissions_permission', 'role_permissions', ['permission_id'])
    op.create_index('idx_role_permissions_role_permission', 'role_permissions', ['role_id', 'permission_id'], unique=True)

    # =================================================================
    # 6. INSERT DEFAULT ROLES
    # =================================================================
    op.execute("""
        INSERT INTO roles (name, display_name, description, priority, is_system, is_active) VALUES
        ('admin', 'Administrator', 'Full system access with all permissions', 100, true, true),
        ('data_engineer', 'Data Engineer', 'Can create and manage data pipelines and tables', 80, true, true),
        ('data_analyst', 'Data Analyst', 'Can execute queries and view data', 60, true, true),
        ('data_viewer', 'Data Viewer', 'Read-only access to data and queries', 40, true, true)
    """)

    # =================================================================
    # 7. INSERT DEFAULT PERMISSIONS
    # =================================================================
    op.execute("""
        INSERT INTO permissions (name, display_name, description, resource, action, scope, is_active) VALUES
        -- Query permissions
        ('query:execute', 'Execute Queries', 'Execute SQL queries', 'query', 'execute', 'global', true),
        ('query:explain', 'Explain Queries', 'View query execution plans', 'query', 'explain', 'global', true),
        ('query:cancel', 'Cancel Queries', 'Cancel running queries', 'query', 'cancel', 'global', true),
        ('query:save', 'Save Queries', 'Save queries for reuse', 'query', 'save', 'global', true),

        -- Data permissions
        ('data:read', 'Read Data', 'Read data from tables', 'data', 'read', 'table', true),
        ('data:write', 'Write Data', 'Insert or update data', 'data', 'write', 'table', true),
        ('data:delete', 'Delete Data', 'Delete data from tables', 'data', 'delete', 'table', true),
        ('data:create_table', 'Create Tables', 'Create new tables', 'data', 'create_table', 'schema', true),
        ('data:drop_table', 'Drop Tables', 'Delete tables', 'data', 'drop_table', 'schema', true),

        -- Catalog permissions
        ('catalog:read', 'Browse Catalog', 'View catalog metadata', 'catalog', 'read', 'global', true),
        ('catalog:write', 'Update Catalog', 'Modify catalog metadata', 'catalog', 'write', 'global', true),
        ('catalog:manage', 'Manage Catalog', 'Full catalog management', 'catalog', 'manage', 'global', true),

        -- Pipeline permissions
        ('pipeline:read', 'View Pipelines', 'View pipeline definitions', 'pipeline', 'read', 'global', true),
        ('pipeline:create', 'Create Pipelines', 'Create new pipelines', 'pipeline', 'create', 'global', true),
        ('pipeline:execute', 'Execute Pipelines', 'Run pipelines', 'pipeline', 'execute', 'global', true),
        ('pipeline:delete', 'Delete Pipelines', 'Delete pipelines', 'pipeline', 'delete', 'global', true),

        -- Admin permissions
        ('admin:users', 'Manage Users', 'Create and manage users', 'admin', 'users', 'global', true),
        ('admin:roles', 'Manage Roles', 'Create and manage roles', 'admin', 'roles', 'global', true),
        ('admin:permissions', 'Manage Permissions', 'Assign permissions', 'admin', 'permissions', 'global', true),
        ('admin:system', 'System Administration', 'Full system administration', 'admin', 'system', 'global', true)
    """)

    # =================================================================
    # 8. ASSIGN PERMISSIONS TO ROLES
    # =================================================================
    # Admin gets all permissions
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name = 'admin'
    """)

    # Data Engineer permissions
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name = 'data_engineer'
        AND p.name IN (
            'query:execute', 'query:explain', 'query:cancel', 'query:save',
            'data:read', 'data:write', 'data:delete', 'data:create_table', 'data:drop_table',
            'catalog:read', 'catalog:write',
            'pipeline:read', 'pipeline:create', 'pipeline:execute', 'pipeline:delete'
        )
    """)

    # Data Analyst permissions
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name = 'data_analyst'
        AND p.name IN (
            'query:execute', 'query:explain', 'query:cancel', 'query:save',
            'data:read',
            'catalog:read',
            'pipeline:read'
        )
    """)

    # Data Viewer permissions
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name = 'data_viewer'
        AND p.name IN (
            'query:execute',
            'data:read',
            'catalog:read',
            'pipeline:read'
        )
    """)


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('role_permissions')
    op.drop_table('user_roles')
    op.drop_table('permissions')
    op.drop_table('roles')

    # Drop added indexes
    op.drop_index('idx_users_verified', 'users')
    op.drop_index('idx_users_superuser', 'users')

    # Drop added columns
    op.drop_column('users', 'require_password_change')
    op.drop_column('users', 'is_verified')
    op.drop_column('users', 'is_superuser')
