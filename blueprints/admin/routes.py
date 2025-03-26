from flask import render_template, redirect, url_for, flash, request, session, jsonify
from database.models import User, Category, UserCategory, Question, Option
from shared import db
from functools import wraps
from typing import Optional
from sqlalchemy.orm import joinedload
from . import admin_bp
import uuid

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('user.login'))
        
        user = db.get(User, session['user_id'])
        if not user or not user.is_admin:
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('user.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@admin_required
def admin_dashboard():
    users = db.get_all(User)
    categories = db.get_all(Category)
    
    # Calculate category counts
    category_counts = {}
    for category in categories:
        count = db.query(UserCategory).filter_by(category_id=category.id).count()
        category_counts[category.id] = count
    
    return render_template('admin/dashboard.html',
                         users=users,
                         categories=categories,
                         category_counts=category_counts)

@admin_bp.route('/categories')
@admin_required
def manage_categories():
    """Manage categories and their questions"""
    # Get categories with questions eagerly loaded
    categories = db.query(Category).options(
        joinedload(Category.questions)
    ).all()
    return render_template('admin/categories.html', categories=categories)

@admin_bp.route('/categories/add', methods=['GET', 'POST'])
@admin_required
def add_category():
    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            flash('Category name is required.', 'error')
            return redirect(url_for('admin.add_category'))
        
        category = Category(name=name)
        db.add(category)
        flash('Category added successfully!', 'success')
        return redirect(url_for('admin.manage_categories'))
    
    return render_template('admin/category_form.html')

@admin_bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_category(category_id):
    category = db.get(Category, category_id)
    if not category:
        flash('Category not found.', 'error')
        return redirect(url_for('admin.manage_categories'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            flash('Category name is required.', 'error')
            return redirect(url_for('admin.edit_category', category_id=category_id))
        
        category.name = name
        db.add(category)
        flash('Category updated successfully!', 'success')
        return redirect(url_for('admin.manage_categories'))
    
    return render_template('admin/category_form.html', category=category)

@admin_bp.route('/users')
@admin_required
def manage_users():
    users = db.get_all(User)
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:user_id>/categories')
@admin_required
def manage_user_categories(user_id):
    user = db.get(User, user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.manage_users'))
    
    categories = db.get_all(Category)
    user_categories = {
        uc.category_id: uc for uc in db.query(UserCategory).filter_by(user_id=user_id).all()
    }
    
    return render_template('admin/user_categories.html',
                         user=user,
                         categories=categories,
                         user_categories=user_categories)

@admin_bp.route('/users/<int:user_id>/categories/assign', methods=['POST'])
@admin_required
def assign_category(user_id):
    user = db.get(User, user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.manage_users'))
    
    category_id = request.form.get('category_id')
    if not category_id:
        flash('Category is required.', 'error')
        return redirect(url_for('admin.manage_user_categories', user_id=user_id))
    
    # Check if category is already assigned
    existing = db.query(UserCategory).filter_by(
        user_id=user_id,
        category_id=category_id
    ).first()
    
    if existing:
        flash('Category is already assigned to this user.', 'warning')
        return redirect(url_for('admin.manage_user_categories', user_id=user_id))
    
    user_category = UserCategory(
        user_id=user_id,
        category_id=category_id
    )
    db.add(user_category)
    flash('Category assigned successfully!', 'success')
    
    return redirect(url_for('admin.manage_user_categories', user_id=user_id))

@admin_bp.route('/users/<int:user_id>/categories/<int:category_id>/remove', methods=['POST'])
@admin_required
def remove_category(user_id, category_id):
    user_category = db.query(UserCategory).filter_by(
        user_id=user_id,
        category_id=category_id
    ).first()
    
    if user_category:
        db.query(UserCategory).filter_by(
            user_id=user_id,
            category_id=category_id
        ).delete()
        flash('Category removed successfully!', 'success')
    else:
        flash('Category assignment not found.', 'error')
    
    return redirect(url_for('admin.manage_user_categories', user_id=user_id))

@admin_bp.route('/categories/<int:category_id>/questions/add', methods=['GET', 'POST'])
@admin_required
def add_question(category_id):
    category = db.get(Category, category_id)
    if not category:
        flash('Category not found.', 'error')
        return redirect(url_for('admin.manage_categories'))
    
    if request.method == 'POST':
        text = request.form.get('text')
        options = request.form.getlist('options[]')
        correct_option = request.form.get('correct_option')
        
        if not text or not options or not correct_option:
            flash('All fields are required.', 'error')
            return redirect(url_for('admin.add_question', category_id=category_id))
        
        question = Question(text=text, category_id=category_id, uuid=str(uuid.uuid4()))
        db.add(question)
        
        for i, option_text in enumerate(options):
            option = Option(
                text=option_text,
                is_correct=(str(i) == correct_option),
                question_id=question.id,
                uuid=str(uuid.uuid4())
            )
            db.add(option)
        
        flash('Question added successfully!', 'success')
        return redirect(url_for('admin.manage_categories'))
    
    return render_template('admin/question_form.html', category=category)

@admin_bp.route('/questions/<int:question_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_question(question_id):
    # Get question with options eagerly loaded
    question = db.query(Question).filter_by(id=question_id).options(
        joinedload(Question.options)
    ).first()
    
    if not question:
        flash('Question not found.', 'error')
        return redirect(url_for('admin.manage_categories'))
    
    if request.method == 'POST':
        text = request.form.get('text')
        options = request.form.getlist('options[]')
        correct_option = request.form.get('correct_option')
        
        if not text or not options or not correct_option:
            flash('All fields are required.', 'error')
            return redirect(url_for('admin.edit_question', question_id=question_id))
        
        question.text = text
        
        # Delete existing options
        db.query(Option).filter_by(question_id=question_id).delete()
        
        # Add new options
        for i, option_text in enumerate(options):
            option = Option(
                text=option_text,
                is_correct=(str(i) == correct_option),
                question_id=question_id
            )
            db.add(option)
        
        flash('Question updated successfully!', 'success')
        return redirect(url_for('admin.manage_categories'))
    
    return render_template('admin/question_form.html', question=question)

@admin_bp.route('/questions/<int:question_id>', methods=['DELETE'])
@admin_required
def delete_question(question_id):
    question = db.get(Question, question_id)
    if not question:
        return jsonify({'success': False, 'error': 'Question not found'}), 404
    
    # Delete all options first
    db.query(Option).filter_by(question_id=question_id).delete()
    # Then delete the question
    db.query(Question).filter_by(id=question_id).delete()
    
    return jsonify({'success': True})

@admin_bp.route('/api/categories/<int:category_id>/questions')
@admin_required
def get_category_questions(category_id):
    """API endpoint to fetch questions for a category"""
    questions = db.query(Question).filter_by(category_id=category_id).options(
        joinedload(Question.options)
    ).all()
    
    return jsonify([{
        'id': q.id,
        'text': q.text,
        'options': [{
            'id': opt.id,
            'text': opt.text,
            'is_correct': opt.is_correct
        } for opt in q.options]
    } for q in questions])

@admin_bp.route('/categories/<int:category_id>/questions')
@admin_required
def view_category_questions(category_id):
    """View questions for a specific category"""
    category = db.get(Category, category_id)
    if not category:
        flash('Category not found.', 'error')
        return redirect(url_for('admin.manage_categories'))
    
    # Get questions with options eagerly loaded
    questions = db.query(Question).filter_by(category_id=category_id).options(
        joinedload(Question.options)
    ).all()
    
    return render_template('admin/category_questions.html',
                         category=category,
                         questions=questions) 