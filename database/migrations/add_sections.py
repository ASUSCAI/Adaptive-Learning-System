"""
Migration script to add section tables to the database

This script creates:
1. sections table
2. section_users association table
3. section_categories association table
"""

import sqlite3
import os
from pathlib import Path

# Get the database file path (adjust if needed)
DB_PATH = Path(__file__).parent.parent.parent / 'AdaptiveLearning.db'

def run_migration():
    """Execute the migration to add section tables"""
    print(f"Running migration on database: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Create sections table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            uuid TEXT NOT NULL UNIQUE
        )
        ''')
        
        # Create section_users association table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS section_users (
            section_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY (section_id, user_id),
            FOREIGN KEY (section_id) REFERENCES sections (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        ''')
        
        # Create section_categories association table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS section_categories (
            section_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            PRIMARY KEY (section_id, category_id),
            FOREIGN KEY (section_id) REFERENCES sections (id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
        )
        ''')
        
        conn.commit()
        print("Migration completed successfully.")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {str(e)}")
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration() 