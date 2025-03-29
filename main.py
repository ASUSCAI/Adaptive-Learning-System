from flask import Flask, render_template, redirect, url_for, session, g
from shared import db
from blueprints.admin import admin_bp
from blueprints.user import user_bp
from database.models import Category, User

app = Flask(__name__, template_folder="templates")
app.secret_key = 'dev'  # Change this to a secure secret key in production

app.register_blueprint(user_bp)
app.register_blueprint(admin_bp, url_prefix="/admin")

@app.before_request
def before_request():
    g.db_session = db.get_session()

@app.after_request
def after_request(response):
    if hasattr(g, 'db_session'):
        g.db_session.close()
    return response

@app.route("/")
def index():
    if 'user_id' in session:
        try:
            user = g.db_session.query(User).get(session['user_id'])
            if user and user.is_admin:
                return redirect(url_for('admin.manage_users'))
            return redirect(url_for('user.dashboard'))
        except Exception as e:
            print(f"Error in index route: {e}")
            return redirect(url_for('user.login'))
    return redirect(url_for('user.login'))

@app.route("/category/<uuid:category_uuid>")
def redirect_category(category_uuid):
    return redirect(url_for('user.category_detail', category_uuid=category_uuid))

@app.route("/categories")
def categories():
    try:
        categories = g.db_session.query(Category).all()
        return render_template("categories.html", categories=categories)
    except Exception as e:
        print(f"Error in categories route: {e}")
        return redirect(url_for('user.login'))

@app.route("/addQuestion")
def addQestion():
    pass

if __name__ == "__main__":
    app.run(debug=True)
