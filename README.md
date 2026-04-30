# Zmluvy - Slovak Contracts Ingestion & Analysis System

A comprehensive system for downloading, processing, and analyzing Slovak public contracts from the CRZ (Central Registry of Contracts) using semantic search, embeddings, and large language models.

## 🎯 Features

- **Automated Contract Download**: Downloads contracts from CRZ registry for specified companies (by ICO)
- **PDF Processing**: Extracts text from contract PDFs using OCR (Tesseract)
- **Incremental Processing**: Processes only new contracts since last run
- **Semantic Search**: Indexes contracts using embeddings and vector search (Qdrant + Ollama)
- **REST API**: FastAPI endpoints for contract queries
- **Metadata Management**: Tracks contract parties, dates, amounts, and document sources
- **Pipeline Orchestration**: Automated multi-step processing pipeline with state management

## 📋 Project Structure

```
zmluvy/
├── ingest/                              # Data ingestion pipeline
│   ├── pipeline.py                      # Main orchestrator for all pipeline steps
│   ├── pipeline_state.py                # Pipeline state management (START_DATE)
│   ├── download_xml.py                  # Download contracts from CRZ registry
│   ├── download_pdf.py                  # Download PDF files from contracts
│   ├── ocr_pdf.py                       # Extract text from PDFs (OCR)
│   ├── ingest_chunks_with_metadata.py   # Create embeddings & store in Qdrant
│   ├── load_xml_metadata.py             # Load contract metadata from XML
│   └── parse_xml.py                     # Parse contract XML structures
├── api/                                 # FastAPI REST endpoints
│   ├── main.py                          # REST API with /ask endpoint
│   └── query_service.py                 # Shared query service
├── query/                               # Query processing
│   └── ask.py                           # Command-line interface for queries
├── ui/                                  # Frontend (HTML)
│   └── index.html                       # Web interface
├── data/                                # Data storage
│   ├── xml/                             # Downloaded XML files (YYYY-MM-DD.xml)
│   ├── xml_filtered/                    # Filtered XML files (by ICO)
│   ├── tmp_pdf/                         # Downloaded PDFs
│   ├── tmp_txt/                         # OCR-extracted text files
│   └── pipeline_state.json              # Pipeline execution state
├── config.py                            # Centralized configuration
├── ico_list.txt                         # List of ICO codes to track
├── requirements.txt                     # Python dependencies
├── Dockerfile                           # Docker container setup
├── docker-compose.yml                   # Docker Compose configuration
└── README.md                            # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (recommended)
- Tesseract OCR (for PDF text extraction)
- Poppler (for PDF to images conversion)
- Qdrant vector database
- Ollama (for embeddings and LLM)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/zmluvy.git
   cd zmluvy
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure ICO list**
   Create or edit `ico_list.txt` with one company ICO per line:
   ```
   1234567890
   0987654321
   ```

5. **Set up Qdrant and Ollama**
   ```bash
   docker-compose up -d
   ```

### Usage

#### Automated Pipeline (Recommended)

Run the entire pipeline with automatic state management:

```bash
python -m ingest.pipeline
```

This orchestrator runs all steps in sequence:
1. ✅ Downloads XML from CRZ and filters by ICO
2. ✅ Downloads PDF files from contracts
3. ✅ Extracts text from PDFs using OCR
4. ✅ Ingests text chunks with metadata to Qdrant
5. ✅ Automatically updates `pipeline_state.json` on success

**Pipeline State Management**:
- `pipeline_state.json` tracks the `start_date` for incremental processing
- Each successful pipeline run updates the start date to "today"
- Subsequent runs only process contracts from the new start date onwards
- This prevents reprocessing and optimizes performance

#### Manual Step Execution

If you prefer running individual steps:

**1. Download Contract XML from CRZ**
```bash
python -m ingest.download_xml
```
- Downloads daily exports from CRZ
- Filters contracts by ICOs in `ico_list.txt`
- Skips already downloaded files
- Reads `start_date` from `pipeline_state.json`

**2. Download PDF Files**
```bash
python -m ingest.download_pdf
```
- Extracts PDF URLs from filtered XML
- Downloads all referenced PDFs
- Only processes XML files from `start_date` onwards

**3. Extract Text from PDFs (OCR)**
```bash
python -m ingest.ocr_pdf
```
- Converts PDFs to images using Poppler
- Extracts text using Tesseract OCR (Slovak + English)
- Processes only new PDFs (without existing text files)
- Deletes PDFs after successful OCR to save space

**4. Create Embeddings and Index**
```bash
python -m ingest.ingest_chunks_with_metadata
```
- Chunks text into 800-character segments
- Generates embeddings using Ollama
- Stores in Qdrant with contract metadata
- Filters contracts by `start_date`

**5. Query Contracts**

*Command-line:*
```bash
python -m query.ask
```
Edit the question variable and run to perform semantic search.

*REST API:*
```bash
python -m uvicorn api.main:app --reload
```
Access at `http://localhost:8000/docs`

*API Request Example:*
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Show me contracts with payment terms"}'
```

## ⚙️ Configuration

Edit `config.py` to customize settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `QDRANT_HOST` | `localhost` | Qdrant server host |
| `QDRANT_PORT` | `6333` | Qdrant server port |
| `QDRANT_COLLECTION` | `zmluvy_v2` | Qdrant collection name |
| `OLLAMA_HOST` | `localhost` | Ollama server host |
| `OLLAMA_PORT` | `11434` | Ollama server port |
| `EMBED_MODEL` | `nomic-embed-text` | Embedding model (768-dim) |
| `CHAT_MODEL` | `qwen2.5:7b` | LLM chat model |
| `CHUNK_SIZE` | `800` | Text chunk size for embeddings |
| `VECTOR_SIZE` | `768` | Vector dimension size |
| `VECTOR_DISTANCE` | `cosine` | Distance metric (cosine/euclid) |
| `UPSERT_BATCH_SIZE` | `50` | Batch size for Qdrant uploads |
| `DOWNLOAD_TIMEOUT` | `30` | PDF download timeout (seconds) |
| `REQUEST_TIMEOUT` | `60` | LLM request timeout (seconds) |

## 📊 Data Pipeline Flow

```
Pipeline Start
    ↓
[Load START_DATE from pipeline_state.json]
    ↓
[1] Download XML from CRZ (from START_DATE onwards)
    ↓
[2] Filter by ICO & Extract PDF filenames
    ↓
[3] Download PDFs (only for new contracts)
    ↓
[4] Extract text via OCR (processing only new PDFs)
    ↓
[5] Split text into chunks (800 chars)
    ↓
[6] Generate embeddings with Ollama
    ↓
[7] Store in Qdrant (indexed with metadata)
    ↓
[Update START_DATE in pipeline_state.json]
    ↓
Pipeline Complete ✅
```

## 📈 State Management

Pipeline state is managed through `pipeline_state.json`:

```json
{
  "start_date": "2026-01-24",
  "updated_at": "2026-04-01 12:00:00"
}
```

- **start_date**: Used as filter for incremental processing
- **updated_at**: Timestamp of last successful pipeline run
- Updated automatically after each successful pipeline execution

## 🐳 Docker Deployment

Using Docker Compose:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services included:
- **Qdrant**: Vector database (port 6333)
- **Ollama**: LLM and embeddings (port 11434)
- Volume mounts for data persistence

## 🔍 Query Examples

### By Contract ID
```
"Show me details of contract ID 11892369"
```

### By Party Name
```
"Find contracts related to Dogma Theater"
```

### Semantic Search
```
"What are the payment terms in these contracts?"
```

## 🛠️ Technologies & Dependencies

### Core Technologies
- **Framework**: FastAPI (REST API)
- **Vector DB**: Qdrant (semantic search, similarity)
- **LLM**: Ollama (embeddings & chat models)
- **Embedding Model**: Nomic-embed-text (768-dimensional)
- **Chat Model**: Qwen 2.5 7B
- **OCR**: Tesseract (text extraction from PDFs)
- **PDF Processing**: pdf2image + pytesseract
- **XML Parsing**: lxml, ElementTree
- **Python**: 3.11+

### Python Dependencies
```
fastapi              # REST API framework
qdrant-client        # Vector database client
requests             # HTTP client
lxml                 # XML parsing
pytesseract          # OCR wrapper
pdf2image            # PDF to image conversion
tqdm                 # Progress tracking
uvicorn              # ASGI server
```

See `requirements.txt` for complete list.

## 📝 CRZ Integration

This system integrates with the Slovak Central Registry of Contracts (CRZ):

- **URL**: http://www.crz.gov.sk/
- **Data Source**: Public procurement contracts
- **Format**: Daily ZIP exports containing XML files
- **Updates**: New contracts typically available daily
- **Filtering**: Specifies organizations by Tax ID (ICO)

### Rate Limiting
The system respects CRZ rate limits:
- Daytime (6:00-20:00): ~2.5 requests/second
- Night time: ~3 requests/second
- Automatic delays between requests

## 🔐 Important Notes

- ✅ Respects CRZ rate limits (automatic request delays)
- ✅ Deletes PDFs after successful OCR to save disk space
- ✅ Batch processing with progress tracking (tqdm)
- ✅ Incremental updates (processes only new data)
- ✅ Graceful error handling and recovery
- ✅ Metadata preservation throughout pipeline

## 🚧 Development

### Project Guidelines

- **Pipeline Architecture**: Modular scripts for each processing step
- **Configuration**: Centralized in `config.py`
- **API Design**: Single `/ask` endpoint with semantic search
- **Error Handling**: Graceful failures with informative logging
- **Incremental Processing**: Only processes data since last run

### Code Structure Notes

- Each pipeline step is independent and can be run manually
- `pipeline_state.py` handles centralized state persistence
- `pipeline.py` orchestrates all steps with error handling
- Exit codes (0 = success, 1 = error) enable pipeline chaining

### Contributing

1. Maintain PEP 8 style guide compliance
2. Update `config.py` for new configurable settings
3. Add docstrings to all functions
4. Test with sample contracts before submitting
5. Use meaningful commit messages

## 📄 License

Licensed under the Apache License 2.0.

## Legal Notice

This project processes publicly available contract data from the Slovak Central Registry of Contracts (CRZ).

The software itself is licensed under the Apache License 2.0.
Contract documents and extracted data remain subject to their original legal status and ownership.

## 👥 Author

Ivan Kubica, 
GitHub: https://github.com/modreoko  
Email: ivan@example.com


## 🤝 Support

For issues, questions, or contributions, please open an issue on GitHub.

## 🔗 Related Resources

- [CRZ Official Website](http://www.crz.gov.sk/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Ollama Models](https://ollama.ai/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
- [Poppler Documentation](https://poppler.freedesktop.org/)
