"""
Модуль для работы с базой данных PostgreSQL.
Содержит функции для подключения к БД и выполнения операций с таблицей binance_atr.
"""
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import logging
import os
import sys
import traceback
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

# Настройка расширенного логирования
# Получаем абсолютный путь к директории проекта
project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
log_file = os.path.join(project_dir, 'database_operations.log')

# Создаем директорию для логов, если она не существует
os.makedirs(os.path.dirname(log_file), exist_ok=True)

# Настраиваем логирование
logging.basicConfig(
    level=logging.DEBUG,  # Используем DEBUG для максимально подробного логирования
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, mode='a')  # Режим append для сохранения истории
    ]
)
logger = logging.getLogger('database')
logger.info(f"Database module initialized. Log file: {log_file}")
logger.info(f"Database configuration: Host={DB_HOST}, Port={DB_PORT}, DB={DB_NAME}, Schema={DB_SCHEMA}, Table={DB_TABLE}")

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
        logger.debug(f"Initializing connection pool with min_conn={min_conn}, max_conn={max_conn}")
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
        
        # Проверяем соединение
        conn = connection_pool.getconn()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        logger.debug(f"Connection test result: {result}")
        connection_pool.putconn(conn)
        
        return True
    except Exception as e:
        logger.error(f"Error initializing connection pool: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def get_connection():
    """
    Получение соединения из пула.
    
    Returns:
        Connection: Объект соединения с базой данных
    """
    global connection_pool
    try:
        if connection_pool is None:
            logger.debug("Connection pool is None, initializing...")
            init_connection_pool()
        
        conn = connection_pool.getconn()
        logger.debug("Got connection from pool")
        return conn
    except Exception as e:
        logger.error(f"Error getting connection from pool: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def release_connection(conn):
    """
    Возвращение соединения в пул.
    
    Args:
        conn: Объект соединения с базой данных
    """
    global connection_pool
    try:
        if connection_pool is not None:
            connection_pool.putconn(conn)
            logger.debug("Released connection back to pool")
    except Exception as e:
        logger.error(f"Error releasing connection to pool: {str(e)}")
        logger.error(traceback.format_exc())

def check_column_exists(column_name, schema_name, table_name):
    """
    Проверка существования колонки в таблице.
    
    Args:
        column_name: Имя колонки
        schema_name: Имя схемы
        table_name: Имя таблицы
        
    Returns:
        bool: True, если колонка существует, иначе False
    """
    conn = None
    try:
        logger.debug(f"Checking if column {column_name} exists in {schema_name}.{table_name}")
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_schema = %s 
            AND table_name = %s 
            AND column_name = %s
        )
        """
        
        cursor.execute(query, (schema_name, table_name, column_name))
        result = cursor.fetchone()
        
        exists = result[0]
        logger.debug(f"Column {column_name} exists: {exists}")
        return exists
    except Exception as e:
        logger.error(f"Error checking column existence: {str(e)}")
        logger.error(traceback.format_exc())
        return False
    finally:
        if conn:
            release_connection(conn)

def add_column(column_name, column_definition, schema_name, table_name):
    """
    Добавление колонки в таблицу.
    
    Args:
        column_name: Имя колонки
        column_definition: Определение колонки (тип и ограничения)
        schema_name: Имя схемы
        table_name: Имя таблицы
        
    Returns:
        bool: True, если колонка добавлена успешно, иначе False
    """
    conn = None
    try:
        logger.debug(f"Adding column {column_name} with definition '{column_definition}' to {schema_name}.{table_name}")
        conn = get_connection()
        cursor = conn.cursor()
        
        query = f"""
        ALTER TABLE {schema_name}.{table_name}
        ADD COLUMN IF NOT EXISTS {column_name} {column_definition}
        """
        
        logger.debug(f"Executing query: {query}")
        cursor.execute(query)
        conn.commit()
        
        logger.info(f"Column {column_name} added to {schema_name}.{table_name}")
        return True
    except Exception as e:
        logger.error(f"Error adding column: {str(e)}")
        logger.error(traceback.format_exc())
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            release_connection(conn)

def ensure_table_exists():
    """
    Проверка существования таблицы и её создание при необходимости.
    Также проверяет наличие необходимых колонок и добавляет их при необходимости.
    """
    conn = None
    try:
        logger.info(f"Ensuring table {DB_SCHEMA}.{DB_TABLE} exists")
        conn = get_connection()
        cursor = conn.cursor()
        
        # Проверяем существование схемы и создаем её при необходимости
        logger.debug(f"Creating schema {DB_SCHEMA} if not exists")
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}")
        
        # Создаем таблицу, если она не существует
        create_table_query = f"""
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
            hot_1h BOOLEAN
        )
        """
        logger.debug(f"Creating table with query: {create_table_query}")
        cursor.execute(create_table_query)
        
        conn.commit()
        logger.info(f"Table {DB_SCHEMA}.{DB_TABLE} ensured")
        
        # Проверяем наличие колонки last_updated и добавляем её при необходимости
        if not check_column_exists("last_updated", DB_SCHEMA, DB_TABLE):
            logger.debug("Column last_updated does not exist, adding it")
            add_column("last_updated", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", DB_SCHEMA, DB_TABLE)
            logger.info(f"Column last_updated added to {DB_SCHEMA}.{DB_TABLE}")
        else:
            logger.debug("Column last_updated already exists")
            
        # Проверяем, есть ли данные в таблице
        cursor.execute(f"SELECT COUNT(*) FROM {DB_SCHEMA}.{DB_TABLE}")
        count = cursor.fetchone()[0]
        logger.info(f"Current record count in {DB_SCHEMA}.{DB_TABLE}: {count}")
        
        return True
    except Exception as e:
        logger.error(f"Error ensuring table exists: {str(e)}")
        logger.error(traceback.format_exc())
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
        logger.info(f"Saving ATR data for {len(atr_results)} symbols")
        
        # Убеждаемся, что таблица существует
        ensure_table_exists()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Счетчик обработанных записей
        processed_count = 0
        
        # Текущее время для всех записей
        current_time = datetime.now()
        logger.debug(f"Using current_time: {current_time}")
        
        # Проверяем наличие колонки last_updated
        has_last_updated = check_column_exists("last_updated", DB_SCHEMA, DB_TABLE)
        logger.debug(f"Column last_updated exists: {has_last_updated}")
        
        # Обрабатываем каждый результат
        for result in atr_results:
            symbol = result["symbol"]
            price = result["price"]
            
            logger.debug(f"Processing symbol: {symbol}, price: {price}")
            
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
            
            logger.debug(f"ATR values for {symbol}: 1m={atr_1m}({hot_1m}), 3m={atr_3m}({hot_3m}), 5m={atr_5m}({hot_5m}), 15m={atr_15m}({hot_15m}), 1h={atr_1h}({hot_1h})")
            
            # SQL запрос для вставки или обновления данных (UPSERT)
            if has_last_updated:
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
                try:
                    cursor.execute(query, (
                        symbol, price, 
                        atr_1m, hot_1m, 
                        atr_3m, hot_3m, 
                        atr_5m, hot_5m, 
                        atr_15m, hot_15m, 
                        atr_1h, hot_1h,
                        current_time
                    ))
                    logger.debug(f"Executed insert/update query for {symbol} with last_updated")
                except Exception as e:
                    logger.error(f"Error executing query for {symbol}: {str(e)}")
                    logger.error(traceback.format_exc())
                    continue
            else:
                # Запрос без колонки last_updated
                query = f"""
                INSERT INTO {DB_SCHEMA}.{DB_TABLE} 
                (symbol, price, atr_1m, hot_1m, atr_3m, hot_3m, atr_5m, hot_5m, atr_15m, hot_15m, atr_1h, hot_1h)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    hot_1h = EXCLUDED.hot_1h
                """
                
                # Выполняем запрос
                try:
                    cursor.execute(query, (
                        symbol, price, 
                        atr_1m, hot_1m, 
                        atr_3m, hot_3m, 
                        atr_5m, hot_5m, 
                        atr_15m, hot_15m, 
                        atr_1h, hot_1h
                    ))
                    logger.debug(f"Executed insert/update query for {symbol} without last_updated")
                except Exception as e:
                    logger.error(f"Error executing query for {symbol}: {str(e)}")
                    logger.error(traceback.format_exc())
                    continue
            
            processed_count += 1
            
            # Логируем каждые 10 записей для уменьшения объема логов
            if processed_count % 10 == 0:
                logger.info(f"Processed {processed_count} symbols so far")
        
        # Фиксируем изменения
        conn.commit()
        logger.info(f"Saved {processed_count} ATR records to database")
        
        # Проверяем, что данные действительно сохранились
        cursor.execute(f"SELECT COUNT(*) FROM {DB_SCHEMA}.{DB_TABLE}")
        count_after = cursor.fetchone()[0]
        logger.info(f"Record count in {DB_SCHEMA}.{DB_TABLE} after save: {count_after}")
        
        return processed_count
    except Exception as e:
        logger.error(f"Error saving ATR data: {str(e)}")
        logger.error(traceback.format_exc())
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
        logger.info("Retrieving all ATR data from database")
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Проверяем наличие колонки last_updated
        has_last_updated = check_column_exists("last_updated", DB_SCHEMA, DB_TABLE)
        logger.debug(f"Column last_updated exists: {has_last_updated}")
        
        # SQL запрос для получения всех данных
        if has_last_updated:
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
        else:
            query = f"""
            SELECT 
                symbol, price, 
                atr_1m, hot_1m, 
                atr_3m, hot_3m, 
                atr_5m, hot_5m, 
                atr_15m, hot_15m, 
                atr_1h, hot_1h
            FROM {DB_SCHEMA}.{DB_TABLE}
            ORDER BY symbol
            """
        
        logger.debug(f"Executing query: {query}")
        cursor.execute(query)
        results = cursor.fetchall()
        logger.debug(f"Retrieved {len(results)} rows from database")
        
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
        
        logger.info(f"Retrieved and formatted {len(formatted_results)} ATR records from database")
        return formatted_results
    except Exception as e:
        logger.error(f"Error retrieving ATR data: {str(e)}")
        logger.error(traceback.format_exc())
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
        logger.info("Getting last update time from database")
        conn = get_connection()
        cursor = conn.cursor()
        
        # Проверяем наличие колонки last_updated
        has_last_updated = check_column_exists("last_updated", DB_SCHEMA, DB_TABLE)
        logger.debug(f"Column last_updated exists: {has_last_updated}")
        
        if not has_last_updated:
            # Если колонки нет, возвращаем текущее время
            logger.warning("Column last_updated does not exist, returning current time")
            return datetime.now()
        
        # SQL запрос для получения максимального времени обновления
        query = f"""
        SELECT MAX(last_updated) as last_updated
        FROM {DB_SCHEMA}.{DB_TABLE}
        """
        
        logger.debug(f"Executing query: {query}")
        cursor.execute(query)
        result = cursor.fetchone()
        
        if result and result[0]:
            logger.info(f"Last update time: {result[0]}")
            return result[0]
        
        logger.warning("No last update time found in database")
        return None
    except Exception as e:
        logger.error(f"Error retrieving last update time: {str(e)}")
        logger.error(traceback.format_exc())
        return None
    finally:
        if conn:
            release_connection(conn)

def close_connection_pool():
    """
    Закрытие пула соединений при завершении работы.
    """
    global connection_pool
    try:
        if connection_pool:
            connection_pool.closeall()
            logger.info("Connection pool closed")
    except Exception as e:
        logger.error(f"Error closing connection pool: {str(e)}")
        logger.error(traceback.format_exc())

def test_database_connection():
    """
    Тестирование соединения с базой данных.
    
    Returns:
        bool: True, если соединение успешно, иначе False
    """
    conn = None
    try:
        logger.info("Testing database connection")
        conn = get_connection()
        cursor = conn.cursor()
        
        # Проверяем соединение
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        # Проверяем доступ к схеме
        cursor.execute(f"SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = '{DB_SCHEMA}')")
        schema_exists = cursor.fetchone()[0]
        
        if not schema_exists:
            logger.warning(f"Schema {DB_SCHEMA} does not exist")
            return False
        
        # Проверяем доступ к таблице
        cursor.execute(f"""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_schema = '{DB_SCHEMA}' 
            AND table_name = '{DB_TABLE}'
        )
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            logger.warning(f"Table {DB_SCHEMA}.{DB_TABLE} does not exist")
            return False
        
        logger.info(f"Database connection test successful: {result}, schema exists: {schema_exists}, table exists: {table_exists}")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        logger.error(traceback.format_exc())
        return False
    finally:
        if conn:
            release_connection(conn)
