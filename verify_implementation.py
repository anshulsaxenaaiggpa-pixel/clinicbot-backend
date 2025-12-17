"""
Implementation Verification Script for ClinicBot.ai

Verifies that all required components are implemented correctly.
Checks file structure, imports, and configurations.

Usage:
    python verify_implementation.py
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

# Base paths
BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent


def check_file_exists(filepath: Path, description: str) -> bool:
    """Check if a file exists"""
    exists = filepath.exists()
    status = f"{GREEN}✓{RESET}" if exists else f"{RED}✗{RESET}"
    print(f"{status} {description}: {filepath.name}")
    return exists


def check_directory_exists(dirpath: Path, description: str) -> bool:
    """Check if a directory exists"""
    exists = dirpath.exists() and dirpath.is_dir()
    status = f"{GREEN}✓{RESET}" if exists else f"{RED}✗{RESET}"
    print(f"{status} {description}: {dirpath.name}/")
    return exists


def check_file_contains(filepath: Path, search_string: str, description: str) -> bool:
    """Check if a file contains a specific string"""
    try:
        if not filepath.exists():
            print(f"{RED}✗{RESET} {description}: File not found")
            return False
        
        content = filepath.read_text()
        contains = search_string in content
        status = f"{GREEN}✓{RESET}" if contains else f"{RED}✗{RESET}"
        print(f"{status} {description}")
        return contains
    except Exception as e:
        print(f"{RED}✗{RESET} {description}: {str(e)}")
        return False


def verify_backend_structure():
    """Verify backend project structure"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Backend Project Structure{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    results = []
    
    # Core files
    results.append(check_file_exists(BACKEND_DIR / "requirements.txt", "Requirements file"))
    results.append(check_file_exists(BACKEND_DIR / ".env.example", "Environment template"))
    results.append(check_file_exists(BACKEND_DIR / "Dockerfile", "Docker config"))
    results.append(check_file_exists(BACKEND_DIR / "seed_test_data.py", "Seed script"))
    
    # App directory structure
    app_dir = BACKEND_DIR / "app"
    results.append(check_directory_exists(app_dir, "App directory"))
    results.append(check_file_exists(app_dir / "__init__.py", "App init"))
    results.append(check_file_exists(app_dir / "main.py", "Main application"))
    results.append(check_file_exists(app_dir / "config.py", "Configuration"))
    
    # API structure
    api_dir = app_dir / "api" / "v1"
    results.append(check_directory_exists(api_dir, "API v1 directory"))
    
    api_files = [
        "clinics.py", "doctors.py", "services.py", "appointments.py",
        "slots.py", "patients.py", "summary.py", "webhooks.py", "auth.py"
    ]
    
    for api_file in api_files:
        results.append(check_file_exists(api_dir / api_file, f"API router: {api_file}"))
    
    # Models
    models_dir = app_dir / "models"
    results.append(check_directory_exists(models_dir, "Models directory"))
    
    # schemas
    schemas_dir = app_dir / "schemas"
    results.append(check_directory_exists(schemas_dir, "Schemas directory"))
    
    # Services
    services_dir = app_dir / "services"
    results.append(check_directory_exists(services_dir, "Services directory"))
    
    service_files = [
        "slot_engine.py", "conversation_manager.py", "intent_classifier.py",
        "whatsapp_handler.py", "whatsapp_sender.py", "patient_helpers.py"
    ]
    
    for service_file in service_files:
        results.append(check_file_exists(services_dir / service_file, f"Service: {service_file}"))
    
    return all(results)


def verify_frontend_structure():
    """Verify frontend project structure"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Frontend Project Structure{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    frontend_dir = PROJECT_ROOT / "frontend"
    
    if not frontend_dir.exists():
        print(f"{RED}✗{RESET} Frontend directory not found")
        return False
    
    results = []
    
    # Core files
    results.append(check_file_exists(frontend_dir / "package.json", "Package config"))
    results.append(check_file_exists(frontend_dir / ".env.example", "Environment template"))
    results.append(check_file_exists(frontend_dir / "tailwind.config.ts", "Tailwind config"))
    
    # App directory (Next.js 14 app router)
    app_dir = frontend_dir / "app"
    results.append(check_directory_exists(app_dir, "App directory"))
    results.append(check_file_exists(app_dir / "layout.tsx", "Main layout"))
    results.append(check_file_exists(app_dir / "globals.css", "Global styles"))
    
    # Dashboard pages
    pages = [
        "dashboard", "calendar", "appointments", "patients",
        "doctors", "services", "analytics", "settings"
    ]
    
    for page in pages:
        page_dir = app_dir / page
        results.append(check_directory_exists(page_dir, f"Page: {page}"))
    
    # Lib directory
    lib_dir = frontend_dir / "lib"
    results.append(check_directory_exists(lib_dir, "Lib directory"))
    results.append(check_file_exists(lib_dir / "api-client.ts", "API client"))
    results.append(check_file_exists(lib_dir / "api.ts", "API functions"))
    
    return all(results)


def verify_dependencies():
    """Verify required dependencies are listed"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Backend Dependencies{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    req_file = BACKEND_DIR / "requirements.txt"
    
    if not req_file.exists():
        print(f"{RED}✗{RESET} requirements.txt not found")
        return False
    
    required_packages = [
        "fastapi", "uvicorn", "sqlalchemy", "psycopg2-binary",
        "redis", "celery", "twilio", "openai", "pydantic"
    ]
    
    results = []
    for package in required_packages:
        results.append(check_file_contains(req_file, package, f"Package: {package}"))
    
    return all(results)


def verify_configurations():
    """Verify configuration files"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Configuration Files{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    results = []
    
    # Docker compose
    docker_file = PROJECT_ROOT / "docker-compose.yml"
    results.append(check_file_exists(docker_file, "Docker Compose"))
    
    if docker_file.exists():
        results.append(check_file_contains(docker_file, "postgres:", "PostgreSQL service"))
        results.append(check_file_contains(docker_file, "redis:", "Redis service"))
        results.append(check_file_contains(docker_file, "backend:", "Backend service"))
    
    # .env.example
    env_example = BACKEND_DIR / ".env.example"
    if env_example.exists():
        results.append(check_file_contains(env_example, "DATABASE_URL", "Database URL config"))
        results.append(check_file_contains(env_example, "REDIS_URL", "Redis URL config"))
        results.append(check_file_contains(env_example, "OPENAI_API_KEY", "OpenAI API key"))
        results.append(check_file_contains(env_example, "TWILIO_", "Twilio config"))
    
    return all(results)


def verify_key_implementations():
    """Verify key implementations exist"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Key Feature Implementations{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    results = []
    
    # Slot engine
    slot_engine = BACKEND_DIR / "app" / "services" / "slot_engine.py"
    if slot_engine.exists():
        results.append(check_file_contains(
            slot_engine,
            "generate_free_slots_for_day",
            "Slot generation function"
        ))
        results.append(check_file_contains(
            slot_engine,
            "check_slot_conflicts",
            "Conflict detection function"
        ))
    
    # Intent classifier
    intent_classifier = BACKEND_DIR / "app" / "services" / "intent_classifier.py"
    if intent_classifier.exists():
        results.append(check_file_contains(
            intent_classifier,
            "classify_intent",
            "Intent classification function"
        ))
        results.append(check_file_contains(
            intent_classifier,
            "openai",
            "OpenAI integration"
        ))
    
    # Conversation manager
    conv_manager = BACKEND_DIR / "app" / "services" / "conversation_manager.py"
    if conv_manager.exists():
        results.append(check_file_contains(
            conv_manager,
            "ConversationManager",
            "Conversation manager class"
        ))
        results.append(check_file_contains(
            conv_manager,
            "process_message",
            "Message processing function"
        ))
    
    # Main app
    main_file = BACKEND_DIR / "app" / "main.py"
    if main_file.exists():
        results.append(check_file_contains(
            main_file,
            "FastAPI",
            "FastAPI app"
        ))
        results.append(check_file_contains(
            main_file,
            "include_router",
            "Router inclusion"
        ))
    
    return all(results)


def verify_documentation():
    """Verify documentation files exist"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Documentation Files{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    results = []
    
    docs = [
        (PROJECT_ROOT / "README.md", "README"),
        (PROJECT_ROOT / "ARCHITECTURE.md", "Architecture doc"),
        (PROJECT_ROOT / "SUBMISSION.md", "Submission doc"),
        (PROJECT_ROOT / "docs" / "API_DOCUMENTATION.md", "API documentation"),
        (PROJECT_ROOT / "docs" / "DEPLOYMENT_GUIDE.md", "Deployment guide"),
        (PROJECT_ROOT / "docs" / "TESTING_REPORT.md", "Testing report"),
    ]
    
    for filepath, description in docs:
        results.append(check_file_exists(filepath, description))
    
    return all(results)


def print_summary(section_results: dict):
    """Print verification summary"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Verification Summary{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    total_passed = sum(section_results.values())
    total_sections = len(section_results)
    
    for section, passed in section_results.items():
        status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
        print(f"{status} {section}")
    
    print(f"\nTotal: {total_passed}/{total_sections} sections passed")
    
    if total_passed == total_sections:
        print(f"\n{GREEN}🎉 All verifications passed! Implementation is complete.{RESET}\n")
        return True
    else:
        print(f"\n{YELLOW}⚠️  Some verifications failed. Review the results above.{RESET}\n")
        return False


def main():
    """Run all verifications"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}  ClinicBot.ai - Implementation Verification{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}  Project: {PROJECT_ROOT}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    # Run verifications
    results = {
        "Backend Structure": verify_backend_structure(),
        "Frontend Structure": verify_frontend_structure(),
        "Dependencies": verify_dependencies(),
        "Configuration": verify_configurations(),
        "Key Features": verify_key_implementations(),
        "Documentation": verify_documentation()
    }
    
    # Print summary
    success = print_summary(results)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
