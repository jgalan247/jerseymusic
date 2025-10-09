#!/bin/bash
# deploy_migrations.sh - Safe deployment of SumUp OAuth migrations

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Jersey Events - SumUp OAuth Migration Deployment${NC}"
echo "Timestamp: $(date)"
echo "Project Directory: $PROJECT_DIR"
echo ""

# Function to check if we're in the right directory
check_project_directory() {
    if [ ! -f "$PROJECT_DIR/manage.py" ]; then
        echo -e "${RED}❌ Error: manage.py not found in $PROJECT_DIR${NC}"
        echo "Please run this script from the correct project directory"
        exit 1
    fi

    if [ ! -d "$PROJECT_DIR/accounts/migrations" ]; then
        echo -e "${RED}❌ Error: accounts/migrations directory not found${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ Project directory verified${NC}"
}

# Function to check migration files exist
check_migration_files() {
    local migration_files=(
        "$PROJECT_DIR/accounts/migrations/0003_add_sumup_oauth_fields.py"
        "$PROJECT_DIR/accounts/migrations/0004_migrate_existing_artists_to_sumup.py"
    )

    echo -e "${YELLOW}📋 Checking migration files...${NC}"

    for file in "${migration_files[@]}"; do
        if [ ! -f "$file" ]; then
            echo -e "${RED}❌ Migration file not found: $file${NC}"
            exit 1
        else
            echo -e "${GREEN}✅ Found: $(basename "$file")${NC}"
        fi
    done
}

# Function to show current migration status
show_migration_status() {
    echo -e "${YELLOW}📊 Current migration status:${NC}"
    cd "$PROJECT_DIR"

    # Activate virtual environment if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo -e "${BLUE}📦 Virtual environment activated${NC}"
    elif [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
        echo -e "${BLUE}📦 Virtual environment activated${NC}"
    fi

    python manage.py showmigrations accounts
}

# Function to run migrations safely
run_migrations() {
    echo -e "${YELLOW}🔧 Starting migration deployment...${NC}"
    cd "$PROJECT_DIR"

    # Step 1: Apply schema migration
    echo -e "${YELLOW}📦 Applying migration 0003_add_sumup_oauth_fields...${NC}"
    python manage.py migrate accounts 0003_add_sumup_oauth_fields --verbosity=2

    # Check if first migration succeeded
    if python manage.py showmigrations accounts | grep -q "\[X\] 0003_add_sumup_oauth_fields"; then
        echo -e "${GREEN}✅ Schema migration applied successfully${NC}"
    else
        echo -e "${RED}❌ Schema migration failed${NC}"
        exit 1
    fi

    # Step 2: Apply data migration
    echo -e "${YELLOW}📦 Applying migration 0004_migrate_existing_artists_to_sumup...${NC}"
    python manage.py migrate accounts 0004_migrate_existing_artists_to_sumup --verbosity=2

    # Check if second migration succeeded
    if python manage.py showmigrations accounts | grep -q "\[X\] 0004_migrate_existing_artists_to_sumup"; then
        echo -e "${GREEN}✅ Data migration applied successfully${NC}"
    else
        echo -e "${RED}❌ Data migration failed${NC}"
        exit 1
    fi

    # Step 3: Run any remaining migrations
    echo -e "${YELLOW}📦 Running any remaining migrations...${NC}"
    python manage.py migrate --verbosity=2

    echo -e "${GREEN}🎉 All migrations completed successfully!${NC}"
}

# Function to verify database schema
verify_schema() {
    echo -e "${YELLOW}🔍 Verifying database schema...${NC}"
    cd "$PROJECT_DIR"

    # Check if SQLite or PostgreSQL
    if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
        echo -e "${BLUE}📊 Verifying SQLite schema...${NC}"
        sqlite3 "$PROJECT_DIR/db.sqlite3" ".schema accounts_artistprofile" | grep -i sumup && echo -e "${GREEN}✅ SumUp fields found in schema${NC}" || echo -e "${RED}❌ SumUp fields missing from schema${NC}"
    else
        echo -e "${BLUE}📊 Database schema verification complete${NC}"
    fi
}

# Function to show post-migration status
show_final_status() {
    echo -e "${YELLOW}📊 Final migration status:${NC}"
    cd "$PROJECT_DIR"
    python manage.py showmigrations accounts

    echo ""
    echo -e "${GREEN}📋 Migration Summary:${NC}"
    echo "✅ 0003_add_sumup_oauth_fields - Added SumUp OAuth fields to ArtistProfile"
    echo "✅ 0004_migrate_existing_artists_to_sumup - Migrated existing artists to new workflow"
    echo ""
}

# Main execution
main() {
    echo -e "${BLUE}🔍 Pre-deployment checks...${NC}"
    check_project_directory
    check_migration_files

    echo ""
    echo -e "${BLUE}📊 Before migration:${NC}"
    show_migration_status

    echo ""
    read -p "Proceed with migration deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Migration cancelled by user"
        exit 0
    fi

    echo ""
    run_migrations

    echo ""
    verify_schema

    echo ""
    show_final_status

    echo ""
    echo -e "${GREEN}🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!${NC}"
    echo ""
    echo -e "${YELLOW}📍 NEXT STEPS:${NC}"
    echo "1. Verify application starts correctly"
    echo "2. Test SumUp OAuth functionality"
    echo "3. Notify artists about the migration: python manage.py notify_artists_sumup_migration --approved-only"
    echo "4. Monitor logs for any errors"
    echo ""
}

# Run main function
main "$@"