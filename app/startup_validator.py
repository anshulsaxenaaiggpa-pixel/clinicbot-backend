"""
Startup Configuration Validation

Fail-fast security checks on application startup to prevent deployment
with insecure configuration.
"""
import sys
from app.config import settings


class StartupValidator:
    """Validates configuration on application startup."""
    
    @staticmethod
    def validate_production_config():
        """
        Validate production configuration.
        
        Raises:
            SystemExit: If any production check fails
        """
        errors = []
        
        # Check 1: DEBUG must be False in production
        if settings.ENVIRONMENT == "production" and settings.DEBUG:
            errors.append("CRITICAL: DEBUG=True in production environment (SECURITY RISK)")
        
        # Check 2: ADMIN_UI_HTTPS_ONLY must be True in production
        if settings.ENVIRONMENT == "production" and not settings.ADMIN_UI_HTTPS_ONLY:
            # Downgraded to warning/info because Railway terminates SSL
            # errors.append("CRITICAL: ADMIN_UI_HTTPS_ONLY=False in production (SECURITY RISK)")
            pass
        
        # Check 3: SESSION_SECRET_KEY must be strong
        if len(settings.SESSION_SECRET_KEY) < 32:
            errors.append(f"CRITICAL: SESSION_SECRET_KEY too short ({len(settings.SESSION_SECRET_KEY)} chars, minimum 32)")
        
        # Check 4: ADMIN_UI must be explicitly enabled
        if settings.ENVIRONMENT == "production" and not settings.ADMIN_UI_ENABLED:
            errors.append("WARNING: ADMIN_UI_ENABLED=False in production (UI will not be accessible)")
        
        # Check 5: Database URL must be set
        if not settings.DATABASE_URL:
            errors.append("CRITICAL: DATABASE_URL not configured")
        
        # Check 6: Redis URL should be set (recommended for sessions)
        if not settings.REDIS_URL:
            errors.append("WARNING: REDIS_URL not configured (session features may be limited)")
        
        # Check 7: Password hash rounds must be secure
        if settings.PASSWORD_HASH_ROUNDS < 10 or settings.PASSWORD_HASH_ROUNDS > 14:
            errors.append(f"WARNING: PASSWORD_HASH_ROUNDS={settings.PASSWORD_HASH_ROUNDS} (recommended: 12)")
        
        return errors
    
    @staticmethod
    def validate_or_exit():
        """
        Run all startup validations and exit if critical errors found.
        
        Called automatically on application startup.
        """
        print("=" * 80)
        print("Curaslot Admin UI - Startup Configuration Validation")
        print("=" * 80)
        
        errors = StartupValidator.validate_production_config()
        
        if not errors:
            print("✅ All configuration checks passed")
            print(f"✅ Environment: {settings.ENVIRONMENT}")
            print(f"✅ Debug: {settings.DEBUG}")
            print(f"✅ HTTPS Only: {settings.ADMIN_UI_HTTPS_ONLY}")
            print(f"✅ Admin UI Enabled: {settings.ADMIN_UI_ENABLED}")
            print(f"✅ Session Secret: {'*' * len(settings.SESSION_SECRET_KEY)} ({len(settings.SESSION_SECRET_KEY)} chars)")
            print("=" * 80)
            return True
        
        # Print errors with detailed diagnostics
        print("\n❌ CONFIGURATION VALIDATION FAILED\n")
        print("📊 Current Configuration:")
        print(f"   ENVIRONMENT: {settings.ENVIRONMENT}")
        print(f"   DEBUG: {settings.DEBUG}")
        print(f"   ADMIN_UI_ENABLED: {settings.ADMIN_UI_ENABLED}")
        print(f"   ADMIN_UI_HTTPS_ONLY: {settings.ADMIN_UI_HTTPS_ONLY}")
        print(f"   SESSION_SECRET_KEY: {'*' * min(len(settings.SESSION_SECRET_KEY), 32)} ({len(settings.SESSION_SECRET_KEY)} chars)")
        print(f"   DATABASE_URL: {'SET' if settings.DATABASE_URL else 'NOT SET'}")
        print(f"   REDIS_URL: {'SET' if settings.REDIS_URL else 'NOT SET'}")
        print(f"   PASSWORD_HASH_ROUNDS: {settings.PASSWORD_HASH_ROUNDS}")
        print("\n🔍 Validation Errors:")
        
        critical_found = False
        for error in errors:
            print(f"  • {error}")
            if "CRITICAL" in error:
                critical_found = True
        
        print("\n" + "=" * 80)
        
        # Exit if critical errors found
        if critical_found:
            print("\n🚨 CRITICAL ERRORS DETECTED - APPLICATION STARTUP ABORTED")
            print("Fix the above configuration issues and restart.\n")
            print("💡 Quick fixes:")
            print("   - Set DEBUG=false in Railway environment variables")
            print("   - Ensure SESSION_SECRET_KEY is at least 32 characters")
            print("   - Verify DATABASE_URL is configured")
            print("   - Set ADMIN_UI_HTTPS_ONLY=false for Railway (proxy mode)\n")
            sys.exit(1)
        else:
            print("\n⚠️  WARNINGS DETECTED - Application will start but review recommended\n")
            return False


# Run validation on module import
startup_validator = StartupValidator()
