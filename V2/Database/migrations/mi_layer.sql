-- Store processed high-level signals
CREATE TABLE IF NOT EXISTS market_intelligence_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    signal_timestamp DATETIME NOT NULL,
    event_type TEXT,
    sentiment_score REAL,
    impact_score REAL,
    summary TEXT,
    source TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Store raw inputs for auditing/debugging
CREATE TABLE IF NOT EXISTS market_intelligence_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT UNIQUE, -- e.g. URL hash
    raw_content TEXT,
    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mi_symbol_ts ON market_intelligence_signals(symbol, signal_timestamp);
