import os
import re
import time
import uuid
import logging
from typing import Dict, Any, List, Tuple, Optional
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.config import ALLOWED_EXTENSIONS
from app.database import get_connection
from app.services.ast_parser import ASTParser
from app.services.vector_store import vector_store

logger = logging.getLogger("AUTOQUIZ.DOC")

class DocumentService:
    """
    Document Ingestion & AST Parsing Service (UC-1, UC-7, REQ_01 to REQ_05, BR-1).
    Handles file integrity verification, text extraction, semantic chunking with overlap,
    sub-topic discovery, vector persistence, and duplicate resolution (overwrite/version).
    """

    @staticmethod
    def validate_file_format(filename: str) -> Tuple[bool, str]:
        """Validates file extension case-insensitively (REQ_01, TC-08, TC-09)."""
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".ppt":
            return False, "Legacy .ppt binary format detected. Please save your presentation as PDF (.pdf) or modern PowerPoint (.pptx) and re-upload."
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"Unsupported file format: '{ext}'. Allowed formats are PDF (.pdf), PowerPoint (.pptx), Markdown (.md), and Text (.txt)."
        return True, ext

    @staticmethod
    def extract_text_from_file(file_bytes: bytes, filename: str) -> Tuple[str, List[str]]:
        """
        Extracts raw text while performing file integrity, password, and readability checks.
        (REQ_04, TC-10, TC-11, TC-12, Exception 1.0.E.2).
        """
        ext = os.path.splitext(filename)[1].lower()
        warnings = []

        if len(file_bytes) == 0:
            raise ValueError("The uploaded file is empty (0 bytes) and contains no readable text.")

        if ext == ".pptx":
            import zipfile
            import io
            import xml.etree.ElementTree as ET

            try:
                z = zipfile.ZipFile(io.BytesIO(file_bytes))
            except Exception as e:
                raise ValueError(f"Corrupted or invalid PowerPoint presentation: {str(e)}")

            slide_files = [f for f in z.namelist() if f.startswith("ppt/slides/slide") and f.endswith(".xml")]
            if not slide_files:
                raise ValueError("The presentation contains no slides or readable text.")

            # Sort slides numerically (slide1.xml, slide2.xml, ...)
            def slide_num(s):
                m = re.search(r'slide(\d+)\.xml', s)
                return int(m.group(1)) if m else 0

            slide_files = sorted(slide_files, key=slide_num)
            slides_text = []

            for sfile in slide_files:
                try:
                    xml_data = z.read(sfile)
                    tree = ET.fromstring(xml_data)
                    slide_paras = []
                    for elem in tree.iter():
                        if elem.tag.endswith('}p'):
                            p_texts = [t.text for t in elem.iter() if (t.tag.endswith('}t') or t.tag.endswith('}fld')) and t.text]
                            p_str = "".join(p_texts).strip()
                            if p_str:
                                slide_paras.append(p_str)
                    if slide_paras:
                        slides_text.append(". ".join(slide_paras) + ".")
                    else:
                        slide_words = [elem.text for elem in tree.iter() if elem.tag.endswith('}t') and elem.text]
                        if slide_words:
                            slides_text.append(" ".join(slide_words) + ".")
                except Exception:
                    continue

            # Also inspect speaker notes slides (ppt/notesSlides/)
            notes_files = [f for f in z.namelist() if f.startswith("ppt/notesSlides/notesSlide") and f.endswith(".xml")]
            for nfile in notes_files:
                try:
                    xml_data = z.read(nfile)
                    tree = ET.fromstring(xml_data)
                    note_words = [elem.text for elem in tree.iter() if elem.tag.endswith('}t') and elem.text]
                    if note_words:
                        slides_text.append(" ".join(note_words) + ".")
                except Exception:
                    pass

            full_text = "\n\n".join(slides_text).strip()
            if not full_text:
                raise ValueError("The presentation contains slides but no readable text.")
            return full_text, warnings

        elif ext == ".pdf":
            # 1. Integrity check: reject executable or fake files renamed to .pdf (TC-10)
            if not file_bytes.startswith(b"%PDF-"):
                # Check for PE executable headers (MZ) or ELF
                if file_bytes.startswith(b"MZ") or file_bytes.startswith(b"\x7fELF"):
                    raise ValueError("File integrity check failed: Executable file disguised as PDF. File rejected.")
                raise ValueError("File integrity check failed: Invalid or corrupted PDF header.")

            # 2. PDF Parsing via pypdf
            import io
            stream = io.BytesIO(file_bytes)
            try:
                reader = PdfReader(stream)
            except Exception as e:
                raise ValueError(f"Corrupted PDF file could not be read: {str(e)}")

            # Check password protection (TC-11, Exception 1.0.E.2)
            if reader.is_encrypted:
                try:
                    # Attempt empty password decrypt
                    decrypted = reader.decrypt("")
                    if not decrypted:
                        raise ValueError("Password-protected PDF detected: The file requires a password to open.")
                except Exception:
                    raise ValueError("Password-protected PDF detected: The file requires a password to open.")

            text_parts = []
            try:
                for page_idx, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            except Exception as e:
                raise ValueError(f"Failed to extract text from PDF: {str(e)}")

            full_text = "\n\n".join(text_parts).strip()
            # 3. Check for scanned image-only PDF with no text layer (TC-12)
            if not full_text:
                raise ValueError("The uploaded PDF contains no readable text layer (scanned image or empty). OCR is required.")

            return full_text, warnings

        elif ext in [".txt", ".md"]:
            try:
                full_text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    full_text = file_bytes.decode("latin-1")
                except Exception:
                    raise ValueError("The text file could not be decoded. Ensure valid UTF-8 encoding.")

            if not full_text.strip():
                raise ValueError("The uploaded text file contains no readable text.")

            return full_text, warnings

        else:
            raise ValueError(f"Unsupported file format: {ext}")

    @staticmethod
    def chunk_text_semantically(full_text: str, chunk_size: int = 500, overlap: int = 100) -> List[Dict[str, Any]]:
        """
        Splits text into semantic units with overlap between adjacent chunks (REQ_02, TC-17).
        Incorporates AST code and LaTeX equation parsing.
        """
        # Run AST parser first to isolate code blocks and LaTeX expressions
        ast_chunks, warnings = ASTParser.parse_text_blocks(full_text)

        final_chunks = []
        for idx, block in enumerate(ast_chunks):
            content = block.get("content", "")
            if block.get("type") == "ast_code":
                # Preserve entire code block as a coherent unit with indentation intact (REQ_02, TC-22)
                final_chunks.append({
                    "chunk_id": f"chunk_ast_{idx}",
                    "content": content,
                    "type": "ast_code",
                    "language": block.get("language", "code"),
                    "ast_nodes": block.get("ast_nodes", []),
                    "has_code": True,
                    "has_latex": False
                })
            else:
                # Standard or LaTeX text chunking with overlap
                paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
                current_chunk = ""
                chunk_num = 0

                for para in paragraphs:
                    if len(current_chunk) + len(para) < chunk_size:
                        current_chunk = (current_chunk + "\n\n" + para).strip()
                    else:
                        if current_chunk:
                            final_chunks.append({
                                "chunk_id": f"chunk_txt_{idx}_{chunk_num}",
                                "content": current_chunk,
                                "type": block.get("type", "text"),
                                "ast_nodes": block.get("ast_nodes", []),
                                "has_code": False,
                                "has_latex": block.get("has_latex", False)
                            })
                            chunk_num += 1
                            # Add overlap from previous paragraph if available
                            current_chunk = current_chunk[-overlap:] + "\n\n" + para if len(current_chunk) > overlap else para
                        else:
                            current_chunk = para

                if current_chunk:
                    final_chunks.append({
                        "chunk_id": f"chunk_txt_{idx}_{chunk_num}",
                        "content": current_chunk,
                        "type": block.get("type", "text"),
                        "ast_nodes": block.get("ast_nodes", []),
                        "has_code": False,
                        "has_latex": block.get("has_latex", False)
                    })

        # Ensure every chunk has an identifier
        for i, c in enumerate(final_chunks):
            c["chunk_id"] = f"chunk_{i+1}"

        return final_chunks

    @staticmethod
    def discover_subtopics(full_text: str, filename: str) -> List[str]:
        """Discovers distinct sub-topics from markdown headers, numbered sections, or content keywords."""
        topics = []
        # Check markdown headings (# Topic)
        header_matches = re.findall(r'^(?:#{1,3})\s+(.+)$', full_text, re.MULTILINE)
        if header_matches:
            topics = [h.strip() for h in header_matches if len(h.strip()) > 3]

        # Check numbered sections (1. Overfitting, Section 2:)
        if not topics:
            sec_matches = re.findall(r'^(?:(?:\d+\.|\bSection\s+\d+:?))\s+([^\n\r]+)', full_text, re.MULTILINE)
            if sec_matches:
                topics = [s.strip() for s in sec_matches if len(s.strip()) > 3]

        # Fallback to key concepts detected in text
        if not topics:
            base_name = os.path.splitext(filename)[0].replace("_", " ").title()
            topics = [f"{base_name} - Core Concepts", f"{base_name} - Advanced Applications"]

        # Deduplicate while preserving order
        unique_topics = []
        for t in topics:
            if t not in unique_topics:
                unique_topics.append(t)

        return unique_topics[:6] # Return up to 6 structured topics

    @staticmethod
    def check_duplicate(user_id: str, title: str) -> Optional[Dict[str, Any]]:
        """Checks if a document with the same title already exists for this student (REQ_05, TC-13)."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT doc_id, title, version, chunk_count FROM documents WHERE user_id = ? AND title = ?",
                       (user_id, title))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    @classmethod
    def ingest_document(
        cls,
        user_id: str,
        filename: str,
        file_bytes: bytes,
        title: Optional[str] = None,
        overwrite: bool = False,
        create_new_version: bool = False
    ) -> Dict[str, Any]:
        """
        Coordinates full document ingestion: validation, extraction, chunking, topic discovery,
        vector storage, and database persistence (UC-1, UC-7).
        """
        start_time = time.time()
        # 1. Format validation
        valid, ext = cls.validate_file_format(filename)
        if not valid:
            raise ValueError(ext)

        # Document title
        doc_title = title or os.path.splitext(filename)[0]

        # 2. Duplicate Detection (REQ_05, TC-13)
        existing = cls.check_duplicate(user_id, doc_title)
        version = 1
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"

        if existing and not overwrite and not create_new_version:
            # Prompt user to overwrite or version (TC-13)
            return {
                "status": "duplicate_prompt",
                "message": f"Document '{doc_title}' already exists. Please choose to Overwrite or Create a New Version.",
                "existing_doc": existing
            }

        if existing and overwrite:
            # Replace existing vectors and DB entries (TC-14, Alt Flow 1.1)
            doc_id = existing["doc_id"]
            vector_store.wipe_collection(user_id, doc_id)
            conn = get_connection()
            conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
            conn.execute("DELETE FROM topics WHERE doc_id = ?", (doc_id,))
            conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
            conn.commit()
            conn.close()
            version = existing.get("version", 1)

        elif existing and create_new_version:
            # Create a new version with distinct ID (TC-15)
            version = existing.get("version", 1) + 1
            doc_title = f"{doc_title} (v{version})"
            doc_id = f"doc_{uuid.uuid4().hex[:8]}"

        # 3. Text Extraction with integrity & safety checks
        raw_text, warnings = cls.extract_text_from_file(file_bytes, filename)

        # 4. Semantic & AST Chunking (REQ_02, TC-17)
        chunks = cls.chunk_text_semantically(raw_text)
        for i, c in enumerate(chunks):
            c["chunk_id"] = f"chk_{doc_id}_{i+1}"

        # 5. Topic Discovery
        subtopics = cls.discover_subtopics(raw_text, filename)

        # 6. Store Vector Embeddings in Chroma DB local store (REQ_03, UC-7)
        try:
            stored_count = vector_store.store_embeddings(user_id, doc_id, chunks)
        except Exception as e:
            # Storage failure exception rollback (Exception 7.0.E.1 / TC-21)
            logger.error("Rolling back document ingestion due to Chroma DB storage error: %s", e)
            raise OSError(f"Vector Database Storage Failure: {str(e)}")

        # 7. Relational Database Persistence
        conn = get_connection()
        cursor = conn.cursor()
        now = time.time()

        cursor.execute('''
        INSERT INTO documents (doc_id, user_id, title, file_type, raw_text, version, chunk_count, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (doc_id, user_id, doc_title, ext, raw_text, version, len(chunks), now))

        # Insert topics with sequential ordering (REQ_12, TC-44)
        for order_idx, tname in enumerate(subtopics):
            topic_id = f"top_{uuid.uuid4().hex[:8]}"
            cursor.execute('''
            INSERT INTO topics (topic_id, doc_id, user_id, name, order_index, mastery_status, created_at)
            VALUES (?, ?, ?, ?, ?, 'Unmastered', ?)
            ''', (topic_id, doc_id, user_id, tname, order_idx, now))

        # Insert chunk records
        for chk in chunks:
            cursor.execute('''
            INSERT INTO chunks (chunk_id, doc_id, user_id, content, chunk_type, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (chk["chunk_id"], doc_id, user_id, chk["content"], chk.get("type", "text"),
                  str(chk.get("ast_nodes", [])), now))

        conn.commit()
        conn.close()

        elapsed = time.time() - start_time
        logger.info("Ingestion completed in %.3fs for doc '%s' (%d chunks, %d topics)",
                    elapsed, doc_title, len(chunks), len(subtopics))

        return {
            "status": "success",
            "doc_id": doc_id,
            "title": doc_title,
            "version": version,
            "chunk_count": len(chunks),
            "topics": subtopics,
            "warnings": warnings,
            "processing_time_seconds": round(elapsed, 3)
        }
