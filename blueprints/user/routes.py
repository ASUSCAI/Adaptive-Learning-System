from flask import render_template, redirect, url_for, flash, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.models import User, Category, UserCategory
from shared import db
from functools import wraps
from typing import Optional
from . import user_bp

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
    category = db.get(Category, category_id)
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