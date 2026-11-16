import json
import time
import uuid
import logging
from typing import Dict, Any, List, Optional, Set
from app.database import get_connection, queue_attempt_write
from app.services.rag_engine import rag_engine

logger = logging.getLogger("AUTOQUIZ.REMEDIATION")

class RemediationEngine:
    """
    Adaptive 100% Mastery Remediation Loop Engine (UC-2, UC-4, REQ_10, REQ_11, REQ_12, REQ_13, BR-2, BR-6).
    Enforces strict 100% mastery threshold, handles anti-guessing confidence validation,
    locks sequential curriculum topics until previous topic is mastered, and manages session recovery.
    """

    @staticmethod
    def get_user_topics(user_id: str, doc_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves topics for a student and enforces sequential module locking (REQ_12, TC-44).
        Only the first topic is unlocked initially. Subsequent topics are unlocked only if the preceding topic is Mastered.
        """
        conn = get_connection()
        cursor = conn.cursor()
        if doc_id:
            cursor.execute('''
            SELECT topic_id, doc_id, user_id, name, order_index, mastery_status, last_mastered_at, attempt_count
            FROM topics
            WHERE user_id = ? AND doc_id = ?
            ORDER BY order_index ASC
            ''', (user_id, doc_id))
        else:
            cursor.execute('''
            SELECT topic_id, doc_id, user_id, name, order_index, mastery_status, last_mastered_at, attempt_count
            FROM topics
            WHERE user_id = ?
            ORDER BY doc_id, order_index ASC
            ''', (user_id,))
        rows = cursor.fetchall()
        conn.close()

        topics = []
        # Group by document to evaluate sequential lock per document
        docs_group: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows:
            d_id = r["doc_id"]
            if d_id not in docs_group:
                docs_group[d_id] = []
            docs_group[d_id].append(dict(r))

        for d_id, doc_topics in docs_group.items():
            preceding_mastered = True # First topic is always unlocked (TC-44)
            for idx, top in enumerate(doc_topics):
                if idx == 0:
                    top["is_unlocked"] = True
                else:
                    top["is_unlocked"] = preceding_mastered

                # Next topic unlocks only if current is Mastered (TC-40, TC-41, TC-42)
                if top["mastery_status"] != "Mastered":
                    preceding_mastered = False

                topics.append(top)

        return topics

    @staticmethod
    def check_topic_access(user_id: str, topic_id: str) -> bool:
        """Verifies if the student is permitted to access/practice this topic based on sequential unlocking (TC-42)."""
        topics = RemediationEngine.get_user_topics(user_id)
        for t in topics:
            if t["topic_id"] == topic_id:
                return t.get("is_unlocked", False)
        return False

    @staticmethod
    def start_or_resume_session(user_id: str, topic_id: str, num_questions: int = 3) -> Dict[str, Any]:
        """
        Initiates a new quiz session or resumes an existing 'In Progress' session (SRS 5.4, TC-47).
        Enforces sequential access check (TC-42).
        """
        # 1. Enforce Sequential Unlocking Check (REQ_12, BR-2, TC-42)
        if not RemediationEngine.check_topic_access(user_id, topic_id):
            raise PermissionError("Access Denied: Preceding topic is not mastered. Complete current module with 100% mastery first.")

        conn = get_connection()
        cursor = conn.cursor()

        # 2. Check for active session in progress (Session Recovery - TC-47)
        cursor.execute('''
        SELECT session_id, current_question_index, questions_json, answers_json
        FROM quiz_sessions
        WHERE user_id = ? AND topic_id = ? AND status = 'In Progress'
        ORDER BY updated_at DESC LIMIT 1
        ''', (user_id, topic_id))
        existing_session = cursor.fetchone()

        if existing_session:
            session_id = existing_session["session_id"]
            questions = json.loads(existing_session["questions_json"])
            answers = json.loads(existing_session["answers_json"])
            curr_idx = existing_session["current_question_index"]
            conn.close()
            logger.info("Resuming existing In Progress session %s at question %d for user %s", session_id, curr_idx, user_id)
            return {
                "session_id": session_id,
                "topic_id": topic_id,
                "status": "In Progress",
                "resumed": True,
                "current_index": curr_idx,
                "total_questions": len(questions),
                "questions": questions,
                "saved_answers": answers
            }

        # 3. Retrieve previous attempts on this topic to enforce BR-3 (Zero Repetition)
        cursor.execute("SELECT details_json FROM attempts WHERE user_id = ? AND topic_id = ? ORDER BY timestamp DESC LIMIT 5",
                       (user_id, topic_id))
        past_attempts = cursor.fetchall()
        previous_stems: Set[str] = set()
        unverified_concepts: List[str] = []

        for att in past_attempts:
            if att["details_json"]:
                try:
                    data = json.loads(att["details_json"])
                    for q in data.get("questions", []):
                        previous_stems.add(q.get("question", ""))
                    for unc in data.get("unverified_concepts", []):
                        unverified_concepts.append(unc)
                except Exception:
                    pass

        # 4. Generate fresh question set via RAG Engine
        questions = rag_engine.generate_questions(
            user_id=user_id,
            topic_id=topic_id,
            num_questions=num_questions,
            previous_question_stems=previous_stems,
            unverified_concepts=unverified_concepts
        )

        session_id = f"sess_{uuid.uuid4().hex[:10]}"
        now = time.time()
        cursor.execute('''
        INSERT INTO quiz_sessions (session_id, user_id, topic_id, status, current_question_index, questions_json, answers_json, created_at, updated_at)
        VALUES (?, ?, ?, 'In Progress', 0, ?, '[]', ?, ?)
        ''', (session_id, user_id, topic_id, json.dumps(questions), now, now))

        # Update topic status to 'In Progress' if Unmastered
        cursor.execute("UPDATE topics SET mastery_status = 'In Progress' WHERE topic_id = ? AND mastery_status = 'Unmastered'",
                       (topic_id,))

        conn.commit()
        conn.close()

        return {
            "session_id": session_id,
            "topic_id": topic_id,
            "status": "In Progress",
            "resumed": False,
            "current_index": 0,
            "total_questions": len(questions),
            "questions": questions,
            "saved_answers": []
        }

    @staticmethod
    def save_question_progress(session_id: str, question_index: int, user_answer: str, confidence_tag: str) -> Dict[str, Any]:
        """Saves incremental answer progress during an active loop (TC-47)."""
        # Validate confidence rating (REQ_10, TC-49, TC-50)
        valid_conf = ["High", "Medium", "Low"]
        if not confidence_tag or confidence_tag not in valid_conf:
            raise ValueError("Unselected Confidence Tag: You must select a confidence rating (High, Medium, or Low) before proceeding.")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT questions_json, answers_json FROM quiz_sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise ValueError(f"Quiz session {session_id} not found.")

        answers = json.loads(row["answers_json"])
        # Update or append
        entry = {
            "question_index": question_index,
            "selected_answer": user_answer,
            "confidence": confidence_tag,
            "answered_at": time.time()
        }
        if question_index < len(answers):
            answers[question_index] = entry
        else:
            answers.append(entry)

        now = time.time()
        cursor.execute('''
        UPDATE quiz_sessions
        SET current_question_index = ?, answers_json = ?, updated_at = ?
        WHERE session_id = ?
        ''', (question_index + 1, json.dumps(answers), now, session_id))
        conn.commit()
        conn.close()

        return {"status": "saved", "current_index": question_index + 1}

    @staticmethod
    def exit_session(session_id: str) -> Dict[str, Any]:
        """Student exits practice session mid-loop with warning confirmation (Alt Flow 2.1, TC-45)."""
        conn = get_connection()
        cursor = conn.cursor()
        now = time.time()
        cursor.execute("UPDATE quiz_sessions SET status = 'In Progress', updated_at = ? WHERE session_id = ?",
                       (now, session_id))
        conn.commit()
        conn.close()
        logger.info("Session %s saved as In Progress upon student exit.", session_id)
        return {"status": "In Progress", "message": "Practice session state successfully preserved as In Progress."}

    @staticmethod
    def evaluate_loop_submission(
        user_id: str,
        session_id: str,
        submission_answers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluates full quiz loop attempt.
        Validates confidence tags (REQ_10, TC-49).
        Enforces Low-confidence unverified concept rule (REQ_11, TC-51).
        Enforces 100% strict mastery rule (REQ_12, BR-2, BR-6, TC-40, TC-52, TC-53).
        Logs attempt in database under 100ms (PERF-4, TC-37).
        """
        start_time = time.time()

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT topic_id, questions_json FROM quiz_sessions WHERE session_id = ?", (session_id,))
        sess_row = cursor.fetchone()
        if not sess_row:
            conn.close()
            raise ValueError("Invalid session ID.")

        topic_id = sess_row["topic_id"]
        questions = json.loads(sess_row["questions_json"])
        conn.close()

        if len(submission_answers) != len(questions):
            raise ValueError(f"Submission count ({len(submission_answers)}) does not match question count ({len(questions)}).")

        # 1. Validate confidence tag attached to every submission (REQ_10, TC-49)
        high_cnt = 0
        med_cnt = 0
        low_cnt = 0
        correct_count = 0
        evaluated_details = []
        unverified_concepts = []

        for i, q in enumerate(questions):
            sub = submission_answers[i]
            user_choice = sub.get("selected_answer")
            conf = sub.get("confidence")

            if not conf or conf not in ["High", "Medium", "Low"]:
                raise ValueError(f"Unselected Confidence Tag on Question {i+1}: Every question requires a High, Medium, or Low rating.")

            if conf == "High":
                high_cnt += 1
            elif conf == "Medium":
                med_cnt += 1
            else:
                low_cnt += 1

            is_correct = (str(user_choice).strip().lower() == str(q["answer"]).strip().lower())
            
            # Anti-Guessing Guard: If Correct but Low Confidence -> Flag Unverified (REQ_11, BR-6, TC-51)
            is_unverified = False
            mastery_credit = False

            if is_correct:
                if conf == "Low":
                    is_unverified = True
                    mastery_credit = False
                    unverified_concepts.append(q.get("concept", q["question"][:40]))
                    feedback = f"Correct answer, but flagged as UNVERIFIED due to Low confidence rating. This concept will return in your next loop for conceptual verification."
                else:
                    correct_count += 1
                    mastery_credit = True
                    feedback = f"Correct! {q.get('explanation', '')}"
            else:
                unverified_concepts.append(q.get("concept", q["question"][:40]))
                feedback = f"Incorrect. Grounded Feedback: {q.get('explanation', '')}. The correct answer was '{q['answer']}'."

            evaluated_details.append({
                "question": q["question"],
                "selected": user_choice,
                "correct_answer": q["answer"],
                "is_correct": is_correct,
                "confidence": conf,
                "is_unverified": is_unverified,
                "mastery_credit": mastery_credit,
                "feedback": feedback
            })

        total_q = len(questions)
        score_percent = round((correct_count / total_q) * 100.0, 2)
        overall_conf = "High" if high_cnt >= med_cnt and high_cnt >= low_cnt else ("Medium" if med_cnt >= low_cnt else "Low")

        # 2. Check 100% Mastery Condition (BR-2, BR-6, REQ_12, TC-40, TC-52, TC-53)
        # 100% requires all correct answers to be marked with Medium or High confidence (BR-6)
        is_mastered = (score_percent == 100.0 and low_cnt == 0)

        # 3. Check if first attempt on this topic (BR-4, REQ_17)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM attempts WHERE user_id = ? AND topic_id = ?", (user_id, topic_id))
        past_cnt = cursor.fetchone()["cnt"]
        is_first_attempt = 1 if past_cnt == 0 else 0

        attempt_id = f"att_{uuid.uuid4().hex[:10]}"
        now = time.time()

        attempt_record = {
            "attempt_id": attempt_id,
            "user_id": user_id,
            "topic_id": topic_id,
            "session_id": session_id,
            "score": score_percent,
            "confidence": overall_conf,
            "is_first_attempt": is_first_attempt,
            "high_conf_count": high_cnt,
            "med_conf_count": med_cnt,
            "low_conf_count": low_cnt,
            "details_json": json.dumps({
                "questions": questions,
                "evaluations": evaluated_details,
                "unverified_concepts": unverified_concepts
            }),
            "timestamp": now
        }

        # 4. Fast Database Write with Error Queue Fallback (PERF-4, TC-37, TC-38)
        try:
            cursor.execute('''
            INSERT INTO attempts (
                attempt_id, user_id, topic_id, session_id, score, confidence,
                is_first_attempt, high_conf_count, med_conf_count, low_conf_count,
                details_json, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                attempt_record["attempt_id"], attempt_record["user_id"], attempt_record["topic_id"],
                attempt_record["session_id"], attempt_record["score"], attempt_record["confidence"],
                attempt_record["is_first_attempt"], attempt_record["high_conf_count"],
                attempt_record["med_conf_count"], attempt_record["low_conf_count"],
                attempt_record["details_json"], attempt_record["timestamp"]
            ))

            # Legacy user_scores table log (Report pages 51, 98)
            cursor.execute('''
            INSERT INTO user_scores (user_id, topic, score, feedback)
            VALUES (?, ?, ?, ?)
            ''', (user_id, topic_id, int(score_percent), f"Score {score_percent}% | Conf: {overall_conf}"))

            # Update topic mastery state & session
            new_status = "Mastered" if is_mastered else "In Progress"
            last_mast = now if is_mastered else None

            # Calculate score stability for spaced repetition decay (BR-5)
            cursor.execute("SELECT score FROM attempts WHERE user_id = ? AND topic_id = ?", (user_id, topic_id))
            all_scores = [r["score"] for r in cursor.fetchall()]
            stability = 1.0
            if len(all_scores) > 1:
                variance = sum((s - (sum(all_scores)/len(all_scores))) ** 2 for s in all_scores) / len(all_scores)
                stability = max(0.2, 1.0 - (variance / 10000.0))

            cursor.execute('''
            UPDATE topics
            SET mastery_status = CASE WHEN ? = 'Mastered' THEN 'Mastered' ELSE mastery_status END,
                last_mastered_at = COALESCE(?, last_mastered_at),
                attempt_count = attempt_count + 1,
                score_stability = ?
            WHERE topic_id = ?
            ''', (new_status, last_mast, stability, topic_id))

            cursor.execute("UPDATE quiz_sessions SET status = 'Completed', updated_at = ? WHERE session_id = ?",
                           (now, session_id))

            conn.commit()
        except Exception as db_err:
            logger.error("Database write error encountered: %s. Queueing attempt locally (TC-38).", db_err)
            queue_attempt_write(attempt_record)

        conn.close()
        write_time_ms = round((time.time() - start_time) * 1000, 2)
        logger.info("Evaluation write completed in %.2f ms (PERF-4)", write_time_ms)

        return {
            "attempt_id": attempt_id,
            "session_id": session_id,
            "topic_id": topic_id,
            "score": score_percent,
            "correct_count": correct_count,
            "total_questions": total_q,
            "is_mastered": is_mastered,
            "mastery_status": "Mastered" if is_mastered else "In Progress",
            "confidence_counts": {"high": high_cnt, "medium": med_cnt, "low": low_cnt},
            "evaluations": evaluated_details,
            "unverified_concepts": unverified_concepts,
            "write_latency_ms": write_time_ms
        }

