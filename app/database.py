"""
Модуль для работы с базой данных PostgreSQL.
Содержит функции для подключения к БД и выполнения операций с таблицей binance_atr.
"""
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Конфигурация базы данных
DB_HOST = "46.252.251.117"
DB_PORT = "4791"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "mysecretpassword"
DB_SCHEMA = "crypto"
DB_TABLE = "binance_atr"

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем пул соединений для эффективного использования ресурсов
connection_pool = None

def init_connection_pool(min_conn=1, max_conn=10):
    """
    Инициализация пула соединений с базой данных.
    
    Args:
        min_conn: Минимальное количество соединений в пуле
        max_conn: Максимальное количество соединений в пуле
    """
    global connection_pool
    try:
        connection_pool = pool.ThreadedConnectionPool(
            min_conn,
            max_conn,
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        logger.info("Connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing connection pool: {str(e)}")
        raise

def get_connection():
    """
    Получение соединения из пула.
    
    Returns:
        Connection: Объект соединения с базой данных
    """
    global connection_pool
    if connection_pool is None:
        init_connection_pool()
    return connection_pool.getconn()

def release_connection(conn):
    """
    Возвращение соединения в пул.
    
    Args:
        conn: Объект соединения с базой данных
    """
    global connection_pool
    if connection_pool is not None:
        connection_pool.putconn(conn)

def ensure_table_exists():
    """
    Проверка существования таблицы и её создание при необходимости.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Проверяем существование схемы и создаем её при необходимости
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}")
        
        # Создаем таблицу, если она не существует
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.{DB_TABLE} (
            symbol VARCHAR(10) PRIMARY KEY,
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
        )
        """)
        
        conn.commit()
        logger.info(f"Table {DB_SCHEMA}.{DB_TABLE} ensured")
    except Exception as e:
        logger.error(f"Error ensuring table exists: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            release_connection(conn)

def save_atr_data(atr_results: List[Dict[str, Any]]):
    """
    Сохранение данных ATR в базу данных.
    
    Args:
        atr_results: Список результатов расчета ATR по всем символам
    
    Returns:
        int: Количество обработанных записей
    """
    conn = None
    try:
        # Убеждаемся, что таблица существует
        ensure_table_exists()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Счетчик обработанных записей
        processed_count = 0
        
        # Текущее время для всех записей
        current_time = datetime.now()
        
        # Обрабатываем каждый результат
        for result in atr_results:
            symbol = result["symbol"]
            price = result["price"]
            
            # Извлекаем данные ATR для каждого таймфрейма
            timeframes = result["timeframes"]
            
            # Подготавливаем данные для вставки
            atr_1m = timeframes.get("1m", {}).get("atr_percent", None)
            hot_1m = timeframes.get("1m", {}).get("is_hot", False)
            
            atr_3m = timeframes.get("3m", {}).get("atr_percent", None)
            hot_3m = timeframes.get("3m", {}).get("is_hot", False)
            
            atr_5m = timeframes.get("5m", {}).get("atr_percent", None)
            hot_5m = timeframes.get("5m", {}).get("is_hot", False)
            
            atr_15m = timeframes.get("15m", {}).get("atr_percent", None)
            hot_15m = timeframes.get("15m", {}).get("is_hot", False)
            
            atr_1h = timeframes.get("1h", {}).get("atr_percent", None)
            hot_1h = timeframes.get("1h", {}).get("is_hot", False)
            
            # SQL запрос для вставки или обновления данных (UPSERT)
            query = f"""
            INSERT INTO {DB_SCHEMA}.{DB_TABLE} 
            (symbol, price, atr_1m, hot_1m, atr_3m, hot_3m, atr_5m, hot_5m, atr_15m, hot_15m, atr_1h, hot_1h, last_updated)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol) 
            DO UPDATE SET 
                price = EXCLUDED.price,
                atr_1m = EXCLUDED.atr_1m,
                hot_1m = EXCLUDED.hot_1m,
                atr_3m = EXCLUDED.atr_3m,
                hot_3m = EXCLUDED.hot_3m,
                atr_5m = EXCLUDED.atr_5m,
                hot_5m = EXCLUDED.hot_5m,
                atr_15m = EXCLUDED.atr_15m,
                hot_15m = EXCLUDED.hot_15m,
                atr_1h = EXCLUDED.atr_1h,
                hot_1h = EXCLUDED.hot_1h,
                last_updated = EXCLUDED.last_updated
            """
            
            # Выполняем запрос
            cursor.execute(query, (
                symbol, price, 
                atr_1m, hot_1m, 
                atr_3m, hot_3m, 
                atr_5m, hot_5m, 
                atr_15m, hot_15m, 
                atr_1h, hot_1h,
                current_time
            ))
            
            processed_count += 1
        
        # Фиксируем изменения
        conn.commit()
        logger.info(f"Saved {processed_count} ATR records to database")
        return processed_count
    except Exception as e:
        logger.error(f"Error saving ATR data: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            release_connection(conn)

def get_all_atr_data() -> List[Dict[str, Any]]:
    """
    Получение всех данных ATR из базы данных.
    
    Returns:
        List[Dict[str, Any]]: Список данных ATR по всем символам
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # SQL запрос для получения всех данных
        query = f"""
        SELECT 
            symbol, price, 
            atr_1m, hot_1m, 
            atr_3m, hot_3m, 
            atr_5m, hot_5m, 
            atr_15m, hot_15m, 
            atr_1h, hot_1h,
            last_updated
        FROM {DB_SCHEMA}.{DB_TABLE}
        ORDER BY symbol
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Преобразуем результаты в формат, совместимый с текущим API
        formatted_results = []
        for row in results:
            # Преобразуем строки в нужный формат
            timeframes = {
                "1m": {"atr_percent": float(row["atr_1m"]) if row["atr_1m"] is not None else 0.0, "is_hot": row["hot_1m"]},
                "3m": {"atr_percent": float(row["atr_3m"]) if row["atr_3m"] is not None else 0.0, "is_hot": row["hot_3m"]},
                "5m": {"atr_percent": float(row["atr_5m"]) if row["atr_5m"] is not None else 0.0, "is_hot": row["hot_5m"]},
                "15m": {"atr_percent": float(row["atr_15m"]) if row["atr_15m"] is not None else 0.0, "is_hot": row["hot_15m"]},
                "1h": {"atr_percent": float(row["atr_1h"]) if row["atr_1h"] is not None else 0.0, "is_hot": row["hot_1h"]}
            }
            
            formatted_results.append({
                "symbol": row["symbol"],
                "price": float(row["price"]),
                "timeframes": timeframes
            })
        
        logger.info(f"Retrieved {len(formatted_results)} ATR records from database")
        return formatted_results
    except Exception as e:
        logger.error(f"Error retrieving ATR data: {str(e)}")
        raise
    finally:
        if conn:
            release_connection(conn)

def get_last_update_time() -> Optional[datetime]:
    """
    Получение времени последнего обновления данных.
    
    Returns:
        Optional[datetime]: Время последнего обновления или None, если данных нет
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # SQL запрос для получения максимального времени обновления
        query = f"""
        SELECT MAX(last_updated) as last_updated
        FROM {DB_SCHEMA}.{DB_TABLE}
        """
        
        cursor.execute(query)
        result = cursor.fetchone()
        
        if result and result[0]:
            return result[0]
        return None
    except Exception as e:
        logger.error(f"Error retrieving last update time: {str(e)}")
        return None
    finally:
        if conn:
            release_connection(conn)

def close_connection_pool():
    """
    Закрытие пула соединений при завершении работы.
    """
    global connection_pool
    if connection_pool:
        connection_pool.closeall()
        logger.info("Connection pool closed")
