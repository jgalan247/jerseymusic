# 🚀 Production Migration Deployment Plan
## SumUp OAuth Integration - Safe Deployment Guide

### 📋 **PRE-DEPLOYMENT CHECKLIST**

#### Environment Requirements:
- [ ] Production server access confirmed
- [ ] Database admin credentials available
- [ ] Application service restart permissions
- [ ] SumUp OAuth credentials configured
- [ ] Monitoring systems active

#### Migration Files to Deploy:
```
accounts/migrations/
├── 0003_add_sumup_oauth_fields.py        # Adds new SumUp fields
└── 0004_migrate_existing_artists_to_sumup.py  # Migrates existing data
```

---

## **STEP 1: 📦 CREATE PRODUCTION DATABASE BACKUP**

### SQLite Production Backup:
```bash
# 1. Stop application services first
sudo systemctl stop jersey-events
sudo systemctl stop nginx  # if serving static files

# 2. Create backup directory
mkdir -p /var/backups/jersey-events/$(date +%Y%m%d)
cd /var/backups/jersey-events/$(date +%Y%m%d)

# 3. Create database backup
cp /path/to/production/db.sqlite3 ./db_backup_$(date +%Y%m%d_%H%M%S).sqlite3

# 4. Verify backup integrity
sqlite3 ./db_backup_$(date +%Y%m%d_%H%M%S).sqlite3 "PRAGMA integrity_check;"
```

### PostgreSQL Production Backup:
```bash
# 1. Create backup
pg_dump jersey_events > jersey_events_backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Verify backup
pg_restore --list jersey_events_backup_$(date +%Y%m%d_%H%M%S).sql | head -10

# 3. Test restore on separate DB (optional but recommended)
createdb jersey_events_test
pg_restore -d jersey_events_test jersey_events_backup_$(date +%Y%m%d_%H%M%S).sql
```

### Backup Verification Script:
```bash
#!/bin/bash
# verify_backup.sh

BACKUP_FILE="$1"
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Check file size (should be > 0)
BACKUP_SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE" 2>/dev/null)
if [ "$BACKUP_SIZE" -eq 0 ]; then
    echo "❌ Backup file is empty"
    exit 1
fi

echo "✅ Backup verified: $BACKUP_FILE ($BACKUP_SIZE bytes)"
```

---

## **STEP 2: 🔍 VERIFY MIGRATION ORDER AND DEPENDENCIES**

### Check Migration Status:
```bash
# Navigate to production application directory
cd /path/to/jersey-events/

# Check current migration status
python manage.py showmigrations accounts

# Expected output should show:
# accounts
#  [X] 0001_initial
#  [X] 0002_emailverificationtoken
#  [ ] 0003_add_sumup_oauth_fields        # <- NEW
#  [ ] 0004_migrate_existing_artists_to_sumup  # <- NEW
```

### Verify Dependencies:
```bash
# Check for any conflicting migrations
python manage.py makemigrations --dry-run --check

# Should output: No changes detected
```

---

## **STEP 3: 🛠️ RUN DATABASE MIGRATIONS**

### Safe Migration Execution:
```bash
#!/bin/bash
# deploy_migrations.sh

set -e  # Exit on any error

echo "🚀 Starting SumUp OAuth Migration Deployment..."
echo "Timestamp: $(date)"

# 1. Ensure we're in the right directory
cd /path/to/jersey-events/

# 2. Activate virtual environment
source venv/bin/activate  # or your venv path

# 3. Run migrations with verbose output
echo "📦 Applying migration 0003_add_sumup_oauth_fields..."
python manage.py migrate accounts 0003_add_sumup_oauth_fields --verbosity=2

# 4. Verify the first migration succeeded
python manage.py showmigrations accounts | grep "0003_add_sumup_oauth_fields"

# 5. Run the data migration
echo "📦 Applying migration 0004_migrate_existing_artists_to_sumup..."
python manage.py migrate accounts 0004_migrate_existing_artists_to_sumup --verbosity=2

echo "✅ All migrations completed successfully!"
```

### Manual Migration Steps:
```bash
# Step 1: Add new fields
python manage.py migrate accounts 0003_add_sumup_oauth_fields --verbosity=2

# Step 2: Migrate existing data
python manage.py migrate accounts 0004_migrate_existing_artists_to_sumup --verbosity=2

# Step 3: Run remaining migrations (if any)
python manage.py migrate --verbosity=2
```

---

## **STEP 4: ✅ VERIFY SCHEMA AND DATA INTEGRITY**

### Database Schema Verification:
```sql
-- For SQLite:
.schema accounts_artistprofile

-- For PostgreSQL:
\d+ accounts_artistprofile;
```

### Expected New Columns:
```sql
-- New columns should exist:
sumup_access_token       TEXT
sumup_refresh_token      TEXT
sumup_token_type         VARCHAR(20)
sumup_expires_at         TIMESTAMP
sumup_scope             VARCHAR(255)
sumup_merchant_code     VARCHAR(50)
sumup_connected_at      TIMESTAMP
sumup_connection_status VARCHAR(20)
```

### Data Integrity Tests:
```sql
-- Test 1: Verify all artists have default connection status
SELECT COUNT(*) as total_artists,
       COUNT(CASE WHEN sumup_connection_status = 'not_connected' THEN 1 END) as not_connected_count
FROM accounts_artistprofile;

-- Test 2: Check for any NULL values in required fields
SELECT COUNT(*) as artists_with_null_status
FROM accounts_artistprofile
WHERE sumup_connection_status IS NULL;

-- Test 3: Verify field constraints
SELECT COUNT(*) as invalid_status_count
FROM accounts_artistprofile
WHERE sumup_connection_status NOT IN ('not_connected', 'connected', 'expired', 'error');
```

### Verification Script:
```python
#!/usr/bin/env python
# verify_migration.py

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
django.setup()

from accounts.models import ArtistProfile

def verify_migration():
    print("🔍 Verifying SumUp OAuth migration...")

    # Test 1: Check all artists have connection status
    total_artists = ArtistProfile.objects.count()
    not_connected = ArtistProfile.objects.filter(
        sumup_connection_status='not_connected'
    ).count()

    print(f"📊 Total Artists: {total_artists}")
    print(f"📊 Not Connected: {not_connected}")

    if total_artists == not_connected:
        print("✅ All artists properly migrated to 'not_connected' status")
    else:
        print("❌ Migration issue: Not all artists have correct status")
        return False

    # Test 2: Check model methods work
    if total_artists > 0:
        artist = ArtistProfile.objects.first()
        try:
            # Test new properties
            is_connected = artist.is_sumup_connected
            token_expired = artist.sumup_token_expired
            print("✅ Model methods working correctly")
        except Exception as e:
            print(f"❌ Model method error: {e}")
            return False

    # Test 3: Check field defaults
    null_status_count = ArtistProfile.objects.filter(
        sumup_connection_status__isnull=True
    ).count()

    if null_status_count == 0:
        print("✅ No NULL connection statuses found")
    else:
        print(f"❌ Found {null_status_count} artists with NULL connection status")
        return False

    print("🎉 All verification tests passed!")
    return True

if __name__ == '__main__':
    if verify_migration():
        sys.exit(0)
    else:
        sys.exit(1)
```

---

## **STEP 5: 🧪 TEST SUMUP OAUTH FUNCTIONALITY**

### OAuth Flow Test Script:
```bash
# Test OAuth URLs are accessible
curl -I https://your-domain.com/accounts/sumup/connect/
# Should return 302 (redirect to login) or 200 if authenticated

# Test callback URL
curl -I https://your-domain.com/accounts/sumup/callback/
# Should return 200 or redirect
```

### Django Shell Tests:
```python
# python manage.py shell

from accounts.models import ArtistProfile, User

# Test 1: Create test artist
user = User.objects.create_user(
    username='test_artist',
    email='test@example.com',
    user_type='artist'
)
profile = ArtistProfile.objects.create(
    user=user,
    display_name='Test Artist'
)

# Test 2: Test connection status
print(f"Connected: {profile.is_sumup_connected}")  # Should be False
print(f"Status: {profile.sumup_connection_status}")  # Should be 'not_connected'

# Test 3: Test connection update
profile.update_sumup_connection({
    'access_token': 'test_token',
    'refresh_token': 'test_refresh',
    'expires_in': 3600
})
print(f"Connected: {profile.is_sumup_connected}")  # Should be True

# Clean up
user.delete()
```

---

## **STEP 6: 🔄 CREATE ROLLBACK PLAN**

### Rollback Script:
```bash
#!/bin/bash
# rollback_migrations.sh

set -e
echo "🔄 Starting SumUp OAuth Migration Rollback..."

# 1. Stop application
sudo systemctl stop jersey-events

# 2. Activate virtual environment
cd /path/to/jersey-events/
source venv/bin/activate

# 3. Rollback migrations in reverse order
echo "Rolling back data migration..."
python manage.py migrate accounts 0003_add_sumup_oauth_fields --verbosity=2

echo "Rolling back schema migration..."
python manage.py migrate accounts 0002_emailverificationtoken --verbosity=2

# 4. Verify rollback
python manage.py showmigrations accounts

echo "✅ Rollback completed"
```

### Database Restore (if needed):
```bash
#!/bin/bash
# restore_database.sh

BACKUP_FILE="$1"
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Stop application
sudo systemctl stop jersey-events

# SQLite restore
cp "$BACKUP_FILE" /path/to/production/db.sqlite3

# PostgreSQL restore
# dropdb jersey_events
# createdb jersey_events
# pg_restore -d jersey_events "$BACKUP_FILE"

echo "✅ Database restored from backup"
```

---

## **STEP 7: ⚙️ ENVIRONMENT CONFIGURATION**

### Required Environment Variables:
```bash
# .env updates needed:

# SumUp OAuth Configuration
SUMUP_CLIENT_ID=your_sumup_client_id
SUMUP_CLIENT_SECRET=your_sumup_client_secret
SUMUP_REDIRECT_URI=https://your-domain.com/accounts/sumup/callback/
SUMUP_BASE_URL=https://api.sumup.com
SUMUP_API_URL=https://api.sumup.com/v0.1

# Site URL for OAuth callbacks
SITE_URL=https://your-domain.com
```

### Environment Update Script:
```bash
#!/bin/bash
# update_environment.sh

ENV_FILE="/path/to/.env"

# Backup current environment
cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"

# Add new variables (if not already present)
grep -q "SUMUP_CLIENT_ID" "$ENV_FILE" || echo "SUMUP_CLIENT_ID=your_client_id" >> "$ENV_FILE"
grep -q "SUMUP_CLIENT_SECRET" "$ENV_FILE" || echo "SUMUP_CLIENT_SECRET=your_client_secret" >> "$ENV_FILE"
grep -q "SUMUP_REDIRECT_URI" "$ENV_FILE" || echo "SUMUP_REDIRECT_URI=https://your-domain.com/accounts/sumup/callback/" >> "$ENV_FILE"
grep -q "SITE_URL" "$ENV_FILE" || echo "SITE_URL=https://your-domain.com" >> "$ENV_FILE"

echo "✅ Environment variables updated"
```

---

## **STEP 8: 🔄 RESTART APPLICATION SERVICES**

### Service Restart Script:
```bash
#!/bin/bash
# restart_services.sh

echo "🔄 Restarting Jersey Events services..."

# Restart application
sudo systemctl restart jersey-events
sleep 5

# Check status
sudo systemctl status jersey-events --no-pager

# Restart web server
sudo systemctl restart nginx
sleep 2

# Check status
sudo systemctl status nginx --no-pager

# Test application is responding
curl -f https://your-domain.com/accounts/dashboard/ || echo "⚠️  Application may not be responding"

echo "✅ Services restarted"
```

### Health Check:
```bash
#!/bin/bash
# health_check.sh

echo "🏥 Running post-deployment health checks..."

# 1. Check database connectivity
python manage.py check --database default

# 2. Check migrations
python manage.py showmigrations --plan | tail -5

# 3. Test OAuth URLs
curl -I https://your-domain.com/accounts/sumup/connect/

# 4. Check logs for errors
tail -n 20 /var/log/jersey-events/error.log

echo "✅ Health checks completed"
```

---

## **🚨 EMERGENCY PROCEDURES**

### If Migration Fails:
1. **Stop application immediately**
2. **Restore from backup**:
   ```bash
   ./rollback_migrations.sh
   # or
   ./restore_database.sh /var/backups/jersey-events/backup_file.sqlite3
   ```
3. **Restart services**
4. **Investigate issue in development**

### If Application Won't Start:
1. **Check logs**: `tail -f /var/log/jersey-events/error.log`
2. **Check environment variables**: `env | grep SUMUP`
3. **Test database connection**: `python manage.py dbshell`
4. **Rollback if necessary**

---

## **📝 DEPLOYMENT CHECKLIST**

### Pre-Deployment:
- [ ] Production backup created and verified
- [ ] Migration files reviewed
- [ ] Environment variables prepared
- [ ] Rollback plan tested

### During Deployment:
- [ ] Application stopped
- [ ] Migrations applied successfully
- [ ] Schema verified
- [ ] Data integrity confirmed
- [ ] Environment updated
- [ ] Services restarted

### Post-Deployment:
- [ ] Health checks passed
- [ ] OAuth URLs accessible
- [ ] Artist dashboard showing connection status
- [ ] Logs monitored for errors
- [ ] Notification email prepared for artists

### Success Criteria:
- ✅ All artists show "not_connected" status
- ✅ Dashboard shows SumUp connection card
- ✅ OAuth flow redirects work
- ✅ No application errors
- ✅ Database queries perform normally

---

**🎉 DEPLOYMENT COMPLETE!**

After successful deployment, run:
```bash
python manage.py notify_artists_sumup_migration --approved-only
```

This will send notification emails to approved artists to reconnect their SumUp accounts.