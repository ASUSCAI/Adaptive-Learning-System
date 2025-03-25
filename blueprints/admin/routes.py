from flask import render_template, redirect, url_for, flash, request, session
from database.models import User, Category, UserCategory
from shared import db
from functools import wraps
from typing import Optional
from . import admin_bp

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
    categories = db.get_all(Category)
    
    # Calculate category counts
    category_counts = {}
    for category in categories:
        count = db.query(UserCategory).filter_by(category_id=category.id).count()
        category_counts[category.id] = count
    
    return render_template('admin/categories.html', 
                         categories=categories,
                         category_counts=category_counts)

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