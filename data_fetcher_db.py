"""
Модуль для получения данных из базы данных PostgreSQL для графиков и метрик.
Заменяет прямые запросы к API на чтение из предварительно сохраненных данных.
"""
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import logging
import traceback

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем модуль для работы с базой данных
from app.utils.db.db_connector import (
    execute_query,
    initialize_database
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('data_fetcher_db.log', mode='a')
    ]
)
logger = logging.getLogger('data_fetcher_db')

# Настройки
COIN_IDS = [
    "bitcoin", "ethereum", "tether", "binancecoin",
    "solana", "ripple", "usd-coin", "cardano",
    "dogecoin", "polkadot"
]

def get_market_history_from_db(days=365):
    """
    Получение исторических данных о капитализации и объеме рынка из базы данных.
    
    Args:
        days: Количество дней для получения данных
        
    Returns:
        dict: Словарь с датами, капитализацией и объемами
    """
    try:
        logger.info(f"Getting market history data from database for last {days} days")
        
        # Вычисляем дату начала периода
        start_date = (datetime.now() - timedelta(days=days)).date()
        
        # Запрос к базе данных
        query = """
        SELECT date, total_market_cap, total_volume
        FROM crypto.market_history
        WHERE date >= %s
        ORDER BY date ASC
        """
        
        result = execute_query(query, (start_date,))
        
        if not result:
            logger.warning("No market history data found in database")
            return {
                "dates": [],
                "caps": [],
                "volumes": []
            }
        
        # Преобразуем результаты в нужный формат
        dates = []
        caps = []
        volumes = []
        
        for row in result:
            dates.append(row['date'].strftime('%Y-%m-%d'))
            caps.append(float(row['total_market_cap']))
            volumes.append(float(row['total_volume']))
        
        logger.info(f"Retrieved {len(dates)} market history records from database")
        
        return {
            "dates": dates,
            "caps": caps,
            "volumes": volumes
        }
    except Exception as e:
        logger.error(f"Error getting market history from database: {str(e)}")
        logger.error(traceback.format_exc())
        
        # В случае ошибки возвращаем пустые списки
        return {
            "dates": [],
            "caps": [],
            "volumes": []
        }

def get_top_coins_from_db(limit=20):
    """
    Получение данных о топ-криптовалютах из базы данных.
    
    Args:
        limit: Количество криптовалют для получения
        
    Returns:
        DataFrame: Данные о топ-криптовалютах
    """
    try:
        logger.info(f"Getting top {limit} coins data from database")
        
        # Запрос к базе данных
        query = """
        SELECT symbol, name, current_price, price_change_percentage_24h, 
               market_cap, total_volume, image_url
        FROM crypto.coins_metrics
        ORDER BY market_cap DESC
        LIMIT %s
        """
        
        result = execute_query(query, (limit,))
        
        if not result:
            logger.warning("No coins data found in database")
            # Возвращаем фиктивные данные в случае ошибки
            return pd.DataFrame({
                'symbol': ['BTC', 'ETH', 'USDT', 'BNB', 'SOL', 'XRP', 'USDC', 'ADA', 'AVAX', 'DOGE',
                          'DOT', 'MATIC', 'SHIB', 'TRX', 'TON', 'LINK', 'UNI', 'ATOM', 'LTC', 'BCH'],
                'current_price': [50000, 3000, 1, 400, 100, 0.5, 1, 0.4, 30, 0.1, 
                                 15, 0.8, 0.00001, 0.1, 2, 15, 8, 10, 80, 300],
                'price_change_percentage_24h': [2.5, 1.8, 0.1, -1.2, 5.6, -2.3, 0.0, 3.2, -4.1, 1.5,
                                               -0.8, 2.1, 4.5, -1.7, 3.3, 0.9, -2.8, 1.1, -0.5, 2.2],
                'total_volume': [30000000000, 15000000000, 80000000000, 2000000000, 1500000000, 
                                1000000000, 900000000, 800000000, 700000000, 600000000,
                                500000000, 450000000, 400000000, 350000000, 300000000,
                                250000000, 200000000, 150000000, 100000000, 50000000],
                'market_cap': [900000000000, 350000000000, 80000000000, 60000000000, 40000000000,
                              30000000000, 25000000000, 15000000000, 10000000000, 8000000000,
                              7000000000, 6000000000, 5000000000, 4000000000, 3000000000,
                              2500000000, 2000000000, 1500000000, 1000000000, 500000000],
                'name': ['Bitcoin', 'Ethereum', 'Tether', 'Binance Coin', 'Solana', 'Ripple', 
                        'USD Coin', 'Cardano', 'Avalanche', 'Dogecoin', 'Polkadot', 'Polygon',
                        'Shiba Inu', 'Tron', 'Toncoin', 'Chainlink', 'Uniswap', 'Cosmos', 
                        'Litecoin', 'Bitcoin Cash'],
                'image': [''] * 20
            })
        
        # Преобразуем результаты в DataFrame
        df = pd.DataFrame(result)
        
        # Переименовываем колонку image_url в image для совместимости
        df = df.rename(columns={'image_url': 'image'})
        
        logger.info(f"Retrieved {len(df)} coins from database")
        
        return df
    except Exception as e:
        logger.error(f"Error getting top coins from database: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Возвращаем фиктивные данные в случае ошибки
        return pd.DataFrame({
            'symbol': ['BTC', 'ETH', 'USDT', 'BNB', 'SOL', 'XRP', 'USDC', 'ADA', 'AVAX', 'DOGE',
                      'DOT', 'MATIC', 'SHIB', 'TRX', 'TON', 'LINK', 'UNI', 'ATOM', 'LTC', 'BCH'],
            'current_price': [50000, 3000, 1, 400, 100, 0.5, 1, 0.4, 30, 0.1, 
                             15, 0.8, 0.00001, 0.1, 2, 15, 8, 10, 80, 300],
            'price_change_percentage_24h': [2.5, 1.8, 0.1, -1.2, 5.6, -2.3, 0.0, 3.2, -4.1, 1.5,
                                           -0.8, 2.1, 4.5, -1.7, 3.3, 0.9, -2.8, 1.1, -0.5, 2.2],
            'total_volume': [30000000000, 15000000000, 80000000000, 2000000000, 1500000000, 
                            1000000000, 900000000, 800000000, 700000000, 600000000,
                            500000000, 450000000, 400000000, 350000000, 300000000,
                            250000000, 200000000, 150000000, 100000000, 50000000],
            'market_cap': [900000000000, 350000000000, 80000000000, 60000000000, 40000000000,
                          30000000000, 25000000000, 15000000000, 10000000000, 8000000000,
                          7000000000, 6000000000, 5000000000, 4000000000, 3000000000,
                          2500000000, 2000000000, 1500000000, 1000000000, 500000000],
            'name': ['Bitcoin', 'Ethereum', 'Tether', 'Binance Coin', 'Solana', 'Ripple', 
                    'USD Coin', 'Cardano', 'Avalanche', 'Dogecoin', 'Polkadot', 'Polygon',
                    'Shiba Inu', 'Tron', 'Toncoin', 'Chainlink', 'Uniswap', 'Cosmos', 
                    'Litecoin', 'Bitcoin Cash'],
            'image': [''] * 20
        })

def get_fear_greed_index_from_db(limit=5):
    """
    Получение индекса страха и жадности из базы данных.
    
    Args:
        limit: Количество дней для получения
        
    Returns:
        list: Список данных индекса страха и жадности
    """
    try:
        logger.info(f"Getting fear and greed index from database for last {limit} days")
        
        # Запрос к базе данных
        query = """
        SELECT date, value, value_classification, timestamp
        FROM crypto.fear_greed_index
        ORDER BY date DESC
        LIMIT %s
        """
        
        result = execute_query(query, (limit,))
        
        if not result:
            logger.warning("No fear and greed index data found in database")
            # Возвращаем фиктивные данные в случае ошибки
            return [
                {'value': 74, 'value_classification': 'Greed', 'timestamp': int(time.time())},
                {'value': 73, 'value_classification': 'Greed', 'timestamp': int(time.time()) - 86400},
                {'value': 71, 'value_classification': 'Greed', 'timestamp': int(time.time()) - 172800},
                {'value': 70, 'value_classification': 'Greed', 'timestamp': int(time.time()) - 259200},
                {'value': 68, 'value_classification': 'Greed', 'timestamp': int(time.time()) - 345600}
            ]
        
        # Преобразуем результаты в нужный формат
        fear_greed_data = []
        
        for row in result:
            fear_greed_data.append({
                'value': row['value'],
                'value_classification': row['value_classification'],
                'timestamp': row['timestamp']
            })
        
        logger.info(f"Retrieved {len(fear_greed_data)} fear and greed index records from database")
        
        return fear_greed_data
    except Exception as e:
        logger.error(f"Error getting fear and greed index from database: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Возвращаем фиктивные данные в случае ошибки
        return [
            {'value': 74, 'value_classification': 'Greed', 'timestamp': int(time.time())},
            {'value': 73, 'value_classification': 'Greed', 'timestamp': int(time.time()) - 86400},
            {'value': 71, 'value_classification': 'Greed', 'timestamp': int(time.time()) - 172800},
            {'value': 70, 'value_classification': 'Greed', 'timestamp': int(time.time()) - 259200},
            {'value': 68, 'value_classification': 'Greed', 'timestamp': int(time.time()) - 345600}
        ]

def get_market_global_data_from_db():
    """
    Получение глобальных рыночных данных из базы данных.
    
    Returns:
        dict: Глобальные рыночные данные
    """
    try:
        logger.info("Getting global market data from database")
        
        # Получаем данные о топ-монетах для расчета доминирования
        query = """
        SELECT symbol, market_cap
        FROM crypto.coins_metrics
        ORDER BY market_cap DESC
        LIMIT 20
        """
        
        result = execute_query(query)
        
        if not result:
            logger.warning("No coins data found in database for global market calculation")
            # Возвращаем фиктивные данные в случае ошибки
            return {
                'total_market_cap': {'usd': 2000000000000},
                'total_volume': {'usd': 100000000000},
                'market_cap_percentage': {'btc': 60.79, 'eth': 18.2},
                'market_cap_change_percentage_24h_usd': -1.45
            }
        
        # Рассчитываем общую капитализацию
        total_market_cap = sum(float(row['market_cap']) for row in result)
        
        # Находим BTC и ETH для расчета доминирования
        btc_market_cap = 0
        eth_market_cap = 0
        
        for row in result:
            if row['symbol'].upper() == 'BTC':
                btc_market_cap = float(row['market_cap'])
            elif row['symbol'].upper() == 'ETH':
                eth_market_cap = float(row['market_cap'])
        
        # Рассчитываем процентное доминирование
        btc_dominance = (btc_market_cap / total_market_cap * 100) if total_market_cap > 0 else 60.79
        eth_dominance = (eth_market_cap / total_market_cap * 100) if total_market_cap > 0 else 18.2
        
        # Получаем данные об объеме торгов
        query = """
        SELECT SUM(total_volume) as total_volume
        FROM crypto.coins_metrics
        """
        
        volume_result = execute_query(query)
        total_volume = float(volume_result[0]['total_volume']) if volume_result else 100000000000
        
        # Получаем данные об изменении капитализации за 24 часа
        # Для этого нам нужны данные за последние два дня
        query = """
        SELECT date, total_market_cap
        FROM crypto.market_history
        ORDER BY date DESC
        LIMIT 2
        """
        
        change_result = execute_query(query)
        
        if len(change_result) >= 2:
            today_cap = float(change_result[0]['total_market_cap'])
            yesterday_cap = float(change_result[1]['total_market_cap'])
            market_cap_change = ((today_cap - yesterday_cap) / yesterday_cap * 100) if yesterday_cap > 0 else -1.45
        else:
            market_cap_change = -1.45
        
        logger.info("Retrieved global market data from database")
        
        return {
            'total_market_cap': {'usd': total_market_cap},
            'total_volume': {'usd': total_volume},
            'market_cap_percentage': {'btc': btc_dominance, 'eth': eth_dominance},
            'market_cap_change_percentage_24h_usd': market_cap_change
        }
    except Exception as e:
        logger.error(f"Error getting global market data from database: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Возвращаем фиктивные данные в случае ошибки
        return {
            'total_market_cap': {'usd': 2000000000000},
            'total_volume': {'usd': 100000000000},
            'market_cap_percentage': {'btc': 60.79, 'eth': 18.2},
            'market_cap_change_percentage_24h_usd': -1.45
        }

def get_historical_market_cap_from_db():
    """
    Получение исторических данных о капитализации и объеме торгов рынка из базы данных.
    
    Returns:
        dict: Исторические данные о капитализации и объеме
    """
    try:
        logger.info("Getting historical market cap data from database")
        
        # Получаем данные из базы
        market_data = get_market_history_from_db(days=365)
        
        # Преобразуем строки дат в объекты datetime
        dates = [datetime.strptime(date_str, "%Y-%m-%d") for date_str in market_data["dates"]]
        
        logger.info(f"Retrieved {len(dates)} historical market cap records from database")
        
        return {
            'dates': dates,
            'caps': market_data["caps"],
            'volumes': market_data["volumes"]
        }
    except Exception as e:
        logger.error(f"Error getting historical market cap from database: {str(e)}")
        logger.error(traceback.format_exc())
        
        # В случае ошибки возвращаем пустые списки
        return {
            'dates': [],
            'caps': [],
            'volumes': []
        }

# Функции-обертки для совместимости с существующим кодом

def fetch_market_data(cache_file=None, force_refresh=False):
    """
    Получает данные о капитализации и объеме торгов из базы данных.
    Сохраняет обратную совместимость с оригинальной функцией.
    
    Args:
        cache_file: Игнорируется, оставлен для совместимости
        force_refresh: Игнорируется, оставлен для совместимости
        
    Returns:
        dict: Словарь с датами, капитализацией и объемами
    """
    return get_market_history_from_db()

# Инициализация базы данных при импорте модуля
try:
    initialize_database()
except Exception as e:
    logger.error(f"Error initializing database: {str(e)}")
    logger.error(traceback.format_exc())
