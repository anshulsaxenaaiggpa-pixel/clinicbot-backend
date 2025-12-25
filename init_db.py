#!/usr/bin/env python3
"""Initialize database with migrations and seed data for Railway deployment"""
import subprocess
import sys

def run_command(cmd, description):
    """Run a shell command and print output"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        print(f"❌ Failed: {description}")
        return False
    print(f"✅ Success: {description}")
    return True

def main():
    """Initialize database"""
    print("\n" + "="*60)
    print("🚀 DATABASE INITIALIZATION")
    print("="*60)
    
    # Step 1: Run Alembic migrations
    if not run_command("alembic upgrade head", "Running database migrations"):
        print("\n⚠️  WARNING: Migrations failed, but continuing...")
    
    # Step 2: Seed test data
    if not run_command("python seed_test_data.py", "Seeding test clinic data"):
        print("\n⚠️  WARNING: Seeding failed, but continuing...")
    
    print("\n" + "="*60)
    print("✅ DATABASE INITIALIZATION COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
