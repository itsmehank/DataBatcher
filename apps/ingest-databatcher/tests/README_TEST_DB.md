# Test Database Setup Guide

## Overview

All tests now use a separate test database (`trade_test`) to prevent modification of production data. This ensures that:

1. Production database (`market`) remains untouched during testing
2. Tests can be run safely without affecting real data
3. Test data is isolated and cleaned up after each test run

## Quick Start

### 1. Create Test Database

Before running any tests, create and initialize the test database:

```bash
# Create test database and apply schema
python apps/ingest-databatcher/tests/test_db_setup.py --create
```

This will:
- Create `trade_test` database
- Apply the same schema as production (from `db/init/01_schema.sql`)
- Create all necessary tables

### 2. Run Tests

Tests will automatically use the test database:

```bash
# Run individual test phases
python apps/ingest-databatcher/tests/test_phase1_sync_symbol_master.py
python apps/ingest-databatcher/tests/test_phase2_bulk_update.py
python apps/ingest-databatcher/tests/test_phase3_daily_update_all.py
python apps/ingest-databatcher/tests/test_phase4_weekly_update.py

# Or run all tests
python apps/ingest-databatcher/tests/run_all_tests.py
```

### 3. Clean Up (Optional)

To completely remove the test database:

```bash
python apps/ingest-databatcher/tests/test_db_setup.py --drop
```

## How It Works

### Database Isolation

Each test file:
1. Sets `DATABASE_URL` environment variable to point to `trade_test` database
2. All database operations use this test database
3. Subprocess calls (to scripts like `bulk_update.py`) inherit the test database URL
4. After tests complete, all rows are deleted from test tables (tables remain for next run)

### Test Database Structure

- **Production DB**: `market` (remains untouched)
- **Test DB**: `trade_test` (used by all tests)
- Both have identical schema and tables

### Cleanup Strategy

Tests clean up by **deleting all rows** from tables, not dropping tables:

```python
# Cleanup removes rows, not tables
DELETE FROM stock_indicators_weekly;
DELETE FROM stock_prices_weekly;
DELETE FROM stock_indicators;
DELETE FROM stock_prices;
DELETE FROM symbol_master;
```

This approach:
- Is faster than recreating tables
- Maintains schema consistency
- Allows rerunning tests without re-initialization

## Test Files Modified

All test files have been updated to use the test database:

- `test_phase1_sync_symbol_master.py` - Symbol master sync tests
- `test_phase2_bulk_update.py` - Bulk data collection tests
- `test_phase3_daily_update_all.py` - Daily update tests
- `test_phase4_weekly_update.py` - Weekly data tests

## Database Configuration

### Production Database (Unchanged)

- Database: `market`
- Configured in: `config/settings.dev.yaml` or `config/settings.yaml`
- Used by: Production scripts (`bulk_update.py`, `daily_update.py`, etc.)

### Test Database (New)

- Database: `trade_test`
- Created by: `apps/ingest-databatcher/tests/test_db_setup.py`
- Used by: All test scripts
- Connection: Same host/port/user as production, different database name

## Troubleshooting

### Error: Test database not found

```bash
# Solution: Create the test database
python apps/ingest-databatcher/tests/test_db_setup.py --create
```

### Error: Schema mismatch

```bash
# Solution: Recreate test database
python apps/ingest-databatcher/tests/test_db_setup.py --drop
python apps/ingest-databatcher/tests/test_db_setup.py --create
```

### Tests fail with "No such table"

Ensure you've created the test database schema:
```bash
python apps/ingest-databatcher/tests/test_db_setup.py --create
```

### Check test database contents

```bash
# Connect to test database
mysql -h 127.0.0.1 -u YOUR_DB_USER -pYOUR_DB_PASSWORD trade_test

# View tables
SHOW TABLES;

# Check row counts
SELECT 'symbol_master' as tbl, COUNT(*) as cnt FROM symbol_master
UNION ALL
SELECT 'stock_prices', COUNT(*) FROM stock_prices
UNION ALL
SELECT 'stock_indicators', COUNT(*) FROM stock_indicators;
```

## Benefits

✅ **Safe Testing**: Production data is never modified or deleted  
✅ **Isolation**: Tests run in complete isolation from production  
✅ **Repeatability**: Tests can be rerun without affecting production  
✅ **Fast Cleanup**: Row deletion is faster than table recreation  
✅ **Schema Consistency**: Test and production schemas stay in sync  

## Migration from Old Tests

Old test behavior:
- ❌ Used production database (`market`)
- ❌ Deleted all rows from production tables
- ❌ Risk of data loss

New test behavior:
- ✅ Uses dedicated test database (`trade_test`)
- ✅ Deletes rows only from test database
- ✅ Production data remains safe

## Example Workflow

```bash
# One-time setup
python apps/ingest-databatcher/tests/test_db_setup.py --create

# Run tests as needed
python apps/ingest-databatcher/tests/test_phase1_sync_symbol_master.py
python apps/ingest-databatcher/tests/test_phase2_bulk_update.py
python apps/ingest-databatcher/tests/test_phase3_daily_update_all.py
python apps/ingest-databatcher/tests/test_phase4_weekly_update.py

# Tests automatically clean up after themselves
# Test database is ready for next run

# Optional: Drop test database when done
python apps/ingest-databatcher/tests/test_db_setup.py --drop
```

## Notes

- Test database must be created before running any tests
- All test scripts automatically use `trade_test` via environment variable
- Production scripts are not affected and continue using `market` database
- Test data is automatically cleaned up (rows deleted) after each test run
- Schema changes in `01_schema.sql` require recreating test database
