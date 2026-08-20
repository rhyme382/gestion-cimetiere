-- Création des tables pour le MVP
-- SQLite avec types TEXT pour les dates (ISO 8601 UTC)

CREATE TABLE IF NOT EXISTS cemeteries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    commune TEXT,
    capacity INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cemetery_id INTEGER NOT NULL REFERENCES cemeteries(id),
    section TEXT,
    row INTEGER,
    number INTEGER,
    capacity INTEGER DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'available',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_plots_cemetery_id ON plots(cemetery_id);

CREATE TABLE IF NOT EXISTS concessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cemetery_id INTEGER NOT NULL REFERENCES cemeteries(id),
    plot_id INTEGER REFERENCES plots(id),
    acquired_at TEXT,
    expires_at TEXT,
    renewed_at TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_concessions_cemetery_id ON concessions(cemetery_id);
CREATE INDEX IF NOT EXISTS idx_concessions_plot_id ON concessions(plot_id);

CREATE TABLE IF NOT EXISTS individuals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS burials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concession_id INTEGER NOT NULL REFERENCES concessions(id),
    individual_id INTEGER NOT NULL REFERENCES individuals(id),
    buried_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_burials_concession_id ON burials(concession_id);
CREATE INDEX IF NOT EXISTS idx_burials_individual_id ON burials(individual_id);
