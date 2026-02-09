from pathlib import Path
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from qdrant_client.models import VectorParams, Distance
import sys

import json
import uuid

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    TMP_TXT_DIR, QDRANT_HOST, QDRANT_PORT, VECTOR_DISTANCE
)

# ------------------------
# Konfigurácia
# ------------------------
TXT_DIR = TMP_TXT_DIR
VECTOR_COLLECTION = "zmluvy"  # názov kolekcie v Qdrant

# Model embeddingov
embed_model = SentenceTransformer("all-MiniLM-L6-v2")  # malý, rýchly model

# Qdrant client
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# Vytvorenie kolekcie, ak ešte neexistuje
if not client.collection_exists(VECTOR_COLLECTION):
    distance = Distance.COSINE if VECTOR_DISTANCE == "cosine" else Distance.EUCLID
    client.create_collection(
        collection_name=VECTOR_COLLECTION,
        vectors_config=VectorParams(
            size=embed_model.get_sentence_embedding_dimension(),
            distance=distance,
        ),
    )

# ------------------------
# Funkcia na ingest
# ------------------------
def ingest_txt_file(txt_path: Path):
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Rozdelenie na chunks (napr. po 500 tokenov/slov)
    CHUNK_SIZE = 500
    words = text.split()
    chunks = [" ".join(words[i:i + CHUNK_SIZE]) for i in range(0, len(words), CHUNK_SIZE)]

    points = []
    for i, chunk in enumerate(chunks):
        embedding = embed_model.encode(chunk).tolist()
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),   # ✅ platné ID
                vector=embedding,
                payload={
                    "file": txt_path.name,
                    "chunk_index": i
                }
            )
        )

    # Uloženie do Qdrant
    client.upsert(collection_name=VECTOR_COLLECTION, points=points)

# ------------------------
# Hlavná funkcia
# ------------------------
def main():
    txt_files = list(TXT_DIR.glob("*.txt"))
    print(f"Nájdené TXT súbory: {len(txt_files)}")

    for txt_file in tqdm(txt_files, desc="Ingest TXT do Qdrant"):
        ingest_txt_file(txt_file)

if __name__ == "__main__":
    main()
