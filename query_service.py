"""
Shared query service for contract searches.
Can be used by CLI, FastAPI, and other interfaces.
Provides intelligent multi-strategy search and LLM response generation.
"""

import re
import requests
import json
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from pathlib import Path
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    OLLAMA_CHAT_URL, OLLAMA_EMBED_URL, EMBED_MODEL, CHAT_MODEL,
    COLLECTION_ZMLUVY, QDRANT_HOST, QDRANT_PORT, REQUEST_TIMEOUT
)


client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


# =====================
# EMBEDDING FUNKCIA
# =====================
def embed(text: str) -> list:
    """Generate embeddings for text using Ollama."""
    r = requests.post(
        OLLAMA_EMBED_URL,
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=REQUEST_TIMEOUT
    )
    r.raise_for_status()
    return r.json()["embedding"]


# =====================
# TEXT EXTRACTION FUNCTIONS
# =====================
def extract_contract_id(text: str) -> str:
    """
    Extract contract ID from question.
    Finds formats like:
    - zmluva ID 1234567
    - zmluvu id: 1234567
    - ID 1234567
    """
    match = re.search(r"\bID\s*([0-9]{4,10})\b", text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def extract_contract_party(text: str) -> str:
    """
    Extract contract party name from question.
    Finds names after 's' or 'so' (Slovak prepositions).
    Examples:
    - 's Samuel Budinský'
    - 'so Štefanom Žilinským'
    """
    pattern = r"\b(?:s|so)\s+([A-ZÁČĎÉÍĽŇÓÔŔŠŤÚÝŽ][\wáčďéíľňóôŕšťúýžÁČĎÉÍĽŇÓÔŔŠŤÚÝŽ]*(?:\s[\wáčďéíľňóôŕšťúýžÁČĎÉÍĽŇÓÔŔŠŤÚÝŽ]+)*)\b"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return None


# =====================
# SEARCH STRATEGIES
# =====================
def search_by_contract_id(contract_id: str, limit: int = 50) -> list:
    """Search contracts by exact ID."""
    points, _ = client.scroll(
        collection_name=COLLECTION_ZMLUVY,
        scroll_filter=qm.Filter(
            must=[
                qm.FieldCondition(
                    key="zmluva_id",
                    match=qm.MatchValue(value=contract_id)
                )
            ]
        ),
        limit=limit
    )
    return points


def search_by_party(party_name: str, limit: int = 50) -> list:
    """Search contracts by party name."""
    points, _ = client.scroll(
        collection_name=COLLECTION_ZMLUVY,
        scroll_filter=qm.Filter(
            should=[
                qm.FieldCondition(key="zs1", match=qm.MatchValue(value=party_name)),
                qm.FieldCondition(key="zs2", match=qm.MatchValue(value=party_name)),
            ]
        ),
        limit=limit
    )
    return points


def search_by_embedding(question: str, limit: int = 50) -> list:
    """Search contracts using semantic search (embeddings)."""
    query_vector = embed(question)
    hits = client.query_points(
        collection_name=COLLECTION_ZMLUVY,
        query=query_vector,
        with_payload=True,
        limit=limit
    ).points
    return hits


# =====================
# MAIN QUERY FUNCTION
# =====================
def search_contracts(question: str, limit: int = 50, verbose: bool = False) -> dict:
    """
    Multi-strategy contract search.
    
    Strategy:
    1. Try extracting and searching by contract ID
    2. Try extracting party name and searching by party
    3. Fall back to semantic (embedding) search
    
    Args:
        question: The user's question
        limit: Maximum number of results
        verbose: Print search strategy info
    
    Returns:
        Dict with hits, strategy, and metadata
    """
    
    # Try exact ID search first
    contract_id = extract_contract_id(question)
    if contract_id:
        if verbose:
            print(f"🔍 Strategy 1: Searching by contract ID: {contract_id}")
        hits = search_by_contract_id(contract_id, limit)
        return {
            "hits": hits,
            "strategy": "by_id",
            "contract_id": contract_id,
            "count": len(hits)
        }
    
    # Try party name search
    party_name = extract_contract_party(question)
    if party_name:
        if verbose:
            print(f"🔍 Strategy 2: Searching by party name: {party_name}")
        hits = search_by_party(party_name, limit)
        return {
            "hits": hits,
            "strategy": "by_party",
            "party_name": party_name,
            "count": len(hits)
        }
    
    # Fall back to semantic search
    if verbose:
        print(f"🧠 Strategy 3: Using semantic (embedding) search")
    hits = search_by_embedding(question, limit)
    return {
        "hits": hits,
        "strategy": "semantic",
        "count": len(hits)
    }


# =====================
# LLM RESPONSE GENERATION
# =====================
def generate_llm_response(question: str, hits: list) -> str:
    """
    Generate LLM response using Ollama chat API.
    Uses structured prompt with metadata and contract text.
    
    Args:
        question: The original question
        hits: List of contract hits from Qdrant
    
    Returns:
        LLM response text
    """
    
    if not hits:
        return "V dostupných zmluvách sa informácia nenachádza."
    
    # Use first hit for detailed response
    hit = hits[0]
    p = hit.payload
    
    context = f"""
ZMLUVA ID: {p.get('zmluva_id')}
DÁTUM: {p.get('datum')}
PREDMET: {p.get('predmet', 'neuvedený')}
SUMA: {p.get('suma_zmluva', 'neuvedená')}
PDF: https://www.crz.gov.sk/data/att/{p.get('pdf')}
ZMLUVNÉ STRANY:
 - {p.get('zs1')}
 - {p.get('zs2')}

TEXT:
{p.get('text')}
"""
    
    prompt = f"""
Si právny asistent pracujúci so zmluvami.

Používaj výhradne nasledujúce **metadáta** a text z prílohy ako zdroj odpovede.
Ak niečo nie je uvedené v metadátach, môžeš použiť text, ale nikdy nevymýšľaj nové informácie.

METADÁTA ZMLUVY:
ZMLUVA ID: {p.get('zmluva_id')}
DÁTUM: {p.get('datum')}
SUMA: {p.get('suma_zmluva', 'neuvedená')}
ZMLUVNÉ STRANY:
 - {p.get('zs1')}
 - {p.get('zs2')}
PREDMET: {p.get('predmet', 'neuvedený')}

TEXT ZMLUVY:
{p.get('text')}

OTÁZKA:
{question}

FORMÁT ODPOVEDE:
ZMLUVA ID: <id zmluvy>
DÁTUM: <dátum>
SUMA: <suma z metadát>
ZMLUVNÉ STRANY:
 - <strana 1>
 - <strana 2>
PDF: https://www.crz.gov.sk/data/att/{p.get('pdf')}
PREDMET ZMLUVY: <predmet z metadát>

"""
    
    response = requests.post(
        OLLAMA_CHAT_URL,
        json={
            "model": CHAT_MODEL,
            "messages": [
                {"role": "system", "content": "Si právny asistent pracujúci so zmluvami. Odpovedaj iba z textov."},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        },
        timeout=600
    )
    response.raise_for_status()
    
    return response.json().get("message", {}).get("content", "Chyba pri generovaní odpovede.")


def stream_llm_response(question: str, hits: list):
    """
    Stream LLM response from Ollama using chat API.
    Yields chunks of text as they arrive.
    
    Args:
        question: The original question
        hits: List of contract hits from Qdrant
    
    Yields:
        Text chunks from LLM
    """
    
    if not hits:
        yield "V dostupných zmluvách sa informácia nenachádza."
        return
    
    # Use first hit for detailed response
    hit = hits[0]
    p = hit.payload
    
    context = f"""
ZMLUVA ID: {p.get('zmluva_id')}
DÁTUM: {p.get('datum')}
PREDMET: {p.get('predmet', 'neuvedený')}
SUMA: {p.get('suma_zmluva', 'neuvedená')}
PDF: https://www.crz.gov.sk/data/att/{p.get('pdf')}
ZMLUVNÉ STRANY:
 - {p.get('zs1')}
 - {p.get('zs2')}

TEXT:
{p.get('text')}
"""
    
    prompt = f"""
Si právny asistent pracujúci so zmluvami.

Používaj výhradne nasledujúce **metadáta** a text z prílohy ako zdroj odpovede.
Ak niečo nie je uvedené v metadátach, môžeš použiť text, ale nikdy nevymýšľaj nové informácie.

METADÁTA ZMLUVY:
ZMLUVA ID: {p.get('zmluva_id')}
DÁTUM: {p.get('datum')}
SUMA: {p.get('suma_zmluva', 'neuvedená')}
ZMLUVNÉ STRANY:
 - {p.get('zs1')}
 - {p.get('zs2')}
PREDMET: {p.get('predmet', 'neuvedený')}

TEXT ZMLUVY:
{p.get('text')}

OTÁZKA:
{question}

FORMÁT ODPOVEDE:
ZMLUVA ID: <id zmluvy>
DÁTUM: <dátum>
SUMA: <suma z metadát>
ZMLUVNÉ STRANY:
 - <strana 1>
 - <strana 2>
PDF: https://www.crz.gov.sk/data/att/{p.get('pdf')}
PREDMET ZMLUVY: <predmet z metadát>

"""
    
    response = requests.post(
        OLLAMA_CHAT_URL,
        json={
            "model": CHAT_MODEL,
            "messages": [
                {"role": "system", "content": "Si právny asistent pracujúci so zmluvami. Odpovedaj iba z textov."},
                {"role": "user", "content": prompt}
            ],
            "stream": True
        },
        stream=True,
        timeout=600
    )
    response.raise_for_status()
    
    for line in response.iter_lines():
        if not line:
            continue
        
        try:
            data = json.loads(line.decode("utf-8"))
            if "message" in data and "content" in data["message"]:
                chunk = data["message"]["content"]
                if chunk:
                    yield chunk
            if data.get("done"):
                break
        except json.JSONDecodeError:
            continue
