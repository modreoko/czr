from fastapi import FastAPI
from pydantic import BaseModel
import sys
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import BASE_DIR
from query_service import search_contracts, generate_llm_response, stream_llm_response


UI_DIR = BASE_DIR / "ui"

app = FastAPI()


app.mount("/ui", StaticFiles(directory=str(UI_DIR), html=True), name="ui")

@app.get("/")
def root():
    return FileResponse(UI_DIR / "index.html")

class Question(BaseModel):
    question: str


@app.post("/ask")
def ask(q: Question):
    """
    Query contracts with intelligent multi-strategy search.
    
    Strategies (in order of preference):
    1. Search by contract ID if detected
    2. Search by party name if detected
    3. Fall back to semantic (embedding) search
    """
    question = q.question
    
    # Search contracts using intelligent strategy
    search_result = search_contracts(question, limit=50, verbose=False)
    hits = search_result["hits"]
    
    if not hits:
        return {
            "question": question,
            "strategy": search_result["strategy"],
            "count": 0,
            "answer": "V dostupných zmluvách sa informácia nenachádza."
        }
    
    # Generate LLM response
    answer = generate_llm_response(question, hits)
    
    return {
        "question": question,
        "strategy": search_result["strategy"],
        "count": len(hits),
        "answer": answer
    }
