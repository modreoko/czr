"""
Centralized configuration for the zmluvy project.
All common settings used across the application are defined here.
"""

from pathlib import Path

# =========================
# DIRECTORY PATHS
# =========================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
XML_DIR = DATA_DIR / "xml"
XML_FILTERED_DIR = DATA_DIR / "xml_filtered"
TMP_PDF_DIR = DATA_DIR / "tmp_pdf"
TMP_TXT_DIR = DATA_DIR / "tmp_txt"

# Ensure directories exist
XML_DIR.mkdir(parents=True, exist_ok=True)
XML_FILTERED_DIR.mkdir(parents=True, exist_ok=True)
TMP_PDF_DIR.mkdir(parents=True, exist_ok=True)
TMP_TXT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# FILE PATHS
# =========================
ICO_FILE = BASE_DIR / "ico_list.txt"

# =========================
# QDRANT SETTINGS
# =========================
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

# Collection names
COLLECTION_ZMLUVY = "zmluvy_v2"

# Vector settings
VECTOR_SIZE = 768
VECTOR_DISTANCE = "cosine"

# =========================
# OLLAMA / LLM SETTINGS
# =========================
OLLAMA_HOST = "localhost"
OLLAMA_PORT = 11434
OLLAMA_CHAT_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/chat"
OLLAMA_EMBED_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/embeddings"

# Model names
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "qwen2.5:7b"

# =========================
# TEXT PROCESSING SETTINGS
# =========================
CHUNK_SIZE = 800
REQUEST_TIMEOUT = 60

# =========================
# CRZ DOWNLOAD SETTINGS
# =========================
CRZ_EXPORT_URL = "http://www.crz.gov.sk/export/{date}.zip"
CRZ_PDF_BASE_URL = "https://www.crz.gov.sk/data/att/{filename}"
DOWNLOAD_TIMEOUT = 30

# =========================
# BATCH SETTINGS
# =========================
UPSERT_BATCH_SIZE = 50
