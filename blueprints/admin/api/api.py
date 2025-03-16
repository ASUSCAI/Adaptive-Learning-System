from flask import Blueprint, render_template, jsonify, request
from shared import db
from database.models import Category


admin_api = Blueprint("admin_api", __name__, url_prefix="/api")


@admin_api.route("/")
def index():
    return jsonify({"message": "Welcome to the admin api"})


@admin_api.route("/categories/<string:name>", methods=["POST"])
def create_category(name):
    category = Category(name=name)
    db.add(category)
    return {"message": "Category created successfully"}


@admin_api.route("/categories", methods=["GET"])
def get_categories():
    categories = db.get_all(Category)
    return jsonify(categories)


@admin_api.route("/categories/<int:id>", methods=["GET"])
def get_category(id):
    category = db.get(Category, id)
    return jsonify(category)
