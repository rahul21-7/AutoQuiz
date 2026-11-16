import os
import sqlite3
import time
import logging
from typing import Optional, List, Dict, Any
from app.config import DB_PATH
from app.security import hash_password

logger = logging.getLogger("AUTOQUIZ.DB")

# In-memory retry queue for database operations that encounter timeouts (Exception 9.0.E.1 / TC-38)
_OFFLINE_WRITE_QUEUE: List[Dict[str, Any]] = []

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    target_path = db_path or os.environ.get("AUTOQUIZ_DB_PATH") or DB_PATH
    conn = sqlite3.connect(target_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: Optional[str] = None):
    """Initializes SQLite database tables and indexes as specified in AutoQuiz SRS and Call Graph."""
    target_path = db_path or os.environ.get("AUTOQUIZ_DB_PATH") or DB_PATH
    conn = get_connection(target_path)
    cursor = conn.cursor()

    # Users Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'student',
        created_at REAL NOT NULL
    )''')

    # Documents Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS documents (
        doc_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        title TEXT NOT NULL,
        file_type TEXT NOT NULL,
        raw_text TEXT NOT NULL,
        version INTEGER NOT NULL DEFAULT 1,
        chunk_count INTEGER NOT NULL DEFAULT 0,
        created_at REAL NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )''')

    # Topics Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS topics (
        topic_id TEXT PRIMARY KEY,
        doc_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        name TEXT NOT NULL,
        order_index INTEGER NOT NULL DEFAULT 0,
        mastery_status TEXT NOT NULL DEFAULT 'Unmastered',
        last_mastered_at REAL,
        attempt_count INTEGER NOT NULL DEFAULT 0,
        score_stability REAL NOT NULL DEFAULT 1.0,
        created_at REAL NOT NULL,
        FOREIGN KEY (doc_id) REFERENCES documents(doc_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )''')

    # Chunks Table (persisted semantic chunks with AST metadata)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chunks (
        chunk_id TEXT PRIMARY KEY,
        doc_id TEXT NOT NULL,
        topic_id TEXT,
        user_id TEXT NOT NULL,
        content TEXT NOT NULL,
        chunk_type TEXT NOT NULL,
        metadata_json TEXT NOT NULL,
        created_at REAL NOT NULL,
        FOREIGN KEY (doc_id) REFERENCES documents(doc_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )''')

    # Quiz Sessions Table (for session resumption and continuity - SRS 5.4, TC-45, TC-47)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS quiz_sessions (
        session_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        topic_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'In Progress',
        current_question_index INTEGER NOT NULL DEFAULT 0,
        questions_json TEXT NOT NULL,
        answers_json TEXT NOT NULL DEFAULT '[]',
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (topic_id) REFERENCES topics(topic_id)
    )''')

    # Attempts Table (REQ_13, Call Graph & Test Cases)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attempts (
        attempt_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        topic_id TEXT NOT NULL,
        session_id TEXT,
        score REAL NOT NULL,
        confidence TEXT NOT NULL,
        is_first_attempt INTEGER NOT NULL DEFAULT 1,
        high_conf_count INTEGER NOT NULL DEFAULT 0,
        med_conf_count INTEGER NOT NULL DEFAULT 0,
        low_conf_count INTEGER NOT NULL DEFAULT 0,
        details_json TEXT,
        timestamp REAL NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (topic_id) REFERENCES topics(topic_id)
    )''')

    # user_scores Table (Preserved from report source code pages 51, 98)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        topic TEXT NOT NULL,
        score INTEGER NOT NULL,
        feedback TEXT
    )''')

    # Syllabus Taxonomy Table (UC-10: Admin syllabus management)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS taxonomy (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_name TEXT NOT NULL UNIQUE,
        description TEXT,
        parent_id INTEGER,
        order_index INTEGER DEFAULT 0
    )''')

    # Spaced Repetition Audit Logs Table (REQ_14, TC-58)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS decay_audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        executed_at REAL NOT NULL,
        topics_audited INTEGER NOT NULL,
        decayed_topics_count INTEGER NOT NULL,
        log_message TEXT
    )''')

    # Performance Indexing (Solving Fishbone Diagram 2 'Missing Table Indexes' bottlenecks)
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_attempts_user_topic ON attempts(user_id, topic_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_topics_user_doc ON topics(user_id, doc_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_chunks_topic ON chunks(topic_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user_status ON quiz_sessions(user_id, status)')

    conn.commit()

    # Seed Default Users if not exist
    seed_users = [
        ("24CSB1A12", "Dasari Rahul", "secret_pass", "student"),
        ("24CSB1A13", "Devarapaga Surya Teja", "student_pass_13", "student"),
        ("24CSB1A14", "Dhruv Garg", "student_pass_14", "student"),
        ("Student_A", "Student A", "student_pass_a", "student"),
        ("Student_B", "Student B", "student_pass_b", "student"),
        ("admin", "Course Instructor / Admin", "admin_pass_2026", "admin")
    ]
    for uid, name, pwd, role in seed_users:
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (uid,))
        if not cursor.fetchone():
            hsh, salt = hash_password(pwd)
            cursor.execute(
                "INSERT INTO users (user_id, name, password_hash, salt, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (uid, name, hsh, salt, role, time.time())
            )
    conn.commit()

    # Seed initial syllabus taxonomy if empty (UC-10)
    cursor.execute("SELECT COUNT(*) as cnt FROM taxonomy")
    if cursor.fetchone()["cnt"] == 0:
        initial_topics = [
            ("Machine Learning Foundations", "Core definitions of supervised and unsupervised learning", 0),
            ("Overfitting & Regularization", "Sign of overfitting, validation sets, and dropouts", 1),
            ("Neural Architectures", "Layers, activation functions, and gradient backpropagation", 2)
        ]
        for tname, desc, idx in initial_topics:
            cursor.execute("INSERT INTO taxonomy (topic_name, description, order_index) VALUES (?, ?, ?)",
                           (tname, desc, idx))
        conn.commit()

    conn.close()
    logger.info("AutoQuiz database initialized successfully with complete relational schema and indexes.")

def queue_attempt_write(attempt_data: Dict[str, Any]):
    """Queues an attempt write if a database lock or timeout occurs (Exception 9.0.E.1 / TC-38)."""
    _OFFLINE_WRITE_QUEUE.append(attempt_data)
    logger.warning("Database write queued for retry: %s", attempt_data.get("attempt_id"))

def process_write_queue(db_path: str = DB_PATH) -> int:
    """Processes any queued attempt writes once database connectivity is restored (TC-38)."""
    if not _OFFLINE_WRITE_QUEUE:
        return 0
    conn = get_connection(db_path)
    cursor = conn.cursor()
    processed = 0
    while _OFFLINE_WRITE_QUEUE:
        item = _OFFLINE_WRITE_QUEUE.pop(0)
        # Check if already inserted to prevent duplicates (TC-38)
        cursor.execute("SELECT attempt_id FROM attempts WHERE attempt_id = ?", (item["attempt_id"],))
        if not cursor.fetchone():
            cursor.execute('''
            INSERT INTO attempts (
                attempt_id, user_id, topic_id, session_id, score, confidence,
                is_first_attempt, high_conf_count, med_conf_count, low_conf_count,
                details_json, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item["attempt_id"], item["user_id"], item["topic_id"], item.get("session_id"),
                item["score"], item["confidence"], item.get("is_first_attempt", 1),
                item.get("high_conf_count", 0), item.get("med_conf_count", 0), item.get("low_conf_count", 0),
                item.get("details_json", "{}"), item.get("timestamp", time.time())
            ))
            processed += 1
    conn.commit()
    conn.close()
    return processed
