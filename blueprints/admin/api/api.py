from flask import Blueprint, render_template, jsonify, request
from shared import db
from database.models import Category, Question, Option


admin_api = Blueprint("admin_api", __name__, url_prefix="/api")


@admin_api.route("/")
def index():
    return jsonify({"message": "Welcome to the admin api"})


@admin_api.route("/categories", methods=["POST"])
def create_category():
    data = request.get_json()

    # Ensure 'name' is in the payload
    if not data or 'name' not in data:
        return {"message": "Missing 'name' in request body"}, 400

    category_name = data['name']
    category = Category(name=category_name)
    
    try:
        db.add(category)
        return {"message": "Category created successfully"}, 201
    except Exception as e:
        return {"message": str(e)}, 500


@admin_api.route("/categories", methods=["GET"])
def get_categories():
    categories = db.get_all(Category)
    names = [category.name for category in categories]
    return jsonify({"categories": names}), 200


@admin_api.route("/categories/<int:id>", methods=["GET"])
def get_category(id):
    category = db.get(Category, id)
    return jsonify(category)


@admin_api.route("/questions", methods=["POST"])
def add_question():
    """
    Expects a JSON payload with:
    {
      "text": "Question text",
      "category_name": "Category name",
      "options": [
          {"text": "Option A", "is_correct": false},
          {"text": "Option B", "is_correct": true},
          ...
      ]
    }

    Creates the question (with the given category and options) in the database.
    """
    session = db.get_session()
    data = request.get_json()

    # 1. Extract question text and category name from the payload
    question_text = data.get("text")
    category_name = data.get("category_name")
    options_data = data.get("options", [])

    if not question_text or not category_name:
        return jsonify({"error": "Question text or category name is missing."}), 400

    # 2. Find the category by name
    category = session.query(Category).filter_by(name=category_name).first()
    if not category:
        return jsonify({"error": f"Category '{category_name}' not found."}), 400

    # 3. Create the Question object
    new_question = Question(text=question_text, category_id=category.id)

    # 4. Create and attach the Option objects
    for opt in options_data:
        opt_text = opt.get("text", "")
        is_correct = opt.get("is_correct", False)
        new_option = Option(text=opt_text, is_correct=is_correct)
        new_question.options.append(new_option)

    # 5. Persist to database
    session.add(new_question)
    session.commit()

    return jsonify({"message": "Question added successfully"}), 201
