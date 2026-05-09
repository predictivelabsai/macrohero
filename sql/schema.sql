CREATE SCHEMA IF NOT EXISTS macrohero;

-- Users
CREATE TABLE IF NOT EXISTS macrohero.users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(64) UNIQUE,
    password_hash   VARCHAR(255),
    email           VARCHAR(255) UNIQUE,
    display_name    VARCHAR(128),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- News sources
CREATE TABLE IF NOT EXISTS macrohero.sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    domain          VARCHAR(255) NOT NULL UNIQUE,
    rss_url         TEXT,
    language        VARCHAR(10) NOT NULL DEFAULT 'en',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Event categories (central bank, earnings, gdp, trade, employment, inflation, geopolitical)
CREATE TABLE IF NOT EXISTS macrohero.event_categories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(128) NOT NULL UNIQUE,
    slug            VARCHAR(128) NOT NULL UNIQUE,
    icon            VARCHAR(64),
    color           VARCHAR(32),
    display_order   INTEGER NOT NULL DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Macro news articles
CREATE TABLE IF NOT EXISTS macrohero.macro_news (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       UUID REFERENCES macrohero.sources(id) ON DELETE SET NULL,
    url             TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    summary         TEXT,
    full_text       TEXT,
    author          VARCHAR(512),
    published_at    TIMESTAMPTZ,
    scraped_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    language        VARCHAR(10) DEFAULT 'en',
    word_count      INTEGER,
    region          VARCHAR(64),
    currency_tag    VARCHAR(16),
    event_category  VARCHAR(128),
    market_reasoning TEXT,
    predicted_direction VARCHAR(10),
    predicted_magnitude REAL,
    model_used      VARCHAR(128),
    enriched_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_macro_news_published ON macrohero.macro_news(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_macro_news_created ON macrohero.macro_news(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_macro_news_region ON macrohero.macro_news(region);
CREATE INDEX IF NOT EXISTS idx_macro_news_currency ON macrohero.macro_news(currency_tag);
CREATE INDEX IF NOT EXISTS idx_macro_news_category ON macrohero.macro_news(event_category);

-- Article <-> Event Category junction
CREATE TABLE IF NOT EXISTS macrohero.news_categories (
    news_id         UUID NOT NULL REFERENCES macrohero.macro_news(id) ON DELETE CASCADE,
    category_id     UUID NOT NULL REFERENCES macrohero.event_categories(id) ON DELETE CASCADE,
    relevance_score REAL DEFAULT 1.0,
    PRIMARY KEY (news_id, category_id)
);

CREATE INDEX IF NOT EXISTS idx_news_categories_cat ON macrohero.news_categories(category_id);

-- Rate moves (actual currency pair movements after news)
CREATE TABLE IF NOT EXISTS macrohero.rate_move (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    news_id         UUID REFERENCES macrohero.macro_news(id) ON DELETE SET NULL,
    currency_pair   VARCHAR(16) NOT NULL,
    published_at    TIMESTAMPTZ NOT NULL,
    rate_before     REAL NOT NULL,
    rate_after      REAL NOT NULL,
    rate_change     REAL NOT NULL,
    rate_change_pct REAL NOT NULL,
    actual_direction VARCHAR(10),
    window_minutes  INTEGER NOT NULL DEFAULT 60,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Chat sessions
CREATE TABLE IF NOT EXISTS macrohero.chat_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES macrohero.users(id) ON DELETE SET NULL,
    category_slug   VARCHAR(128),
    title           VARCHAR(255) DEFAULT 'New chat',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON macrohero.chat_sessions(user_id, updated_at DESC);

-- Chat messages
CREATE TABLE IF NOT EXISTS macrohero.chat_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES macrohero.chat_sessions(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,
    content         TEXT NOT NULL,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON macrohero.chat_messages(session_id, created_at ASC);

-- Logs
CREATE TABLE IF NOT EXISTS macrohero.mh_logs (
    id              BIGSERIAL PRIMARY KEY,
    level           VARCHAR(20) NOT NULL,
    message         TEXT NOT NULL,
    source          VARCHAR(128),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ===================== BACKTESTING =====================

CREATE TABLE IF NOT EXISTS macrohero.strategies (
    id SERIAL PRIMARY KEY,
    strategy_id VARCHAR(64) UNIQUE NOT NULL,
    strategy_name VARCHAR(128) NOT NULL,
    strategy_type VARCHAR(32) NOT NULL,
    description TEXT,
    parameters JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS macrohero.backtest_runs (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(64) UNIQUE NOT NULL,
    strategy_id VARCHAR(64) REFERENCES macrohero.strategies(strategy_id),
    status VARCHAR(32) NOT NULL DEFAULT 'running',
    config JSONB,
    results JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backtest_runs_run_id ON macrohero.backtest_runs(run_id);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_status ON macrohero.backtest_runs(status);

CREATE TABLE IF NOT EXISTS macrohero.backtest_summaries (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL REFERENCES macrohero.backtest_runs(run_id),
    variation_index INTEGER NOT NULL DEFAULT 0,
    params JSONB,
    total_return NUMERIC(12,4),
    total_pnl NUMERIC(12,4),
    win_rate NUMERIC(8,4),
    total_trades INTEGER,
    sharpe_ratio NUMERIC(10,4),
    max_drawdown NUMERIC(10,4),
    annualized_return NUMERIC(10,4),
    is_best BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backtest_summaries_run_id ON macrohero.backtest_summaries(run_id);

CREATE TABLE IF NOT EXISTS macrohero.backtest_trades (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL REFERENCES macrohero.backtest_runs(run_id),
    trade_type VARCHAR(16) NOT NULL,
    symbol VARCHAR(16),
    direction VARCHAR(8),
    shares NUMERIC(12,4),
    entry_time TIMESTAMPTZ,
    exit_time TIMESTAMPTZ,
    entry_price NUMERIC(12,4),
    exit_price NUMERIC(12,4),
    target_price NUMERIC(12,4),
    stop_price NUMERIC(12,4),
    hit_target BOOLEAN,
    hit_stop BOOLEAN,
    pnl NUMERIC(12,4),
    pnl_pct NUMERIC(10,4),
    capital_after NUMERIC(12,4),
    total_fees NUMERIC(10,4) DEFAULT 0,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backtest_trades_run_id ON macrohero.backtest_trades(run_id);
CREATE INDEX IF NOT EXISTS idx_backtest_trades_symbol ON macrohero.backtest_trades(symbol);

CREATE TABLE IF NOT EXISTS macrohero.pnl_summary (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL REFERENCES macrohero.backtest_runs(run_id),
    symbol VARCHAR(16),
    trade_count INTEGER,
    win_count INTEGER,
    loss_count INTEGER,
    total_pnl NUMERIC(12,4),
    total_fees NUMERIC(10,4),
    avg_pnl NUMERIC(12,4),
    avg_pnl_pct NUMERIC(10,4),
    best_trade_pnl NUMERIC(12,4),
    worst_trade_pnl NUMERIC(12,4),
    total_return_pct NUMERIC(10,4),
    win_rate NUMERIC(8,4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pnl_summary_run_id ON macrohero.pnl_summary(run_id);
