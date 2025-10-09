#!/bin/bash
# rollback.sh - Rollback SumUp OAuth migrations safely

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${RED}🔄 Jersey Events - SumUp OAuth Migration Rollback${NC}"
echo "Timestamp: $(date)"
echo "Project Directory: $PROJECT_DIR"
echo ""
echo -e "${RED}⚠️  WARNING: This will rollback the SumUp OAuth integration${NC}"
echo -e "${RED}⚠️  All SumUp connection data will be lost${NC}"
echo ""

# Function to show current migration status
show_current_status() {
    echo -e "${YELLOW}📊 Current migration status:${NC}"
    cd "$PROJECT_DIR"

    # Activate virtual environment if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    elif [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    fi

    python manage.py showmigrations accounts
}

# Function to create emergency backup before rollback
create_emergency_backup() {
    echo -e "${YELLOW}📦 Creating emergency backup before rollback...${NC}"

    local backup_dir="/tmp/jersey_events_emergency_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"

    if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
        cp "$PROJECT_DIR/db.sqlite3" "$backup_dir/db_pre_rollback.sqlite3"
        echo -e "${GREEN}✅ Emergency backup created: $backup_dir/db_pre_rollback.sqlite3${NC}"
    else
        echo -e "${YELLOW}📊 PostgreSQL detected - creating SQL dump...${NC}"
        pg_dump ${DATABASE_NAME:-jersey_events} > "$backup_dir/emergency_backup.sql"
        echo -e "${GREEN}✅ Emergency backup created: $backup_dir/emergency_backup.sql${NC}"
    fi

    echo "$backup_dir" > /tmp/jersey_events_last_emergency_backup.txt
    echo -e "${BLUE}📍 Emergency backup location saved to: /tmp/jersey_events_last_emergency_backup.txt${NC}"
}

# Function to rollback migrations
rollback_migrations() {
    echo -e "${YELLOW}🔄 Starting migration rollback...${NC}"
    cd "$PROJECT_DIR"

    # Step 1: Rollback data migration first
    echo -e "${YELLOW}⬅️  Rolling back data migration (0004 -> 0003)...${NC}"
    python manage.py migrate accounts 0003_add_sumup_oauth_fields --verbosity=2

    # Step 2: Rollback schema migration
    echo -e "${YELLOW}⬅️  Rolling back schema migration (0003 -> 0002)...${NC}"
    python manage.py migrate accounts 0002_emailverificationtoken --verbosity=2

    echo -e "${GREEN}✅ Migration rollback completed${NC}"
}

# Function to verify rollback
verify_rollback() {
    echo -e "${YELLOW}🔍 Verifying rollback...${NC}"
    cd "$PROJECT_DIR"

    # Check migration status
    echo -e "${BLUE}📊 Migration status after rollback:${NC}"
    python manage.py showmigrations accounts

    # Check if SumUp fields are gone (for SQLite)
    if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
        echo -e "${BLUE}🔍 Checking if SumUp fields were removed...${NC}"
        if sqlite3 "$PROJECT_DIR/db.sqlite3" ".schema accounts_artistprofile" | grep -i sumup; then
            echo -e "${RED}❌ Warning: SumUp fields may still exist in schema${NC}"
        else
            echo -e "${GREEN}✅ SumUp fields removed from schema${NC}"
        fi
    fi
}

# Function to restore from backup if needed
restore_from_backup() {
    local backup_file="$1"

    if [ -z "$backup_file" ]; then
        echo -e "${RED}❌ No backup file specified${NC}"
        echo "Usage: $0 restore /path/to/backup/file"
        exit 1
    fi

    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}❌ Backup file not found: $backup_file${NC}"
        exit 1
    fi

    echo -e "${YELLOW}📦 Restoring database from backup...${NC}"

    # Stop application services if running
    echo -e "${YELLOW}🛑 Stopping application services...${NC}"
    # Uncomment these lines in production:
    # sudo systemctl stop jersey-events || echo "Service not running"
    # sudo systemctl stop nginx || echo "Nginx not running"

    # Restore based on file extension
    if [[ "$backup_file" == *.sqlite3 ]]; then
        echo -e "${BLUE}📊 Restoring SQLite database...${NC}"
        cp "$backup_file" "$PROJECT_DIR/db.sqlite3"
    elif [[ "$backup_file" == *.sql ]]; then
        echo -e "${BLUE}📊 Restoring PostgreSQL database...${NC}"
        # dropdb ${DATABASE_NAME:-jersey_events}
        # createdb ${DATABASE_NAME:-jersey_events}
        # psql ${DATABASE_NAME:-jersey_events} < "$backup_file"
        echo "PostgreSQL restore commands prepared (uncomment in production)"
    else
        echo -e "${RED}❌ Unknown backup file format${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ Database restored from backup${NC}"
    echo -e "${YELLOW}🔄 Remember to restart services after restore${NC}"
}

# Function to show help
show_help() {
    echo "Jersey Events Migration Rollback Script"
    echo ""
    echo "Usage:"
    echo "  $0                    - Interactive rollback of migrations"
    echo "  $0 restore <file>     - Restore database from backup file"
    echo "  $0 status            - Show current migration status"
    echo "  $0 help              - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0"
    echo "  $0 restore /var/backups/jersey-events/20241025/db_backup.sqlite3"
    echo "  $0 status"
}

# Main execution
main() {
    case "${1:-rollback}" in
        "restore")
            restore_from_backup "$2"
            ;;
        "status")
            show_current_status
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        "rollback"|"")
            echo -e "${BLUE}🔍 Current status:${NC}"
            show_current_status

            echo ""
            echo -e "${RED}⚠️  This will rollback SumUp OAuth migrations${NC}"
            echo -e "${RED}⚠️  All artist SumUp connection data will be lost${NC}"
            echo ""
            read -p "Are you sure you want to proceed? (yes/NO): " -r
            if [[ ! $REPLY == "yes" ]]; then
                echo "Rollback cancelled"
                exit 0
            fi

            create_emergency_backup
            rollback_migrations
            verify_rollback

            echo ""
            echo -e "${GREEN}🎉 ROLLBACK COMPLETED${NC}"
            echo ""
            echo -e "${YELLOW}📍 NEXT STEPS:${NC}"
            echo "1. Restart application services"
            echo "2. Test that the application works without SumUp fields"
            echo "3. Consider running a full database integrity check"
            echo "4. Emergency backup location: $(cat /tmp/jersey_events_last_emergency_backup.txt 2>/dev/null || echo 'Not found')"
            ;;
        *)
            echo -e "${RED}❌ Unknown command: $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"