import time
import logging
from typing import Dict, Any, List, Optional
from app.config import RETENTION_THRESHOLD_DAYS_DEFAULT
from app.database import get_connection
from app.services.rag_engine import rag_engine

logger = logging.getLogger("AUTOQUIZ.SPACED_REPETITION")

class SpacedRepetitionService:
    """
    Automated Spaced Repetition Mastery Decay Trigger (UC-5, REQ_14, REQ_15, BR-5).
    Evaluates elapsed time against dynamic Ebbinghaus decay thresholds,
    transitions decayed topics to 'Review Due', triggers 2-question micro-verifications,
    and revokes mastery upon verification failure.
    """

    @staticmethod
    def calculate_retention_threshold_days(attempt_count: int, score_stability: float) -> float:
        """
        Dynamically adjusts decay intervals based on historical attempt frequencies and score stability (BR-5, TC-57).
        Ebbinghaus scaling: Higher stability and more successful reviews extend retention interval.
        """
        base_days = float(RETENTION_THRESHOLD_DAYS_DEFAULT) # 7.0 days default
        # If single initial attempt with stability=1.0 -> exactly 7.0 days (TC-55, TC-56)
        # Multiple attempts and different stability values scale the retention threshold (TC-57)
        threshold = base_days * (1.0 + 0.15 * max(0, attempt_count - 1)) * max(0.4, score_stability)
        return round(threshold, 4)

    @classmethod
    def audit_mastered_topics(cls, db_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Background scheduler audit running daily (REQ_14, TC-58).
        Checks all Mastered topics; transitions those exceeding dynamic retention thresholds to 'Review Due'.
        """
        conn = get_connection() if db_path is None else get_connection(db_path)
        cursor = conn.cursor()
        now = time.time()

        cursor.execute('''
        SELECT topic_id, user_id, name, last_mastered_at, attempt_count, score_stability
        FROM topics
        WHERE mastery_status = 'Mastered' AND last_mastered_at IS NOT NULL
        ''')
        mastered_topics = cursor.fetchall()

        decayed_count = 0
        decayed_topic_ids = []

        for top in mastered_topics:
            t_id = top["topic_id"]
            last_mast = top["last_mastered_at"]
            attempts = top["attempt_count"]
            stability = top["score_stability"]

            threshold_days = cls.calculate_retention_threshold_days(attempts, stability)
            elapsed_days = (now - last_mast) / 86400.0

            if elapsed_days >= threshold_days:
                # Topic shifts to 'Review Due' (TC-55)
                cursor.execute("UPDATE topics SET mastery_status = 'Review Due' WHERE topic_id = ?", (t_id,))
                decayed_count += 1
                decayed_topic_ids.append(t_id)
                logger.info("Topic %s decayed to 'Review Due' (elapsed=%.2fd >= threshold=%.2fd)",
                            t_id, elapsed_days, threshold_days)

        # Log audit execution
        cursor.execute('''
        INSERT INTO decay_audit_logs (executed_at, topics_audited, decayed_topics_count, log_message)
        VALUES (?, ?, ?, ?)
        ''', (now, len(mastered_topics), decayed_count, f"Audited {len(mastered_topics)} topics. Decayed: {decayed_count}"))

        conn.commit()
        conn.close()

        return {
            "audited_count": len(mastered_topics),
            "decayed_count": decayed_count,
            "decayed_topic_ids": decayed_topic_ids,
            "timestamp": now
        }

    @staticmethod
    def get_review_due_topics(user_id: str) -> List[Dict[str, Any]]:
        """Returns list of topics currently requiring spaced repetition review for this student (TC-68)."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT topic_id, doc_id, name, last_mastered_at, attempt_count
        FROM topics
        WHERE user_id = ? AND mastery_status = 'Review Due'
        ''', (user_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def start_micro_verification_loop(user_id: str, topic_id: str) -> Dict[str, Any]:
        """
        Injects a 2-question micro-verification loop for a decayed topic (TC-59).
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT mastery_status, name FROM topics WHERE topic_id = ? AND user_id = ?", (topic_id, user_id))
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise ValueError("Topic not found.")

        # Generate exactly 2 micro-verification questions (TC-59)
        questions = rag_engine.generate_questions(
            user_id=user_id,
            topic_id=topic_id,
            num_questions=3 # Generates questions, slice first 2
        )[:2]

        return {
            "topic_id": topic_id,
            "topic_name": row["name"],
            "is_micro_verification": True,
            "total_questions": len(questions),
            "questions": questions
        }

    @staticmethod
    def evaluate_micro_verification(user_id: str, topic_id: str, user_answers: List[Dict[str, Any]], questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluates micro-verification:
        - 100% correct -> resets topic state to 'Mastered' (TC-60).
        - Any wrong answer -> revokes Mastered, marks as 'Unmastered', prompts full remediation loop (REQ_15, Exception 5.0.E.1, TC-61).
        """
        if len(user_answers) != len(questions):
            raise ValueError("Answers count does not match verification question count.")

        correct_count = 0
        feedback_list = []

        for i, q in enumerate(questions):
            u_ans = user_answers[i].get("selected_answer", "")
            if str(u_ans).strip().lower() == str(q["answer"]).strip().lower():
                correct_count += 1
                feedback_list.append(f"Q{i+1}: Correct.")
            else:
                feedback_list.append(f"Q{i+1}: Incorrect. Correct answer: {q['answer']}. Grounded concept: {q.get('explanation','')}")

        now = time.time()
        conn = get_connection()
        cursor = conn.cursor()

        if correct_count == len(questions):
            # Resets to Mastered (TC-60)
            cursor.execute("UPDATE topics SET mastery_status = 'Mastered', last_mastered_at = ? WHERE topic_id = ?",
                           (now, topic_id))
            status = "Mastered"
            message = "Retention verified! 100% score achieved. Topic restored to Mastered."
        else:
            # Revokes Mastered status, reverts to Unmastered, prompts full remediation loop (REQ_15, TC-61)
            cursor.execute("UPDATE topics SET mastery_status = 'Unmastered', last_mastered_at = NULL WHERE topic_id = ?",
                           (topic_id,))
            status = "Unmastered"
            message = "Verification failed. Mastered status revoked. Full adaptive remediation loop required to regain mastery."

        conn.commit()
        conn.close()

        return {
            "topic_id": topic_id,
            "correct_count": correct_count,
            "total_questions": len(questions),
            "score": round((correct_count / len(questions)) * 100.0, 2),
            "mastery_status": status,
            "message": message,
            "feedback": feedback_list
        }

