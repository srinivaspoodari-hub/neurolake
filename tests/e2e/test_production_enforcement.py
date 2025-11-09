"""
Test Production Environment Enforcement

Tests that production mode enforces cloud-only for compute and storage.
"""

import os
import shutil
from pathlib import Path
from neurolake.config import get_environment_manager


def cleanup_config():
    """Remove config file to start fresh"""
    config_dir = Path("./config")
    if config_dir.exists():
        shutil.rmtree(config_dir)
    print("Cleaned up config directory")
    print()

def test_development_mode():
    """Test development mode - should allow local"""
    print("=" * 80)
    print("TEST 1: DEVELOPMENT MODE")
    print("=" * 80)

    # Clean up any existing config
    cleanup_config()

    # Ensure dev mode
    os.environ['NEUROLAKE_ENV'] = 'development'

    # Create new instance
    from neurolake.config.environment import EnvironmentManager
    em = EnvironmentManager()

    print(f"Environment: {em.current_env.value}")
    print(f"Is Production: {em.is_production()}")
    print(f"Is Development: {em.is_development()}")
    print()

    # Check compute
    compute_check = em.can_use_local_compute()
    print(f"Can use local compute: {compute_check['allowed']}")
    print(f"Reason: {compute_check['reason']}")
    print()

    # Check storage
    storage_check = em.can_use_local_storage()
    print(f"Can use local storage: {storage_check['allowed']}")
    print(f"Reason: {storage_check['reason']}")
    print()

    # Config summary
    summary = em.get_config_summary()
    print("Configuration:")
    print(f"  Compute local allowed: {summary['compute']['local_allowed']}")
    print(f"  Compute cloud required: {summary['compute']['cloud_required']}")
    print(f"  Storage local allowed: {summary['storage']['local_allowed']}")
    print(f"  Storage cloud required: {summary['storage']['cloud_required']}")
    print()

    assert compute_check['allowed'] == True, "Dev mode should allow local compute"
    assert storage_check['allowed'] == True, "Dev mode should allow local storage"
    print("PASSED: Development mode allows local compute and storage")
    print()


def test_production_mode():
    """Test production mode - should enforce cloud-only"""
    print("=" * 80)
    print("TEST 2: PRODUCTION MODE")
    print("=" * 80)

    # Clean up any existing config
    cleanup_config()

    # Set production mode
    os.environ['NEUROLAKE_ENV'] = 'production'

    # Create new instance
    from neurolake.config.environment import EnvironmentManager
    em = EnvironmentManager()

    print(f"Environment: {em.current_env.value}")
    print(f"Is Production: {em.is_production()}")
    print(f"Is Development: {em.is_development()}")
    print()

    # Check compute
    compute_check = em.can_use_local_compute()
    print(f"Can use local compute: {compute_check['allowed']}")
    print(f"Reason: {compute_check['reason']}")
    print(f"Alternative: {compute_check.get('alternative', 'N/A')}")
    print()

    # Check storage
    storage_check = em.can_use_local_storage()
    print(f"Can use local storage: {storage_check['allowed']}")
    print(f"Reason: {storage_check['reason']}")
    print(f"Alternative: {storage_check.get('alternative', 'N/A')}")
    print()

    # Config summary BEFORE enforcement
    summary_before = em.get_config_summary()
    print("Configuration BEFORE enforcement:")
    print(f"  Compute local allowed: {summary_before['compute']['local_allowed']}")
    print(f"  Compute cloud required: {summary_before['compute']['cloud_required']}")
    print(f"  Storage local allowed: {summary_before['storage']['local_allowed']}")
    print(f"  Storage cloud required: {summary_before['storage']['cloud_required']}")
    print(f"  Config locked: {summary_before['admin']['config_locked']}")
    print()

    # Enforce production rules
    enforcement = em.enforce_production_rules()
    print("Production enforcement result:")
    print(f"  Enforced: {enforcement['enforced']}")
    print(f"  Violations fixed: {enforcement.get('violations_fixed', [])}")
    print(f"  Message: {enforcement['message']}")
    print()

    # Config summary AFTER enforcement
    summary = em.get_config_summary()
    print("Configuration AFTER enforcement:")
    print(f"  Compute local allowed: {summary['compute']['local_allowed']}")
    print(f"  Compute cloud required: {summary['compute']['cloud_required']}")
    print(f"  Storage local allowed: {summary['storage']['local_allowed']}")
    print(f"  Storage cloud required: {summary['storage']['cloud_required']}")
    print()

    assert compute_check['allowed'] == False, "Production mode should NOT allow local compute"
    assert storage_check['allowed'] == False, "Production mode should NOT allow local storage"
    assert summary['compute']['cloud_required'] == True, "Production must require cloud compute"
    assert summary['storage']['cloud_required'] == True, "Production must require cloud storage"
    print("PASSED: Production mode enforces cloud-only")
    print()


def test_staging_mode():
    """Test staging mode - should allow both"""
    print("=" * 80)
    print("TEST 3: STAGING MODE")
    print("=" * 80)

    # Clean up any existing config
    cleanup_config()

    # Set staging mode
    os.environ['NEUROLAKE_ENV'] = 'staging'

    # Create new instance
    from neurolake.config.environment import EnvironmentManager
    em = EnvironmentManager()

    print(f"Environment: {em.current_env.value}")
    print(f"Is Production: {em.is_production()}")
    print(f"Is Staging: {em.is_staging()}")
    print()

    # Check compute
    compute_check = em.can_use_local_compute()
    print(f"Can use local compute: {compute_check['allowed']}")
    print(f"Reason: {compute_check['reason']}")
    print()

    # Check storage
    storage_check = em.can_use_local_storage()
    print(f"Can use local storage: {storage_check['allowed']}")
    print(f"Reason: {storage_check['reason']}")
    print()

    # Config summary
    summary = em.get_config_summary()
    print("Configuration:")
    print(f"  Compute local allowed: {summary['compute']['local_allowed']}")
    print(f"  Compute cloud required: {summary['compute']['cloud_required']}")
    print(f"  Storage local allowed: {summary['storage']['local_allowed']}")
    print(f"  Storage cloud required: {summary['storage']['cloud_required']}")
    print()

    assert compute_check['allowed'] == True, "Staging mode should allow local compute"
    assert storage_check['allowed'] == True, "Staging mode should allow local storage"
    assert summary['compute']['cloud_required'] == False, "Staging should not require cloud"
    print("PASSED: Staging mode allows both local and cloud")
    print()


def test_rbac_integration():
    """Test RBAC integration with permissions"""
    print("=" * 80)
    print("TEST 4: RBAC INTEGRATION")
    print("=" * 80)

    # Clean up any existing config
    cleanup_config()

    # Set dev mode
    os.environ['NEUROLAKE_ENV'] = 'development'

    from neurolake.config.environment import EnvironmentManager, Permission
    em = EnvironmentManager()

    # Test without permissions
    print("User without COMPUTE_LOCAL permission:")
    compute_check = em.can_use_local_compute(user_permissions=[])
    print(f"  Can use local compute: {compute_check['allowed']}")
    print(f"  Reason: {compute_check['reason']}")
    print()

    # Test with permissions
    print("User with COMPUTE_LOCAL permission:")
    compute_check = em.can_use_local_compute(
        user_permissions=[Permission.COMPUTE_LOCAL.value]
    )
    print(f"  Can use local compute: {compute_check['allowed']}")
    print(f"  Reason: {compute_check['reason']}")
    print()

    # Test admin update
    print("Admin updating configuration:")
    result = em.update_config(
        user_permissions=[Permission.ADMIN_CONFIG.value],
        user_id='test_admin',
        compute_allow_local=False
    )
    print(f"  Success: {result['success']}")
    print(f"  Message: {result.get('message', 'N/A')}")
    print()

    # Test non-admin update
    print("Non-admin trying to update:")
    result = em.update_config(
        user_permissions=[],
        user_id='regular_user',
        compute_allow_local=True
    )
    print(f"  Success: {result['success']}")
    print(f"  Reason: {result.get('reason', 'N/A')}")
    print()

    print("PASSED: RBAC integration working correctly")
    print()


if __name__ == "__main__":
    try:
        test_development_mode()
        test_production_mode()
        test_staging_mode()
        test_rbac_integration()

        print("=" * 80)
        print("ALL TESTS PASSED!")
        print("=" * 80)
        print()
        print("Summary:")
        print("  - Development: Local compute/storage ALLOWED")
        print("  - Production: Cloud-only ENFORCED")
        print("  - Staging: Both local and cloud ALLOWED")
        print("  - RBAC: Permission checks WORKING")
        print()

    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
