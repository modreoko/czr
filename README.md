# Zmluvy - Slovak Public Contracts Analysis System

A comprehensive system for downloading, processing, and analyzing Slovak public contracts from the CRZ (Central Registry of Contracts) using semantic search and large language models.

## 🎯 Features

- **Contract Download**: Automatically downloads contracts from the CRZ registry for specified companies (by ICO)
- **PDF Processing**: Extracts text from contract PDFs using OCR (Tesseract)
- **Semantic Search**: Indexes contracts using embeddings and vector search (Qdrant + Ollama)
- **Natural Language Queries**: Ask questions about contracts in Slovak using LLM-powered semantic search
- **REST API**: FastAPI endpoint for programmatic access to contract queries
- **Metadata Management**: Tracks contract parties, dates, amounts, and document sources

## 📋 Project Structure

```
zmluvy/
├── api/                          # FastAPI REST endpoints
│   └── main.py                   # /ask endpoint for contract queries
├── ingest/                       # Data processing pipeline
│   ├── download_xml.py           # Download contracts from CRZ registry
│   ├── download_pdf.py           # Download PDF files from contracts
│   ├── ocr_pdf.py                # Extract text from PDFs (OCR)
│   ├── ingest_chunks.py          # Create embeddings and store in Qdrant
│   ├── ingest_chunks_with_metadata.py  # Ingest with contract metadata
│   ├── ingest_texts.py           # Alternative embedding approach
│   ├── parse_xml.py              # Parse contract XML structures
│   └── load_xml_metadata.py      # Load contract metadata from XML
├── query/                        # Query processing
│   └── ask.py                    # Command-line interface for queries
├── ui/                           # Frontend (HTML)
│   └── index.html
├── data/                         # Data storage
│   ├── xml/                      # Downloaded XML files
│   ├── xml_filtered/             # Filtered XML (by ICO)
│   ├── tmp_pdf/                  # Downloaded PDFs
│   └── tmp_txt/                  # OCR-extracted text files
├── config.py                     # Centralized configuration
├── ico_list.txt                  # List of ICO codes to track
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker container setup
└── docker-compose.yml            # Docker Compose configuration
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (recommended)
- Tesseract OCR (for PDF text extraction)
- Poppler (for PDF conversion to images)
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
   Create `ico_list.txt` with one company ICO per line:
   ```
   1234567890
   0987654321
   ```

5. **Set up Qdrant and Ollama**
   ```bash
   docker-compose up -d
   ```

### Usage

#### 1. Download Contract XML from CRZ
```bash
python -m ingest.download_xml
```
Downloads contracts from the CRZ registry and filters by ICOs in `ico_list.txt`.

#### 2. Download PDF Files
```bash
python -m ingest.download_pdf
```
Extracts and downloads all PDF files referenced in contracts.

#### 3. Extract Text from PDFs (OCR)
```bash
python -m ingest.ocr_pdf
```
Converts PDFs to text using Tesseract OCR.

#### 4. Create Embeddings and Index
```bash
python -m ingest.ingest_chunks_with_metadata
```
Chunks text, creates embeddings, and stores in Qdrant with metadata.

#### 5. Query Contracts
**Command-line:**
```bash
python -m query.ask
```
Edit the question variable in `query/ask.py` and run to perform semantic search.

**API:**
```bash
python -m uvicorn api.main:app --reload
```
Access the API at `http://localhost:8000/docs`

**Request:**
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Napis mi detail zmluvy ID 11892369"}'
```

## ⚙️ Configuration

Edit `config.py` to customize settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `QDRANT_HOST` | `localhost` | Qdrant server host |
| `QDRANT_PORT` | `6333` | Qdrant server port |
| `OLLAMA_HOST` | `localhost` | Ollama server host |
| `OLLAMA_PORT` | `11434` | Ollama server port |
| `EMBED_MODEL` | `nomic-embed-text` | Embedding model name |
| `CHAT_MODEL` | `qwen2.5:7b` | LLM chat model name |
| `CHUNK_SIZE` | `800` | Text chunk size for embeddings |
| `UPSERT_BATCH_SIZE` | `50` | Batch size for Qdrant uploads |
| `DOWNLOAD_TIMEOUT` | `30` | PDF download timeout (seconds) |
| `REQUEST_TIMEOUT` | `60` | LLM request timeout (seconds) |

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

The `docker-compose.yml` includes:
- Qdrant vector database
- Python application container
- Volume mounts for data persistence

## 📊 Data Pipeline

```
↓ Download XML from CRZ
↓ Filter by ICO
↓ Extract PDF filenames
↓ Download PDFs
↓ Extract text via OCR
↓ Split into chunks
↓ Generate embeddings
↓ Store in Qdrant (indexed)
↓ Query via API/CLI with semantic search
```

## 🔍 Query Examples

### By Contract ID
```
"Napis mi detail zmluvy ID 11892369"
```

### By Party Name
```
"Hľadaj zmluvu s Dogma Divadlo"
```

### Semantic Search
```
"Aké sú podmienky platby v zmluvách?"
```

## 🛠️ Technologies Used

- **Framework**: FastAPI (REST API)
- **Vector DB**: Qdrant (semantic search)
- **LLM**: Ollama (embeddings & chat)
- **Embedding Model**: Nomic-embed-text (768-dim)
- **Chat Model**: Qwen 2.5 7B
- **OCR**: Tesseract
- **PDF Processing**: pdf2image + pytesseract
- **XML Parsing**: lxml
- **Python**: 3.11+

## 📝 CRZ Integration

This system integrates with the Slovak Central Registry of Contracts (CRZ):
- **URL**: http://www.crz.gov.sk/
- **Data Source**: Public procurement contracts
- **Update Frequency**: Daily exports available
- **ICO Filtering**: Tracks specific organizations by Tax ID (ICO)

## 🔐 Important Notes

- Respects CRZ rate limits (automatic delay between requests)
- Deletes PDFs after successful OCR to save space
- Batch processing with progress tracking
- Error handling and recovery

## 📦 Dependencies

Key Python packages:
```
fastapi              # REST API framework
qdrant-client        # Vector database client
requests             # HTTP requests
lxml                 # XML parsing
pytesseract          # OCR wrapper
pdf2image            # PDF conversion
sentence-transformers # Embeddings (alternative)
```

See `requirements.txt` for complete list.

## 🚧 Development

### Project Structure Notes

- **Ingest Pipeline**: Modular scripts for each processing step
- **Config Management**: Centralized `config.py` for all settings
- **API Design**: Single `/ask` endpoint with semantic search
- **Error Handling**: Graceful failures with logging

### Contributing

1. Follow PEP 8 style guide
2. Update `config.py` for new configurable settings
3. Add docstrings to functions
4. Test with sample contracts

## 📄 License

[Specify your license here]

## 👥 Author

[Your name/organization]

## 🤝 Support

For issues, questions, or contributions, please open an issue on GitHub.

## 🔗 Related Resources

- [CRZ Official Website](http://www.crz.gov.sk/)
- [Qdrant Documentation](https://qdrant.tech/)
- [Ollama Models](https://ollama.ai/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
