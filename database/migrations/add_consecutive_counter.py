"""
Migration script to add consecutive_correct column to user_categories table

This supports the logarithmic learning curve implementation.
"""

import sqlite3
import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get the database file path (adjust if needed)
DB_PATH = Path(__file__).parent.parent.parent / 'AdaptiveLearning.db'

def run_migration():
    """Execute the migration to add consecutive_correct column"""
    logger.info(f"Running migration on database: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        logger.error(f"Error: Database file not found at {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(user_categories)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'consecutive_correct' not in columns:
            logger.info("Adding consecutive_correct column to user_categories table")
            cursor.execute('''
            ALTER TABLE user_categories 
            ADD COLUMN consecutive_correct INTEGER DEFAULT 0
            ''')
            
            # Update existing records
            cursor.execute('''
            UPDATE user_categories SET consecutive_correct = 0
            ''')
            
            logger.info("Successfully added consecutive_correct column")
        else:
            logger.info("consecutive_correct column already exists, skipping")
        
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error during migration: {str(e)}")
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration() 