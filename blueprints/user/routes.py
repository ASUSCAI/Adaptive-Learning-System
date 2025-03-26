from flask import render_template, redirect, url_for, flash, request, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database.models import User, Category, UserCategory, Question, Option, AttemptLog
from shared import db
from functools import wraps
from typing import Optional
from . import user_bp
from sqlalchemy.sql import func
from sqlalchemy.orm import joinedload
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('user.login'))
        return f(*args, **kwargs)
    return decorated_function

# Get current user
def get_current_user() -> Optional[User]:
    if 'user_id' not in session:
        return None
    return db.get(User, session['user_id'])

# Authentication routes
@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = db.query(User).filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            flash('Successfully logged in!', 'success')
            return redirect(url_for('user.dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('user/login.html')

@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if db.query(User).filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('user.register'))
        
        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.add(user)
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('user.login'))
    
    return render_template('user/register.html')

@user_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('user.login'))

# Dashboard and Category routes
@user_bp.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    categories = db.get_all(Category)
    user_categories = {
        uc.category_id: uc for uc in db.query(UserCategory).filter_by(user_id=user.id).all()
    }
    
    return render_template('user/dashboard.html',
                         user=user,
                         categories=categories,
                         user_categories=user_categories)

@user_bp.route('/category/<int:category_id>')
@login_required
def category_detail(category_id):
    user = get_current_user()
    
    # Get category with questions and options eagerly loaded
    category = db.query(Category).filter_by(id=category_id).options(
        joinedload(Category.questions).joinedload(Question.options)
    ).first()
    
    if not category:
        flash('Category not found.', 'error')
        return redirect(url_for('user.dashboard'))
    
    user_category = db.query(UserCategory).filter_by(
        user_id=user.id,
        category_id=category_id
    ).first()
    
    if not user_category:
        user_category = UserCategory(
            user_id=user.id,
            category_id=category_id
        )
        db.add(user_category)
    
    return render_template('user/category_detail.html',
                         user=user,
                         category=category,
                         user_category=user_category)

@user_bp.route('/category/<int:category_id>/next-question')
@login_required
def get_next_question(category_id):
    logger.debug(f"Accessing next question for category {category_id}")
    user = get_current_user()
    category = db.get(Category, category_id)
    if not category:
        logger.error(f"Category {category_id} not found")
        return jsonify({'error': 'Category not found'}), 404
    
    # Get a random question from the category with options eagerly loaded
    question = db.query(Question).filter_by(category_id=category_id).options(
        joinedload(Question.options)
    ).order_by(func.random()).first()
    
    if not question:
        logger.error(f"No questions found for category {category_id}")
        return jsonify({'error': 'No questions available'}), 404
    
    logger.debug(f"Found question {question.id} for category {category_id}")
    logger.debug(f"Question text: {question.text}")
    logger.debug(f"Number of options: {len(question.options)}")
    logger.debug(f"Options: {[{'id': opt.id, 'text': opt.text, 'is_correct': opt.is_correct} for opt in question.options]}")
    
    # Format the question for the frontend
    options = [{'id': opt.id, 'text': opt.text} for opt in question.options]
    return jsonify({
        'question_id': question.id,
        'text': question.text,
        'options': options
    })


@user_bp.route('/category/<int:category_id>/submit-answer', methods=['POST'])
@login_required
def submit_answer(category_id):
    try:
        user = get_current_user()
        data = request.get_json()
        
        if not data or 'question_id' not in data or 'option_id' not in data:
            logger.error("Invalid request data: missing question_id or option_id")
            return jsonify({'error': 'Invalid request'}), 400
        
        question = db.get(Question, data['question_id'])
        if not question or question.category_id != category_id:
            logger.error(f"Question {data['question_id']} not found or does not belong to category {category_id}")
            return jsonify({'error': 'Question not found'}), 404
        
        option = db.get(Option, data['option_id'])
        if not option or option.question_id != question.id:
            logger.error(f"Option {data['option_id']} not found or does not belong to question {question.id}")
            return jsonify({'error': 'Invalid option'}), 400
        
        # Record the attempt
        attempt = AttemptLog(
            user_id=user.id,
            question_id=question.id,
            option_id=option.id,
            is_correct=option.is_correct
        )
        db.add(attempt)
        
        # Update user's knowledge state
        user_category = db.query(UserCategory).filter_by(
            user_id=user.id,
            category_id=category_id
        ).first()
        
        if not user_category:
            user_category = UserCategory(
                user_id=user.id,
                category_id=category_id
            )
            db.add(user_category)
        
        # Update knowledge state using BKT
        logger.debug(f"Current knowledge state before update: {user_category.current_knowledge}")
        user_category.update_knowledge_state(option.is_correct)
        logger.debug(f"New knowledge state after update: {user_category.current_knowledge}")
        
        # Commit all changes
        db.commit()
        
        return jsonify({
            'correct': option.is_correct,
            'explanation': 'Correct!' if option.is_correct else 'Incorrect. Try again!',
            'knowledge_state': user_category.current_knowledge
        })
    except Exception as e:
        logger.error(f"Error in submit_answer: {str(e)}")
        db.rollback()  # Rollback any uncommitted changes
        return jsonify({'error': 'An error occurred while processing your answer'}), 500

@user_bp.route('/category/<int:category_id>/history')
@login_required
def get_learning_history(category_id):
    user = get_current_user()
    
    # Get the user's attempt history for this category
    attempts = db.query(AttemptLog).join(Question).filter(
        AttemptLog.user_id == user.id,
        Question.category_id == category_id
    ).order_by(AttemptLog.timestamp.desc()).all()
    
    history = [{
        'date': attempt.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'question': attempt.question.text,
        'result': 'Correct' if attempt.is_correct else 'Incorrect'
    } for attempt in attempts]
    
    return jsonify(history) 