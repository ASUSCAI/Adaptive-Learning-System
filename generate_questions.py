import google.generativeai as genai
import json
import os
from typing import List, Dict
import time
from database.models import Category, Question, Option
from database.engine import SessionLocal
import uuid

# Configure the Google Generative AI
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("Please set the GOOGLE_API_KEY environment variable")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# CSE 110 Java Categories and their descriptions
CSE110_CATEGORIES = {
    "Introduction to Java": "Basic concepts of Java programming, JVM, and development environment",
    "Variables and Data Types": "Java primitive types, variables, constants, and type conversion",
    "Control Structures": "If-else statements, switch cases, while loops, for loops, and break/continue",
    "Methods": "Method declaration, parameters, return types, method overloading, and scope",
    "Arrays and Collections": "Arrays, ArrayLists, and basic Java collections framework",
    "Object-Oriented Programming": "Classes, objects, constructors, instance variables, and methods",
    "Inheritance and Polymorphism": "Inheritance, method overriding, abstract classes, and interfaces",
    "Exception Handling": "Try-catch blocks, checked and unchecked exceptions, and finally block",
    "File I/O": "Reading from and writing to files using Java I/O streams",
    "Testing and Debugging": "Unit testing with JUnit, debugging techniques, and code quality"
}

def create_categories(session):
    """Create CSE 110 categories in the database if they don't exist."""
    for category_name, description in CSE110_CATEGORIES.items():
        existing_category = session.query(Category).filter_by(name=category_name).first()
        if not existing_category:
            category = Category(name=category_name)
            session.add(category)
    session.commit()

def generate_question_bank(category_name: str, num_questions: int = 50) -> List[Dict]:
    """
    Generate questions for a specific category using Google's Generative AI.
    
    Args:
        category_name (str): Name of the category to generate questions for
        num_questions (int): Number of questions to generate
    
    Returns:
        List[Dict]: List of questions with their answers and explanations
    """
    category_description = CSE110_CATEGORIES.get(category_name, "")
    
    prompt = f"""Generate {num_questions} multiple choice questions for an Introduction to Java Programming course (CSE 110).
    The questions should be about {category_name}: {category_description}
    
    For each question, provide:
    1. The question text (should be clear and concise)
    2. Four options (A, B, C, D) - one correct and three plausible but incorrect
    3. The correct answer (A, B, C, or D)
    4. A brief explanation of why the correct answer is right
    
    The questions should:
    - Test understanding of Java programming concepts
    - Include Java code snippets where appropriate
    - Have clear, unambiguous answers
    - Be suitable for beginners
    - Focus on practical programming knowledge
    - Include common pitfalls and best practices
    
    Format the response as a JSON array where each question is an object with the following structure:
    {{
        "question": "question text",
        "options": ["A. option1", "B. option2", "C. option3", "D. option4"],
        "correct_answer": "A",
        "explanation": "explanation of the correct answer"
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        questions = json.loads(response.text)
        return questions
    except Exception as e:
        print(f"Error generating questions for {category_name}: {e}")
        return []

def save_questions_to_database(questions: List[Dict], category_id: int, session):
    """Save the generated questions to the database."""
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

def main():
    session = SessionLocal()
    
    try:
        # Create categories
        create_categories(session)
        
        # Generate questions for each category
        for category_name in CSE110_CATEGORIES.keys():
            print(f"Generating questions for {category_name}...")
            
            # Get category from database
            category = session.query(Category).filter_by(name=category_name).first()
            if not category:
                print(f"Category {category_name} not found in database")
                continue
            
            # Generate questions
            questions = generate_question_bank(category_name)
            
            # Save to database
            if questions:
                save_questions_to_database(questions, category.id, session)
                print(f"Saved {len(questions)} questions for {category_name}")
            else:
                print(f"No questions generated for {category_name}")
            
            # Add a small delay between API calls
            time.sleep(1)
            
    finally:
        session.close()

if __name__ == "__main__":
    main() 