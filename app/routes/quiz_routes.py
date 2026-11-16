from flask import Blueprint, request, jsonify, session
from app.services.remediation import RemediationEngine
from app.services.spaced_repetition import SpacedRepetitionService
from app.services.document_service import DocumentService
from app.database import get_connection
import os
from pathlib import Path

quiz_bp = Blueprint("quiz", __name__)

def get_current_user_id() -> str:
    return session.get("user_id") or request.headers.get("X-User-ID") or "24CSB1A12"

@quiz_bp.route("/quick-start", methods=["POST"])
def quick_start():
    """
    1-Click Quick Start: Ingests PDF/TXT/MD/PPTX, extracts concepts, and immediately
    generates the active quiz loop for seamless demo experience.
    """
    user_id = get_current_user_id()
    doc_id = None
    topic_name = "Core Study Material"
    
    try:
        # 1. Check if uploading a file
        if "file" in request.files:
            file = request.files["file"]
            if file and file.filename:
                file_bytes = file.read()
                res = DocumentService.ingest_document(
                    user_id=user_id,
                    filename=file.filename,
                    file_bytes=file_bytes,
                    overwrite=True
                )
                if res.get("status") == "duplicate_prompt":
                    return jsonify(res), 200
                doc_id = res.get("doc_id")
        
        # 2. Check if loading pre-bundled sample
        json_data = request.get_json(silent=True) or {}
        sample_type = request.form.get("sample") or json_data.get("sample")
        if not doc_id and sample_type:
            base_sample_dir = Path(__file__).resolve().parent.parent.parent / "sample_data"
            if sample_type == "ml":
                sample_file = base_sample_dir / "ml_overfitting.pdf"
                fname = "ml_overfitting.pdf"
            elif sample_type == "code":
                sample_file = base_sample_dir / "python_algorithms.md"
                fname = "python_algorithms.md"
            else:
                sample_file = base_sample_dir / "business_essentials.txt"
                fname = "business_essentials.txt"
                
            if sample_file.exists():
                with open(sample_file, "rb") as f:
                    content = f.read()
                res = DocumentService.ingest_document(
                    user_id=user_id,
                    filename=fname,
                    file_bytes=content,
                    overwrite=True
                )
                doc_id = res.get("doc_id")

        # 3. If no doc_id yet, find the most recent document for this user
        if not doc_id:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT doc_id, title FROM documents WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (user_id,))
            recent = cursor.fetchone()
            conn.close()
            if recent:
                doc_id = recent["doc_id"]
            else:
                return jsonify({"error": "No document provided. Please upload a PDF or select a sample."}), 400

        # 4. Find the first topic for this document
        topics = RemediationEngine.get_user_topics(user_id=user_id, doc_id=doc_id)
        if not topics:
            return jsonify({"error": "No topics could be extracted from this document."}), 400

        first_topic = topics[0]
        topic_id = first_topic["topic_id"]
        topic_name = first_topic["name"]

        # 5. Start active quiz session
        session_info = RemediationEngine.start_or_resume_session(
            user_id=user_id,
            topic_id=topic_id,
            num_questions=3
        )
        session_info["topic_name"] = topic_name
        session_info["doc_id"] = doc_id
        return jsonify(session_info), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except PermissionError as pe:
        return jsonify({"error": str(pe)}), 403
    except OSError as oe:
        return jsonify({"error": str(oe)}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to start quiz: {str(e)}"}), 500

@quiz_bp.route("/topics", methods=["GET"])
def get_topics():
    """
    Retrieves syllabus topics for student with sequential module unlocking status (REQ_12, TC-44).
    Only the first topic is unlocked until mastered.
    """
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    doc_id = request.args.get("doc_id")
    topics = RemediationEngine.get_user_topics(user_id=user_id, doc_id=doc_id)
    return jsonify({"topics": topics}), 200

@quiz_bp.route("/session/start", methods=["POST"])
def start_session():
    """
    Starts a new quiz loop or resumes an existing 'In Progress' loop.
    Enforces sequential module unlocking (REQ_12, BR-2, TC-42).
    """
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    data = request.get_json() or {}
    topic_id = data.get("topic_id")
    num_questions = int(data.get("num_questions", 3))

    if not topic_id:
        return jsonify({"error": "topic_id is required."}), 400

    try:
        session_info = RemediationEngine.start_or_resume_session(
            user_id=user_id,
            topic_id=topic_id,
            num_questions=num_questions
        )
        return jsonify(session_info), 200
    except PermissionError as perm_err:
        # Sequential lock refusal (TC-42)
        return jsonify({"error": str(perm_err), "code": "TOPIC_LOCKED"}), 403
    except ValueError as val_err:
        return jsonify({"error": str(val_err)}), 400
    except ConnectionError as conn_err:
        # LLM service unavailable (TC-34)
        return jsonify({"error": str(conn_err)}), 503
    except Exception as ex:
        return jsonify({"error": f"Internal Practice Error: {str(ex)}"}), 500

@quiz_bp.route("/session/<session_id>/progress", methods=["POST"])
def save_progress(session_id: str):
    """
    Saves answer progress for single question (TC-47).
    Enforces mandatory confidence rating selection (REQ_10, TC-49, TC-50).
    """
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    data = request.get_json() or {}
    q_index = data.get("question_index")
    user_answer = data.get("selected_answer")
    conf = data.get("confidence")

    if q_index is None or user_answer is None:
        return jsonify({"error": "question_index and selected_answer are required."}), 400

    try:
        result = RemediationEngine.save_question_progress(
            session_id=session_id,
            question_index=int(q_index),
            user_answer=str(user_choice if (user_choice := user_answer) else ""),
            confidence_tag=str(conf if conf else "")
        )
        return jsonify(result), 200
    except ValueError as val_err:
        # Unselected confidence error (REQ_10, TC-49)
        return jsonify({"error": str(val_err), "code": "CONFIDENCE_REQUIRED"}), 400

@quiz_bp.route("/session/<session_id>/exit", methods=["POST"])
def exit_practice_session(session_id: str):
    """Saves session state as 'In Progress' when student confirms early exit (Alt Flow 2.1, TC-45)."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    result = RemediationEngine.exit_session(session_id)
    return jsonify(result), 200

@quiz_bp.route("/session/<session_id>/submit", methods=["POST"])
def submit_session(session_id: str):
    """
    Evaluates complete quiz loop (UC-2, UC-9, REQ_11, REQ_12, REQ_13, BR-2, BR-6).
    Enforces 100% strict mastery with Medium/High confidence.
    """
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    data = request.get_json() or {}
    answers = data.get("answers", [])

    if not answers:
        return jsonify({"error": "Submission answers are empty."}), 400

    try:
        evaluation = RemediationEngine.evaluate_loop_submission(
            user_id=user_id,
            session_id=session_id,
            submission_answers=answers
        )
        return jsonify(evaluation), 200
    except ValueError as val_err:
        return jsonify({"error": str(val_err)}), 400
    except Exception as ex:
        return jsonify({"error": f"Evaluation Error: {str(ex)}"}), 500

@quiz_bp.route("/micro-verification/start", methods=["POST"])
def start_micro_verification():
    """Starts 2-question micro-verification loop for decayed topic (UC-5, TC-59)."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    data = request.get_json() or {}
    topic_id = data.get("topic_id")
    if not topic_id:
        return jsonify({"error": "topic_id is required."}), 400

    try:
        verification = SpacedRepetitionService.start_micro_verification_loop(user_id=user_id, topic_id=topic_id)
        return jsonify(verification), 200
    except Exception as ex:
        return jsonify({"error": str(ex)}), 400

@quiz_bp.route("/micro-verification/submit", methods=["POST"])
def submit_micro_verification():
    """
    Evaluates micro-verification (TC-60, TC-61).
    100% -> Restored to Mastered. Less -> Revoked, full remediation initiated.
    """
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    data = request.get_json() or {}
    topic_id = data.get("topic_id")
    answers = data.get("answers", [])
    questions = data.get("questions", [])

    if not topic_id or not answers or not questions:
        return jsonify({"error": "topic_id, answers, and questions are required."}), 400

    try:
        result = SpacedRepetitionService.evaluate_micro_verification(
            user_id=user_id,
            topic_id=topic_id,
            user_answers=answers,
            questions=questions
        )
        return jsonify(result), 200
    except Exception as ex:
        return jsonify({"error": str(ex)}), 400

