import logging
from typing import Dict, Any, List, Optional
from app.database import get_connection
from app.services.vector_store import vector_store

logger = logging.getLogger("AUTOQUIZ.ADMIN")

class AdminService:
    """
    Admin & Instructor Management Service (UC-10, UC-11, TC-06, TC-74, TC-75, TC-76, TC-77).
    Provides syllabus taxonomy administration, vector database wipe operations,
    and student performance history resets.
    """

    @staticmethod
    def get_syllabus_taxonomy() -> List[Dict[str, Any]]:
        """Retrieves current syllabus taxonomy nodes (UC-10, TC-74)."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, topic_name, description, parent_id, order_index FROM taxonomy ORDER BY order_index ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def add_taxonomy_topic(topic_name: str, description: str = "", order_index: int = 0) -> Dict[str, Any]:
        """Adds a new curriculum topic to the syllabus taxonomy (UC-10, TC-74)."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO taxonomy (topic_name, description, order_index) VALUES (?, ?, ?)",
                       (topic_name.strip(), description.strip(), order_index))
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logger.info("Admin created taxonomy node: %s (id=%d)", topic_name, new_id)
        return {"id": new_id, "topic_name": topic_name, "description": description, "order_index": order_index}

    @staticmethod
    def update_taxonomy_topic(topic_id: int, topic_name: str, description: str, order_index: int) -> bool:
        """Updates an existing syllabus taxonomy topic (UC-10, TC-74)."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE taxonomy SET topic_name = ?, description = ?, order_index = ? WHERE id = ?",
                       (topic_name.strip(), description.strip(), order_index, topic_id))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    @staticmethod
    def delete_taxonomy_topic(topic_id: int) -> bool:
        """Deletes a syllabus taxonomy node (UC-10, TC-74)."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM taxonomy WHERE id = ?", (topic_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    @staticmethod
    def wipe_document_vectors(admin_user_id: str, target_user_id: str, doc_id: str) -> Dict[str, Any]:
        """
        Wipes vector storage collection for a specified document (UC-11, TC-75, TC-77).
        Raises ValueError if collection does not exist (TC-77).
        """
        count_before = vector_store.get_collection_count(target_user_id, doc_id)
        if count_before == 0:
            raise ValueError(f"Collection for document '{doc_id}' does not exist or has already been cleared.")

        success = vector_store.wipe_collection(target_user_id, doc_id)
        if not success:
            raise ValueError(f"Failed to wipe vector collection for document '{doc_id}'.")

        # Mark chunks deleted in database as well
        conn = get_connection()
        conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        conn.commit()
        conn.close()

        logger.info("Admin %s wiped %d vectors for doc %s", admin_user_id, count_before, doc_id)
        return {"doc_id": doc_id, "vectors_wiped": count_before, "status": "wiped"}

    @staticmethod
    def reset_student_history(admin_user_id: str, student_user_id: str) -> Dict[str, Any]:
        """
        Resets performance history, attempt logs, and mastery states for a student (UC-11, TC-76).
        Student dashboard will immediately show the initial welcome state.
        """
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM attempts WHERE user_id = ?", (student_user_id,))
        deleted_attempts = cursor.rowcount

        cursor.execute("DELETE FROM user_scores WHERE user_id = ?", (student_user_id,))
        cursor.execute("DELETE FROM quiz_sessions WHERE user_id = ?", (student_user_id,))

        # Revert all topics to 'Unmastered'
        cursor.execute('''
        UPDATE topics
        SET mastery_status = 'Unmastered', last_mastered_at = NULL, attempt_count = 0, score_stability = 1.0
        WHERE user_id = ?
        ''', (student_user_id,))

        conn.commit()
        conn.close()

        logger.info("Admin %s reset history for student %s (%d attempts deleted)",
                    admin_user_id, student_user_id, deleted_attempts)
        return {
            "student_user_id": student_user_id,
            "deleted_attempts": deleted_attempts,
            "status": "reset_successful",
            "message": f"Successfully reset history for student {student_user_id}. Dashboard restored to welcome state."
        }

