-- Extend concessions table with business data fields for concession lifecycle management
-- This migration preserves existing columns and adds new columns for the feature FEATURE-CONCESSION-LIFECYCLE-001

-- Add new columns for concession lifecycle management
-- These columns capture the business data required by the specification without removing existing fields
-- Using conditional syntax to prevent re-execution errors

-- Check if columns already exist by attempting to add them
-- SQLite does not support IF NOT EXISTS for ALTER TABLE ADD COLUMN in older versions,
-- so we wrap this in application logic via migrations.rs

ALTER TABLE concessions ADD COLUMN concession_number TEXT;
ALTER TABLE concessions ADD COLUMN concession_type TEXT CHECK(concession_type IN ('TEMPORAIRE', 'TRENTENAIRE', 'CINQUANTENAIRE', 'PERPETUELLE'));
ALTER TABLE concessions ADD COLUMN duration_years INTEGER;
ALTER TABLE concessions ADD COLUMN start_date TEXT;

-- Holder (main concession holder) personal information
ALTER TABLE concessions ADD COLUMN holder_first_name TEXT;
ALTER TABLE concessions ADD COLUMN holder_last_name TEXT;
ALTER TABLE concessions ADD COLUMN holder_address TEXT;
ALTER TABLE concessions ADD COLUMN holder_postal_code TEXT;
ALTER TABLE concessions ADD COLUMN holder_commune TEXT;

-- Additional metadata
ALTER TABLE concessions ADD COLUMN observations TEXT;

-- Create unique partial index on normalized concession_number
-- This index enforces uniqueness on the lowercase, trimmed form of concession_number
-- NULL values are allowed (for historical records without a number)
-- Empty strings and whitespace-only strings are also excluded
CREATE UNIQUE INDEX IF NOT EXISTS idx_concessions_number_unique
  ON concessions(lower(trim(concession_number)))
  WHERE concession_number IS NOT NULL
    AND trim(concession_number) <> '';
