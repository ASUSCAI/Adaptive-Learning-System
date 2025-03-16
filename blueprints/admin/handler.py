from flask import Blueprint, render_template
from blueprints.admin.api.api import admin_api

admin = Blueprint("admin", __name__, template_folder="templates")
admin.register_blueprint(admin_api)


@admin.route("/")
def index():
    return render_template("admin/index.html")


@admin.route("/section/<int:id>")
def section():
    pass
