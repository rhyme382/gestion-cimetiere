-- Extend cemeteries table for FP-001 — Add municipality reference, address, and status flag
-- This migration is additive and fully backward-compatible
--
-- Changes:
-- 1. Add municipality_id: Foreign key to municipalities table (optional, NULL for legacy data)
-- 2. Add address: Street/full address field (complements existing 'commune' field)
-- 3. Add is_active: Boolean flag (1=active, 0=inactive) for soft-deletion without data loss
-- 4. Backfill municipalities from existing 'commune' values in legacy data
--
-- Backfill Strategy:
-- - For each cemetery with existing 'commune' value, create or reference a municipality record
-- - Populate municipality_id from lookup
-- - Keep 'commune' field intact (not deleted) for backward compatibility
--
-- Idempotency:
-- - All ALTER TABLE ADD COLUMN operations are conditional (checked by application layer in migrations.rs)
-- - Backfill uses INSERT OR IGNORE and conditional UPDATE (safe to re-run)
-- - Application logic in Rust tracks this migration via schema_migrations table

-- Add foreign key to municipalities table
-- NULL is allowed to support legacy cemeteries without a municipality yet
ALTER TABLE cemeteries ADD COLUMN municipality_id INTEGER REFERENCES municipalities(id);

-- Add street address field
ALTER TABLE cemeteries ADD COLUMN address TEXT;

-- Add soft-delete flag (1=active, 0=inactive)
-- Default to 1 (active) for all existing records
ALTER TABLE cemeteries ADD COLUMN is_active INTEGER DEFAULT 1;

-- Backfill municipalities from existing 'commune' field
-- Extract distinct commune values from cemeteries, create municipality records for each
INSERT OR IGNORE INTO municipalities (name, created_at, updated_at)
SELECT DISTINCT commune, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM cemeteries
WHERE commune IS NOT NULL AND commune != '';

-- Update cemetery records to reference the newly created or existing municipalities
UPDATE cemeteries
SET municipality_id = (
    SELECT id FROM municipalities
    WHERE municipalities.name = cemeteries.commune
)
WHERE commune IS NOT NULL AND commune != '' AND municipality_id IS NULL;

-- Create index for active/inactive filtering (common query: list active cemeteries)
CREATE INDEX IF NOT EXISTS idx_cemeteries_is_active ON cemeteries(is_active);

-- Create index for municipality lookups (join cemeteries.municipality_id -> municipalities.id)
CREATE INDEX IF NOT EXISTS idx_cemeteries_municipality_id ON cemeteries(municipality_id);
