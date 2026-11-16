from flask import Blueprint, request, jsonify, session
from app.services.analytics_service import AnalyticsService
from app.services.spaced_repetition import SpacedRepetitionService

analytics_bp = Blueprint("analytics", __name__)

def get_current_user_id() -> str:
    return session.get("user_id") or request.headers.get("X-User-ID")

@analytics_bp.route("/dashboard", methods=["GET"])
def get_dashboard_analytics():
    """
    Renders performance metrics, first-try vs looped breakdown, and weakness heatmap in under 1s
    (UC-3, REQ_16, REQ_17, BR-4, PERF-3, TC-04, TC-63 to TC-67).
    """
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required to view analytics."}), 401

    data = AnalyticsService.get_student_dashboard(user_id=user_id)
    return jsonify(data), 200

@analytics_bp.route("/trigger-decay-audit", methods=["POST"])
def trigger_decay_audit():
    """Executes the automated memory decay audit across all mastered topics (REQ_14, TC-55 to TC-58)."""
    # Background audit can be invoked by system scheduler or admin
    result = SpacedRepetitionService.audit_mastered_topics()
    return jsonify({"status": "success", "result": result}), 200

