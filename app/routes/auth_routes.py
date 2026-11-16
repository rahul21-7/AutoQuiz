import time
from flask import Blueprint, request, jsonify, session
from app.database import get_connection
from app.security import hash_password, verify_password

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    """Positive: Register Student A and Student B with salted PBKDF2/Bcrypt hashes (SRS 5.3, TC-01)."""
    data = request.get_json() or {}
    user_id = data.get("user_id", "").strip()
    name = data.get("name", "").strip() or user_id
    password = data.get("password", "")
    role = data.get("role", "student").strip()

    if not user_id or not password:
        return jsonify({"error": "User ID and password are required."}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": f"User ID '{user_id}' already registered."}), 409

    pwd_hash, salt = hash_password(password)
    now = time.time()
    cursor.execute(
        "INSERT INTO users (user_id, name, password_hash, salt, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, name, pwd_hash, salt, role, now)
    )
    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": f"User '{user_id}' registered successfully.",
        "user_id": user_id,
        "role": role
    }), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Positive & Negative: Authenticates user credentials.
    Rejects wrong passwords and unknown users with generic error message (SRS 5.3, TC-02, TC-03).
    """
    data = request.get_json() or {}
    user_id = data.get("user_id", "").strip()
    password = data.get("password", "")

    if not user_id or not password:
        return jsonify({"error": "Invalid username or password"}), 401

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, name, password_hash, salt, role FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    # Generic error message to prevent enumeration (TC-03)
    if not user or not verify_password(password, user["password_hash"], user["salt"]):
        return jsonify({"error": "Invalid username or password"}), 401

    session["user_id"] = user["user_id"]
    session["role"] = user["role"]
    session["name"] = user["name"]

    return jsonify({
        "status": "success",
        "message": "Login successful.",
        "user": {
            "user_id": user["user_id"],
            "name": user["name"],
            "role": user["role"]
        }
    }), 200

@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "success", "message": "Logged out successfully."}), 200

@auth_bp.route("/me", methods=["GET"])
def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"authenticated": False}), 401
    return jsonify({
        "authenticated": True,
        "user_id": user_id,
        "name": session.get("name"),
        "role": session.get("role")
    }), 200

