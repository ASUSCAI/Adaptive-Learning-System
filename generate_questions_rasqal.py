import json
import os
from typing import List, Dict
import time
from database.models import Category, Question, Option
from database.engine import DatabaseEngine
import uuid
from dotenv import load_dotenv
from sqlalchemy.orm import joinedload
from sqlalchemy import func

# Load environment variables from .env file
load_dotenv()

# Initialize database engine
db_engine = DatabaseEngine('sqlite:///AdaptiveLearning.db')

# CSE 110 Java Categories and their descriptions
CSE445_CATEGORIES = {
    "Introduction to Microservices": "Basic concepts of microservices architecture, including its advantages and disadvantages.",
}

def create_categories():
    """Create CSE 110 categories in the database if they don't exist."""
    session = db_engine.get_session()
    try:
        for category_name, description in CSE445_CATEGORIES.items():
            existing_category = session.query(Category).filter_by(name=category_name).first()
            if not existing_category:
                category = Category(name=category_name, uuid=str(uuid.uuid4()))
                session.add(category)
        session.commit()
    finally:
        session.close()

def generate_question_bank(category_name: str, num_questions: int = 25) -> List[Dict]:
    """
    Generate questions for a specific category using Google's Generative AI.
    
    Args:
        category_name (str): Name of the category to generate questions for
        num_questions (int): Number of questions to generate
    
    Returns:
        List[Dict]: List of questions with their answers and explanations
    """
    category_description = CSE445_CATEGORIES.get(category_name, "")
    
    prompt = f"""You are a Java programming instructor creating multiple choice questions for CSE 110.
    Generate exactly {num_questions} multiple choice questions about {category_name}: {category_description}
    
    Requirements:
    1. Each question must be clear and concise
    2. Include Java code snippets where appropriate
    3. Questions should test understanding, not memorization
    4. All questions must be suitable for beginners
    5. Include common pitfalls and best practices
    6. Each question must have exactly 4 options (A, B, C, D)
    7. Only one option should be correct
    8. Provide a clear explanation for the correct answer
    
    IMPORTANT: Your response must be a valid JSON array with exactly this structure:
    [
        {{
            "question": "question text",
            "options": ["A. option1", "B. option2", "C. option3", "D. option4"],
            "correct_answer": "A",
            "explanation": "explanation of the correct answer"
        }},
        // ... more questions ...
    ]
    
    Do not include any text before or after the JSON array. The response must be valid JSON that can be parsed directly.
    """
    try:
        
        questions = [
            {
                "question": "question text",
                "options": ["A. option1", "B. option2", "C. option3", "D. option4"],
                "correct_answer": "A",
                "explanation": "explanation of the correct answer"
            }
        ]
        return questions
    except Exception as e:
        print(f"Error generating questions for {category_name}: {e}")
        print(f"Questions: {questions}")
        return []
    
def save_questions_to_database(questions: List[Dict], category_id: int):
    """Save the generated questions to the database."""
    session = db_engine.get_session()
    try:
        for q in questions:
            # Create question
            question = Question(
                text=q["question"],
                category_id=category_id,
                uuid=str(uuid.uuid4())
            )
            session.add(question)
            session.flush()  # Get the question ID
            
            # Create options
            for i, option_text in enumerate(q["options"]):
                option = Option(
                    text=option_text,
                    is_correct=(chr(65 + i) == q["correct_answer"]),  # Convert A,B,C,D to 0,1,2,3
                    question_id=question.id,
                    uuid=str(uuid.uuid4())
                )
                session.add(option)
        
        session.commit()
    finally:
        session.close()

def main():
    try:
        # Create categories
        create_categories()
        
        # Generate questions for each category
        for category_name in CSE445_CATEGORIES.keys():
            print(f"Generating questions for {category_name}...")
            
            # Get category from database
            session = db_engine.get_session()
            try:
                category = session.query(Category).filter_by(name=category_name).first()
                if not category:
                    print(f"Category {category_name} not found in database")
                    continue
                
                # Generate questions
                questions = generate_question_bank(category_name, num_questions=25)  # Reduced to 3 questions per category
                
                # Save to database
                if questions:
                    save_questions_to_database(questions, category.id)
                    print(f"Saved {len(questions)} questions for {category_name}")
                else:
                    print(f"No questions generated for {category_name}")
                
            finally:
                session.close()
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main() 