-- Create municipalities table for FP-001 — Référentiel communal
-- This table normalizes municipality (French commune) data with optional regional information
-- Idempotent: uses CREATE TABLE IF NOT EXISTS to allow re-running without errors

CREATE TABLE IF NOT EXISTS municipalities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    postal_code TEXT,
    department TEXT,
    region TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast lookups by name (common query: find municipality by name string)
CREATE INDEX IF NOT EXISTS idx_municipalities_name ON municipalities(name);
