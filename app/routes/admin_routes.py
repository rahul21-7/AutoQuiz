from flask import Blueprint, request, jsonify, session
from app.services.admin_service import AdminService

admin_bp = Blueprint("admin", __name__)

def check_admin_access():
    """Checks if current session has admin privileges (TC-06)."""
    role = session.get("role") or request.headers.get("X-User-Role")
    user_id = session.get("user_id") or request.headers.get("X-User-ID")
    return (role == "admin" or user_id == "admin"), user_id

@admin_bp.before_request
def require_admin():
    is_admin, _ = check_admin_access()
    if not is_admin:
        return jsonify({"error": "Unauthorized: Admin privileges required."}), 403

@admin_bp.route("/taxonomy", methods=["GET"])
def get_taxonomy():
    """Lists syllabus taxonomy nodes (UC-10, TC-74)."""
    items = AdminService.get_syllabus_taxonomy()
    return jsonify({"taxonomy": items}), 200

@admin_bp.route("/taxonomy", methods=["POST"])
def add_taxonomy():
    """Adds a new curriculum syllabus topic (UC-10, TC-74)."""
    data = request.get_json() or {}
    name = data.get("topic_name")
    desc = data.get("description", "")
    order = int(data.get("order_index", 0))

    if not name:
        return jsonify({"error": "topic_name is required."}), 400

    try:
        new_item = AdminService.add_taxonomy_topic(topic_name=name, description=desc, order_index=order)
        return jsonify({"status": "created", "item": new_item}), 201
    except Exception as ex:
        return jsonify({"error": str(ex)}), 400

@admin_bp.route("/taxonomy/<int:topic_id>", methods=["PUT"])
def update_taxonomy(topic_id: int):
    """Updates a syllabus taxonomy node (UC-10, TC-74)."""
    data = request.get_json() or {}
    name = data.get("topic_name", "")
    desc = data.get("description", "")
    order = int(data.get("order_index", 0))

    updated = AdminService.update_taxonomy_topic(topic_id, name, desc, order)
    if not updated:
        return jsonify({"error": "Topic not found."}), 404
    return jsonify({"status": "updated", "id": topic_id}), 200

@admin_bp.route("/taxonomy/<int:topic_id>", methods=["DELETE"])
def delete_taxonomy(topic_id: int):
    """Deletes a syllabus taxonomy node (UC-10, TC-74)."""
    deleted = AdminService.delete_taxonomy_topic(topic_id)
    if not deleted:
        return jsonify({"error": "Topic not found."}), 404
    return jsonify({"status": "deleted", "id": topic_id}), 200

@admin_bp.route("/wipe-vectors", methods=["POST"])
def wipe_vectors():
    """Wipes vector store collection for a document (UC-11, TC-75, TC-77)."""
    _, admin_id = check_admin_access()
    data = request.get_json() or {}
    target_user = data.get("user_id")
    doc_id = data.get("doc_id")

    if not target_user or not doc_id:
        return jsonify({"error": "user_id and doc_id are required."}), 400

    try:
        res = AdminService.wipe_document_vectors(admin_user_id=admin_id or "admin", target_user_id=target_user, doc_id=doc_id)
        return jsonify(res), 200
    except ValueError as ve:
        # TC-77: Negative - collection does not exist
        return jsonify({"error": str(ve)}), 404
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500

@admin_bp.route("/reset-student", methods=["POST"])
def reset_student():
    """Resets performance history and test logs for a student (UC-11, TC-76)."""
    _, admin_id = check_admin_access()
    data = request.get_json() or {}
    student_id = data.get("student_user_id")

    if not student_id:
        return jsonify({"error": "student_user_id is required."}), 400

    try:
        res = AdminService.reset_student_history(admin_user_id=admin_id or "admin", student_user_id=student_id)
        return jsonify(res), 200
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500

