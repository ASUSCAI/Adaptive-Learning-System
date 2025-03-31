from flask import render_template, redirect, url_for, flash, request, session, jsonify, Blueprint, g
from werkzeug.security import generate_password_hash
from database.models import User, Category, UserCategory, Question, Option, Section
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

@admin_bp.route('/categories/<uuid:category_uuid>/questions/add', methods=['GET', 'POST'])
@admin_required
def add_question(category_uuid):
    category = db.query(Category).filter_by(uuid=category_uuid).first()
    if not category:
        flash('Category not found.', 'error')
        return redirect(url_for('admin.manage_categories'))
    
    if request.method == 'POST':
        text = request.form.get('text')
        options = request.form.getlist('options[]')
        correct_option = request.form.get('correct_option')
        
        if not text or not options or not correct_option:
            flash('All fields are required.', 'error')
            return redirect(url_for('admin.add_question', category_uuid=category_uuid))
        
        question = Question(text=text, category_id=category.id, uuid=str(uuid.uuid4()))
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

@admin_bp.route('/questions/<uuid:question_uuid>/edit', methods=['GET', 'POST'])
@admin_required
def edit_question(question_uuid):
    # Get question with options eagerly loaded
    question = db.query(Question).filter_by(uuid=question_uuid).options(
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
            return redirect(url_for('admin.edit_question', question_uuid=question_uuid))
        
        question.text = text
        
        # Delete existing options
        db.query(Option).filter_by(question_id=question.id).delete()
        
        # Add new options
        for i, option_text in enumerate(options):
            option = Option(
                text=option_text,
                is_correct=(str(i) == correct_option),
                question_id=question.id,
                uuid=str(uuid.uuid4())
            )
            db.add(option)
        
        flash('Question updated successfully!', 'success')
        return redirect(url_for('admin.manage_categories'))
    
    return render_template('admin/question_form.html', question=question)

@admin_bp.route('/questions/<uuid:question_uuid>', methods=['DELETE'])
@admin_required
def delete_question(question_uuid):
    question = db.query(Question).filter_by(uuid=question_uuid).first()
    if not question:
        return jsonify({'success': False, 'error': 'Question not found'}), 404
    
    # Delete all options first
    db.query(Option).filter_by(question_id=question.id).delete()
    # Then delete the question
    db.query(Question).filter_by(uuid=question_uuid).delete()
    
    return jsonify({'success': True})

@admin_bp.route('/api/categories/<uuid:category_uuid>/questions')
@admin_required
def get_category_questions(category_uuid):
    """API endpoint to fetch questions for a category"""
    category = db.query(Category).filter_by(uuid=category_uuid).first()
    if not category:
        return jsonify({'error': 'Category not found'}), 404
        
    questions = db.query(Question).filter_by(category_id=category.id).options(
        joinedload(Question.options)
    ).all()
    
    return jsonify([{
        'uuid': q.uuid,
        'text': q.text,
        'options': [{
            'uuid': opt.uuid,
            'text': opt.text,
            'is_correct': opt.is_correct
        } for opt in q.options]
    } for q in questions])

@admin_bp.route('/categories/<uuid:category_uuid>/questions')
@admin_required
def view_category_questions(category_uuid):
    """View questions for a specific category"""
    category = db.query(Category).filter_by(uuid=category_uuid).first()
    if not category:
        flash('Category not found.', 'error')
        return redirect(url_for('admin.manage_categories'))
    
    # Get questions with options eagerly loaded
    questions = db.query(Question).filter_by(category_id=category.id).options(
        joinedload(Question.options)
    ).all()
    
    return render_template('admin/category_questions.html',
                         category=category,
                         questions=questions)

# Section Management Routes
@admin_bp.route('/sections')
@admin_required
def manage_sections():
    # Get a new session
    session = db.get_session()
    
    try:
        sections = session.query(Section).all()
        return render_template('admin/sections/index.html', sections=sections)
    finally:
        session.close()

@admin_bp.route('/sections/new', methods=['GET', 'POST'])
@admin_required
def new_section():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        if not name:
            flash('Section name is required.', 'error')
            return redirect(url_for('admin.new_section'))
        
        # Get a new session
        session = db.get_session()
        
        try:
            # Check if section with same name already exists
            existing = session.query(Section).filter_by(name=name).first()
            if existing:
                flash('A section with this name already exists.', 'error')
                return redirect(url_for('admin.new_section'))
            
            section = Section(
                name=name,
                description=description,
                uuid=str(uuid.uuid4())
            )
            session.add(section)
            session.commit()
            flash('Section created successfully!', 'success')
            return redirect(url_for('admin.manage_sections'))
        except Exception as e:
            session.rollback()
            flash(f'Error creating section: {str(e)}', 'error')
            return redirect(url_for('admin.new_section'))
        finally:
            session.close()
    
    return render_template('admin/sections/new.html')

@admin_bp.route('/sections/<uuid:section_uuid>')
@admin_required
def section_detail(section_uuid):
    section_uuid_str = str(section_uuid)
    # Get a new session
    session = db.get_session()
    
    try:
        # Eagerly load both users and categories relationships
        section = session.query(Section).options(
            joinedload(Section.users),
            joinedload(Section.categories)
        ).filter_by(uuid=section_uuid_str).first()
        
        if not section:
            flash('Section not found.', 'error')
            return redirect(url_for('admin.manage_sections'))
        
        users = session.query(User).all()
        categories = session.query(Category).all()
        
        return render_template('admin/sections/detail.html',
                            section=section,
                            all_users=users,
                            all_categories=categories)
    finally:
        session.close()

@admin_bp.route('/sections/<uuid:section_uuid>/users/add', methods=['POST'])
@admin_required
def add_user_to_section(section_uuid):
    section_uuid_str = str(section_uuid)
    # Get a new session
    session = db.get_session()
    
    try:
        # Eagerly load users relationship
        section = session.query(Section).options(joinedload(Section.users)).filter_by(uuid=section_uuid_str).first()
        
        if not section:
            flash('Section not found.', 'error')
            return redirect(url_for('admin.manage_sections'))
        
        user_id = request.form.get('user_id')
        if not user_id:
            flash('User is required.', 'error')
            return redirect(url_for('admin.section_detail', section_uuid=section_uuid))
        
        user = session.query(User).get(user_id)
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('admin.section_detail', section_uuid=section_uuid))
        
        if user in section.users:
            flash('User is already in this section.', 'warning')
            return redirect(url_for('admin.section_detail', section_uuid=section_uuid))
        
        section.users.append(user)
        session.commit()
        flash('User added to section successfully!', 'success')
        return redirect(url_for('admin.section_detail', section_uuid=section_uuid))
    except Exception as e:
        session.rollback()
        flash(f'Error adding user to section: {str(e)}', 'error')
        return redirect(url_for('admin.section_detail', section_uuid=section_uuid))
    finally:
        session.close()

@admin_bp.route('/sections/<uuid:section_uuid>/users/<int:user_id>/remove')
@admin_required
def remove_user_from_section(section_uuid, user_id):
    section_uuid_str = str(section_uuid)
    # Get a new session
    session = db.get_session()
    
    try:
        # Eagerly load users relationship
        section = session.query(Section).options(joinedload(Section.users)).filter_by(uuid=section_uuid_str).first()
        
        if not section:
            flash('Section not found.', 'error')
            return redirect(url_for('admin.manage_sections'))
        
        user = session.query(User).get(user_id)
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('admin.section_detail', section_uuid=section_uuid))
        
        if user not in section.users:
            flash('User is not in this section.', 'warning')
            return redirect(url_for('admin.section_detail', section_uuid=section_uuid))
        
        section.users.remove(user)
        session.commit()
        flash('User removed from section successfully!', 'success')
        return redirect(url_for('admin.section_detail', section_uuid=section_uuid))
    except Exception as e:
        session.rollback()
        flash(f'Error removing user from section: {str(e)}', 'error')
        return redirect(url_for('admin.section_detail', section_uuid=section_uuid))
    finally:
        session.close()

@admin_bp.route('/sections/<uuid:section_uuid>/categories/add', methods=['POST'])
@admin_required
def add_category_to_section(section_uuid):
    section_uuid_str = str(section_uuid)
    # Get a new session
    session = db.get_session()
    
    try:
        # Use joinedload to eagerly load the categories relationship
        section = session.query(Section).options(
            joinedload(Section.categories),
            joinedload(Section.users)
        ).filter_by(uuid=section_uuid_str).first()
        
        if not section:
            flash('Section not found.', 'error')
            return redirect(url_for('admin.manage_sections'))
        
        category_id = request.form.get('category_id')
        if not category_id:
            flash('Category is required.', 'error')
            return redirect(url_for('admin.section_detail', section_uuid=section_uuid))
        
        category = session.query(Category).get(category_id)
        if not category:
            flash('Category not found.', 'error')
            return redirect(url_for('admin.section_detail', section_uuid=section_uuid))
        
        # Check if category is already in this section (now safe because categories is eagerly loaded)
        if category in section.categories:
            flash('Category is already in this section.', 'warning')
            return redirect(url_for('admin.section_detail', section_uuid=section_uuid))
        
        section.categories.append(category)
        
        # Auto-assign this category to all users in the section
        for user in section.users:
            # Check if user already has this category
            existing = session.query(UserCategory).filter_by(
                user_id=user.id,
                category_id=category.id
            ).first()
            
            if not existing:
                user_category = UserCategory(
                    user_id=user.id,
                    category_id=category.id
                )
                session.add(user_category)
        
        session.commit()
        flash('Category added to section successfully!', 'success')
        return redirect(url_for('admin.section_detail', section_uuid=section_uuid))
    except Exception as e:
        session.rollback()
        flash(f'Error adding category to section: {str(e)}', 'error')
        return redirect(url_for('admin.section_detail', section_uuid=section_uuid))
    finally:
        session.close()

@admin_bp.route('/sections/<uuid:section_uuid>/categories/<int:category_id>/remove')
@admin_required
def remove_category_from_section(section_uuid, category_id):
    section_uuid_str = str(section_uuid)
    # Get a new session
    session = db.get_session()
    
    try:
        # Use joinedload to eagerly load the categories relationship
        section = session.query(Section).options(joinedload(Section.categories)).filter_by(uuid=section_uuid_str).first()
        
        if not section:
            flash('Section not found.', 'error')
            return redirect(url_for('admin.manage_sections'))
        
        category = session.query(Category).get(category_id)
        if not category:
            flash('Category not found.', 'error')
            return redirect(url_for('admin.section_detail', section_uuid=section_uuid))
        
        # Safe to check relationship now that categories is eagerly loaded
        if category not in section.categories:
            flash('Category is not in this section.', 'warning')
            return redirect(url_for('admin.section_detail', section_uuid=section_uuid))
        
        section.categories.remove(category)
        session.commit()
        flash('Category removed from section successfully!', 'success')
        return redirect(url_for('admin.section_detail', section_uuid=section_uuid))
    except Exception as e:
        session.rollback()
        flash(f'Error removing category from section: {str(e)}', 'error')
        return redirect(url_for('admin.section_detail', section_uuid=section_uuid))
    finally:
        session.close()

@admin_bp.route('/users/<int:user_id>/categories/<int:category_id>/reset', methods=['POST'])
@admin_required
def reset_user_progress(user_id, category_id):
    """Reset a user's progress for a specific learning objective."""
    # Get a new session to ensure consistency
    session = db.get_session()
    
    try:
        # Get the user_category entry within this session
        user_category = session.query(UserCategory).filter_by(
            user_id=user_id,
            category_id=category_id
        ).first()
        
        if user_category:
            # Reset knowledge to zero (instead of p_init)
            user_category.current_knowledge = 0.0
            # Reset consecutive correct counter
            user_category.consecutive_correct = 0
            # For IBKT, also reset the learning metrics and history
            user_category.performance_history = []
            user_category.total_attempts = 0
            user_category.correct_attempts = 0
            user_category.consistency_score = 0.0
            user_category.improvement_rate = 0.0
            user_category.error_recovery = 0.0
            user_category.transit_adjustment = 0.0
            user_category.slip_adjustment = 0.0
            user_category.guess_adjustment = 0.0
            
            # Commit within this session
            session.commit()
            flash('Learning objective progress reset successfully!', 'success')
        else:
            flash('Learning objective assignment not found.', 'error')
            
        return redirect(url_for('admin.manage_user_categories', user_id=user_id))
    except Exception as e:
        session.rollback()
        flash(f'Error resetting progress: {str(e)}', 'error')
        return redirect(url_for('admin.manage_user_categories', user_id=user_id))
    finally:
        session.close()

@admin_bp.route('/users/<int:user_id>/reset-all-progress', methods=['POST'])
@admin_required
def reset_all_user_progress(user_id):
    """Reset all learning objective progress for a user."""
    # Get a new session to ensure consistency
    session = db.get_session()
    
    try:
        user = session.query(User).get(user_id)
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('admin.manage_users'))
        
        # Get all UserCategory entries for this user within this session
        user_categories = session.query(UserCategory).filter_by(user_id=user_id).all()
        
        if user_categories:
            # Reset progress for each category
            for user_category in user_categories:
                # Reset knowledge to zero (instead of p_init)
                user_category.current_knowledge = 0.0
                # Reset consecutive correct counter
                user_category.consecutive_correct = 0
                # For IBKT, also reset the learning metrics and history
                user_category.performance_history = []
                user_category.total_attempts = 0
                user_category.correct_attempts = 0
                user_category.consistency_score = 0.0
                user_category.improvement_rate = 0.0
                user_category.error_recovery = 0.0
                user_category.transit_adjustment = 0.0
                user_category.slip_adjustment = 0.0
                user_category.guess_adjustment = 0.0
            
            # Commit all changes within this session
            session.commit()
            flash(f'All learning objective progress for {user.name} has been reset successfully!', 'success')
        else:
            flash('No learning objectives found for this user.', 'warning')
        
        return redirect(url_for('admin.manage_user_categories', user_id=user_id))
    except Exception as e:
        session.rollback()
        flash(f'Error resetting progress: {str(e)}', 'error')
        return redirect(url_for('admin.manage_user_categories', user_id=user_id))
    finally:
        session.close() 