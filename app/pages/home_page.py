"""
Модуль для интеграции функций чтения данных из PostgreSQL в страницы приложения.
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import traceback
import sys
import os
import time

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Импортируем модуль для получения данных из базы
from app.data_fetcher_db import (
    get_top_coins_from_db,
    get_market_global_data_from_db,
    get_fear_greed_index_from_db,
    get_historical_market_cap_from_db
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('home_page_db.log', mode='a')
    ]
)
logger = logging.getLogger('home_page_db')

@st.cache_data(ttl=60)
def get_top_coins(limit=20):
    """
    Получение данных о топ-криптовалютах из базы данных
    """
    try:
        return get_top_coins_from_db(limit)
    except Exception as e:
        logger.error(f"Error in get_top_coins: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"Ошибка при получении данных о топ-криптовалютах: {str(e)}")
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

@st.cache_data(ttl=60)
def get_market_global_data():
    """
    Получение глобальных рыночных данных из базы данных
    """
    try:
        return get_market_global_data_from_db()
    except Exception as e:
        logger.error(f"Error in get_market_global_data: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"Ошибка при получении глобальных рыночных данных: {str(e)}")
        # Возвращаем фиктивные данные в случае ошибки
        return {
            'total_market_cap': {'usd': 2000000000000},
            'total_volume': {'usd': 100000000000},
            'market_cap_percentage': {'btc': 60.79, 'eth': 18.2},
            'market_cap_change_percentage_24h_usd': -1.45
        }

@st.cache_data(ttl=60)
def get_fear_greed_index(limit=5):
    """
    Получение индекса страха и жадности из базы данных
    """
    try:
        return get_fear_greed_index_from_db(limit)
    except Exception as e:
        logger.error(f"Error in get_fear_greed_index: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"Ошибка при получении индекса страха и жадности: {str(e)}")
        # Возвращаем фиктивные данные в случае ошибки
        return [
            {'value': 74, 'value_classification': 'Greed', 'timestamp': int(time.time())},
            {'value': 73, 'value_classification': 'Greed', 'timestamp': int(time.time()) - 86400},
            {'value': 71, 'value_classification': 'Greed', 'timestamp': int(time.time()) - 172800},
            {'value': 70, 'value_classification': 'Greed', 'timestamp': int(time.time()) - 259200},
            {'value': 68, 'value_classification': 'Greed', 'timestamp': int(time.time()) - 345600}
        ]

@st.cache_data(ttl=3600)  # Кэшируем на 1 час
def get_historical_market_cap():
    """
    Получение исторических данных о капитализации и объеме торгов рынка из базы данных
    """
    try:
        return get_historical_market_cap_from_db()
    except Exception as e:
        logger.error(f"Error in get_historical_market_cap: {str(e)}")
        logger.error(traceback.format_exc())
        st.error(f"Ошибка при получении исторических данных о капитализации: {str(e)}")
        # В случае ошибки возвращаем пустые списки
        return {
            'dates': [],
            'caps': [],
            'volumes': []
        }
