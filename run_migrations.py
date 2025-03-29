"""
Run all migrations in the correct order
"""

import importlib
import sys
import os
from pathlib import Path

# Add the project root to the Python path to allow importing modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database.migrations import add_sections
from database.migrations import add_consecutive_counter

def run_migrations():
    """Run all migrations in the correct order"""
    print("Running all migrations...")
    
    # Ensure instance directory exists
    instance_dir = project_root / 'instance'
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)
        print(f"Created instance directory: {instance_dir}")
    
    # List of migration modules to run in order
    migrations = [
        add_sections,
        add_consecutive_counter,
    ]
    
    success = True
    
    # Run each migration
    for migration in migrations:
        migration_name = migration.__name__.split('.')[-1]
        print(f"\nRunning migration: {migration_name}")
        
        if not migration.run_migration():
            print(f"Migration failed: {migration_name}")
            success = False
            break
    
    if success:
        print("\nAll migrations completed successfully.")
    else:
        print("\nMigration process failed.")
    
    return success

if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1) 