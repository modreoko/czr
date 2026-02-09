from qdrant_client.models import Filter, FieldCondition, MatchText
from fastapi import FastAPI
from pydantic import BaseModel
import requests
from qdrant_client import QdrantClient
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    QDRANT_HOST, QDRANT_PORT, COLLECTION_ZMLUVY,
    OLLAMA_EMBED_URL, EMBED_MODEL, CHAT_MODEL
)

app = FastAPI()

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

class Question(BaseModel):
    question: str

def embed(text: str):
    r = requests.post(
        OLLAMA_EMBED_URL,
        json={"model": EMBED_MODEL, "prompt": text}
    )
    return r.json()["embedding"]

import re

def detect_filter_terms(question: str):
    """
    Vráti zoznam výrazov, ktoré vyzerajú ako mená / obce / organizácie
    """
    terms = []

    # veľké písmená + medzery (Mesto Trenčín, Erich Vladár)
    candidates = re.findall(r"[A-ZÁČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ][a-záčďéíĺľňóôŕšťúýž]+(?:\s+[A-ZÁČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ][a-záčďéíĺľňóôŕšťúýž]+)+", question)

    for c in candidates:
        terms.append(c.strip())

    return terms

def extract_relevant_sentence(text, question):
    keywords = [
        w.lower() for w in re.findall(r"\w+", question) if len(w) > 4
    ]

    sentences = re.split(r"(?<=[.!?])\s+", text)

    for s in sentences:
        s_low = s.lower()
        if any(k in s_low for k in keywords):
            return s.strip()

    return sentences[0].strip() if sentences else text[:200]

@app.post("/ask")
def ask(q: Question):
    question = q.question

    # 1️⃣ detekcia mien / obcí
    terms = detect_filter_terms(question)

    query_vector = embed(question)

    query_filter = None

    if terms:
        conditions = []
        for t in terms:
            conditions.append(FieldCondition(key="zs1", match=MatchText(text=t)))
            conditions.append(FieldCondition(key="zs2", match=MatchText(text=t)))

        query_filter = Filter(should=conditions)

    # 2️⃣ Qdrant dotaz
    hits = client.query_points(
        collection_name=COLLECTION_ZMLUVY,
        query=query_vector,
        query_filter=query_filter,
        limit=10
    ).points

    if not hits:
        return {
            "answer": "V dostupných zmluvách sa informácia nenachádza."
        }

    # 3️⃣ deduplikácia podľa zmluvy
    seen = set()
    context_blocks = []

    for h in hits:
        p = h.payload
        key = (p["zmluva_id"], p["text"][:100])

        if key in seen:
            continue

        seen.add(key)

        context_blocks.append(f"""
ZMLUVA ID: {p.get('zmluva_id')}
DÁTUM: {p.get('datum')}
ZMLUVNÉ STRANY: {p.get('zs1')} | {p.get('zs2')}
ZDROJ: {p.get('pdf')}
CITÁCIA:
"{p.get('text').strip()}"
""".strip())

    context = "\n\n---\n\n".join(context_blocks)

    prompt = f"""
Si právny asistent.

PRAVIDLÁ:
- Odpovedaj výlučne z poskytnutých citácií.
- Nevymýšľaj.
- Ak odpoveď nevyplýva z textov, odpíš presne:
  "V dostupných zmluvách sa informácia nenachádza."

FORMÁT ODPOVEDE:
Pre každú zmluvu:

ZMLUVA ID:
DÁTUM:
ZMLUVNÉ STRANY:
SUMA ZMLUVY:
SUMA SPOLU:
CITÁCIA:
ZDROJ:

TEXTY:
{context}

OTÁZKA:
{question}
"""

    r = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": CHAT_MODEL,
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    )

    return {
        "answer": r.json()["response"]
    }
