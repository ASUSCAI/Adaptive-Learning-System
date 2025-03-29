from flask import Blueprint, render_template, jsonify, request
from shared import db
from database.models import Category, Question, Option
from uuid import uuid4

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
    category = Category(name=category_name, uuid = str(uuid4()))
    
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
      "category_uuid": "Category UUID",
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

    # 1. Extract question text and category UUID from the payload
    question_text = data.get("text")
    category_uuid = data.get("category_uuid")
    options_data = data.get("options", [])

    if not question_text or not category_uuid:
        return jsonify({"error": "Question text or category UUID is missing."}), 400

    # 2. Find the category by UUID
    category = session.query(Category).filter_by(uuid=category_uuid).first()
    if not category:
        return jsonify({"error": f"Category with UUID '{category_uuid}' not found."}), 400

    # 3. Create the Question object
    new_question = Question(text=question_text, category_id=category.id, uuid=str(uuid4()))

    # 4. Create and attach the Option objects
    for opt in options_data:
        opt_text = opt.get("text", "")
        is_correct = opt.get("is_correct", False)
        new_option = Option(text=opt_text, is_correct=is_correct, uuid=str(uuid4()))
        new_question.options.append(new_option)

    # 5. Persist to database
    session.add(new_question)
    session.commit()

    return jsonify({
        "message": "Question added successfully",
        "question": {
            "uuid": new_question.uuid,
            "text": new_question.text,
            "options": [{"uuid": opt.uuid, "text": opt.text, "is_correct": opt.is_correct} for opt in new_question.options]
        }
    }), 201
