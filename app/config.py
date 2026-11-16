import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.environ.get("AUTOQUIZ_DB_PATH", str(BASE_DIR / "autoquiz.db"))
VECTOR_DIR = os.environ.get("AUTOQUIZ_VECTOR_DIR", str(BASE_DIR / "vector_store_data"))
SECRET_KEY = os.environ.get("AUTOQUIZ_SECRET_KEY", "autoquiz-super-secret-key-nitw-2026")

# Algorithm constants as per SRS & Vision doc
RETENTION_THRESHOLD_DAYS_DEFAULT = 7
MIN_QUESTIONS_PER_LOOP = 3
MAX_QUESTIONS_PER_LOOP = 5
MASTERY_SCORE_TARGET = 100.0
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".pptx"}

