import json
import time
import logging
from typing import Dict, Any, List
from app.database import get_connection

logger = logging.getLogger("AUTOQUIZ.ANALYTICS")

class AnalyticsService:
    """
    Weakness Analytics Dashboard & Heatmap Engine (UC-3, REQ_16, REQ_17, BR-4, TC-63 to TC-67).
    Calculates overall exam readiness, separates first-attempt vs remediated success (BR-4),
    computes weakness heatmaps and topic failure frequencies, and handles new user empty states (TC-66).
    """

    @staticmethod
    def get_student_dashboard(user_id: str) -> Dict[str, Any]:
        """
        Retrieves all analytics metrics for a student in under 1 second (PERF-3, TC-63).
        """
        start_time = time.time()
        conn = get_connection()
        cursor = conn.cursor()

        # 1. Check if user has any completed attempts (Exception 3.0.E.1 / TC-66)
        cursor.execute("SELECT COUNT(*) as cnt FROM attempts WHERE user_id = ?", (user_id,))
        total_attempts = cursor.fetchone()["cnt"]

        if total_attempts == 0:
            conn.close()
            # Return welcoming onboarding state (TC-66)
            return {
                "has_data": False,
                "welcome_state": True,
                "message": "Welcome to AutoQuiz! You haven't taken any quiz loops yet. Upload study materials or start your first practice session to generate your personalized weakness heatmap.",
                "readiness_percentage": 0.0,
                "first_try_success_rate": 0.0,
                "looped_mastery_rate": 0.0,
                "weak_concepts": [],
                "heatmap_data": [],
                "retry_history": [],
                "render_time_ms": round((time.time() - start_time) * 1000, 2)
            }

        # 2. Overall Readiness Percentage & Topic Statuses
        cursor.execute("SELECT topic_id, name, mastery_status FROM topics WHERE user_id = ?", (user_id,))
        topics = [dict(r) for r in cursor.fetchall()]
        total_topics = len(topics)
        mastered_topics = sum(1 for t in topics if t["mastery_status"] == "Mastered")
        readiness_percentage = round((mastered_topics / total_topics * 100.0), 1) if total_topics > 0 else 0.0

        # 3. First-Attempt vs Looped/Remediated Success Metrics (BR-4, REQ_17, TC-64)
        cursor.execute('''
        SELECT
            COUNT(CASE WHEN is_first_attempt = 1 THEN 1 END) as first_try_total,
            COUNT(CASE WHEN is_first_attempt = 1 AND score >= 100.0 AND low_conf_count = 0 THEN 1 END) as first_try_passed,
            AVG(CASE WHEN is_first_attempt = 1 THEN score END) as avg_first_try_score,
            COUNT(CASE WHEN is_first_attempt = 0 THEN 1 END) as looped_total,
            COUNT(CASE WHEN is_first_attempt = 0 AND score >= 100.0 AND low_conf_count = 0 THEN 1 END) as looped_passed,
            AVG(CASE WHEN is_first_attempt = 0 THEN score END) as avg_looped_score
        FROM attempts
        WHERE user_id = ?
        ''', (user_id,))
        breakdown = dict(cursor.fetchone())

        first_try_rate = 0.0
        if breakdown["first_try_total"] and breakdown["first_try_total"] > 0:
            first_try_rate = round((breakdown["first_try_passed"] / breakdown["first_try_total"]) * 100.0, 1)

        looped_rate = 0.0
        if breakdown["looped_total"] and breakdown["looped_total"] > 0:
            looped_rate = round((breakdown["looped_passed"] / breakdown["looped_total"]) * 100.0, 1)

        # 4. Weakness Heatmap & Topic Failure Frequencies (TC-63, TC-67)
        # Calculates average score, failure count (<100%), and weakness level (High, Moderate, Mastered)
        cursor.execute('''
        SELECT
            t.topic_id,
            t.name as topic_name,
            t.mastery_status,
            COUNT(a.attempt_id) as attempts_count,
            AVG(a.score) as avg_score,
            SUM(CASE WHEN a.score < 100.0 THEN 1 ELSE 0 END) as failure_count,
            SUM(a.low_conf_count) as total_unverified_guesses
        FROM topics t
        LEFT JOIN attempts a ON t.topic_id = a.topic_id AND a.user_id = t.user_id
        WHERE t.user_id = ?
        GROUP BY t.topic_id, t.name, t.mastery_status
        ORDER BY failure_count DESC, avg_score ASC
        ''', (user_id,))
        topic_stats = [dict(r) for r in cursor.fetchall()]

        heatmap_data = []
        weak_concepts = []

        for stat in topic_stats:
            avg_sc = round(stat["avg_score"] or 0.0, 1)
            fails = stat["failure_count"] or 0
            
            # Determine weakness intensity: Critical (Red), Warning (Amber), Solid (Green)
            if fails >= 2 or (stat["attempts_count"] > 0 and avg_sc < 60.0):
                intensity = "High Weakness"
                color = "#EF4444" # Red
                weak_concepts.append({
                    "topic_name": stat["topic_name"],
                    "failure_count": fails,
                    "avg_score": avg_sc,
                    "reason": f"{fails} failed iterations with average score {avg_sc}%"
                })
            elif fails == 1 or (stat["attempts_count"] > 0 and avg_sc < 100.0):
                intensity = "Moderate Weakness"
                color = "#F59E0B" # Amber
                weak_concepts.append({
                    "topic_name": stat["topic_name"],
                    "failure_count": fails,
                    "avg_score": avg_sc,
                    "reason": f"Remediation in progress (Average: {avg_sc}%)"
                })
            else:
                intensity = "Mastered / Strong"
                color = "#10B981" # Green

            heatmap_data.append({
                "topic_id": stat["topic_id"],
                "topic_name": stat["topic_name"],
                "mastery_status": stat["mastery_status"],
                "attempts": stat["attempts_count"],
                "average_score": avg_sc,
                "failure_count": fails,
                "unverified_guesses": stat["total_unverified_guesses"] or 0,
                "weakness_level": intensity,
                "color_hex": color
            })

        # 5. Retry History Timeline
        cursor.execute('''
        SELECT a.attempt_id, a.topic_id, t.name as topic_name, a.score, a.confidence,
               a.is_first_attempt, a.timestamp
        FROM attempts a
        JOIN topics t ON a.topic_id = t.topic_id
        WHERE a.user_id = ?
        ORDER BY a.timestamp ASC
        LIMIT 50
        ''', (user_id,))
        history = [dict(r) for r in cursor.fetchall()]

        # 6. Decaying Review Alerts (TC-68)
        cursor.execute("SELECT topic_id, name, last_mastered_at FROM topics WHERE user_id = ? AND mastery_status = 'Review Due'", (user_id,))
        decay_alerts = [dict(r) for r in cursor.fetchall()]

        conn.close()

        render_ms = round((time.time() - start_time) * 1000, 2)
        logger.info("Dashboard analytics compiled in %.2f ms (PERF-3)", render_ms)

        return {
            "has_data": True,
            "welcome_state": False,
            "readiness_percentage": readiness_percentage,
            "total_topics": total_topics,
            "mastered_topics": mastered_topics,
            "first_attempt_metrics": {
                "total": breakdown["first_try_total"] or 0,
                "passed": breakdown["first_try_passed"] or 0,
                "success_rate_percent": first_try_rate,
                "average_score": round(breakdown["avg_first_try_score"] or 0.0, 1),
                "label": "First-Attempt Pass Rate"
            },
            "looped_mastery_metrics": {
                "total": breakdown["looped_total"] or 0,
                "passed": breakdown["looped_passed"] or 0,
                "success_rate_percent": looped_rate,
                "average_score": round(breakdown["avg_looped_score"] or 0.0, 1),
                "label": "Remediated / Looped Mastery Rate"
            },
            "weak_concepts": weak_concepts,
            "heatmap_data": heatmap_data,
            "retry_history": history,
            "decay_alerts": decay_alerts,
            "render_time_ms": render_ms
        }

