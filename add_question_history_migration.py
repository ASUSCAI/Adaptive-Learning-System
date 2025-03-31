#!/usr/bin/env python3
"""
Add question_history column to user_categories table.

This is a standalone migration script to fix the error:
sqlalchemy.exc.OperationalError: no such column: user_categories.question_history
"""

import sqlite3
import logging
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database file path
DB_PATH = Path(__file__).parent / "AdaptiveLearning.db"

def run_migration():
    """Add question_history column to user_categories table."""
    logger.info(f"Running migration on database: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        logger.error(f"Database file not found: {DB_PATH}")
        return False

    try:
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(user_categories)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'question_history' in column_names:
            logger.info("question_history column already exists, skipping")
            conn.close()
            return True
        
        # Add the question_history column (SQLite doesn't support much DDL in ALTER TABLE)
        logger.info("Adding question_history column to user_categories table")
        cursor.execute("ALTER TABLE user_categories ADD COLUMN question_history BLOB")
        
        # Initialize the column with empty dicts
        logger.info("Initializing question_history with empty dictionaries")
        cursor.execute("UPDATE user_categories SET question_history = ?", ('gASV9QAAAAAAAH0u'.encode(),))  # pickled empty dict
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        logger.info("Migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_migration()
    exit(0 if success else 1) 