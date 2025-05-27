"""
Модуль для подключения к базе данных PostgreSQL.
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
DB_SCHEMA = "crypto"  # Используем схему crypto

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('db_operations.log', mode='a')
    ]
)
logger = logging.getLogger('db_connector')

# Создаем пул соединений
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

def close_connection_pool():
    """
    Закрытие пула соединений.
    """
    global connection_pool
    try:
        if connection_pool is not None:
            connection_pool.closeall()
            logger.info("Connection pool closed")
            connection_pool = None
    except Exception as e:
        logger.error(f"Error closing connection pool: {str(e)}")
        logger.error(traceback.format_exc())

def execute_query(query, params=None, fetch=True, commit=True):
    """
    Выполнение SQL-запроса с возможностью получения результатов.
    
    Args:
        query: SQL-запрос
        params: Параметры запроса
        fetch: Флаг получения результатов
        commit: Флаг фиксации изменений
        
    Returns:
        List[Dict] или None: Результаты запроса или None
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(query, params)
        
        if fetch:
            result = cursor.fetchall()
        else:
            result = None
            
        if commit:
            conn.commit()
            
        return result
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        logger.error(f"Query: {query}")
        logger.error(f"Params: {params}")
        logger.error(traceback.format_exc())
        if conn and commit:
            conn.rollback()
        raise
    finally:
        if conn:
            release_connection(conn)

def execute_script(script):
    """
    Выполнение SQL-скрипта.
    
    Args:
        script: SQL-скрипт
        
    Returns:
        bool: Результат выполнения
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(script)
        conn.commit()
        
        logger.info("SQL script executed successfully")
        return True
    except Exception as e:
        logger.error(f"Error executing SQL script: {str(e)}")
        logger.error(traceback.format_exc())
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            release_connection(conn)

def ensure_schema_exists():
    """
    Проверка существования схемы и её создание при необходимости.
    """
    try:
        logger.info(f"Ensuring schema {DB_SCHEMA} exists")
        query = f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"
        execute_query(query, fetch=False)
        logger.info(f"Schema {DB_SCHEMA} ensured")
        return True
    except Exception as e:
        logger.error(f"Error ensuring schema exists: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def initialize_database():
    """
    Инициализация базы данных: создание схемы и таблиц.
    """
    try:
        # Убеждаемся, что схема существует
        ensure_schema_exists()
        
        # Читаем SQL-скрипт для создания таблиц
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')
        with open(script_path, 'r') as f:
            script = f.read()
        
        # Выполняем скрипт
        result = execute_script(script)
        
        if result:
            logger.info("Database initialized successfully")
        else:
            logger.error("Failed to initialize database")
            
        return result
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        logger.error(traceback.format_exc())
        return False
