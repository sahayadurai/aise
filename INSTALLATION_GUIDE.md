# PostgreSQL Installation & Setup - Complete Guide

## System Requirements

- Python 3.9+
- PostgreSQL 12+ (database server)
- 500MB free disk space (minimum)
- 2GB RAM (recommended)

## Step-by-Step Installation

### Phase 1: Install PostgreSQL (15 minutes)

#### macOS Users

```bash
# 1. Install PostgreSQL using Homebrew
brew install postgresql

# 2. Start PostgreSQL service
brew services start postgresql

# 3. Verify installation
pg_isready
# Expected output: accepting connections

# 4. Test connection
psql --version
# Expected output: psql (PostgreSQL) 15.x or higher
```

#### Linux (Ubuntu/Debian) Users

```bash
# 1. Update package manager
sudo apt-get update

# 2. Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# 3. Verify PostgreSQL started
sudo systemctl status postgresql
# Expected: active (running)

# 4. Enable on boot
sudo systemctl enable postgresql

# 5. Verify installation
psql --version
```

#### Linux (Fedora/RHEL) Users

```bash
# 1. Install PostgreSQL
sudo dnf install postgresql-server postgresql-contrib

# 2. Initialize database
sudo postgresql-setup initdb

# 3. Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 4. Verify
psql --version
```

#### Windows Users

1. Download PostgreSQL installer from https://www.postgresql.org/download/windows/
2. Run the installer
3. During installation:
   - Set password for "postgres" user (remember this!)
   - Accept default port 5432
   - Choose "all" optional components
4. Complete installation
5. PostgreSQL service will start automatically

---

### Phase 2: Create Database (5 minutes)

#### Option A: Automated Setup (Recommended)

```bash
cd /path/to/rag-benchmark-system

# Make script executable (macOS/Linux only)
chmod +x setup_postgres.sh

# Run setup script
./setup_postgres.sh
```

This script will:
- ✅ Verify PostgreSQL is running
- ✅ Create the database
- ✅ Display connection details

#### Option B: Manual Setup

**macOS/Linux:**

```bash
# Connect to PostgreSQL as default user
psql -U postgres

# In the psql prompt, run:
CREATE DATABASE rag_benchmark;
\q
```

**Windows (using pgAdmin):**

1. Open pgAdmin (installed with PostgreSQL)
2. Right-click "Databases" → "Create" → "Database"
3. Enter name: `rag_benchmark`
4. Click "Save"

---

### Phase 3: Verify Database Creation (2 minutes)

```bash
# List all databases
psql -U postgres -l

# You should see "rag_benchmark" in the list

# Connect to the new database
psql -U postgres -d rag_benchmark

# In psql prompt, test connection
SELECT 1;
# Expected output: 1

# Exit psql
\q
```

---

### Phase 4: Configure Python Application (5 minutes)

#### 1. Verify .env File

```bash
cat .env
```

Should contain:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag_benchmark
```

If using non-default credentials, update accordingly:
```env
DATABASE_URL=postgresql://[username]:[password]@[host]:[port]/[database]
```

#### 2. Install Python Dependencies

```bash
# Activate virtual environment (if using one)
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Install requirements
pip install -r app/requirements.txt
```

This will install:
- sqlalchemy==2.0.23 (ORM)
- psycopg2-binary==2.9.10 (PostgreSQL driver)
- All other dependencies

#### 3. Verify Installation

```bash
# Check SQLAlchemy installed
python -c "import sqlalchemy; print(sqlalchemy.__version__)"
# Expected: 2.0.23

# Check psycopg2 installed
python -c "import psycopg2; print(psycopg2.__version__)"
# Expected: 2.9.x or higher
```

---

### Phase 5: Start Application (2 minutes)

```bash
# Make sure venv is activated
source venv/bin/activate

# Start the server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

🎉 **The database is now initialized automatically!** Tables will be created on first run.

---

### Phase 6: Test the System (5 minutes)

#### 1. Open Web Interface

- Open browser: http://localhost:8000
- You should see the RAG Benchmark interface

#### 2. Upload a Test PDF

1. Click "Upload PDFs"
2. Select a PDF file
3. Click "Upload"
4. Verify: File appears in the interface

#### 3. Verify Database Storage

In a new terminal:

```bash
# Connect to database
psql -U postgres -d rag_benchmark

# View uploaded files
SELECT filename, index_status FROM uploaded_files;

# View sessions
SELECT id, created_at FROM sessions;

# Exit
\q
```

✅ If you see your uploaded file, database integration is working!

#### 4. Test Query

1. Back in web interface
2. Select a model (e.g., GPT-4o)
3. Enter a query about the PDF
4. Click "Query"
5. Verify response appears

Then check database:

```bash
psql -U postgres -d rag_benchmark -c "SELECT query, timestamp FROM chat_messages;"
```

✅ If you see your query, the system is fully operational!

---

## Verification Checklist

- [ ] PostgreSQL installed: `psql --version`
- [ ] PostgreSQL running: `pg_isready`
- [ ] Database exists: `psql -l | grep rag_benchmark`
- [ ] Python packages installed: `pip list | grep sqlalchemy`
- [ ] .env configured: `grep DATABASE_URL .env`
- [ ] Server starts: `python -m uvicorn app.main:app --reload`
- [ ] Can upload PDF: Test via web interface
- [ ] Data in database: `SELECT * FROM sessions;`
- [ ] Can query: Test via web interface
- [ ] Chat history saved: `SELECT * FROM chat_messages;`

---

## Common Issues & Solutions

### Issue: "could not connect to the database"

**Cause**: PostgreSQL not running or wrong credentials

**Solution**:
```bash
# Check if PostgreSQL is running
pg_isready
# Should output: accepting connections

# If not running, start it
brew services start postgresql  # macOS
sudo systemctl start postgresql # Linux
```

### Issue: "database "rag_benchmark" does not exist"

**Cause**: Database was not created

**Solution**:
```bash
psql -U postgres -c "CREATE DATABASE rag_benchmark;"
```

### Issue: "role "postgres" does not exist"

**Cause**: Different PostgreSQL user setup

**Solution**:
```bash
# List existing roles
psql -U postgres -c "\du"

# Use an existing role in .env
# Example: DATABASE_URL=postgresql://your_username:password@localhost:5432/rag_benchmark
```

### Issue: "psql: command not found"

**Cause**: PostgreSQL not in PATH

**Solution**:
```bash
# macOS
export PATH="/usr/local/opt/postgresql/bin:$PATH"

# Add to ~/.bash_profile or ~/.zshrc for permanent fix
echo 'export PATH="/usr/local/opt/postgresql/bin:$PATH"' >> ~/.zshrc
```

### Issue: Tables not created when server starts

**Cause**: Database permission issue

**Solution**:
```bash
# Check database permissions
psql -U postgres -d rag_benchmark -c "SELECT * FROM sessions;"

# If error, recreate database
psql -U postgres -c "DROP DATABASE rag_benchmark;"
psql -U postgres -c "CREATE DATABASE rag_benchmark;"

# Restart server - tables will be created
python -m uvicorn app.main:app --reload
```

### Issue: "Illegal header value" error when querying

**Cause**: OpenRouter API key not set

**Solution**:
```bash
# Edit .env and add your API key
OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here

# Restart server
```

---

## Next Steps

1. ✅ PostgreSQL installed and running
2. ✅ Database created and configured
3. ✅ Application connected to database
4. Read: `POSTGRES_MIGRATION.md` for feature overview
5. Read: `DB_SETUP.md` for advanced configuration
6. Read: `DATABASE_INTEGRATION.md` for architecture details

---

## Production Deployment Checklist

For production environments:

- [ ] Use strong PostgreSQL password
- [ ] Enable SSL/TLS for database connections
- [ ] Set up automated daily backups
- [ ] Monitor database size and performance
- [ ] Use connection pooling (PgBouncer)
- [ ] Set up database user with limited privileges
- [ ] Enable PostgreSQL logging
- [ ] Regular database maintenance (VACUUM, ANALYZE)
- [ ] Set up monitoring/alerting

---

## Useful PostgreSQL Commands

```bash
# Connect to database
psql -U postgres -d rag_benchmark

# Backup database
pg_dump -U postgres rag_benchmark > backup.sql

# Restore database
psql -U postgres < backup.sql

# List databases
psql -U postgres -l

# List tables in database
psql -U postgres -d rag_benchmark -c "\dt"

# Query all sessions
psql -U postgres -d rag_benchmark -c "SELECT * FROM sessions;"

# Count records in each table
psql -U postgres -d rag_benchmark -c "
  SELECT 'sessions' as table_name, COUNT(*) as count FROM sessions
  UNION ALL
  SELECT 'uploaded_files', COUNT(*) FROM uploaded_files
  UNION ALL
  SELECT 'chat_messages', COUNT(*) FROM chat_messages
  UNION ALL
  SELECT 'benchmarks', COUNT(*) FROM benchmarks;
"
```

---

## Support Resources

- PostgreSQL Documentation: https://www.postgresql.org/docs/
- SQLAlchemy Documentation: https://docs.sqlalchemy.org/
- psycopg2 Documentation: https://www.psycopg.org/
- pgAdmin (Web UI): https://www.pgadmin.org/

---

**Status**: 🎉 Ready for database-backed RAG system!
