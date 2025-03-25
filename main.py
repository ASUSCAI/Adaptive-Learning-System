from flask import Flask, render_template
from shared import db
from blueprints.admin import admin_bp
from blueprints.user import user_bp
from database.models import Category

app = Flask(__name__, template_folder="templates")
app.secret_key = 'dev'  # Change this to a secure secret key in production

app.register_blueprint(user_bp, url_prefix="/")
app.register_blueprint(admin_bp, url_prefix="/admin")

@app.route("/categories")
def categories():
    categories = db.get_all(Category)
    return render_template("categories.html", categories=categories)

@app.route("/addQuestion")
def addQestion():
    pass

if __name__ == "__main__":
    app.run(debug=True)
