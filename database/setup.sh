#!/bin/bash

# Database setup script for arbitrage analysis app
# This script sets up the PostgreSQL database schema and initial data

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up arbitrage analysis database...${NC}"

# Check if psql is installed
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: psql is not installed. Please install PostgreSQL client tools.${NC}"
    exit 1
fi

# Database connection parameters
DB_HOST=${DB_HOST:-"localhost"}
DB_PORT=${DB_PORT:-"5432"}
DB_NAME=${DB_NAME:-"arbitrage"}
DB_USER=${DB_USER:-"arbitrage_user"}

# Check if database exists
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; then
    echo -e "${YELLOW}Database $DB_NAME already exists.${NC}"
else
    echo -e "${YELLOW}Creating database $DB_NAME...${NC}"
    createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"
fi

# Run schema setup
echo -e "${GREEN}Running database schema setup...${NC}"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f schema.sql

# Verify tables were created
echo -e "${GREEN}Verifying database setup...${NC}"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
SELECT 
    table_name, 
    column_name, 
    data_type 
FROM information_schema.columns 
WHERE table_schema = 'public' 
ORDER BY table_name, ordinal_position;
"

echo -e "${GREEN}Database setup completed successfully!${NC}"

# Test the setup
echo -e "${GREEN}Testing database functionality...${NC}"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
SELECT 
    COUNT(*) as manifest_count,
    SUM(total_items) as total_items,
    SUM(total_msrp) as total_msrp,
    SUM(projected_revenue) as projected_revenue
FROM manifests;
"

echo -e "${GREEN}Database is ready for use!${NC}"
