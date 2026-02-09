import uuid
import requests
from pathlib import Path
from tqdm import tqdm
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    TMP_TXT_DIR, COLLECTION_ZMLUVY, CHUNK_SIZE, OLLAMA_EMBED_URL, EMBED_MODEL,
    QDRANT_HOST, QDRANT_PORT, VECTOR_SIZE, VECTOR_DISTANCE, REQUEST_TIMEOUT, UPSERT_BATCH_SIZE
)
from ingest.load_xml_metadata import load_metadata

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

txt_files = list(TXT_DIR.glob("*.txt"))
print(f"📄 Nájdené TXT súbory: {len(txt_files)}")  # 👀 LOG

points = []

for txt_file in tqdm(txt_files, desc="Ingestujem TXT"):
    pdf_name = txt_file.name.replace(".txt", ".pdf")

    print(f"\n📄 Spracúvam TXT: {txt_file.name}")  # 👀 LOG

    # nájdeme zmluvu podľa PDF
    zmluva = next(
        (c for c in contracts.values() if pdf_name in c["pdfs"]),
        None
    )

    if not zmluva:
        print(f"⚠️  Preskakujem – nenašiel som metadata pre PDF: {pdf_name}")  # 👀 LOG
        continue

    print(
        f"✅ ZMLUVA {zmluva['zmluva_id']} | "
        f"{zmluva.get('zs1', '')} × {zmluva.get('zs2', '')}"
    )  # 👀 LOG

    text = txt_file.read_text(encoding="utf-8", errors="ignore")

    chunks = chunk_text(text, CHUNK_SIZE)
    print(f"   → počet chunkov: {len(chunks)}")  # 👀 LOG

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
            print(f"   ⬆️  Uložených 50 chunkov do Qdrant")  # 👀 LOG
            points.clear()

if points:
    client.upsert(collection_name=COLLECTION, points=points)
    print(f"⬆️  Uložených posledných {len(points)} chunkov")  # 👀 LOG

print("✅ Metadata + hybrid ingest hotový")
