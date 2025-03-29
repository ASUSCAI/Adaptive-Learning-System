from flask import render_template, redirect, url_for, flash, request, session, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from database.models import User, Category, UserCategory, Question, Option, AttemptLog, Progress, Section
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
    return g.db_session.query(User).get(session['user_id'])

# Authentication routes
@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = g.db_session.query(User).filter_by(email=email).first()
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
        
        if g.db_session.query(User).filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('user.register'))
        
        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password)
        )
        g.db_session.add(user)
        g.db_session.commit()
        
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
    
    # Get all categories
    all_categories = g.db_session.query(Category).all()
    logger.debug(f"Found {len(all_categories)} categories in database")
    
    # Get categories from user's sections
    section_categories = set()
    user_sections = user.sections
    logger.debug(f"User {user.id} belongs to {len(user_sections)} sections")
    
    for section in user_sections:
        for category in section.categories:
            section_categories.add(category)
            logger.debug(f"Adding category {category.name} from section {section.name}")
    
    # All categories the user has access to (direct assignments + section assignments)
    categories = list(set(all_categories).union(section_categories))
    
    # Get user's learning state for each category
    user_categories = {
        uc.category_id: uc for uc in g.db_session.query(UserCategory).filter_by(user_id=user.id).all()
    }
    logger.debug(f"Found {len(user_categories)} user categories for user {user.id}")
    
    # Get the user's sections
    sections = user.sections
    
    return render_template('user/dashboard.html',
                         user=user,
                         categories=categories,
                         user_categories=user_categories,
                         sections=sections)

@user_bp.route('/category/<uuid:category_uuid>')
@login_required
def category_detail(category_uuid):
    user = get_current_user()
    logger.debug(f"Accessing category detail for UUID: {category_uuid}")
    
    # Convert uuid parameter to string for database lookup
    category_uuid_str = str(category_uuid)
    
    # Get category with questions and options eagerly loaded
    category = g.db_session.query(Category).filter_by(uuid=category_uuid_str).options(
        joinedload(Category.questions).joinedload(Question.options)
    ).first()
    print(f"Category: {category}")
    
    if not category:
        logger.error(f"Category with UUID {category_uuid} not found")
        flash('Category not found.', 'error')
        return redirect(url_for('user.dashboard'))
    
    logger.debug(f"Found category: {category.name} (ID: {category.id}, UUID: {category.uuid})")
    
    user_category = g.db_session.query(UserCategory).filter_by(
        user_id=user.id,
        category_id=category.id
    ).first()
    
    if not user_category:
        logger.debug(f"Creating new UserCategory for user {user.id} and category {category.id}")
        user_category = UserCategory(
            user_id=user.id,
            category_id=category.id
        )
        g.db_session.add(user_category)
        g.db_session.commit()  # Commit the new user_category
    
    # Get progress data
    progress = g.db_session.query(Progress).filter_by(
        user_id=user.id,
        category_id=category.id
    ).first()
    
    logger.debug(f"Rendering category detail template with category: {category.name}, user_category: {user_category.current_knowledge if user_category else 'None'}")
    
    return render_template('user/category_detail.html',
                         user=user,
                         category=category,
                         user_category=user_category,
                         progress=progress)

@user_bp.route('/category/<uuid:category_uuid>/next-question')
@login_required
def get_next_question(category_uuid):
    logger.debug(f"Accessing next question for category {category_uuid}")
    user = get_current_user()
    logger.debug(f"Current user: {user.id}")
    
    # Convert uuid parameter to string for database lookup
    category_uuid_str = str(category_uuid)
    
    category = g.db_session.query(Category).filter_by(uuid=category_uuid_str).first()
    if not category:
        logger.error(f"Category {category_uuid} not found")
        return jsonify({'error': 'Category not found'}), 404
    
    logger.debug(f"Found category: {category.name} (ID: {category.id}, UUID: {category.uuid})")
    
    # Get a random question from the category with options eagerly loaded
    question = g.db_session.query(Question).filter_by(category_id=category.id).options(
        joinedload(Question.options)
    ).order_by(func.random()).first()
    
    if not question:
        logger.error(f"No questions found for category {category_uuid}")
        return jsonify({'error': 'No questions available'}), 404
    
    logger.debug(f"Found question {question.uuid} for category {category_uuid}")
    logger.debug(f"Question text: {question.text}")
    logger.debug(f"Number of options: {len(question.options)}")
    
    # Format the question for the frontend
    options = [{'uuid': opt.uuid, 'text': opt.text} for opt in question.options]
    response_data = {
        'question_uuid': question.uuid,
        'text': question.text,
        'options': options
    }
    logger.debug(f"Sending response: {response_data}")
    
    return jsonify(response_data)

@user_bp.route('/category/<uuid:category_uuid>/submit-answer', methods=['POST'])
@login_required
def submit_answer(category_uuid):
    try:
        user = get_current_user()
        data = request.get_json()
        
        if not data or 'question_uuid' not in data or 'option_uuid' not in data:
            logger.error("Invalid request data: missing question_uuid or option_uuid")
            return jsonify({'error': 'Invalid request'}), 400
        
        # Convert uuid parameter to string for database lookup
        category_uuid_str = str(category_uuid)
        
        category = g.db_session.query(Category).filter_by(uuid=category_uuid_str).first()
        if not category:
            logger.error(f"Category {category_uuid} not found")
            return jsonify({'error': 'Category not found'}), 404
        
        question = g.db_session.query(Question).filter_by(uuid=data['question_uuid']).first()
        if not question or question.category_id != category.id:
            logger.error(f"Question {data['question_uuid']} not found or does not belong to category {category_uuid}")
            return jsonify({'error': 'Question not found'}), 404
        
        option = g.db_session.query(Option).filter_by(uuid=data['option_uuid']).first()
        if not option or option.question_id != question.id:
            logger.error(f"Option {data['option_uuid']} not found or does not belong to question {question.uuid}")
            return jsonify({'error': 'Invalid option'}), 400
        
        # Record the attempt
        attempt = AttemptLog(
            user_id=user.id,
            question_id=question.id,
            option_id=option.id,
            is_correct=option.is_correct
        )
        g.db_session.add(attempt)
        
        # Update user's knowledge state
        user_category = g.db_session.query(UserCategory).filter_by(
            user_id=user.id,
            category_id=category.id
        ).first()
        
        if not user_category:
            user_category = UserCategory(
                user_id=user.id,
                category_id=category.id
            )
            g.db_session.add(user_category)
        
        # Update knowledge state using BKT
        logger.debug(f"Current knowledge state before update: {user_category.current_knowledge}")
        user_category.update_knowledge_state(option.is_correct)
        logger.debug(f"New knowledge state after update: {user_category.current_knowledge}")
        
        # Commit all changes
        g.db_session.commit()
        
        return jsonify({
            'success': True,
            'is_correct': option.is_correct,
            'knowledge_state': user_category.current_knowledge
        })
            
    except Exception as e:
        logger.error(f"Error processing answer: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@user_bp.route('/category/<uuid:category_uuid>/history')
@login_required
def get_learning_history(category_uuid):
    user = get_current_user()
    
    # Convert uuid parameter to string for database lookup
    category_uuid_str = str(category_uuid)
    
    # Get the category first
    category = g.db_session.query(Category).filter_by(uuid=category_uuid_str).first()
    if not category:
        return jsonify({'error': 'Category not found'}), 404
    
    # Get the user's attempt history for this category
    attempts = g.db_session.query(AttemptLog).join(Question).filter(
        AttemptLog.user_id == user.id,
        Question.category_id == category.id
    ).order_by(AttemptLog.timestamp.desc()).all()
    
    history = [{
        'date': attempt.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'question': attempt.question.text,
        'result': 'Correct' if attempt.is_correct else 'Incorrect'
    } for attempt in attempts]
    
    return jsonify(history)

@user_bp.route('/section/<uuid:section_uuid>/categories')
@login_required
def section_categories(section_uuid):
    user = get_current_user()
    
    # Get the section
    section = g.db_session.query(Section).filter_by(uuid=str(section_uuid)).first()
    if not section or section not in user.sections:
        flash('Section not found or access denied.', 'error')
        return redirect(url_for('user.dashboard'))
    
    # Get user's learning state for each category
    user_categories = {
        uc.category_id: uc for uc in g.db_session.query(UserCategory).filter_by(user_id=user.id).all()
    }
    
    return render_template('user/section_categories.html',
                         user=user,
                         section=section,
                         user_categories=user_categories) 