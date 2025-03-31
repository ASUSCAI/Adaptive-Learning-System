#!/usr/bin/env python3
"""
Database Export/Import Utility for Adaptive Learning System

This script provides functionality to export and import database data,
specifically focused on Question Data and User Information.

Usage:
  python database_export_import.py --export [filename.json]
  python database_export_import.py --import [filename.json]
  python database_export_import.py --export-questions [filename.json]
  python database_export_import.py --import-questions [filename.json]
  python database_export_import.py --export-users [filename.json]
  python database_export_import.py --import-users [filename.json]
"""

import argparse
import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
import uuid

# Import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.models import (
    Base, User, Category, Question, Option, UserCategory, 
    section_users, section_categories, Section
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default database path
DB_PATH = Path("AdaptiveLearning.db")

def create_session(db_path=DB_PATH):
    """Create a database session."""
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    return Session()

def export_data(output_file, export_questions=True, export_users=True):
    """
    Export data from the database to a JSON file.
    
    Args:
        output_file: Path to the output JSON file
        export_questions: Whether to export question data
        export_users: Whether to export user data
    """
    session = create_session()
    
    data = {
        "metadata": {
            "exported_at": datetime.now().isoformat(),
            "version": "1.0"
        }
    }
    
    try:
        # Export question data
        if export_questions:
            logger.info("Exporting question data...")
            
            # Export categories
            categories = []
            for cat in session.query(Category).all():
                categories.append({
                    "id": cat.id,
                    "name": cat.name,
                    "uuid": cat.uuid
                })
            data["categories"] = categories
            logger.info(f"Exported {len(categories)} categories")
            
            # Export questions with options
            questions = []
            for q in session.query(Question).all():
                q_data = {
                    "id": q.id,
                    "text": q.text,
                    "category_id": q.category_id,
                    "uuid": q.uuid,
                    "options": []
                }
                
                # Add options for this question
                for opt in q.options:
                    q_data["options"].append({
                        "id": opt.id,
                        "text": opt.text,
                        "is_correct": opt.is_correct,
                        "uuid": opt.uuid
                    })
                
                questions.append(q_data)
            
            data["questions"] = questions
            logger.info(f"Exported {len(questions)} questions with options")
            
            # Export sections
            sections = []
            for section in session.query(Section).all():
                section_data = {
                    "id": section.id,
                    "name": section.name,
                    "description": section.description,
                    "uuid": section.uuid,
                    "category_ids": [cat.id for cat in section.categories]
                }
                sections.append(section_data)
            
            data["sections"] = sections
            logger.info(f"Exported {len(sections)} sections")
        
        # Export user data
        if export_users:
            logger.info("Exporting user data...")
            
            # Export users
            users = []
            for user in session.query(User).all():
                # Don't export password hashes for security
                user_data = {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "is_admin": user.is_admin,
                    "section_ids": [section.id for section in user.sections]
                }
                
                # Export user's learning progress
                user_data["progress"] = []
                for uc in session.query(UserCategory).filter_by(user_id=user.id).all():
                    user_data["progress"].append({
                        "category_id": uc.category_id,
                        "current_knowledge": uc.current_knowledge,
                        "consecutive_correct": uc.consecutive_correct
                    })
                
                users.append(user_data)
            
            data["users"] = users
            logger.info(f"Exported {len(users)} users with their progress")
        
        # Write the data to the output file
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Successfully exported data to {output_file}")
    
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}")
        raise
    finally:
        session.close()

def import_data(input_file, import_questions=True, import_users=True):
    """
    Import data from a JSON file into the database.
    
    Args:
        input_file: Path to the JSON file
        import_questions: Whether to import question data
        import_users: Whether to import user data
    """
    session = create_session()
    
    try:
        # Read the JSON file
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        if "metadata" not in data:
            logger.warning("No metadata found in the import file")
        else:
            logger.info(f"Importing data exported at {data['metadata'].get('exported_at')}")
        
        # Import question data
        if import_questions and "categories" in data and "questions" in data:
            logger.info("Importing question data...")
            
            # Import categories
            category_map = {}  # To map old IDs to new IDs
            for cat_data in data["categories"]:
                # Check if category already exists by UUID
                cat = session.query(Category).filter_by(uuid=cat_data["uuid"]).first()
                
                if not cat:
                    # Create a new category
                    cat = Category(
                        name=cat_data["name"],
                        uuid=cat_data["uuid"]
                    )
                    session.add(cat)
                    session.flush()  # To get the ID
                
                category_map[cat_data["id"]] = cat.id
            
            logger.info(f"Imported {len(data['categories'])} categories")
            
            # Import questions with options
            question_map = {}  # To map old IDs to new IDs
            for q_data in data["questions"]:
                # Map category ID
                category_id = category_map.get(q_data["category_id"])
                if not category_id:
                    logger.warning(f"Skipping question: category ID {q_data['category_id']} not found")
                    continue
                
                # Check if question already exists by UUID
                q = session.query(Question).filter_by(uuid=q_data["uuid"]).first()
                
                if not q:
                    # Create a new question
                    q = Question(
                        text=q_data["text"],
                        category_id=category_id,
                        uuid=q_data["uuid"]
                    )
                    session.add(q)
                    session.flush()  # To get the ID
                
                question_map[q_data["id"]] = q.id
                
                # Get existing options for this question to avoid duplicates
                existing_options = {opt.uuid for opt in q.options}
                
                # Import options
                for opt_data in q_data["options"]:
                    if opt_data["uuid"] in existing_options:
                        continue
                    
                    opt = Option(
                        text=opt_data["text"],
                        is_correct=opt_data["is_correct"],
                        question_id=q.id,
                        uuid=opt_data["uuid"]
                    )
                    session.add(opt)
            
            logger.info(f"Imported {len(data['questions'])} questions with options")
            
            # Import sections
            if "sections" in data:
                section_map = {}  # To map old IDs to new IDs
                for section_data in data["sections"]:
                    # Check if section already exists by UUID
                    section = session.query(Section).filter_by(uuid=section_data["uuid"]).first()
                    
                    if not section:
                        # Create a new section
                        section = Section(
                            name=section_data["name"],
                            description=section_data["description"],
                            uuid=section_data["uuid"]
                        )
                        session.add(section)
                        session.flush()  # To get the ID
                    
                    section_map[section_data["id"]] = section.id
                    
                    # Clear existing category associations to avoid duplicates
                    section.categories = []
                    
                    # Add categories to section
                    for cat_id in section_data["category_ids"]:
                        mapped_cat_id = category_map.get(cat_id)
                        if mapped_cat_id:
                            cat = session.query(Category).get(mapped_cat_id)
                            if cat:
                                section.categories.append(cat)
                
                logger.info(f"Imported {len(data['sections'])} sections")
        
        # Import user data
        if import_users and "users" in data:
            logger.info("Importing user data...")
            
            # Import users
            user_map = {}  # To map old IDs to new IDs
            for user_data in data["users"]:
                # Check if user already exists by email
                user = session.query(User).filter_by(email=user_data["email"]).first()
                
                if not user:
                    # Create a new user (note: password hash is missing, will need to reset)
                    user = User(
                        name=user_data["name"],
                        email=user_data["email"],
                        password_hash="IMPORTED_USER_NEEDS_PASSWORD_RESET",
                        is_admin=user_data["is_admin"]
                    )
                    session.add(user)
                    session.flush()  # To get the ID
                    logger.info(f"Created new user: {user.email} (password needs to be reset)")
                
                user_map[user_data["id"]] = user.id
                
                # Clear existing section associations to avoid duplicates
                user.sections = []
                
                # Add user to sections
                if "section_ids" in user_data:
                    for section_id in user_data["section_ids"]:
                        mapped_section_id = section_map.get(section_id)
                        if mapped_section_id:
                            section = session.query(Section).get(mapped_section_id)
                            if section:
                                user.sections.append(section)
                
                # Import user progress
                if "progress" in user_data:
                    for progress in user_data["progress"]:
                        # Map category ID
                        category_id = category_map.get(progress["category_id"])
                        if not category_id:
                            logger.warning(f"Skipping progress: category ID {progress['category_id']} not found")
                            continue
                        
                        # Check if progress already exists
                        uc = session.query(UserCategory).filter_by(
                            user_id=user.id,
                            category_id=category_id
                        ).first()
                        
                        if not uc:
                            # Create new progress entry
                            uc = UserCategory(
                                user_id=user.id,
                                category_id=category_id,
                                current_knowledge=progress["current_knowledge"],
                                consecutive_correct=progress["consecutive_correct"]
                            )
                            session.add(uc)
                        else:
                            # Update existing progress
                            uc.current_knowledge = progress["current_knowledge"]
                            uc.consecutive_correct = progress["consecutive_correct"]
            
            logger.info(f"Imported {len(data['users'])} users with their progress")
        
        # Commit all changes
        session.commit()
        logger.info("Successfully imported data")
    
    except Exception as e:
        logger.error(f"Error importing data: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

def main():
    parser = argparse.ArgumentParser(description='Database Export/Import Utility for Adaptive Learning System')
    
    # Export/import options
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--export', metavar='FILE', help='Export all data to a JSON file')
    group.add_argument('--import', metavar='FILE', dest='import_file', help='Import all data from a JSON file')
    group.add_argument('--export-questions', metavar='FILE', help='Export only question data to a JSON file')
    group.add_argument('--import-questions', metavar='FILE', help='Import only question data from a JSON file')
    group.add_argument('--export-users', metavar='FILE', help='Export only user data to a JSON file')
    group.add_argument('--import-users', metavar='FILE', help='Import only user data from a JSON file')
    
    # Database path option
    parser.add_argument('--db', metavar='PATH', help=f'Path to the database file (default: {DB_PATH})')
    
    args = parser.parse_args()
    
    # Set the database path if provided
    if args.db:
        global DB_PATH
        DB_PATH = Path(args.db)
    
    # Check if the database exists
    if not DB_PATH.exists():
        logger.error(f"Database file not found: {DB_PATH}")
        return 1
    
    try:
        # Handle export options
        if args.export:
            export_data(args.export, export_questions=True, export_users=True)
        elif args.export_questions:
            export_data(args.export_questions, export_questions=True, export_users=False)
        elif args.export_users:
            export_data(args.export_users, export_questions=False, export_users=True)
        
        # Handle import options
        elif args.import_file:
            import_data(args.import_file, import_questions=True, import_users=True)
        elif args.import_questions:
            import_data(args.import_questions, import_questions=True, import_users=False)
        elif args.import_users:
            import_data(args.import_users, import_questions=False, import_users=True)
        
        return 0
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 