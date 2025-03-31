#!/usr/bin/env python3
"""
Fix the question_history column in user_categories table.

This script fixes the UnpicklingError by properly serializing an empty dict.
"""

import sqlite3
import logging
import os
import pickle
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database file path
DB_PATH = Path(__file__).parent / "AdaptiveLearning.db"

def run_migration():
    """Fix the question_history column data."""
    logger.info(f"Running migration on database: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        logger.error(f"Database file not found: {DB_PATH}")
        return False

    try:
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if the column exists
        cursor.execute("PRAGMA table_info(user_categories)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'question_history' not in column_names:
            logger.error("question_history column doesn't exist")
            conn.close()
            return False
        
        # Create a properly pickled empty dictionary
        empty_dict = {}
        pickled_empty_dict = pickle.dumps(empty_dict)
        
        logger.info("Fixing question_history with properly pickled empty dictionaries")
        cursor.execute("UPDATE user_categories SET question_history = ?", (pickled_empty_dict,))
        
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