#!/bin/bash
# PostgreSQL Database Setup Script for RAG Benchmark

echo "=========================================="
echo "RAG Benchmark PostgreSQL Setup"
echo "=========================================="

# Check if PostgreSQL is running
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL is not installed. Please install it first."
    echo "   macOS: brew install postgresql"
    echo "   Ubuntu/Debian: sudo apt-get install postgresql"
    exit 1
fi

# Check if postgres service is running
if ! pg_isready -h localhost &> /dev/null; then
    echo "⚠️  PostgreSQL server is not running."
    echo "   Starting PostgreSQL..."
    
    if command -v brew &> /dev/null; then
        brew services start postgresql
    elif command -v systemctl &> /dev/null; then
        sudo systemctl start postgresql
    else
        echo "❌ Could not start PostgreSQL. Please start it manually."
        exit 1
    fi
fi

# Create database and user if they don't exist
echo "🔧 Setting up database and user..."

# Default credentials (from .env)
DB_USER="postgres"
DB_PASSWORD="postgres"
DB_NAME="rag_benchmark"
DB_HOST="localhost"

# Create database
psql -U "$DB_USER" -h "$DB_HOST" <<EOF
-- Create database if not exists
SELECT 'CREATE DATABASE $DB_NAME'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Verify
\c $DB_NAME
\dt

EOF

if [ $? -eq 0 ]; then
    echo "✅ Database '$DB_NAME' is ready!"
    echo ""
    echo "Connection details:"
    echo "  Host: $DB_HOST"
    echo "  Port: 5432"
    echo "  User: $DB_USER"
    echo "  Database: $DB_NAME"
    echo ""
    echo "Next steps:"
    echo "  1. Ensure .env has: DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag_benchmark"
    echo "  2. Run: pip install -r app/requirements.txt"
    echo "  3. Start the server: python -m uvicorn app.main:app --reload"
else
    echo "❌ Failed to create database"
    exit 1
fi
