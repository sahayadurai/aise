# RAG Benchmark PDF Data Extractor — Complete Project Documentation

## Academic Report — System Design, Architecture, Database Integration & Deployment Guide

---

## EXECUTIVE SUMMARY

This comprehensive report documents the design and implementation of a **Retrieval-Augmented Generation (RAG) Benchmarking System** built as a FastAPI application with PostgreSQL persistence. The system enables users to upload PDF documents, configure hyperparameters for text and image extraction, build FAISS vector indices, query multiple LLM models via OpenRouter, and evaluate response quality using established NLP benchmarking metrics.

**Key Features:**
- [OK] Multi-model RAG pipeline with FastAPI
- [OK] PostgreSQL persistent storage with SQLAlchemy ORM
- [OK] Automated benchmarking with 8 evaluation metrics
- [OK] Containerized with Docker for easy deployment
- [OK] Single-command setup via `run.sh` script
- [OK] Support for text, image, and table extraction from PDFs

**Latest Optimizations (v1.2.0):**
- [OK] Consolidated all setup functionality into single `run.sh` script
- [OK] Cleaned Dockerfile (removed comments for production efficiency)
- [OK] Merged all documentation files into unified REPORT.md
- [OK] Removed redundant setup scripts and duplicate documentation
- [OK] Production-ready, minimal project footprint

The architecture follows a modular pipeline pattern with separate components for extraction, embedding, retrieval, generation, evaluation, and data persistence.

---

## TABLE OF CONTENTS

1. [Abstract](#abstract)
2. [System Overview](#system-overview)
3. [Architecture Components](#architecture-components)
4. [PDF Processing Pipeline](#pdf-processing-pipeline)
5. [Embedding & Retrieval](#embedding--retrieval)
6. [LLM Integration](#llm-integration-via-openrouter)
7. [Benchmarking Framework](#benchmarking-framework)
8. [Database Architecture & PostgreSQL Integration](#database-architecture)
9. [API Reference](#api-reference)
10. [Installation & Setup Guide](#installation--setup-guide)
11. [Docker Deployment](#docker-deployment)
12. [Running the Application](#running-the-application)
13. [Directory Structure](#directory-structure)
14. [Additional Enhancements](#additional-changes--enhancements)
15. [Troubleshooting](#troubleshooting)
16. [Future Work & Limitations](#limitations--future-work)
17. [References](#references)

---

## 1. ABSTRACT

This report presents the design and implementation of a **Retrieval-Augmented Generation (RAG) Benchmarking System** built as a FastAPI application. The system enables users to upload PDF documents, configure hyperparameters for text and image extraction, build FAISS vector indices, query multiple LLM models via OpenRouter, and evaluate response quality using established NLP benchmarking metrics. The architecture follows a modular pipeline pattern with separate components for extraction, embedding, retrieval, generation, and evaluation.

---

## 2. SYSTEM OVERVIEW

The system is composed of seven core modules operating in a sequential pipeline:
1. **PDF Processor** - Extract text, images, tables, and ground truth Q&A pairs
2. **Embeddings Engine** - Generate vector embeddings and build FAISS indices
3. **Retrieval System** - Query FAISS indices and rerank results
4. **LLM Integration** - Query multiple models via OpenRouter API
5. **Benchmarking Engine** - Evaluate responses with 8 metrics
6. **Database Layer** - PostgreSQL persistence via SQLAlchemy ORM
7. **Web Frontend** - Responsive HTML/CSS/JavaScript UI

A unified deployment script (`run.sh`) provisions the entire environment — virtual environment, dependencies, directory structure, database setup, configuration, and server launch in a single command.

### 2.1 High-Level Process Flow

```mermaid
flowchart TD
    A["User Uploads PDFs"] --> B["PDF Processor"]
    B --> C["Text Chunking"]
    B --> D["Image Extraction"]
    B --> E["Table Extraction"]
    B --> F["Ground Truth Extraction"]
    C --> G["Embedding Generator"]
    D --> G
    E --> G
    G --> H["FAISS Index Builder"]
    H --> I["Index Storage (.faiss + .pkl)"]
    F --> J["Ground Truth Store"]
    K["User Query"] --> L["Query Encoder"]
    L --> M["FAISS Retrieval (Top-K)"]
    I --> M
    M --> N["Cosine Reranking"]
    N --> O["Context Assembly"]
    O --> P["OpenRouter LLM (Multi-Model)"]
    P --> Q["Response Generation"]
    Q --> R["Output + Sources"]
    Q --> S["Benchmark Evaluator"]
    J --> S
    S --> T["Metrics Dashboard"]
```

---

## 3. Architecture Components

### 3.1 Component Interaction Diagram

```mermaid
flowchart LR
    subgraph Frontend["Frontend (HTML/CSS/JS)"]
        UI["Responsive Web UI"]
        SB["Sidebar (Sessions/Files/Chats)"]
        UP["Upload Panel"]
        QP["Query Panel"]
        BP["Benchmark Panel"]
    end

    subgraph Backend["Backend (FastAPI)"]
        API["REST API Routes"]
        PDF["PDF Processor Module"]
        EMB["Embedding Engine"]
        IDX["FAISS Index Manager"]
        LLM["OpenRouter LLM Client"]
        BEN["Benchmark Evaluator"]
        SES["Session Manager"]
    end

    subgraph Storage["Storage Layer"]
        UPL["uploads/"]
        IND["indices/ (.faiss + .pkl)"]
        RES["results/"]
        CHA["chats/"]
    end

    subgraph External["External Services"]
        OR["OpenRouter API"]
        ST["Sentence Transformers"]
    end

    UI --> API
    SB --> API
    UP --> API
    QP --> API
    BP --> API

    API --> PDF
    API --> EMB
    API --> IDX
    API --> LLM
    API --> BEN
    API --> SES

    PDF --> UPL
    EMB --> ST
    IDX --> IND
    LLM --> OR
    SES --> CHA
    BEN --> RES
```

### 3.2 Module Descriptions

| Module | File | Responsibility |
|--------|------|----------------|
| **Config** | `app/config.py` | Central configuration, environment variables, model registry |
| **PDF Processor** | `app/pdf_processor.py` | Text chunking, image extraction, table extraction, ground-truth mining |
| **Embeddings** | `app/embeddings.py` | Sentence-Transformer encoding, FAISS index build/query |
| **LLM Client** | `app/llm_client.py` | Async OpenRouter chat completion with latency tracking |
| **Benchmarks** | `app/benchmarks.py` | BLEU, ROUGE-L, Faithfulness, Context Precision/Recall, MRR, Hit Rate |
| **Main App** | `app/main.py` | FastAPI routes, session management, orchestration |
| **Frontend** | `app/templates/` + `app/static/` | HTML template, CSS styling, JavaScript client logic |

---

## 4. PDF Processing Pipeline

### 4.1 Extraction Flow

```mermaid
flowchart TD
    A["Input PDF File"] --> B{"Extract Content"}
    B --> C["Text Extraction (pdfplumber)"]
    B --> D["Image Extraction (pypdf)"]
    B --> E["Table Extraction (pdfplumber)"]
    B --> F["Ground Truth Mining"]

    C --> G["Sliding Window Chunking"]
    G --> |"chunk_size, overlap"| H["Text Chunks"]

    D --> I["Image Metadata + Hash"]

    E --> J["Table → Row Text"]

    F --> K["Q&A Pattern Matching"]
    F --> L["Section Heading Analysis"]
    K --> M["Ground Truth Pairs"]
    L --> M

    H --> N["Unified Chunk List"]
    I --> N
    J --> N

    N --> O["FAISS Indexing"]
    M --> P["Benchmark Storage"]
```

### 4.2 Configurable Hyperparameters

| Parameter | Default | Range | Applies To | Description |
|-----------|---------|-------|------------|-------------|
| `text_chunk_size` | 512 | 64–4096 | Text | Number of words per text chunk |
| `text_chunk_overlap` | 64 | 0–512 | Text | Overlapping words between consecutive chunks |
| `image_chunk_size` | 256 | 64–2048 | Images | Metadata chunk granularity |
| `top_k` | 5 | 1–50 | Retrieval | Number of chunks to retrieve |
| `cosine_threshold` | 0.0 | 0.0–1.0 | Reranking | Minimum cosine similarity to keep a chunk |
| `temperature` | 0.3 | 0.0–2.0 | Generation | LLM sampling temperature |

---

## 5. Embedding & Retrieval

### 5.1 Vector Index Pipeline

```mermaid
flowchart LR
    A["Text Chunks"] --> B["Sentence Transformer\n(all-MiniLM-L6-v2)"]
    B --> C["L2-Normalized Embeddings\n(384-dim float32)"]
    C --> D["FAISS IndexFlatIP\n(Inner Product = Cosine)"]
    D --> E[".faiss File"]
    A --> F["Metadata Pickle"]
    F --> G[".pkl File"]

    H["User Query"] --> I["Query Embedding"]
    I --> J["FAISS Search (2×top_k)"]
    E --> J
    J --> K["Score Filtering\n(cosine_threshold)"]
    K --> L["Top-K Reranked Results"]
    G --> L
```

Key design decisions:

- **L2 normalization** of embeddings converts inner-product search to cosine similarity.
- **Over-retrieval** (2×top_k) followed by threshold filtering provides better precision.
- **Per-PDF indices** allow selective querying and independent updates.

---

## 6. LLM Integration via OpenRouter

### 6.1 Multi-Model Query Flow

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant FAISS as FAISS Index
    participant OR as OpenRouter

    U->>API: POST /api/query (query, models[], params)
    API->>FAISS: Retrieve top-k chunks from all PDFs
    FAISS-->>API: Ranked chunks with scores

    loop For each selected model
        API->>OR: Chat completion (system=context, user=query)
        OR-->>API: Response + usage + latency
        API->>API: Run benchmarks (if enabled)
    end

    API-->>U: Results per model with sources + benchmarks
```

### 6.2 Supported Models

| Provider | Model ID | Display Name |
|----------|----------|-------------|
| OpenAI | `openai/gpt-4o` | GPT-4o |
| OpenAI | `openai/gpt-4o-mini` | GPT-4o Mini |
| Anthropic | `anthropic/claude-sonnet-4` | Claude Sonnet 4 |
| Anthropic | `anthropic/claude-haiku-3.5` | Claude 3.5 Haiku |
| Google | `google/gemini-2.0-flash-001` | Gemini 2.0 Flash |
| Meta | `meta-llama/llama-3.3-70b-instruct` | Llama 3.3 70B |
| DeepSeek | `deepseek/deepseek-chat-v3-0324` | DeepSeek V3 |
| Mistral | `mistralai/mistral-large-2411` | Mistral Large |

---

## 7. Benchmarking Framework

### 7.1 Evaluation Metrics

```mermaid
flowchart TD
    A["Benchmark Evaluator"] --> B["Lexical Metrics"]
    A --> C["Semantic Metrics"]
    A --> D["Retrieval Metrics"]

    B --> B1["BLEU (n-gram precision\nwith brevity penalty)"]
    B --> B2["ROUGE-L (LCS-based\nprecision, recall, F1)"]

    C --> C1["Faithfulness (answer-context\ntoken overlap ratio)"]
    C --> C2["Answer Relevancy (answer-question\ntoken overlap ratio)"]

    D --> D1["Context Precision (relevant chunks\nin ranked positions)"]
    D --> D2["Context Recall (reference tokens\ncovered by retrieved chunks)"]
    D --> D3["MRR (Mean Reciprocal Rank\nof first relevant chunk)"]
    D --> D4["Hit Rate (binary: any relevant\nchunk in top-k)"]
```

### 7.2 Metric Definitions

| Metric | Category | Formula Summary | Range |
|--------|----------|-----------------|-------|
| **BLEU** | Lexical | Geometric mean of n-gram precisions (n=1..4) × brevity penalty | 0–1 |
| **ROUGE-L** | Lexical | LCS-based precision, recall, F1 between prediction and reference | 0–1 |
| **Faithfulness** | Semantic | \|answer_tokens ∩ context_tokens\| / \|answer_tokens\| | 0–1 |
| **Answer Relevancy** | Semantic | \|answer_tokens ∩ question_tokens\| / \|question_tokens\| | 0–1 |
| **Context Precision** | Retrieval | Average precision at relevant positions in top-k | 0–1 |
| **Context Recall** | Retrieval | \|reference_tokens ∩ retrieved_tokens\| / \|reference_tokens\| | 0–1 |
| **MRR** | Retrieval | 1 / rank of first relevant chunk (0 if none) | 0–1 |
| **Hit Rate** | Retrieval | 1 if any relevant chunk found, else 0 | 0 or 1 |

### 7.3 Ground Truth Extraction

The system automatically mines ground-truth Q&A pairs from uploaded PDFs using two heuristic strategies:

1. **Q&A pattern matching**: Regex detection of `Q: ... A: ...` or `Question: ... Answer: ...` patterns.
2. **Section heading analysis**: ALL-CAPS headings followed by substantial body text are converted to `"What is discussed under '<heading>'?"` → `<body text>` pairs.

---

## 8. API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves the web UI |
| `/api/models` | GET | Lists available LLM models |
| `/api/sessions` | GET | Lists all active sessions |
| `/api/session/{id}` | GET | Returns full session data |
| `/api/upload` | POST | Upload PDFs, extract, index |
| `/api/query` | POST | Query RAG pipeline with multi-model |
| `/api/benchmark` | POST | Run full benchmark on ground-truth |
| `/api/chat_history/{id}` | GET | Returns chat history for session |

---

## 8. DATABASE ARCHITECTURE & POSTGRESQL INTEGRATION

### 8.1 Overview

The system has been upgraded to persist all data in PostgreSQL instead of storing it in-memory or as loose files. This includes sessions, uploaded files, ground truths, chat messages, and benchmark results. Data is now durable across server restarts and supports multiple concurrent users.

**Data Now Persisted:**
- Session metadata and lifecycle tracking
- Uploaded PDF file metadata and processing status
- Ground truth Q&A pairs extracted from PDFs
- Chat message history with responses from all models
- Benchmark evaluation results and metrics

### 8.2 Database Schema

The database consists of 5 interconnected tables with proper foreign key relationships:

```
sessions (root)
├── uploaded_files (many) → ground_truths (many)
├── chat_messages (many)
└── benchmarks (many)
```

#### Table: `sessions`
- `id` (String, PK): Unique session identifier
- `created_at` (DateTime): Session creation timestamp
- `updated_at` (DateTime): Last update timestamp
- **Relationships**: Has many files, chats, and benchmarks

#### Table: `uploaded_files`
- `id` (String, PK): Unique file identifier
- `session_id` (String, FK): Associated session
- `filename` (String): Original PDF filename
- `file_path` (String): Path where PDF is stored on disk
- `file_size` (Integer): File size in bytes
- `upload_date` (DateTime): Upload timestamp
- `text_chunks_count` (Integer): Number of text chunks extracted
- `image_chunks_count` (Integer): Number of image chunks extracted
- `table_chunks_count` (Integer): Number of table chunks extracted
- `ground_truth_count` (Integer): Number of Q&A pairs extracted
- `index_path` (String): Path to FAISS index file (.faiss)
- `metadata_path` (String): Path to metadata pickle file (.pkl)
- `index_status` (String): Status of indexing ("pending", "indexed", "error")
- `text_chunk_size` (Integer): Chunk size used for extraction
- `text_chunk_overlap` (Integer): Overlap used for extraction
- `image_chunk_size` (Integer): Image metadata chunk size
- **Relationships**: Has many ground truths; belongs to session

#### Table: `ground_truths`
- `id` (String, PK): Unique ground truth identifier
- `file_id` (String, FK): Associated uploaded file
- `question` (Text): The question/query
- `answer` (Text): The reference answer
- `extraction_method` (String): How it was extracted ("qa_pattern" or "section_heading")
- `created_at` (DateTime): Creation timestamp
- **Relationships**: Belongs to uploaded_file

#### Table: `chat_messages`
- `id` (String, PK): Unique chat message identifier
- `session_id` (String, FK): Associated session
- `query` (Text): The user's query
- `timestamp` (DateTime): When the query was made
- `top_k` (Integer): Number of top chunks retrieved
- `temperature` (Integer): Temperature × 10 (stored as int for efficiency)
- `cosine_threshold` (Integer): Threshold × 100
- `model_ids` (String): Comma-separated list of models queried
- `responses` (JSON): Full response objects from all models
- `run_benchmark` (Boolean): Whether benchmarking was requested
- **Relationships**: Belongs to session

#### Table: `benchmarks`
- `id` (String, PK): Unique benchmark identifier
- `session_id` (String, FK): Associated session
- `chat_message_id` (String, Nullable): Associated chat message if from a chat query
- `model_id` (String): Which model was evaluated
- `timestamp` (DateTime): When benchmark was run
- `max_questions` (Integer): Number of questions evaluated
- `top_k` (Integer): Number of chunks retrieved per question
- `aggregate_metrics` (JSON): Aggregated metrics (mean, min, max for each metric type)
- `detailed_results` (JSON): Per-question results
- **Relationships**: Belongs to session

### 8.3 Data Storage Architecture

**Hybrid Storage Strategy:**

| Data Type | Storage Medium | Rationale |
|-----------|---|---|
| Session metadata | PostgreSQL | Query history, relationships |
| Uploaded PDF files | Filesystem (`data/uploads/`) | Large binary files |
| FAISS vector indices | Filesystem (`data/indices/`) | Efficient vectorized search |
| Chat history & responses | PostgreSQL | Query and analysis |
| Ground truth Q&A pairs | PostgreSQL | Relationship to files, benchmarking |
| Benchmark results | PostgreSQL | Analysis and aggregation |
| Configuration | `.env` file | Environment-specific settings |

**Benefits of This Approach:**

[OK] **Durability**: Data persists across server restarts
[OK] **Scalability**: Support multiple concurrent users
[OK] **Queryability**: SQL queries on chat history and benchmarks
[OK] **Efficiency**: Filesystem for large files, DB for relationships
[OK] **Integrity**: Foreign keys maintain referential integrity
[OK] **Backups**: Standard PostgreSQL tools available
[OK] **Performance**: Indexed queries on frequently accessed data

### 8.4 Database Initialization

The database is automatically initialized on application startup via SQLAlchemy's ORM:

```python
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    try:
        init_db()  # Creates all tables if they don't exist
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
```

All tables are created with proper constraints and relationships. If the database already exists, the application continues seamlessly.

### 8.5 Querying the Database

**Connect to PostgreSQL:**
```bash
psql -U postgres -d rag_benchmark
```

**Useful SQL Queries:**

```sql
-- List all sessions
SELECT id, created_at, updated_at FROM sessions
ORDER BY created_at DESC;

-- Get files uploaded in a specific session
SELECT filename, file_size, text_chunks_count, index_status, upload_date
FROM uploaded_files
WHERE session_id = 'your_session_id'
ORDER BY upload_date DESC;

-- Get chat history
SELECT query, timestamp, model_ids, run_benchmark
FROM chat_messages
WHERE session_id = 'your_session_id'
ORDER BY timestamp DESC;

-- Get ground truth count per file
SELECT f.filename, COUNT(g.id) as gt_count
FROM uploaded_files f
LEFT JOIN ground_truths g ON f.id = g.file_id
WHERE f.session_id = 'your_session_id'
GROUP BY f.filename;

-- Get benchmark results for a session
SELECT model_id, timestamp, aggregate_metrics
FROM benchmarks
WHERE session_id = 'your_session_id'
ORDER BY timestamp DESC;

-- Get average metrics across all models
SELECT model_id,
       AVG((aggregate_metrics->>'bleu')::float) as avg_bleu,
       AVG((aggregate_metrics->>'rouge_l')::float) as avg_rouge_l,
       AVG((aggregate_metrics->>'mrr')::float) as avg_mrr
FROM benchmarks
GROUP BY model_id;
```

### 8.6 Backup and Restore

**Backup PostgreSQL Database:**
```bash
pg_dump -U postgres rag_benchmark > backup_$(date +%Y%m%d_%H%M%S).sql
```

**Restore from Backup:**
```bash
psql -U postgres -d rag_benchmark < backup.sql
```

**Backup All PDFs and Indices:**
```bash
tar -czf rag_data_backup_$(date +%Y%m%d).tar.gz data/uploads/ data/indices/
```

### 8.7 API Compatibility

**No breaking changes!** All existing endpoints work identically with database backend:

| Endpoint | Data Source |
|----------|---|
| `POST /api/upload` | Saves file metadata to PostgreSQL |
| `POST /api/query` | Saves chat messages to PostgreSQL |
| `POST /api/benchmark` | Saves results to PostgreSQL |
| `GET /api/sessions` | Reads sessions from PostgreSQL |
| `GET /api/session/{id}` | Reads session data from PostgreSQL |
| `GET /api/chat_history/{id}` | Reads chat from PostgreSQL |

---

## 8a. ORIGINAL API REFERENCE

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves the web UI |
| `/api/models` | GET | Lists available LLM models |
| `/api/sessions` | GET | Lists all active sessions |
| `/api/session/{id}` | GET | Returns full session data |
| `/api/upload` | POST | Upload PDFs, extract, index |
| `/api/query` | POST | Query RAG pipeline with multi-model |
| `/api/benchmark` | POST | Run full benchmark on ground-truth |
| `/api/chat_history/{id}` | GET | Returns chat history for session |

---

## 9. INSTALLATION & SETUP GUIDE

### 9.1 System Requirements

- **Python**: 3.9 or higher
- **PostgreSQL**: 12 or higher (server, not just client)
- **Disk Space**: 500MB minimum (2GB+ recommended)
- **RAM**: 2GB minimum (4GB+ recommended for models)
- **Network**: Internet access for OpenRouter API

### 9.2 PostgreSQL Installation

#### macOS

```bash
# Install PostgreSQL using Homebrew
brew install postgresql

# Start PostgreSQL service
brew services start postgresql

# Verify installation
pg_isready
# Expected: accepting connections

# Test connection
psql --version
# Expected: psql (PostgreSQL) 15.x or higher
```

#### Linux (Ubuntu/Debian)

```bash
# Update package manager
sudo apt-get update

# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Verify PostgreSQL started
sudo systemctl status postgresql
# Expected: active (running)

# Enable on boot
sudo systemctl enable postgresql

# Verify installation
psql --version
```

#### Linux (Fedora/RHEL)

```bash
# Install PostgreSQL
sudo dnf install postgresql-server postgresql-contrib

# Initialize database
sudo postgresql-setup initdb

# Start and enable service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### Windows

1. Download PostgreSQL installer from https://www.postgresql.org/download/windows/
2. Run the installer
3. During installation:
   - Set a password for the "postgres" user (save this!)
   - Accept default port 5432
   - Choose "all" optional components
4. Complete installation
5. PostgreSQL service will start automatically

### 9.3 Database Creation

The `run.sh` script handles database creation automatically. However, if you prefer manual setup:

#### Option A: Automatic Setup (Recommended - use run.sh)

The main `run.sh` script includes all database setup:
```bash
./run.sh
```

This handles:
- [OK] PostgreSQL installation check
- [OK] PostgreSQL server startup
- [OK] Database creation
- [OK] Dependency installation
- [OK] Server launch

#### Option B: Manual Setup

**macOS/Linux:**
```bash
# Connect to PostgreSQL
psql -U postgres

# In the psql prompt:
CREATE DATABASE rag_benchmark;
\q
```

**Windows (using pgAdmin):**
1. Open pgAdmin (installed with PostgreSQL)
2. Right-click "Databases" → "Create" → "Database"
3. Enter name: `rag_benchmark`
4. Click "Save"

### 9.4 Verify Database Creation

```bash
# List all databases
psql -U postgres -l

# You should see "rag_benchmark" in the list

# Connect to the new database
psql -U postgres -d rag_benchmark

# Test connection
SELECT 1;
# Expected: 1

# Exit psql
\q
```

### 9.5 Configure Python Application

#### 1. Verify or Update .env File

```bash
# Check current .env
cat .env
```

Ensure it contains:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag_benchmark
OPENROUTER_API_KEY=your_api_key_here
EMBEDDING_MODEL=all-MiniLM-L6-v2
HOST=0.0.0.0
PORT=8000
```

If using different PostgreSQL credentials, update the DATABASE_URL:
```env
DATABASE_URL=postgresql://[username]:[password]@[host]:[port]/[database]
```

#### 2. Verify or Install Python Dependencies

```bash
# Check Python version
python3 --version
# Should be 3.9 or higher

# Verify or create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Install requirements
pip install -r app/requirements.txt
```

This installs:
- `sqlalchemy==2.0.23` (ORM)
- `psycopg2-binary==2.9.10` (PostgreSQL driver)
- All other dependencies (FastAPI, torch, sentence-transformers, etc.)

#### 3. Verify Installation

```bash
# Check SQLAlchemy
python -c "import sqlalchemy; print(sqlalchemy.__version__)"
# Expected: 2.0.23

# Check psycopg2
python -c "import psycopg2; print(psycopg2.__version__)"
# Expected: 2.9.x or higher

# Check SQLAlchemy can connect
python -c "from sqlalchemy import create_engine; engine = create_engine('postgresql://postgres:postgres@localhost:5432/rag_benchmark'); print('Connection OK')"
# Expected: Connection OK
```

---

## 10. DOCKER DEPLOYMENT

### 10.1 Build Docker Image

```bash
# Build the Docker image
docker build -t rag-benchmark:latest .

# Verify image was created
docker images | grep rag-benchmark
```

### 10.2 Run with Docker Compose (with PostgreSQL)

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: rag_benchmark
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  rag-app:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/rag_benchmark
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
      HOST: 0.0.0.0
      PORT: 8000
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env
    command: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

volumes:
  postgres_data:
```

Run with Docker Compose:

```bash
# Set your API key first
export OPENROUTER_API_KEY="your_api_key_here"

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f rag-app

# Stop services
docker-compose down
```

### 10.3 Run Docker Container Standalone

```bash
# Run PostgreSQL separately
docker run -d \
  --name pg-rag \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=rag_benchmark \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:15-alpine

# Wait for PostgreSQL to start
sleep 10

# Run the RAG application
docker run -d \
  --name rag-app \
  -e DATABASE_URL=postgresql://postgres:postgres://localhost:5432/rag_benchmark \
  -e OPENROUTER_API_KEY=your_api_key_here \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --link pg-rag:postgres \
  rag-benchmark:latest
```

### 10.4 Docker Management

```bash
# View running containers
docker ps

# View container logs
docker logs rag-app

# Stop container
docker stop rag-app

# Remove container
docker rm rag-app

# Remove image
docker rmi rag-benchmark:latest

# Docker cleanup
docker system prune -a
```

---

## 11. RUNNING THE APPLICATION

### 11.1 Quick Start (All-in-One)

```bash
# Navigate to project directory
cd /path/to/rag-benchmark-system

# Make run script executable
chmod +x run.sh

# Execute the run script
./run.sh
```

The `run.sh` script automatically:
1. Checks Python 3 installation
2. Creates/activates virtual environment
3. Upgrades pip and setuptools
4. Installs all dependencies
5. Creates data directories
6. Configures .env if needed
7. Checks/starts PostgreSQL
8. Creates database if needed
9. Launches the FastAPI server

### 11.2 Manual Setup & Execution

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r app/requirements.txt

# Create data directories
mkdir -p data/uploads data/indices data/results data/chats

# Verify PostgreSQL is running
pg_isready
# Output: accepting connections

# Create database if not exists
psql -U postgres -c "CREATE DATABASE rag_benchmark;"

# Update .env with your API key
export OPENROUTER_API_KEY="sk-or-v1-your-key"

# Launch the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 11.3 Access the Application

Once the server is running:

- **Web UI**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc

### 11.4 Configuration Options

Edit `.env` to customize:

```env
# API Configuration
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Embedding Model
EMBEDDING_MODEL=all-MiniLM-L6-v2
# Other options: all-MiniLM-L12-v2, all-mpnet-base-v2, etc.

# Server Configuration
HOST=0.0.0.0          # Accessible from any IP
PORT=8000             # Port to listen on

# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag_benchmark
# Format: postgresql://username:password@host:port/database
```

### 11.5 Troubleshooting Startup

**Issue: "PostgreSQL not running"**
```bash
# macOS
brew services start postgresql

# Linux
sudo systemctl start postgresql

# Windows
# Start PostgreSQL service from Services app
```

**Issue: "Could not connect to database"**
```bash
# Verify database exists
psql -U postgres -l | grep rag_benchmark

# Create if missing
psql -U postgres -c "CREATE DATABASE rag_benchmark;"

# Test connection
psql -U postgres -d rag_benchmark -c "SELECT 1;"
```

**Issue: "ModuleNotFoundError"**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r app/requirements.txt --force-reinstall
```

**Issue: "Port 8000 already in use"**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process (macOS/Linux)
kill -9 <PID>

# Or use a different port
python -m uvicorn app.main:app --port 8001
```

---

## 12. END-TO-END WORKFLOW

```mermaid
flowchart TD
    A["Step 1: Launch Server\nrun.sh or docker-compose up"] --> B["Step 2: Open Browser\nhttp://localhost:8000"]
    B --> C["Step 3: Upload PDFs\nDrag & drop or browse"]
    C --> D["Step 4: Configure Extraction Parameters\nchunk_size, overlap, etc."]
    D --> E["Step 5: Click Upload & Index\nBuilds FAISS + extracts ground truth"]
    E --> F["Step 6: Select LLM Models\nChoose 1 or more models"]
    F --> G["Step 7: Enter Your Query\nType question in text area"]
    G --> H["Step 8: View Results\nAnswers + sources + latency"]
    H --> I{"Run Benchmarks?"}
    I -->|"Yes"| J["Step 9: Full Benchmark\nEvaluate all ground truth pairs"]
    I -->|"No"| K["Step 9: Continue Querying"]
    J --> L["Step 10: Review Metrics\nBLEU, ROUGE-L, MRR, Hit Rate, etc."]
    L --> M["Data Persisted in PostgreSQL"]
    K --> G
    M --> N["Access Chat History & Results"]
```

---

## 13. DIRECTORY STRUCTURE

```
rag-benchmark-system/
├── Dockerfile                        # Docker containerization
├── run.sh                            # All-in-one setup & launch script
├── docker-compose.yml                # Optional: Docker Compose configuration
├── .env                              # Environment variables & API keys
├── .gitignore                        # Git ignore rules
│
├── app/                              # Python application
│   ├── __init__.py
│   ├── main.py                       # FastAPI application & routes
│   ├── config.py                     # Configuration settings
│   ├── database.py                   # SQLAlchemy ORM models
│   ├── pdf_processor.py              # PDF extraction (text/images/tables)
│   ├── embeddings.py                 # Embedding & FAISS indexing
│   ├── llm_client.py                 # OpenRouter LLM client
│   ├── benchmarks.py                 # Evaluation metrics
│   ├── requirements.txt              # Python dependencies
│   ├── templates/
│   │   └── index.html                # Web UI HTML template
│   └── static/
│       ├── css/
│       │   └── style.css             # Styling & responsive design
│       └── js/
│           └── app.js                # Frontend logic & interactions
│
├── data/                             # Data storage (created by app)
│   ├── uploads/                      # Uploaded PDF files
│   ├── indices/                      # FAISS vector indices (.faiss)
│   ├── results/                      # Benchmark results
│   └── chats/                        # Chat persistence
│
└── venv/                             # Python virtual environment (created by run.sh)
```

### Key Files Explained

| File/Directory | Purpose |
|---|---|
| **Dockerfile** | Containerizes app for Docker deployment |
| **run.sh** | Single command to setup & launch everything (includes DB creation) |
| **docker-compose.yml** | Defines PostgreSQL + app services for Docker Compose |
| **.env** | API keys, database URL, server config |
| **app/main.py** | FastAPI routes & session management |
| **app/database.py** | SQLAlchemy models for PostgreSQL persistence |
| **app/pdf_processor.py** | Text/image/table extraction from PDFs |
| **app/embeddings.py** | Vector embeddings & FAISS index management |
| **app/llm_client.py** | Integration with OpenRouter API |
| **app/benchmarks.py** | 8 evaluation metrics implementation |
| **app/templates/index.html** | Web UI template |
| **app/static/** | CSS styling & JavaScript client logic |
| **data/** | Persisted data (PDFs, indices, results) |
| **venv/** | Python virtual environment |

---

## 14. ADDITIONAL CHANGES & ENHANCEMENTS

### 14.1 Completed Enhancements

The following enhancements have been completed beyond the original requirements:

| # | Enhancement | Rationale | Component |
|---|---|---|---|
| 1 | PostgreSQL database integration | Persistent data across server restarts | app/database.py |
| 2 | Docker containerization | Easy deployment on any system | Dockerfile |
| 3 | Automated setup with run.sh | Single-command deployment | run.sh |
| 4 | Added table extraction | Structured data in academic PDFs | app/pdf_processor.py |
| 5 | Sliding-window chunking with overlap | Prevent info loss at boundaries | app/pdf_processor.py |
| 6 | Automatic ground-truth extraction | No manual annotation needed | app/pdf_processor.py |
| 7 | L2-normalized embeddings | Fast cosine similarity via FAISS | app/embeddings.py |
| 8 | Over-retrieve then filter | Improve precision without losing recall | app/embeddings.py |
| 9 | Per-PDF index files | Independent document management | app/embeddings.py |
| 10 | 8 evaluation metrics | Lexical, semantic, and retrieval quality | app/benchmarks.py |
| 11 | Aggregate statistics | Min/mean/max per metric type | app/main.py |
| 12 | Session management | Multi-user support | app/main.py |
| 13 | Chat history persistence | Revisit past queries | app/main.py |
| 14 | Drag-and-drop uploads | Better UX | app/static/js/app.js |
| 15 | Responsive UI | Mobile/tablet/desktop | app/static/css/style.css |
| 16 | Keyboard shortcuts | Faster interaction | app/static/js/app.js |
| 17 | Latency tracking | Performance metrics | app/llm_client.py |
| 18 | Token usage reporting | Cost analysis | app/llm_client.py |
| 19 | Source citations in prompts | Ground responses in context | app/main.py |
| 20 | Docker support | Production deployment | Dockerfile |
| 21 | Database backup scripts | Data protection | (documented above) |
| 22 | Comprehensive documentation | System understanding | REPORT.md |

### 14.2 What Was Migrated from In-Memory to PostgreSQL

**Before (In-Memory):**
- Sessions stored in `_sessions` dict (lost on restart)
- Chats and benchmarks as list/dict (no persistence)
- No concurrent user support
- No queryable history

**After (PostgreSQL):**
- All sessions persisted with relationships
- Chat history fully queryable
- Support for multiple concurrent users
- Standard SQL backups available
- Data survives server restarts
- Easy scaling to production

---

## 15. TROUBLESHOOTING

### General Issues

**Q: "Could not connect to database"**
```bash
# Verify PostgreSQL is running
pg_isready
# Output should be: accepting connections

# Verify database exists
psql -U postgres -l | grep rag_benchmark

# Create if missing
psql -U postgres -c "CREATE DATABASE rag_benchmark;"

# Check DATABASE_URL in .env
cat .env | grep DATABASE_URL
```

**Q: "ModuleNotFoundError: No module named sqlalchemy"**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r app/requirements.txt
```

**Q: "Port 8000 already in use"**
```bash
# Find what's using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use different port
python -m uvicorn app.main:app --port 8001
```

**Q: "OPENROUTER_API_KEY not set"**
```bash
# Update .env file
echo "OPENROUTER_API_KEY=sk-or-v1-your-key" >> .env

# Or export in current shell
export OPENROUTER_API_KEY="sk-or-v1-your-key"
```

### Docker Issues

**Q: "Docker: command not found"**
```bash
# Install Docker from https://www.docker.com/products/docker-desktop
# or for Linux: sudo apt-get install docker.io
```

**Q: "Database host not found in Docker"**
- Ensure docker-compose.yml uses service name `postgres` as hostname
- Or use `--link pg-rag:postgres` flag when running container

**Q: "Permission denied while trying to connect to Docker daemon"**
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
# Logout and login again for group change to take effect
```

### Performance Issues

**Q: "Slow embeddings generation"**
- This is normal for first run (model download: ~400MB)
- Subsequent runs use cached model
- Consider using GPU if available: set `CUDA_VISIBLE_DEVICES=0`

**Q: "High memory usage"**
- Torch and transformer models require significant memory
- Recommended: 4GB+ RAM
- Consider running on machine with GPU for faster inference

**Q: "Slow FAISS indexing"**
- Normal for large documents
- FAISS operations are optimized; no configuration needed
- Per-PDF indices allow parallel uploads

---

## 16. LIMITATIONS & FUTURE WORK

### Current Limitations

1. **Ground-truth extraction** relies on heuristics
   - Q&A patterns and section headings may miss complex structures
   - Manually curated pairs would improve benchmark reliability
   - Solution: Manual review interface planned for future

2. **Image understanding** stores metadata only
   - No actual vision-language model integration yet
   - Current: Image hashes + dimensions extracted
   - Planned: GPT-4o Vision integration for true multimodal RAG

3. **Concurrent model querying** is sequential
   - Models queried one at a time
   - Increases total latency for multi-model comparisons
   - Planned: Async parallel dispatch for next version

4. **BERTScore** not in evaluation loop
   - Dependency installed but not wired up
   - Computational cost too high for real-time queries
   - Planned: Optional offline evaluation mode

5. **Horizontal scalability** requires infrastructure
   - Single instance only (no clustering)
   - Database can handle concurrent users but no auto-scaling
   - Solution: Containerized deployment recommended

### Future Enhancements

- [ ] Vision-language model integration (GPT-4o Vision)
- [ ] Parallel model querying with async/await
- [ ] GraphQL API alongside REST
- [ ] Kubernetes deployment manifests
- [ ] Real-time query streaming
- [ ] Advanced visualizations (t-SNE, UMAP for embeddings)
- [ ] User authentication & multi-tenant support
- [ ] Cost tracking dashboard for OpenRouter API
- [ ] Evaluation result caching
- [ ] Custom metric plugins

---

## 17. REFERENCES

1. Lewis, P. et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS.
2. Papineni, K. et al. (2002). *BLEU: A Method for Automatic Evaluation of Machine Translation*. ACL.
3. Lin, C.Y. (2004). *ROUGE: A Package for Automatic Evaluation of Summaries*. ACL Workshop.
4. Zhang, T. et al. (2020). *BERTScore: Evaluating Text Generation with BERT*. ICLR.
5. Es, S. et al. (2024). *RAGAS: Automated Evaluation of Retrieval Augmented Generation*. EACL.
6. Johnson, J. et al. (2019). *Billion-scale Similarity Search with GPUs*. IEEE Big Data.
7. PostgreSQL Documentation: https://www.postgresql.org/docs/
8. SQLAlchemy Documentation: https://docs.sqlalchemy.org/
9. FastAPI Documentation: https://fastapi.tiangolo.com/
10. Docker Documentation: https://docs.docker.com/

---

## APPENDIX: QUICK REFERENCE

### Commands

**Setup & Run:**
```bash
./run.sh                                    # Complete setup & launch
docker-compose up -d                        # Docker deployment
```

**Database Management:**
```bash
psql -U postgres -d rag_benchmark           # Connect to DB
pg_dump -U postgres rag_benchmark > backup.sql  # Backup
psql -U postgres -d rag_benchmark < backup.sql  # Restore
```

**Application Control:**
```bash
source venv/bin/activate                    # Activate venv
python -m uvicorn app.main:app --reload     # Dev server
python -m uvicorn app.main:app              # Production
```

### Endpoints

- **UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Upload**: POST /api/upload
- **Query**: POST /api/query
- **Benchmark**: POST /api/benchmark

### Default Credentials

- **PostgreSQL User**: postgres
- **PostgreSQL Password**: postgres
- **Database Name**: rag_benchmark
- **Server Host**: 0.0.0.0
- **Server Port**: 8000

---

*Report generated for academic evaluation and production deployment. System version 1.2.0 with PostgreSQL persistence, Docker containerization, and production-ready cleanup.*

**Last Updated**: May 2026
**Status**: Production Ready [OK]
**Key Optimizations**: 
- Removed all setup script dependencies (consolidated into `run.sh`)
- Cleaned Dockerfile (removed comments for production efficiency)
- Merged all documentation into single REPORT.md
- Removed redundant files (setup_postgres.sh, 5 separate .md files)

**Deployment Options**: Standalone, Docker, Docker Compose
**Execution**: Single command - `./run.sh`
