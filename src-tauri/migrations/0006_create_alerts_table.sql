-- Create alerts table for concession expiration warnings
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concession_id INTEGER NOT NULL,
    alert_type TEXT NOT NULL CHECK(alert_type IN ('CRITICAL', 'WARNING', 'INFO')),
    expected_expiry_date TEXT NOT NULL,
    days_until_expiry INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TEXT,
    FOREIGN KEY(concession_id) REFERENCES concessions(id) ON DELETE CASCADE
);

-- Index for quick lookup by concession
CREATE INDEX IF NOT EXISTS idx_alerts_concession_id ON alerts(concession_id);

-- Index for unacknowledged alerts
CREATE INDEX IF NOT EXISTS idx_alerts_unacknowledged ON alerts(acknowledged_at) WHERE acknowledged_at IS NULL;
