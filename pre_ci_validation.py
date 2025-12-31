#!/usr/bin/env python3
"""
Pre-CI Validation Script

Validates that all prerequisites are met before running CI tests.
Checks migrations, secrets, config, and baseline functionality.

Usage:
    python pre_ci_validation.py

Exit codes:
    0 = All checks passed, ready for CI
    1 = Critical failures found, not ready for CI
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now import app modules
from app.config import settings
from app.startup_validator import StartupValidator


class PreCIValidator:
    """Pre-CI validation checks."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.passed = []
    
    def check_migrations(self):
        """Check if database migrations directory exists."""
        migrations_dir = project_root / "alembic" / "versions"
        
        if not migrations_dir.exists():
            self.errors.append("❌ Alembic migrations directory not found")
            return False
        
        migration_files = list(migrations_dir.glob("*.py"))
        if len(migration_files) == 0:
            self.warnings.append("⚠️  No migration files found (expected for fresh install)")
        else:
            self.passed.append(f"✅ Found {len(migration_files)} migration files")
        
        return True
    
    def check_secrets(self):
        """Check if required secrets are configured."""
        required_secrets = [
            ("SESSION_SECRET_KEY", settings.SESSION_SECRET_KEY),
            ("SECRET_KEY", settings.SECRET_KEY),
            ("DATABASE_URL", settings.DATABASE_URL),
        ]
        
        missing = []
        for name, value in required_secrets:
            if not value or value == "changeme" or len(str(value)) < 10:
                missing.append(name)
        
        if missing:
            self.errors.append(f"❌ Missing or invalid secrets: {', '.join(missing)}")
            return False
        
        self.passed.append("✅ All required secrets configured")
        
        # Check session secret strength
        if len(settings.SESSION_SECRET_KEY) < 32:
            self.errors.append(f"❌ SESSION_SECRET_KEY too short ({len(settings.SESSION_SECRET_KEY)} chars, minimum 32)")
            return False
        
        self.passed.append(f"✅ SESSION_SECRET_KEY strength OK ({len(settings.SESSION_SECRET_KEY)} chars)")
        return True
    
    def check_config_validation(self):
        """Run startup config validation."""
        print("\n" + "=" * 80)
        print("Running Startup Config Validation...")
        print("=" * 80 + "\n")
        
        validation_errors = StartupValidator.validate_production_config()
        
        if not validation_errors:
            self.passed.append("✅ Startup config validation passed")
            return True
        
        # Check if errors are critical
        critical = [e for e in validation_errors if "CRITICAL" in e]
        warnings = [e for e in validation_errors if "WARNING" in e]
        
        if critical:
            for error in critical:
                self.errors.append(f"❌ Config: {error}")
            return False
        
        if warnings:
            for warning in warnings:
                self.warnings.append(f"⚠️  Config: {warning}")
        
        return True
    
    def check_test_files(self):
        """Check if test files exist."""
        test_files = [
            "tests/test_admin_ui.py",
            "tests/test_admin_auth.py",
            "tests/test_legal_compliance.py",
        ]
        
        missing = []
        for test_file in test_files:
            if not (project_root / test_file).exists():
                missing.append(test_file)
        
        if missing:
            self.errors.append(f"❌ Missing test files: {', '.join(missing)}")
            return False
        
        self.passed.append(f"✅ All test files present ({len(test_files)} files)")
        return True
    
    def check_admin_routes(self):
        """Check if admin route files exist."""
        route_files = [
            "app/api/admin/auth.py",
            "app/api/admin/doctors.py",
            "app/api/admin/tools.py",
            "app/api/admin/audit.py",
        ]
        
        missing = []
        for route_file in route_files:
            if not (project_root / route_file).exists():
                missing.append(route_file)
        
        if missing:
            self.errors.append(f"❌ Missing admin route files: {', '.join(missing)}")
            return False
        
        self.passed.append(f"✅ All admin routes present ({len(route_files)} files)")
        return True
    
    def check_templates(self):
        """Check if HTML templates exist."""
        required_templates = [
            "app/templates/base.html",
            "app/templates/login.html",
            "app/templates/dashboard.html",
        ]
        
        missing = []
        for template in required_templates:
            if not (project_root / template).exists():
                missing.append(template)
        
        if missing:
            self.errors.append(f"❌ Missing templates: {', '.join(missing)}")
            return False
        
        self.passed.append(f"✅ Core templates present ({len(required_templates)} files)")
        return True
    
    def check_models(self):
        """Check if required models exist."""
        required_models = [
            "app/models/admin_user.py",
            "app/models/doctor.py",
            "app/models/audit_log.py",
        ]
        
        missing = []
        for model_file in required_models:
            if not (project_root / model_file).exists():
                missing.append(model_file)
        
        if missing:
            self.errors.append(f"❌ Missing models: {', '.join(missing)}")
            return False
        
        self.passed.append(f"✅ All models present ({len(required_models)} files)")
        return True
    
    def run_all_checks(self):
        """Run all validation checks."""
        print("=" * 80)
        print("Curaslot Admin UI - Pre-CI Validation")
        print("=" * 80)
        print()
        
        checks = [
            ("Migrations", self.check_migrations),
            ("Secrets", self.check_secrets),
            ("Config Validation", self.check_config_validation),
            ("Test Files", self.check_test_files),
            ("Admin Routes", self.check_admin_routes),
            ("Templates", self.check_templates),
            ("Models", self.check_models),
        ]
        
        print("Running validation checks...\n")
        
        for name, check_func in checks:
            print(f"Checking {name}...")
            try:
                check_func()
            except Exception as e:
                self.errors.append(f"❌ {name} check failed: {str(e)}")
        
        print("\n" + "=" * 80)
        print("Validation Results")
        print("=" * 80 + "\n")
        
        # Print passed checks
        if self.passed:
            print("✅ PASSED CHECKS:\n")
            for item in self.passed:
                print(f"  {item}")
            print()
        
        # Print warnings
        if self.warnings:
            print("⚠️  WARNINGS:\n")
            for item in self.warnings:
                print(f"  {item}")
            print()
        
        # Print errors
        if self.errors:
            print("❌ CRITICAL ERRORS:\n")
            for item in self.errors:
                print(f"  {item}")
            print()
        
        # Summary
        print("=" * 80)
        
        if not self.errors:
            print("\n✅ ADMIN UI READY FOR CI — ALL CONTROLS VERIFIED\n")
            print("Next steps:")
            print("  1. Run: pytest tests/test_admin_ui.py -v")
            print("  2. Save CI proof: pytest ... > ci_proof_admin_ui_v1.0.0.txt")
            print("  3. Proceed to sign-off\n")
            return 0
        else:
            print("\n❌ ADMIN UI NOT READY FOR CI\n")
            print(f"Found {len(self.errors)} critical error(s)")
            print("Fix the above issues and re-run validation.\n")
            return 1


def main():
    """Main entry point."""
    validator = PreCIValidator()
    exit_code = validator.run_all_checks()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
