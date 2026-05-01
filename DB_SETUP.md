# PostgreSQL Database Integration

This document explains the database integration for the RAG Benchmark system.

## Overview

The system has been updated to persist all data in PostgreSQL instead of storing it in-memory or as loose files. This includes:

- **Sessions**: User session tracking
- **Uploaded Files**: PDF file metadata and processing status
- **Ground Truths**: Q&A pairs extracted from PDFs
- **Chat Messages**: Query history with responses from multiple models
- **Benchmarks**: Evaluation metrics and results

## Database Schema

### Tables

#### `sessions`
- `id` (String, PK): Unique session identifier
- `created_at` (DateTime): Session creation timestamp
- `updated_at` (DateTime): Last update timestamp
- **Relationships**: Has many files, chats, and benchmarks

#### `uploaded_files`
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
- `index_path` (String): Path to FAISS index file
- `metadata_path` (String): Path to metadata pickle file
- `index_status` (String): Status of indexing ("pending", "indexed", "error")
- `text_chunk_size` (Integer): Chunk size used for extraction
- `text_chunk_overlap` (Integer): Overlap used for extraction
- `image_chunk_size` (Integer): Image metadata chunk size
- **Relationships**: Has many ground truths; belongs to session

#### `ground_truths`
- `id` (String, PK): Unique ground truth identifier
- `file_id` (String, FK): Associated uploaded file
- `question` (Text): The question
- `answer` (Text): The reference answer
- `extraction_method` (String): How it was extracted ("qa_pattern" or "section_heading")
- `created_at` (DateTime): Creation timestamp
- **Relationships**: Belongs to uploaded_file

#### `chat_messages`
- `id` (String, PK): Unique chat message identifier
- `session_id` (String, FK): Associated session
- `query` (Text): The user's query
- `timestamp` (DateTime): When the query was made
- `top_k` (Integer): Number of top chunks retrieved
- `temperature` (Integer): Temperature * 10 (stored as int for space efficiency)
- `cosine_threshold` (Integer): Threshold * 100
- `model_ids` (String): Comma-separated list of models queried
- `responses` (JSON): Full response objects from all models
- `run_benchmark` (Boolean): Whether benchmarking was requested
- **Relationships**: Belongs to session

#### `benchmarks`
- `id` (String, PK): Unique benchmark identifier
- `session_id` (String, FK): Associated session
- `chat_message_id` (String, Nullable): Associated chat message if from a chat query
- `model_id` (String): Which model was evaluated
- `timestamp` (DateTime): When benchmark was run
- `max_questions` (Integer): Number of questions evaluated
- `top_k` (Integer): Number of chunks retrieved per question
- `aggregate_metrics` (JSON): Aggregated benchmark metrics (mean, min, max for each metric)
- `detailed_results` (JSON): Per-question results
- **Relationships**: Belongs to session

## Setup Instructions

### 1. Install PostgreSQL

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**Windows:**
- Download installer from https://www.postgresql.org/download/windows/
- Follow installation wizard

### 2. Create Database and User

Run the provided setup script:

```bash
chmod +x setup_postgres.sh
./setup_postgres.sh
```

Or manually:

```bash
# Connect to PostgreSQL
psql -U postgres

# In the psql prompt:
CREATE DATABASE rag_benchmark;
\q
```

### 3. Update .env File

Ensure your `.env` file contains:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag_benchmark
```

Modify if you used different credentials during setup.

### 4. Install Python Dependencies

```bash
pip install -r app/requirements.txt
```

This will install SQLAlchemy and psycopg2-binary (PostgreSQL driver).

### 5. Start the Server

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The database tables will be automatically created on the first run (via the `startup_event`).

## Data Storage

### Where Data is Stored

| Data Type | Storage |
|-----------|---------|
| Session metadata | PostgreSQL |
| Uploaded PDF files | Filesystem (`data/uploads/`) |
| FAISS indices | Filesystem (`data/indices/`) |
| Chat history | PostgreSQL |
| Ground truths | PostgreSQL |
| Benchmark results | PostgreSQL |

### Benefits of This Approach

1. **Durability**: Data persists across server restarts
2. **Scalability**: Easy to support multiple concurrent users
3. **Queryability**: SQL queries on chat history and benchmarks
4. **Efficiency**: Indexing and relationships built into the database
5. **Backups**: Standard PostgreSQL backup tools available

## Querying the Database

### Connect to PostgreSQL

```bash
psql -U postgres -d rag_benchmark
```

### Useful Queries

**List all sessions:**
```sql
SELECT id, created_at, updated_at FROM sessions;
```

**Get files uploaded in a session:**
```sql
SELECT filename, file_size, text_chunks_count, index_status 
FROM uploaded_files 
WHERE session_id = 'your_session_id';
```

**Get chat history:**
```sql
SELECT query, timestamp, model_ids, run_benchmark 
FROM chat_messages 
WHERE session_id = 'your_session_id' 
ORDER BY timestamp DESC;
```

**Get benchmark aggregates:**
```sql
SELECT model_id, timestamp, aggregate_metrics 
FROM benchmarks 
WHERE session_id = 'your_session_id';
```

**Get ground truth count per file:**
```sql
SELECT filename, COUNT(*) as gt_count 
FROM uploaded_files 
LEFT JOIN ground_truths ON uploaded_files.id = ground_truths.file_id 
WHERE uploaded_files.session_id = 'your_session_id' 
GROUP BY filename;
```

## Migration from In-Memory Storage

If you had data in the old in-memory format and want to migrate it:

1. Export old session data to JSON
2. Create a migration script to convert to new format
3. Insert into PostgreSQL

Example migration script can be provided on request.

## Troubleshooting

### "could not connect to database"

- Verify PostgreSQL is running: `pg_isready`
- Check DATABASE_URL in .env
- Verify database exists: `psql -l`

### "role "postgres" does not exist"

- Create the user: `createuser -U postgres postgres`
- Or use your system user: `psql -U $USER`

### "database "rag_benchmark" does not exist"

- Create it: `createdb -U postgres rag_benchmark`
- Or run: `./setup_postgres.sh`

### Tables not created

- Check server startup logs for errors
- Tables are created automatically when server starts
- Force recreate: Delete database and let it auto-create

## Backup and Restore

### Backup Database

```bash
pg_dump -U postgres rag_benchmark > backup.sql
```

### Restore Database

```bash
psql -U postgres < backup.sql
```

## Performance Optimization

For large deployments, consider:

1. **Indexes**: Add indexes to frequently queried columns (query, timestamp, session_id)
2. **Connection pooling**: Use PgBouncer or SQLAlchemy's connection pool settings
3. **Archiving**: Archive old sessions/results to a separate table or archive database
4. **Monitoring**: Use pgAdmin or pg_stat_statements for query analysis

## Next Steps

1. ✅ PostgreSQL is now configured
2. ✅ Database schema is created automatically
3. Run the application and test with `/api/upload` and `/api/query`
4. Query the database to verify data storage
5. Set up regular backups for production use
