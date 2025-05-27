-- Создание схемы crypto, если она не существует
CREATE SCHEMA IF NOT EXISTS crypto;

-- Таблица для хранения исторических данных о капитализации и объеме рынка
CREATE TABLE IF NOT EXISTS crypto.market_history (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    total_market_cap DECIMAL(24, 2) NOT NULL,
    total_volume DECIMAL(24, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индекс для ускорения запросов по дате
CREATE INDEX IF NOT EXISTS idx_market_history_date ON crypto.market_history(date);

-- Таблица для хранения текущих метрик по топ-монетам
CREATE TABLE IF NOT EXISTS crypto.coins_metrics (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    name VARCHAR(100) NOT NULL,
    current_price DECIMAL(24, 8) NOT NULL,
    price_change_percentage_24h DECIMAL(10, 2),
    market_cap DECIMAL(24, 2),
    total_volume DECIMAL(24, 2),
    image_url TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Уникальный индекс для предотвращения дубликатов по символу
CREATE UNIQUE INDEX IF NOT EXISTS idx_coins_metrics_symbol ON crypto.coins_metrics(symbol);

-- Таблица для хранения данных индекса страха и жадности
CREATE TABLE IF NOT EXISTS crypto.fear_greed_index (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    value INTEGER NOT NULL,
    value_classification VARCHAR(50) NOT NULL,
    timestamp BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индекс для ускорения запросов по дате
CREATE INDEX IF NOT EXISTS idx_fear_greed_date ON crypto.fear_greed_index(date);

-- Таблица для хранения данных ATR по всем символам и таймфреймам
CREATE TABLE IF NOT EXISTS crypto.binance_atr (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    price DECIMAL(15, 5) NOT NULL,
    atr_1m DECIMAL(15, 5),
    hot_1m BOOLEAN,
    atr_3m DECIMAL(15, 5),
    hot_3m BOOLEAN,
    atr_5m DECIMAL(15, 5),
    hot_5m BOOLEAN,
    atr_15m DECIMAL(15, 5),
    hot_15m BOOLEAN,
    atr_1h DECIMAL(15, 5),
    hot_1h BOOLEAN,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Уникальный индекс для предотвращения дубликатов по символу
CREATE UNIQUE INDEX IF NOT EXISTS idx_binance_atr_symbol ON crypto.binance_atr(symbol);

-- Функция для автоматического обновления поля updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер для автоматического обновления поля updated_at в таблице market_history
CREATE TRIGGER update_market_history_updated_at
BEFORE UPDATE ON crypto.market_history
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Триггер для автоматического обновления поля last_updated в таблице coins_metrics
CREATE OR REPLACE TRIGGER update_coins_metrics_last_updated
BEFORE UPDATE ON crypto.coins_metrics
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
