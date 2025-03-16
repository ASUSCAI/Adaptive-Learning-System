from flask import Flask, render_template
from shared import db
from blueprints.admin.handler import admin

app = Flask(__name__, template_folder="templates")


app.register_blueprint(admin, url_prefix="/admin")


@app.route("/")
def index():
    return render_template("base.html")


@app.route("/categories")
def categories():
    categories = db.get_all("Category")
    return render_template("categories.html")


@app.route("/addQuestion")
def addQestion():
    pass


if __name__ == "__main__":
    app.run(debug=True)
