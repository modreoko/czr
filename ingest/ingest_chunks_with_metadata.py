import uuid
import requests
from pathlib import Path
from tqdm import tqdm
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import sys
from datetime import datetime
import logging

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    TMP_TXT_DIR, COLLECTION_ZMLUVY, CHUNK_SIZE, OLLAMA_EMBED_URL, EMBED_MODEL,
    QDRANT_HOST, QDRANT_PORT, VECTOR_SIZE, VECTOR_DISTANCE, REQUEST_TIMEOUT, UPSERT_BATCH_SIZE
)
from ingest.load_xml_metadata import load_metadata
from ingest.pipeline_state import load_start_date
from ingest.logger import get_logger

# Get logger
logger = get_logger()

# =========================
# KONFIGURÁCIA
# =========================

TXT_DIR = TMP_TXT_DIR
COLLECTION = COLLECTION_ZMLUVY

EMBED_URL = OLLAMA_EMBED_URL

# =========================
# NAČÍTANIE METADÁT
# =========================

contracts = load_metadata()

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

if not client.collection_exists(COLLECTION):
    distance = Distance.COSINE if VECTOR_DISTANCE == "cosine" else Distance.EUCLID
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=distance)
    )

# =========================
# FUNKCIE
# =========================

def chunk_text(text, size):
    return [text[i:i + size] for i in range(0, len(text), size)]

def embed(text: str):
    r = requests.post(
        EMBED_URL,
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=REQUEST_TIMEOUT
    )
    r.raise_for_status()
    return r.json()["embedding"]

# =========================
# INGEST
# =========================

# Načítanie START_DATE
start_date = load_start_date()
if not start_date:
    logger.warning("⚠️ START_DATE nenájdený, ingestujem všetky TXT súbory")
    start_date = datetime.min

logger.info(f"📅 Ingestujeme iba zmluvy od: {start_date.strftime('%Y-%m-%d')}")

txt_files = list(TXT_DIR.glob("*.txt"))
logger.info(f"📄 Nájdené TXT súbory: {len(txt_files)}")

points = []

for txt_file in tqdm(txt_files, desc="Ingestujem TXT"):
    pdf_name = txt_file.name.replace(".txt", ".pdf")

    logger.debug(f"\n📄 Spracúvam TXT: {txt_file.name}")

    # nájdeme zmluvu podľa PDF
    zmluva = next(
        (c for c in contracts.values() if pdf_name in c["pdfs"]),
        None
    )

    if not zmluva:
        logger.debug(f"⚠️  Preskakujem – nenašiel som metadata pre PDF: {pdf_name}")
        continue

    # Filtrovanie podľa START_DATE
    if zmluva.get("datum"):
        try:
            zmluva_date = datetime.strptime(zmluva["datum"], "%Y-%m-%d")
            if zmluva_date < start_date:
                logger.debug(f"⏭️  Preskakujem – zmluva je stará ({zmluva['datum']} < {start_date.strftime('%Y-%m-%d')})")
                continue
        except ValueError:
            # Ak dátum nemá správny formát, spracúvam zmluvu
            pass

    logger.info(
        f"✅ ZMLUVA {zmluva['zmluva_id']} | "
        f"{zmluva.get('zs1', '')} × {zmluva.get('zs2', '')}"
    )

    text = txt_file.read_text(encoding="utf-8", errors="ignore")

    chunks = chunk_text(text, CHUNK_SIZE)
    logger.debug(f"   → počet chunkov: {len(chunks)}")

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

        vector = embed(hybrid_text)

        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
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

        if len(points) >= 50:
            client.upsert(collection_name=COLLECTION, points=points)
            logger.debug(f"   ⬆️  Uložených 50 chunkov do Qdrant")
            points.clear()

if points:
    client.upsert(collection_name=COLLECTION, points=points)
    logger.info(f"⬆️  Uložených posledných {len(points)} chunkov")

logger.info("✅ Metadata + hybrid ingest hotový")
sys.exit(0)
