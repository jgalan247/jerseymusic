#!/bin/bash
# create_backup.sh - Create production database backup before migration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
BACKUP_DIR="/var/backups/jersey-events/$(date +%Y%m%d)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔒 Jersey Events - Database Backup Script${NC}"
echo "Timestamp: $(date)"
echo "Backup Directory: $BACKUP_DIR"

# Create backup directory
echo -e "${YELLOW}📁 Creating backup directory...${NC}"
sudo mkdir -p "$BACKUP_DIR"
sudo chown $(whoami):$(whoami) "$BACKUP_DIR"

# Function to backup SQLite
backup_sqlite() {
    local db_path="$1"
    local backup_name="db_backup_${TIMESTAMP}.sqlite3"
    local backup_path="$BACKUP_DIR/$backup_name"

    echo -e "${YELLOW}📦 Backing up SQLite database...${NC}"

    # Copy database file
    cp "$db_path" "$backup_path"

    # Verify integrity
    echo -e "${YELLOW}🔍 Verifying backup integrity...${NC}"
    sqlite3 "$backup_path" "PRAGMA integrity_check;" > /tmp/integrity_check.txt

    if grep -q "ok" /tmp/integrity_check.txt; then
        echo -e "${GREEN}✅ SQLite backup verified: $backup_path${NC}"
        echo "Backup size: $(du -h "$backup_path" | cut -f1)"
    else
        echo -e "${RED}❌ SQLite backup integrity check failed${NC}"
        cat /tmp/integrity_check.txt
        exit 1
    fi

    rm /tmp/integrity_check.txt
    echo "$backup_path" > "$BACKUP_DIR/latest_backup.txt"
}

# Function to backup PostgreSQL
backup_postgresql() {
    local db_name="$1"
    local backup_name="jersey_events_backup_${TIMESTAMP}.sql"
    local backup_path="$BACKUP_DIR/$backup_name"

    echo -e "${YELLOW}📦 Backing up PostgreSQL database...${NC}"

    # Create SQL dump
    pg_dump "$db_name" > "$backup_path"

    # Verify backup
    if [ -s "$backup_path" ]; then
        echo -e "${GREEN}✅ PostgreSQL backup created: $backup_path${NC}"
        echo "Backup size: $(du -h "$backup_path" | cut -f1)"
        echo "Tables in backup: $(grep -c "CREATE TABLE" "$backup_path")"
    else
        echo -e "${RED}❌ PostgreSQL backup failed or empty${NC}"
        exit 1
    fi

    echo "$backup_path" > "$BACKUP_DIR/latest_backup.txt"
}

# Detect database type and create backup
if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
    echo -e "${YELLOW}📊 Detected SQLite database${NC}"
    backup_sqlite "$PROJECT_DIR/db.sqlite3"
elif command -v psql &> /dev/null; then
    echo -e "${YELLOW}📊 Detected PostgreSQL database${NC}"
    DB_NAME=${DATABASE_NAME:-jersey_events}
    backup_postgresql "$DB_NAME"
else
    echo -e "${RED}❌ No supported database found${NC}"
    echo "Please ensure either db.sqlite3 exists or PostgreSQL is configured"
    exit 1
fi

# Create metadata file
cat > "$BACKUP_DIR/backup_info.txt" << EOF
Backup Information
==================
Date: $(date)
Database Type: $([ -f "$PROJECT_DIR/db.sqlite3" ] && echo "SQLite" || echo "PostgreSQL")
Project Directory: $PROJECT_DIR
Backup Directory: $BACKUP_DIR
Created by: $(whoami)
Host: $(hostname)

Migration Context:
- Adding SumUp OAuth integration
- Migrations: 0003_add_sumup_oauth_fields, 0004_migrate_existing_artists_to_sumup
- Rollback: Use restore_backup.sh if needed

Files in backup:
$(ls -la "$BACKUP_DIR")
EOF

echo -e "${GREEN}📋 Backup metadata saved to: $BACKUP_DIR/backup_info.txt${NC}"

# Set permissions
chmod 600 "$BACKUP_DIR"/*
chmod 644 "$BACKUP_DIR/backup_info.txt"

echo -e "${GREEN}🎉 Backup completed successfully!${NC}"
echo -e "${YELLOW}📍 Backup location: $BACKUP_DIR${NC}"
echo -e "${YELLOW}📍 Latest backup file: $(cat "$BACKUP_DIR/latest_backup.txt")${NC}"

echo ""
echo "Next steps:"
echo "1. Run: ./deploy_migrations.sh"
echo "2. If issues occur: ./rollback.sh"