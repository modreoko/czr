import requests
import hashlib
import uuid
from pathlib import Path
from tqdm import tqdm
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import sys
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    TMP_TXT_DIR, COLLECTION_ZMLUVY, CHUNK_SIZE, OLLAMA_EMBED_URL, EMBED_MODEL,
    QDRANT_HOST, QDRANT_PORT, VECTOR_SIZE, VECTOR_DISTANCE, REQUEST_TIMEOUT, UPSERT_BATCH_SIZE
)
from ingest.load_xml_metadata import load_metadata
from ingest.pipeline_state import load_start_date
from ingest.logger import get_logger

logger = get_logger()

# =========================
# CONFIG
# =========================

TXT_DIR = TMP_TXT_DIR
COLLECTION = COLLECTION_ZMLUVY
EMBED_URL = OLLAMA_EMBED_URL

# =========================
# HELPERS
# =========================

def normalize(text: str) -> str:
    return " ".join(text.split()).strip()


def chunk_id(text: str) -> str:
    # Generate deterministic UUID from text hash
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, text))


def chunk_text(text, size):
    return [text[i:i + size] for i in range(0, len(text), size)]


# =========================
# EMBEDDING (BATCH)
# =========================

def _try_ollama_embedding(text: str):
    candidates = [
        EMBED_URL,
        EMBED_URL.rstrip("/").replace("/api/embeddings", "/api/embed"),
        EMBED_URL.rstrip("/").replace("/api/embeddings", "/embeddings"),
    ]

    last_exception = None

    for url in candidates:
        try:
            r = requests.post(
                url,
                json={
                    "model": EMBED_MODEL,
                    "prompt": text
                },
                timeout=REQUEST_TIMEOUT
            )

            if r.status_code >= 400:
                last_exception = f"HTTP {r.status_code}: {r.text}"
                continue

            r.raise_for_status()

            data = r.json()

            if "embedding" in data:
                return data["embedding"]

            if "data" in data and len(data["data"]) > 0:
                return data["data"][0]["embedding"]

            raise ValueError(f"Unknown response format: {data}")

        except Exception as e:
            last_exception = e
            continue

    raise RuntimeError(
        f"Failed to generate embedding using Ollama. Tried endpoints: {candidates}. Last error: {last_exception}"
    )


def embed_batch(texts: list[str]):
    """
    Embed multiple texts individually.
    Ollama API expects one text per request.
    """
    embeddings = []

    for text in texts:
        try:
            embedding = _try_ollama_embedding(text)
            embeddings.append(embedding)
        except Exception as e:
            logger.error(f"[ERROR] Error embedding text: {e}")
            raise

    return embeddings


# =========================
# INIT
# =========================

contracts = load_metadata()

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

try:
    if not client.collection_exists(COLLECTION):
        distance = Distance.COSINE if VECTOR_DISTANCE == "cosine" else Distance.EUCLID
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=distance)
        )
except Exception as e:
    logger.error(f"[ERROR] Cannot connect to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}. Make sure Qdrant is running and accessible.")
    logger.error(f"[ERROR] {e}")
    sys.exit(1)

# =========================
# INGEST STATE
# =========================

start_date = load_start_date()
if not start_date:
    logger.warning("[WARNING] START_DATE nenajdeny, ingestujem vsetky TXT subory")
    start_date = datetime.min

logger.info(f"[DATE] Ingestujeme od: {start_date.strftime('%Y-%m-%d')}")

txt_files = list(TXT_DIR.glob("*.txt"))
logger.info(f"[FILE] Najdene TXT subory: {len(txt_files)}")

# =========================
# MAIN INGEST
# =========================

points = []

for txt_file in tqdm(txt_files, desc="Ingestujem TXT"):

    pdf_name = txt_file.name.replace(".txt", ".pdf")

    zmluva = next(
        (c for c in contracts.values() if pdf_name in c["pdfs"]),
        None
    )

    if not zmluva:
        continue

    # date filter
    if zmluva.get("datum"):
        try:
            zmluva_date = datetime.strptime(zmluva["datum"], "%Y-%m-%d")
            if zmluva_date < start_date:
                continue
        except ValueError:
            pass

    logger.info(
        f"[OK] ZMLUVA {zmluva['zmluva_id']} | "
        f"{zmluva.get('zs1', '')} x {zmluva.get('zs2', '')}"
    )

    text = txt_file.read_text(encoding="utf-8", errors="ignore")
    chunks = chunk_text(text, CHUNK_SIZE)

    batch_texts = []
    batch_meta = []

    for idx, chunk in enumerate(chunks):

        hybrid_text = f"""
ZMLUVNÉ STRANY:
{zmluva.get('zs1', '')}
{zmluva.get('zs2', '')}

NÁZOV ZMLUVY:
{zmluva.get('nazov', '')}

PREDMET ZMLUVY:
{zmluva.get('predmet', '')}

SUMA ZMLUVY:
{zmluva.get('suma_zmluva', '')}
SUMA SPOLU:
{zmluva.get('suma_spolu', '')}

TEXT ZMLUVY:
{chunk}
""".strip()

        batch_texts.append(normalize(hybrid_text))
        batch_meta.append((idx, chunk, pdf_name, zmluva))

    # =========================
    # EMBED + UPSERT BATCH
    # =========================

    if batch_texts:

        vectors = embed_batch(batch_texts)

        for (idx, chunk, pdf_name, zmluva), vector in zip(batch_meta, vectors):

            cid = chunk_id(chunk)

            points.append(
                PointStruct(
                    id=cid,
                    vector=vector,
                    payload={
                        "zmluva_id": zmluva["zmluva_id"],
                        "datum": zmluva["datum"],
                        "zs1": zmluva["zs1"],
                        "zs2": zmluva["zs2"],
                        "nazov": zmluva["nazov"],
                        "predmet": zmluva["predmet"],
                        "suma_zmluva": zmluva["suma_zmluva"],
                        "suma_spolu": zmluva["suma_spolu"],
                        "pdf": pdf_name,
                        "chunk": idx,
                        "text": chunk
                    }
                )
            )

        batch_texts.clear()
        batch_meta.clear()

    # =========================
    # UPSERT CONTROL
    # =========================

    if len(points) >= UPSERT_BATCH_SIZE:
        client.upsert(collection_name=COLLECTION, points=points)
        logger.info(f"[UP] Uložených {len(points)} chunkov")
        points.clear()

# =========================
# FINAL FLUSH
# =========================

if points:
    client.upsert(collection_name=COLLECTION, points=points)
    logger.info(f"[UP] Final batch: {len(points)} chunkov")

logger.info("[DONE] Ingest hotový")
sys.exit(0)