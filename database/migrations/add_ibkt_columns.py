"""
Migration script to add IBKT (Individualized Bayesian Knowledge Tracing) columns to user_categories table

This migration supports the transition from standard BKT to individualized BKT.
"""

import sqlite3
import os
from pathlib import Path
import logging
import pickle

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get the database file path (adjust if needed)
DB_PATH = Path(__file__).parent.parent.parent / 'AdaptiveLearning.db'

def run_migration():
    """Execute the migration to add IBKT columns to user_categories table"""
    logger.info(f"Running migration on database: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        logger.error(f"Error: Database file not found at {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(user_categories)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        # Define new columns to add
        new_columns = [
            # IBKT parameters
            ("performance_history", "BLOB DEFAULT NULL"),
            ("total_attempts", "INTEGER DEFAULT 0"),
            ("correct_attempts", "INTEGER DEFAULT 0"),
            
            # Learning style metrics
            ("consistency_score", "REAL DEFAULT 0.0"),
            ("improvement_rate", "REAL DEFAULT 0.0"),
            ("error_recovery", "REAL DEFAULT 0.0"),
            
            # Parameter adjustments
            ("transit_adjustment", "REAL DEFAULT 0.0"),
            ("slip_adjustment", "REAL DEFAULT 0.0"),
            ("guess_adjustment", "REAL DEFAULT 0.0"),
            
            # Adaptation settings
            ("learning_rate", "REAL DEFAULT 0.05"),
            ("adaptivity_threshold", "INTEGER DEFAULT 10"),
            ("adaptation_rate", "REAL DEFAULT 0.05")
        ]
        
        # Add new columns if they don't already exist
        for column_name, definition in new_columns:
            if column_name not in existing_columns:
                logger.info(f"Adding {column_name} column to user_categories table")
                cursor.execute(f'''
                ALTER TABLE user_categories 
                ADD COLUMN {column_name} {definition}
                ''')
            else:
                logger.info(f"{column_name} column already exists, skipping")
        
        # Initialize empty lists for performance_history
        cursor.execute("SELECT id FROM user_categories")
        category_ids = [row[0] for row in cursor.fetchall()]
        
        for category_id in category_ids:
            # Get existing attempts for each user_category to seed performance history
            cursor.execute('''
                SELECT attempt_logs.is_correct 
                FROM attempt_logs 
                JOIN questions ON attempt_logs.question_id = questions.id
                JOIN user_categories ON user_categories.user_id = attempt_logs.user_id 
                    AND user_categories.category_id = questions.category_id
                WHERE user_categories.id = ?
                ORDER BY attempt_logs.timestamp
            ''', (category_id,))
            
            attempts = [bool(row[0]) for row in cursor.fetchall()]
            
            # Update performance history with historical data
            if attempts:
                # Limit to most recent 100 attempts
                if len(attempts) > 100:
                    attempts = attempts[-100:]
                
                binary_history = pickle.dumps(attempts)
                
                # Update counters based on performance history
                total_attempts = len(attempts)
                correct_attempts = sum(1 for a in attempts if a)
                
                cursor.execute('''
                    UPDATE user_categories
                    SET performance_history = ?,
                        total_attempts = ?,
                        correct_attempts = ?
                    WHERE id = ?
                ''', (binary_history, total_attempts, correct_attempts, category_id))
            else:
                # Initialize with empty list if no attempts found
                empty_list = pickle.dumps([])
                cursor.execute('''
                    UPDATE user_categories
                    SET performance_history = ?
                    WHERE id = ?
                ''', (empty_list, category_id))
        
        logger.info("Successfully added IBKT columns and initialized data")
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