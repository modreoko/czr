import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from query_service import search_contracts, stream_llm_response

# ❓ MODIFY QUESTION HERE
question = "Hľadaj zmluvu s Dogma Divadlo"
# question = "Napis mi detail zmluvy ID 11892369"


# =====================
# SEARCH CONTRACTS
# =====================
print(f"❓ Otázka: {question}\n")

search_result = search_contracts(question, limit=50, verbose=True)
hits = search_result["hits"]
count = search_result["count"]

print(f"🔹 Počet výsledkov: {count}\n")

if not hits:
    print("⚠️ Zmluva sa nenašla.")
    exit()

# =====================
# STREAM RESPONSE
# =====================
print("\n---- ODPOVEĎ ----\n")

for chunk in stream_llm_response(question, hits):
    print(chunk, end="", flush=True)

print("\n-----------------")
