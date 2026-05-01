# PostgreSQL Migration - Quick Start Guide

## What Changed

Your RAG Benchmark system has been updated to use PostgreSQL for persistent data storage instead of in-memory storage. This means all your data (sessions, chats, uploaded files, ground truths, benchmarks) will now survive server restarts.

## Key Changes

### 1. **New Database Models** (`app/database.py`)
- `Session`: User session tracking
- `UploadedFile`: PDF metadata and processing status  
- `GroundTruth`: Q&A pairs extracted from PDFs
- `ChatMessage`: Query history with all responses
- `Benchmark`: Evaluation results

### 2. **Updated Core Files**
- `app/main.py`: All endpoints now use database instead of in-memory dict
- `app/config.py`: Added `DATABASE_URL` configuration
- `app/requirements.txt`: Added `sqlalchemy` and `psycopg2-binary`
- `.env`: Added `DATABASE_URL` setting

### 3. **New Setup Files**
- `setup_postgres.sh`: Script to initialize PostgreSQL
- `DB_SETUP.md`: Comprehensive database documentation

## Quick Start (5 minutes)

### Step 1: Install PostgreSQL

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Linux:**
```bash
sudo apt-get install postgresql
sudo systemctl start postgresql
```

### Step 2: Create Database

```bash
chmod +x setup_postgres.sh
./setup_postgres.sh
```

Or manually:
```bash
psql -U postgres -c "CREATE DATABASE rag_benchmark;"
```

### Step 3: Install Dependencies

```bash
pip install -r app/requirements.txt
```

### Step 4: Start Server

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**That's it!** The database tables will be created automatically on first run.

## Verification

### Check PostgreSQL is Running

```bash
pg_isready
```
Should output: `accepting connections`

### Check Database Connection

```bash
psql -U postgres -d rag_benchmark -c "SELECT 1;"
```

### Test the API

1. Open http://localhost:8000
2. Upload a PDF
3. Enter a query
4. Data should now persist in PostgreSQL

### Query the Database

```bash
psql -U postgres -d rag_benchmark

# View all sessions
SELECT id, created_at FROM sessions;

# View uploaded files
SELECT filename, index_status FROM uploaded_files;

# View chat messages
SELECT query, timestamp FROM chat_messages;
```

## Data Locations

| Data | Location |
|------|----------|
| Session/Chat/Benchmark Data | PostgreSQL database |
| PDF Files | `data/uploads/` (filesystem) |
| FAISS Indices | `data/indices/` (filesystem) |
| Configuration | `.env` file |

## Migration from Old Version

If you have existing session data in memory:

1. Back up your old data (take screenshots/notes of queries/results)
2. The new system starts fresh with an empty database
3. Old FAISS indices in `data/indices/` will still work
4. You can manually re-upload PDFs if needed

## Troubleshooting

### "could not connect to database"
- Verify PostgreSQL is running: `pg_isready`
- Check `.env` has correct `DATABASE_URL`
- Verify database exists: `psql -l`

### "database does not exist"
```bash
psql -U postgres -c "CREATE DATABASE rag_benchmark;"
```

### "role postgres does not exist"  
```bash
createuser -U postgres postgres
psql -U postgres -d rag_benchmark
```

### Tables not appearing
- Check server logs for startup errors
- Tables are auto-created on first server run
- Force recreate: delete database, server will recreate it

## Features Now Available

✅ **Persistent Sessions** - Queries survive server restarts
✅ **Chat History** - Full query/response history stored
✅ **Benchmark Tracking** - All evaluation results saved
✅ **Multi-User Support** - Multiple concurrent sessions
✅ **Data Queries** - SQL queries on chat history and benchmarks
✅ **Scalability** - Database handles large deployments

## Next Steps

1. Follow the Quick Start above
2. Test the system with a PDF upload and query
3. Read `DB_SETUP.md` for advanced configuration
4. Check `app/database.py` for schema details
5. Set up regular backups for production use

## Need Help?

- Check `DB_SETUP.md` for detailed documentation
- Review `app/database.py` for the data model
- Look at `app/main.py` to see how database is used
- PostgreSQL docs: https://www.postgresql.org/docs/

---

**Questions or Issues?** Check the error messages in server logs - they'll point you to the right configuration.
