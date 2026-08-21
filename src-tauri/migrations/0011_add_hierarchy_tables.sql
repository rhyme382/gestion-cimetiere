-- Migration 0011: Add normalized cemetery hierarchy tables for FP-004
-- Introduces sections, squares (carrés), and rows (rangées) normalization
-- Updates plots table to reference normalized hierarchy while preserving backward compatibility
--
-- Changes:
-- 1. Create normalized tables: sections, squares, rows with is_active soft-delete
-- 2. Add row_id and administrative_reference columns to plots
-- 3. Preserve existing section and row columns for compatibility
-- 4. Ensure uniqueness of normalized codes per level within parent scope
-- 5. Enforce normalization via PRAGMA and triggers on normalized_code column
--
-- Backward Compatibility:
-- - Old section and row columns remain unchanged
-- - plots.id continues as the primary technical identifier
-- - Existing plot IDs and relationships are preserved

-- Create sections table (niveau 1 de la hiérarchie)
CREATE TABLE IF NOT EXISTS sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cemetery_id INTEGER NOT NULL REFERENCES cemeteries(id),
    normalized_code TEXT NOT NULL,
    display_label TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cemetery_id, normalized_code),
    CHECK(normalized_code IS NOT NULL AND trim(normalized_code) != '')
);

CREATE INDEX IF NOT EXISTS idx_sections_cemetery_id ON sections(cemetery_id);
CREATE INDEX IF NOT EXISTS idx_sections_is_active ON sections(is_active);
CREATE INDEX IF NOT EXISTS idx_sections_display_order ON sections(cemetery_id, display_order, normalized_code);

-- Create squares table (carrés - niveau 2 de la hiérarchie)
CREATE TABLE IF NOT EXISTS squares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id INTEGER NOT NULL REFERENCES sections(id),
    normalized_code TEXT NOT NULL,
    display_label TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(section_id, normalized_code),
    CHECK(normalized_code IS NOT NULL AND trim(normalized_code) != '')
);

CREATE INDEX IF NOT EXISTS idx_squares_section_id ON squares(section_id);
CREATE INDEX IF NOT EXISTS idx_squares_is_active ON squares(is_active);
CREATE INDEX IF NOT EXISTS idx_squares_display_order ON squares(section_id, display_order, normalized_code);

-- Create rows table (rangées - niveau 3 de la hiérarchie)
CREATE TABLE IF NOT EXISTS rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    square_id INTEGER NOT NULL REFERENCES squares(id),
    normalized_code TEXT NOT NULL,
    display_label TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(square_id, normalized_code),
    CHECK(normalized_code IS NOT NULL AND trim(normalized_code) != '')
);

CREATE INDEX IF NOT EXISTS idx_rows_square_id ON rows(square_id);
CREATE INDEX IF NOT EXISTS idx_rows_is_active ON rows(is_active);
CREATE INDEX IF NOT EXISTS idx_rows_display_order ON rows(square_id, display_order, normalized_code);

-- Extend plots table to reference normalized hierarchy
ALTER TABLE plots ADD COLUMN row_id INTEGER REFERENCES rows(id);
-- administrative_reference is mandatory after migration (backfilled via Rust code to EMP-{id})
-- Normalized: trimmed, compared case-insensitively, unique per cemetery
-- Added with transient default __AUTO__ to support legacy INSERT statements that omit this column
-- An AFTER INSERT trigger immediately replaces __AUTO__ with EMP-{id}
-- CHECK constraint ensures only non-empty, non-whitespace values are stored
ALTER TABLE plots ADD COLUMN administrative_reference TEXT NOT NULL DEFAULT '__AUTO__' CHECK(trim(administrative_reference) != '');

-- Create index for administrative_reference lookup
CREATE INDEX IF NOT EXISTS idx_plots_administrative_reference ON plots(administrative_reference);
CREATE INDEX IF NOT EXISTS idx_plots_row_id ON plots(row_id);

-- NOTE: UNIQUE index for administrative_reference per cemetery is created in Rust code after backfill
-- This is done to allow temporary marker values during migration without violating uniqueness
-- The index enforces uniqueness per cemetery, normalized to lowercase after trimming

-- Create trigger to validate administrative_reference on INSERT (before the auto-generate)
-- Prevents leading/trailing spaces from being inserted
CREATE TRIGGER IF NOT EXISTS trg_plots_admin_ref_validate_insert
BEFORE INSERT ON plots
FOR EACH ROW
WHEN NEW.administrative_reference != '__AUTO__'
BEGIN
  SELECT CASE
    WHEN NEW.administrative_reference != trim(NEW.administrative_reference)
    THEN RAISE(ABORT, 'administrative_reference must not have leading or trailing spaces')
  END;
END;

-- Create trigger to replace transient __AUTO__ marker with EMP-{id} on INSERT
-- This allows legacy code that omits administrative_reference to still work
-- The column defaults to __AUTO__, then this trigger immediately replaces it with EMP-{id}
CREATE TRIGGER IF NOT EXISTS trg_plots_admin_ref_auto_generate_insert
AFTER INSERT ON plots
FOR EACH ROW
WHEN NEW.administrative_reference = '__AUTO__'
BEGIN
  UPDATE plots SET administrative_reference = 'EMP-' || NEW.id WHERE id = NEW.id;
END;

-- Create trigger to ensure administrative_reference cannot be set to empty or whitespace-only via UPDATE
-- Also prevents explicit NULL values and leading/trailing spaces
CREATE TRIGGER IF NOT EXISTS trg_plots_admin_ref_validate_update
BEFORE UPDATE OF administrative_reference ON plots
FOR EACH ROW
BEGIN
  SELECT CASE
    WHEN NEW.administrative_reference IS NULL
    THEN RAISE(ABORT, 'administrative_reference must not be NULL')
    WHEN length(trim(NEW.administrative_reference)) = 0
    THEN RAISE(ABORT, 'administrative_reference must not be empty or whitespace-only')
    WHEN NEW.administrative_reference != trim(NEW.administrative_reference)
    THEN RAISE(ABORT, 'administrative_reference must not have leading or trailing spaces')
  END;
END;

-- Create trigger to prevent cemetery mismatch on INSERT (row_id must belong to same cemetery)
CREATE TRIGGER IF NOT EXISTS trg_plots_row_id_insert_cemetery_match
BEFORE INSERT ON plots
FOR EACH ROW
WHEN NEW.row_id IS NOT NULL
BEGIN
  SELECT CASE
    WHEN NOT EXISTS (
      SELECT 1 FROM rows r
      INNER JOIN squares sq ON r.square_id = sq.id
      INNER JOIN sections s ON sq.section_id = s.id
      WHERE r.id = NEW.row_id AND s.cemetery_id = NEW.cemetery_id
    )
    THEN RAISE(ABORT, 'plots.row_id must reference a row belonging to the same cemetery')
  END;
END;

-- Create trigger to prevent cemetery mismatch on UPDATE (row_id must belong to same cemetery)
CREATE TRIGGER IF NOT EXISTS trg_plots_row_id_update_cemetery_match
BEFORE UPDATE OF row_id ON plots
FOR EACH ROW
WHEN NEW.row_id IS NOT NULL
BEGIN
  SELECT CASE
    WHEN NOT EXISTS (
      SELECT 1 FROM rows r
      INNER JOIN squares sq ON r.square_id = sq.id
      INNER JOIN sections s ON sq.section_id = s.id
      WHERE r.id = NEW.row_id AND s.cemetery_id = NEW.cemetery_id
    )
    THEN RAISE(ABORT, 'plots.row_id must reference a row belonging to the same cemetery')
  END;
END;

-- Triggers to validate code normalization format on insert
-- Ensures codes are properly formatted: trimmed, uppercase, no leading/trailing spaces, no multiple consecutive spaces
-- (The Rust code is responsible for normalizing the code before insert)
CREATE TRIGGER IF NOT EXISTS trg_sections_validate_normalized_code_insert
BEFORE INSERT ON sections
FOR EACH ROW
BEGIN
  SELECT CASE
    WHEN NEW.normalized_code != upper(trim(NEW.normalized_code))
    THEN RAISE(ABORT, 'Section code must be uppercase and trimmed')
    WHEN instr(NEW.normalized_code, '  ') > 0
    THEN RAISE(ABORT, 'Section code must not contain multiple consecutive spaces')
  END;
END;

CREATE TRIGGER IF NOT EXISTS trg_squares_validate_normalized_code_insert
BEFORE INSERT ON squares
FOR EACH ROW
BEGIN
  SELECT CASE
    WHEN NEW.normalized_code != upper(trim(NEW.normalized_code))
    THEN RAISE(ABORT, 'Square code must be uppercase and trimmed')
    WHEN instr(NEW.normalized_code, '  ') > 0
    THEN RAISE(ABORT, 'Square code must not contain multiple consecutive spaces')
  END;
END;

CREATE TRIGGER IF NOT EXISTS trg_rows_validate_normalized_code_insert
BEFORE INSERT ON rows
FOR EACH ROW
BEGIN
  SELECT CASE
    WHEN NEW.normalized_code != upper(trim(NEW.normalized_code))
    THEN RAISE(ABORT, 'Row code must be uppercase and trimmed')
    WHEN instr(NEW.normalized_code, '  ') > 0
    THEN RAISE(ABORT, 'Row code must not contain multiple consecutive spaces')
  END;
END;

-- Triggers to validate code normalization on UPDATE (prevent direct SQL modifications)
CREATE TRIGGER IF NOT EXISTS trg_sections_validate_normalized_code_update
BEFORE UPDATE OF normalized_code ON sections
FOR EACH ROW
BEGIN
  SELECT CASE
    WHEN NEW.normalized_code != upper(trim(NEW.normalized_code))
    THEN RAISE(ABORT, 'Section code must be uppercase and trimmed')
    WHEN instr(NEW.normalized_code, '  ') > 0
    THEN RAISE(ABORT, 'Section code must not contain multiple consecutive spaces')
  END;
END;

CREATE TRIGGER IF NOT EXISTS trg_squares_validate_normalized_code_update
BEFORE UPDATE OF normalized_code ON squares
FOR EACH ROW
BEGIN
  SELECT CASE
    WHEN NEW.normalized_code != upper(trim(NEW.normalized_code))
    THEN RAISE(ABORT, 'Square code must be uppercase and trimmed')
    WHEN instr(NEW.normalized_code, '  ') > 0
    THEN RAISE(ABORT, 'Square code must not contain multiple consecutive spaces')
  END;
END;

CREATE TRIGGER IF NOT EXISTS trg_rows_validate_normalized_code_update
BEFORE UPDATE OF normalized_code ON rows
FOR EACH ROW
BEGIN
  SELECT CASE
    WHEN NEW.normalized_code != upper(trim(NEW.normalized_code))
    THEN RAISE(ABORT, 'Row code must be uppercase and trimmed')
    WHEN instr(NEW.normalized_code, '  ') > 0
    THEN RAISE(ABORT, 'Row code must not contain multiple consecutive spaces')
  END;
END;
