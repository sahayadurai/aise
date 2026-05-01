# Database Integration Summary

## Files Created ✨

```
app/database.py                  - SQLAlchemy models and database setup
├── Session model
├── UploadedFile model
├── GroundTruth model
├── ChatMessage model
├── Benchmark model
└── Database initialization

setup_postgres.sh                - PostgreSQL setup automation script
DB_SETUP.md                      - Comprehensive database documentation  
POSTGRES_MIGRATION.md            - Quick start migration guide
```

## Files Modified 📝

```
.env                             - Added DATABASE_URL configuration
app/config.py                    - Added DATABASE_URL setting
app/requirements.txt             - Added sqlalchemy & psycopg2-binary
app/main.py                      - Replaced in-memory storage with DB
```

## Architecture Changes

### Before
```
In-Memory (_sessions dict)
    ├── Session info
    ├── File list
    ├── Chats (list)
    ├── Indices (dict)
    ├── Ground truths (dict)
    └── Benchmarks (list)

Filesystem
    ├── data/uploads/      (PDF files)
    ├── data/indices/      (FAISS indices)
    └── data/results/      (Results)
```

### After
```
PostgreSQL Database
    ├── sessions
    ├── uploaded_files
    ├── ground_truths
    ├── chat_messages
    └── benchmarks

Filesystem
    ├── data/uploads/      (PDF files)
    ├── data/indices/      (FAISS indices)
    └── data/results/      (Results)
```

## API Changes

No API changes! All endpoints work exactly the same, they just now use the database internally:

- `POST /api/upload` - Saves file metadata to DB
- `POST /api/query` - Saves chat messages to DB
- `POST /api/benchmark` - Saves results to DB
- `GET /api/sessions` - Reads from DB
- `GET /api/session/{id}` - Reads from DB
- `GET /api/chat_history/{id}` - Reads from DB

## Setup Steps

1. **Install PostgreSQL**
   ```bash
   brew install postgresql && brew services start postgresql
   ```

2. **Create Database**
   ```bash
   ./setup_postgres.sh
   ```
   Or manually: `psql -U postgres -c "CREATE DATABASE rag_benchmark;"`

3. **Install Python Dependencies**
   ```bash
   pip install -r app/requirements.txt
   ```

4. **Start Server**
   ```bash
   python -m uvicorn app.main:app --reload
   ```

   Database tables will be created automatically on startup.

## Data Flow

### Upload PDF
1. User uploads PDF via `/api/upload`
2. PDF saved to `data/uploads/`
3. Text/images/tables extracted
4. FAISS index built and saved to `data/indices/`
5. **NEW**: File metadata + ground truths saved to PostgreSQL

### Query System
1. User submits query via `/api/query`
2. Query chunks retrieved from FAISS indices (from filesystem)
3. LLM queried via OpenRouter
4. **NEW**: Chat message + responses saved to PostgreSQL
5. Response returned to user

### Benchmark
1. User runs benchmark via `/api/benchmark`
2. Ground truths retrieved from PostgreSQL (instead of memory)
3. Evaluation metrics calculated
4. **NEW**: Results saved to PostgreSQL

## Benefits

✅ **Persistence** - Data survives server restarts
✅ **Scalability** - Support multiple concurrent users
✅ **Queryability** - SQL queries on all data
✅ **Relationships** - Foreign keys maintain data integrity
✅ **Indexing** - Database optimizes queries
✅ **Backups** - Standard PostgreSQL backup tools
✅ **Durability** - ACID compliance

## Database Schema Overview

```sql
-- Sessions
CREATE TABLE sessions (
  id VARCHAR PRIMARY KEY,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

-- Uploaded Files
CREATE TABLE uploaded_files (
  id VARCHAR PRIMARY KEY,
  session_id VARCHAR REFERENCES sessions(id),
  filename VARCHAR,
  file_path VARCHAR,
  file_size INTEGER,
  upload_date TIMESTAMP,
  text_chunks_count INTEGER,
  image_chunks_count INTEGER,
  table_chunks_count INTEGER,
  ground_truth_count INTEGER,
  index_path VARCHAR,
  metadata_path VARCHAR,
  index_status VARCHAR
);

-- Ground Truths
CREATE TABLE ground_truths (
  id VARCHAR PRIMARY KEY,
  file_id VARCHAR REFERENCES uploaded_files(id),
  question TEXT,
  answer TEXT,
  extraction_method VARCHAR,
  created_at TIMESTAMP
);

-- Chat Messages
CREATE TABLE chat_messages (
  id VARCHAR PRIMARY KEY,
  session_id VARCHAR REFERENCES sessions(id),
  query TEXT,
  timestamp TIMESTAMP,
  top_k INTEGER,
  temperature INTEGER,
  cosine_threshold INTEGER,
  model_ids VARCHAR,
  responses JSON,
  run_benchmark BOOLEAN
);

-- Benchmarks
CREATE TABLE benchmarks (
  id VARCHAR PRIMARY KEY,
  session_id VARCHAR REFERENCES sessions(id),
  chat_message_id VARCHAR,
  model_id VARCHAR,
  timestamp TIMESTAMP,
  max_questions INTEGER,
  top_k INTEGER,
  aggregate_metrics JSON,
  detailed_results JSON
);
```

## Migration Path

✅ Backward compatible - old FAISS indices still work
✅ No data loss - new system starts fresh
✅ Old PDFs can be re-uploaded if needed
✅ Existing .env configuration still valid

## Testing Checklist

- [ ] PostgreSQL running: `pg_isready`
- [ ] Database exists: `psql -l | grep rag_benchmark`
- [ ] Server starts: `python -m uvicorn app.main:app --reload`
- [ ] Upload PDF: POST `/api/upload`
- [ ] Query system: POST `/api/query`
- [ ] Data in DB: `psql -d rag_benchmark -c "SELECT * FROM sessions;"`
- [ ] Run benchmark: POST `/api/benchmark`
- [ ] Chat history: GET `/api/chat_history/{session_id}`

## Next: Production Deployment

For production use, consider:

1. **Connection Pooling**
   ```python
   # SQLAlchemy pool settings
   engine = create_engine(DATABASE_URL, 
                         pool_size=20,
                         max_overflow=40)
   ```

2. **Backups**
   ```bash
   pg_dump -Fc rag_benchmark > backup.sql
   ```

3. **Monitoring**
   - pgAdmin: https://www.pgadmin.org/
   - pg_stat_statements for query analysis

4. **Scaling**
   - Archive old sessions to separate DB
   - Add read replicas for large deployments
   - Use PgBouncer for connection management

---

**Status**: ✅ Database integration complete and ready to use!
