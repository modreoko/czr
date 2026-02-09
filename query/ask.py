import re
import requests
import json
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from pathlib import Path
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    OLLAMA_CHAT_URL, OLLAMA_EMBED_URL, EMBED_MODEL, CHAT_MODEL,
    COLLECTION_ZMLUVY, QDRANT_HOST, QDRANT_PORT, REQUEST_TIMEOUT
)

COLLECTION = COLLECTION_ZMLUVY

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# =====================
# EMBEDDING FUNKCIA
# =====================
def embed(text):
    r = requests.post(
        OLLAMA_EMBED_URL,
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=REQUEST_TIMEOUT
    )
    r.raise_for_status()
    return r.json()["embedding"]

# =====================
# DETEKCIA ZMLUVY ID
# =====================
def extract_contract_id(text):
    """
    Nájde formáty typu:
    - zmluva ID 1234567
    - zmluvu id: 1234567
    - ID 1234567
    """
    match = re.search(r"\bID\s*([0-9]{4,10})\b", text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def extract_contract_party(text):
    """
    Extrahuje meno zmluvnej strany z otázky typu:
    - 's Samuel Budinský'
    - 'so Štefanom Žilinským'
    """
    pattern = r"\b(?:s|so)\s+([A-ZÁČĎÉÍĽŇÓÔŔŠŤÚÝŽ][\wáčďéíľňóôŕšťúýžÁČĎÉÍĽŇÓÔŔŠŤÚÝŽ]*(?:\s[\wáčďéíľňóôŕšťúýžÁČĎÉÍĽŇÓÔŔŠŤÚÝŽ]+)*)\b"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return None


# ❓ ZADAJ OTÁZKU
#question = "Napis mi detail zmluvy ID 11892369"
question = "Hľadaj zmluvu s Dogma Divadlo"

contract_id = extract_contract_id(question)

# =====================
# 1) PRESNÉ HĽADANIE PODĽA ID
# =====================
if contract_id:
    print(f"🔍 Detekované ID zmluvy: {contract_id}")

    points, _ = client.scroll(
        collection_name=COLLECTION,
        scroll_filter=qm.Filter(
            must=[
                qm.FieldCondition(
                    key="zmluva_id",
                    match=qm.MatchValue(value=contract_id)
                )
            ]
        ),
        limit=50
    )

    hits = points

# =====================
# 2) PRESNÉ HĽADANIE PODĽA ZMLUVNEJ STRANY
# =====================
else:
# skúsime extrahovať meno z otázky
    # jednoduchý regex, berieme posledné dve slová za "s"
    #match = re.search(r"s\s+([\wáčďéíľňóôŕšťúýžÁČĎÉÍĽŇÓÔŔŠŤÚÝŽ]+(?:\s[\wáčďéíľňóôŕšťúýžÁČĎÉÍĽŇÓÔŔŠŤÚÝŽ]+)?)", question, flags=re.IGNORECASE)
    contract_party = extract_contract_party(question)

    if contract_party:
        print(f"🔍 Hľadám podľa zmluvnej strany: {contract_party}")

        points, _ = client.scroll(
            collection_name=COLLECTION,
            scroll_filter=qm.Filter(
                should=[
                    qm.FieldCondition(key="zs1", match=qm.MatchValue(value=contract_party)),
                    qm.FieldCondition(key="zs2", match=qm.MatchValue(value=contract_party)),
                ]
            ),
            limit=50
        )

        hits = points

    else:
        # =====================
        # 3) EMBEDDING SEARCH (fallback)
        # =====================
        print("🧠 ID ani zmluvná strana nezistená → používam embedding search")
        query_vector = embed(question)

        hits = client.query_points(
            collection_name=COLLECTION,
            query=query_vector,
            with_payload=True,
            limit=50
        ).points


print(f"🔹 Počet výsledkov: {len(hits)}")

# Ak nič nenašlo → vrátime odpoveď
if not hits:
    print("⚠️ Zmluva sa nenašla.")
    exit()


# =====================
# KONŠTRUKCIA KONTEXTU
# =====================
h = hits[0]
p = h.payload

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

# =====================
# PROMPT PRE MODEL
# =====================
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

# =====================
# STREAM OD OLLAMY
# =====================
print("\n---- ODPOVEĎ ----")

r = requests.post(
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

answer = ""

for line in r.iter_lines():
    if not line:
        continue

    data = json.loads(line.decode("utf-8"))

    # chat stream
    if "message" in data and "content" in data["message"]:
        chunk = data["message"]["content"]
        print(chunk, end="", flush=True)
        answer += chunk

    if data.get("done"):
        break

print("\n-----------------")
