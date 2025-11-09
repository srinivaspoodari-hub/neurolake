"""
Initialize Admin User and Default Permissions

This script creates the initial superuser account and sets up default roles
and permissions for the NeuroLake platform.

Usage:
    python scripts/init_admin_user.py

Environment Variables:
    ADMIN_USERNAME: Admin username (default: admin)
    ADMIN_EMAIL: Admin email (default: admin@neurolake.local)
    ADMIN_PASSWORD: Admin password (REQUIRED)
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from neurolake.db import DatabaseManager
from neurolake.auth.models import User, Role, Permission, UserRole, RolePermission
from neurolake.auth.password_utils import PasswordUtils
from neurolake.config import get_settings

settings = get_settings()


def create_permissions(db: Session) -> dict:
    """
    Create default permissions for the platform.

    Returns:
        Dict mapping permission names to Permission objects
    """
    permissions_data = [
        # Query permissions
        ("query:execute", "Execute SQL queries", "query", "execute"),
        ("query:explain", "View query execution plans", "query", "explain"),
        ("query:cancel", "Cancel running queries", "query", "cancel"),
        ("query:history", "View query history", "query", "history"),

        # Data permissions
        ("data:read", "Read data from tables", "data", "read"),
        ("data:write", "Write data to tables", "data", "write"),
        ("data:update", "Update existing data", "data", "update"),
        ("data:delete", "Delete data from tables", "data", "delete"),
        ("data:upload", "Upload files to create tables", "data", "upload"),
        ("data:schema", "View and manage table schemas", "data", "schema"),

        # Catalog permissions
        ("catalog:read", "Read catalog metadata", "catalog", "read"),
        ("catalog:write", "Modify catalog metadata", "catalog", "write"),
        ("catalog:search", "Search the data catalog", "catalog", "search"),
        ("catalog:lineage", "View data lineage", "catalog", "lineage"),
        ("catalog:tags", "Manage data tags", "catalog", "tags"),

        # NCF permissions
        ("ncf:read", "Read NCF format data", "ncf", "read"),
        ("ncf:write", "Write NCF format data", "ncf", "write"),
        ("ncf:optimize", "Run NCF optimization operations", "ncf", "optimize"),
        ("ncf:vacuum", "Run NCF vacuum operations", "ncf", "vacuum"),
        ("ncf:merge", "Run NCF merge operations", "ncf", "merge"),
        ("ncf:timetravel", "Use NCF time travel features", "ncf", "timetravel"),

        # Admin permissions
        ("admin:users", "Manage users", "admin", "users"),
        ("admin:roles", "Manage roles and permissions", "admin", "roles"),
        ("admin:system", "Manage system settings", "admin", "system"),
        ("admin:audit", "View audit logs", "admin", "audit"),
    ]

    permissions = {}
    for name, display_name, resource, action in permissions_data:
        perm = db.query(Permission).filter(Permission.name == name).first()
        if not perm:
            perm = Permission(
                name=name,
                display_name=display_name,
                description=f"Permission to {action} {resource}",
                resource=resource,
                action=action,
                is_active=True
            )
            db.add(perm)
            print(f"  ✓ Created permission: {name}")
        else:
            print(f"  - Permission already exists: {name}")

        permissions[name] = perm

    db.commit()
    return permissions


def create_roles(db: Session, permissions: dict) -> dict:
    """
    Create default roles with assigned permissions.

    Args:
        permissions: Dict of permission objects

    Returns:
        Dict mapping role names to Role objects
    """
    roles_data = {
        "admin": {
            "display_name": "Administrator",
            "description": "Full system access",
            "priority": 100,
            "permissions": list(permissions.keys())  # All permissions
        },
        "data_engineer": {
            "display_name": "Data Engineer",
            "description": "Create and manage data pipelines",
            "priority": 80,
            "permissions": [
                "query:execute", "query:explain", "query:history",
                "data:read", "data:write", "data:update", "data:upload", "data:schema",
                "catalog:read", "catalog:write", "catalog:search", "catalog:lineage", "catalog:tags",
                "ncf:read", "ncf:write", "ncf:optimize", "ncf:vacuum", "ncf:merge", "ncf:timetravel"
            ]
        },
        "data_analyst": {
            "display_name": "Data Analyst",
            "description": "Query and analyze data",
            "priority": 60,
            "permissions": [
                "query:execute", "query:explain", "query:history",
                "data:read", "data:schema",
                "catalog:read", "catalog:search", "catalog:lineage",
                "ncf:read", "ncf:timetravel"
            ]
        },
        "data_scientist": {
            "display_name": "Data Scientist",
            "description": "Advanced analytics and model building",
            "priority": 70,
            "permissions": [
                "query:execute", "query:explain", "query:history",
                "data:read", "data:write", "data:schema",
                "catalog:read", "catalog:search", "catalog:lineage", "catalog:tags",
                "ncf:read", "ncf:write", "ncf:timetravel"
            ]
        },
        "viewer": {
            "display_name": "Viewer",
            "description": "Read-only access to data and catalog",
            "priority": 40,
            "permissions": [
                "query:execute", "query:history",
                "data:read", "data:schema",
                "catalog:read", "catalog:search", "catalog:lineage"
            ]
        }
    }

    roles = {}
    for role_name, role_data in roles_data.items():
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            role = Role(
                name=role_name,
                display_name=role_data["display_name"],
                description=role_data["description"],
                priority=role_data["priority"],
                is_active=True,
                is_system=True  # System roles cannot be deleted
            )
            db.add(role)
            db.flush()  # Get role ID
            print(f"  ✓ Created role: {role_name}")
        else:
            print(f"  - Role already exists: {role_name}")

        # Assign permissions to role
        for perm_name in role_data["permissions"]:
            if perm_name in permissions:
                perm = permissions[perm_name]
                if perm not in role.permissions:
                    role.permissions.append(perm)

        roles[role_name] = role

    db.commit()
    return roles


def create_admin_user(db: Session, roles: dict) -> User:
    """
    Create the initial admin user.

    Args:
        roles: Dict of role objects

    Returns:
        Created admin User object
    """
    # Get credentials from environment or use defaults
    username = os.getenv("ADMIN_USERNAME", "admin")
    email = os.getenv("ADMIN_EMAIL", "admin@neurolake.local")
    password = os.getenv("ADMIN_PASSWORD")

    if not password:
        print("\n⚠️  ERROR: ADMIN_PASSWORD environment variable not set!")
        print("   Please set a secure admin password:")
        print("   export ADMIN_PASSWORD='your-secure-password'")
        sys.exit(1)

    # Check if admin already exists
    existing_user = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()

    if existing_user:
        print(f"\n⚠️  Admin user already exists: {existing_user.username}")
        print("   Skipping user creation.")
        return existing_user

    # Create admin user
    hashed_password = PasswordUtils.hash_password(password)

    admin_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        full_name="System Administrator",
        is_active=True,
        is_verified=True,
        is_superuser=True  # Superuser has all permissions
    )

    db.add(admin_user)
    db.flush()  # Get user ID

    # Assign admin role
    if "admin" in roles:
        admin_user.roles.append(roles["admin"])

    db.commit()

    print(f"\n✅ Admin user created successfully!")
    print(f"   Username: {username}")
    print(f"   Email: {email}")
    print(f"   Role: Administrator (Superuser)")

    return admin_user


def main():
    """Main initialization function."""
    print("=" * 60)
    print("NeuroLake Admin Initialization")
    print("=" * 60)

    # Initialize database
    print("\n1. Connecting to database...")
    db_manager = DatabaseManager()
    db = db_manager.get_session()

    try:
        # Create permissions
        print("\n2. Creating permissions...")
        permissions = create_permissions(db)
        print(f"   Total permissions: {len(permissions)}")

        # Create roles
        print("\n3. Creating roles...")
        roles = create_roles(db, permissions)
        print(f"   Total roles: {len(roles)}")

        # Create admin user
        print("\n4. Creating admin user...")
        admin_user = create_admin_user(db, roles)

        print("\n" + "=" * 60)
        print("✅ Initialization Complete!")
        print("=" * 60)
        print("\nYou can now log in with the admin credentials.")
        print("\nNext steps:")
        print("  1. Start the API: uvicorn neurolake.api.main:app --reload")
        print("  2. Visit docs: http://localhost:8000/docs")
        print("  3. Login at: POST /api/auth/login")
        print("  4. Create additional users via: POST /api/auth/register")
        print("\n")

    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        db.rollback()
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
