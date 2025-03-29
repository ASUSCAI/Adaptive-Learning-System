"""
Script to update BKT parameters for existing records to slow down progression

This updates the parameters for all existing UserCategory records.
"""

import sqlite3
import os
from pathlib import Path
from shared import db
from database.models import UserCategory
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get the database path from the environment or use the default
DB_PATH = os.environ.get('DB_PATH', 'AdaptiveLearning.db')

def update_bkt_parameters():
    # Connect to the database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Retrieve all user categories
    c.execute('SELECT id, p_init, p_transit, p_slip, p_guess FROM user_categories')
    categories = c.fetchall()
    
    # Update parameters for each user category
    for category in categories:
        category_id, p_init, p_transit, p_slip, p_guess = category
        
        # New extremely reduced parameters for slower learning
        new_p_init = 0.15  # Lower initial knowledge (was 0.2)
        new_p_transit = 0.15  # Much slower learning rate (was 0.3/0.25)
        new_p_slip = 0.15  # Higher chance of slipping (was 0.1)
        new_p_guess = 0.08  # Lower chance of guessing (was 0.1)
        
        # Update user category with new parameters
        c.execute('''
            UPDATE user_categories 
            SET p_init = ?, p_transit = ?, p_slip = ?, p_guess = ?
            WHERE id = ?
        ''', (new_p_init, new_p_transit, new_p_slip, new_p_guess, category_id))
    
    # Update all users' knowledge states to be more conservative
    c.execute('SELECT id, current_knowledge FROM user_categories')
    user_categories = c.fetchall()
    
    for user_category in user_categories:
        user_category_id, current_knowledge = user_category
        
        # Reset consecutive_correct to 0 for all users to ensure consistent behavior
        c.execute('UPDATE user_categories SET consecutive_correct = 0 WHERE id = ?', (user_category_id,))
        
        # Even more aggressive scaling down of all knowledge states
        if current_knowledge > 0.7:
            # Extremely aggressive reset of very high knowledge states (cut to 1/4)
            new_knowledge = current_knowledge / 4
        elif current_knowledge > 0.5:
            # Very aggressive reset of high knowledge states (cut to 1/3)
            new_knowledge = current_knowledge / 3
        elif current_knowledge > 0.3:
            # Significant reset of medium knowledge states (cut to 1/2)
            new_knowledge = current_knowledge / 2
        else:
            # Moderate reduction of beginner knowledge states
            new_knowledge = current_knowledge * 0.6
        
        # Add a small buffer above initial knowledge for experienced users
        # This ensures they don't start over completely, but progression is still very slow
        if current_knowledge > 0.4:
            new_knowledge = max(new_knowledge, new_p_init * 1.2)
        else:
            # For beginners, ensure the knowledge is just slightly above initial
            new_knowledge = max(new_knowledge, new_p_init * 1.05)
        
        # Update the user's knowledge state
        c.execute('UPDATE user_categories SET current_knowledge = ? WHERE id = ?', (new_knowledge, user_category_id))
    
    # Commit changes and close the connection
    conn.commit()
    conn.close()

if __name__ == '__main__':
    update_bkt_parameters() 