import os
from flask import Blueprint, request, jsonify, session
from app.database import get_connection
from app.services.document_service import DocumentService
from app.services.vector_store import vector_store

doc_bp = Blueprint("documents", __name__)

def get_current_user_id() -> str:
    """Helper to get authenticated user or return None."""
    return session.get("user_id") or request.headers.get("X-User-ID")

@doc_bp.route("/upload", methods=["POST"])
def upload_document():
    """
    Ingests PDF, TXT, or MD study notes (REQ_01 to REQ_05, TC-07 to TC-16).
    Supports single or multiple file uploads in one batch.
    """
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required to upload documents."}), 401

    overwrite = request.form.get("overwrite", "false").lower() == "true"
    create_new_version = request.form.get("create_new_version", "false").lower() == "true"

    # Support multiple files: files[] or multiple file fields
    uploaded_files = request.files.getlist("files") or request.files.getlist("file")
    
    if uploaded_files:
        results = []
        duplicate_prompts = []
        
        for up_file in uploaded_files:
            filename = up_file.filename
            if not filename:
                continue
            file_bytes = up_file.read()
            try:
                res = DocumentService.ingest_document(
                    user_id=user_id,
                    filename=filename,
                    file_bytes=file_bytes,
                    overwrite=overwrite,
                    create_new_version=create_new_version
                )
                if res.get("status") == "duplicate_prompt":
                    duplicate_prompts.append(res)
                else:
                    results.append(res)
            except Exception as e:
                return jsonify({"error": f"Error ingesting '{filename}': {str(e)}"}), 400

        if duplicate_prompts and not results:
            return jsonify(duplicate_prompts[0]), 200

        if len(results) == 1:
            return jsonify(results[0]), 201
        elif len(results) > 1:
            total_chunks = sum(r.get("chunk_count", 0) for r in results)
            all_topics = []
            for r in results:
                all_topics.extend(r.get("topics", []))
            return jsonify({
                "status": "success",
                "message": f"Successfully ingested {len(results)} files.",
                "total_chunks": total_chunks,
                "topics": list(dict.fromkeys(all_topics)),
                "documents": results
            }), 201
        else:
            return jsonify({"error": "No valid files could be processed."}), 400

    # Fallback to json payload (used in tests and API calls)
    json_data = request.get_json() or {}
    filename = json_data.get("filename", "")
    content = json_data.get("content", "")
    file_bytes = content.encode("utf-8") if isinstance(content, str) else b""
    title = json_data.get("title")
    overwrite = bool(json_data.get("overwrite", False))
    create_new_version = bool(json_data.get("create_new_version", False))

    if not filename or file_bytes is None:
        return jsonify({"error": "No file uploaded or file content missing."}), 400

    try:
        result = DocumentService.ingest_document(
            user_id=user_id,
            filename=filename,
            file_bytes=file_bytes,
            title=title,
            overwrite=overwrite,
            create_new_version=create_new_version
        )
        status_code = 200 if result.get("status") == "duplicate_prompt" else 201
        return jsonify(result), status_code
    except ValueError as val_err:
        return jsonify({"error": str(val_err)}), 400
    except OSError as os_err:
        return jsonify({"error": str(os_err)}), 500
    except Exception as ex:
        return jsonify({"error": f"Internal Ingestion Error: {str(ex)}"}), 500

@doc_bp.route("", methods=["GET"])
def list_documents():
    """Lists uploaded documents strictly for the authenticated student (SRS 5.3 data isolation, TC-05)."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT doc_id, user_id, title, file_type, version, chunk_count, created_at
    FROM documents
    WHERE user_id = ?
    ORDER BY created_at DESC
    ''', (user_id,))
    docs = [dict(r) for r in cursor.fetchall()]

    # Attach topics for each document
    for d in docs:
        cursor.execute("SELECT topic_id, name, order_index, mastery_status FROM topics WHERE doc_id = ? ORDER BY order_index ASC", (d["doc_id"],))
        d["topics"] = [dict(t) for t in cursor.fetchall()]

    conn.close()
    return jsonify({"documents": docs}), 200

@doc_bp.route("/<doc_id>", methods=["GET"])
def get_document(doc_id: str):
    """Retrieves document details with user isolation (SRS 5.3, TC-05)."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT doc_id, user_id, title, file_type, version, chunk_count, created_at FROM documents WHERE doc_id = ? AND user_id = ?",
                   (doc_id, user_id))
    doc = cursor.fetchone()
    if not doc:
        conn.close()
        return jsonify({"error": "Document not found or access denied."}), 404

    result = dict(doc)
    cursor.execute("SELECT topic_id, name, order_index, mastery_status FROM topics WHERE doc_id = ? ORDER BY order_index ASC", (doc_id,))
    result["topics"] = [dict(t) for t in cursor.fetchall()]
    conn.close()
    return jsonify(result), 200

@doc_bp.route("/<doc_id>", methods=["DELETE"])
def delete_document(doc_id: str):
    """Deletes document and vectors for current student."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    vector_store.wipe_collection(user_id, doc_id)
    conn = get_connection()
    conn.execute("DELETE FROM chunks WHERE doc_id = ? AND user_id = ?", (doc_id, user_id))
    conn.execute("DELETE FROM topics WHERE doc_id = ? AND user_id = ?", (doc_id, user_id))
    conn.execute("DELETE FROM documents WHERE doc_id = ? AND user_id = ?", (doc_id, user_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted", "doc_id": doc_id}), 200

