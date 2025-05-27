"""
Модуль для периодического сбора и записи данных в базу PostgreSQL.
Предназначен для предварительной загрузки данных, чтобы избежать
прямых запросов к API при открытии страницы.
"""
import os
import sys
import time
import json
import logging
import pandas as pd
import requests
from datetime import datetime, timedelta
import traceback
import schedule

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем модуль для работы с базой данных
from app.utils.db.db_connector import (
    initialize_database,
    execute_query,
    close_connection_pool
)

# Импортируем модуль для получения данных
from app.data_fetcher import (
    get_coin_data,
    process_weekly_data,
    COIN_IDS,
    fetch_market_data
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('data_collector.log', mode='a')
    ]
)
logger = logging.getLogger('data_collector')

def get_and_save_market_history():
    """
    Получение и сохранение исторических данных о капитализации и объеме рынка.
    """
    try:
        logger.info("Fetching market history data...")
        
        # Получаем данные через существующую функцию
        market_data = fetch_market_data(force_refresh=True)
        
        if not market_data or 'dates' not in market_data or not market_data['dates']:
            logger.error("Failed to fetch market history data: empty response")
            return False
        
        logger.info(f"Fetched {len(market_data['dates'])} market history records")
        
        # Подготавливаем данные для вставки
        records = []
        for i in range(len(market_data['dates'])):
            date_str = market_data['dates'][i]
            cap = market_data['caps'][i]
            volume = market_data['volumes'][i]
            
            # Преобразуем строку даты в объект date
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            records.append({
                'date': date_obj,
                'total_market_cap': cap,
                'total_volume': volume
            })
        
        # Сохраняем данные в базу
        for record in records:
            # Проверяем, существует ли запись для этой даты
            query = """
            SELECT id FROM all_futures.market_history
            WHERE date = %s
            """
            result = execute_query(query, (record['date'],))
            
            if result and len(result) > 0:
                # Обновляем существующую запись
                query = """
                UPDATE all_futures.market_history
                SET total_market_cap = %s, total_volume = %s, updated_at = CURRENT_TIMESTAMP
                WHERE date = %s
                """
                execute_query(
                    query, 
                    (record['total_market_cap'], record['total_volume'], record['date']),
                    fetch=False
                )
            else:
                # Вставляем новую запись
                query = """
                INSERT INTO all_futures.market_history (date, total_market_cap, total_volume)
                VALUES (%s, %s, %s)
                """
                execute_query(
                    query, 
                    (record['date'], record['total_market_cap'], record['total_volume']),
                    fetch=False
                )
        
        logger.info(f"Saved {len(records)} market history records to database")
        return True
    except Exception as e:
        logger.error(f"Error saving market history data: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def get_and_save_top_coins(limit=20):
    """
    Получение и сохранение данных о топ-криптовалютах.
    
    Args:
        limit: Количество криптовалют для получения
    """
    try:
        logger.info(f"Fetching top {limit} coins data...")
        
        # Получаем данные о топ-криптовалютах с CoinGecko
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': limit,
            'page': 1,
            'sparkline': False,
            'price_change_percentage': '24h'
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        coins_data = response.json()
        
        logger.info(f"Fetched {len(coins_data)} coins")
        
        # Сохраняем данные в базу
        for coin in coins_data:
            # Извлекаем необходимые данные
            symbol = coin.get('symbol', '').upper()
            name = coin.get('name', '')
            current_price = coin.get('current_price', 0)
            price_change_percentage_24h = coin.get('price_change_percentage_24h', 0)
            market_cap = coin.get('market_cap', 0)
            total_volume = coin.get('total_volume', 0)
            image_url = coin.get('image', '')
            
            # Проверяем, существует ли запись для этого символа
            query = """
            SELECT id FROM all_futures.coins_metrics
            WHERE symbol = %s
            """
            result = execute_query(query, (symbol,))
            
            if result and len(result) > 0:
                # Обновляем существующую запись
                query = """
                UPDATE all_futures.coins_metrics
                SET name = %s, current_price = %s, price_change_percentage_24h = %s,
                    market_cap = %s, total_volume = %s, image_url = %s,
                    last_updated = CURRENT_TIMESTAMP
                WHERE symbol = %s
                """
                execute_query(
                    query, 
                    (name, current_price, price_change_percentage_24h, 
                     market_cap, total_volume, image_url, symbol),
                    fetch=False
                )
            else:
                # Вставляем новую запись
                query = """
                INSERT INTO all_futures.coins_metrics 
                (symbol, name, current_price, price_change_percentage_24h, market_cap, total_volume, image_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                execute_query(
                    query, 
                    (symbol, name, current_price, price_change_percentage_24h, 
                     market_cap, total_volume, image_url),
                    fetch=False
                )
        
        logger.info(f"Saved {len(coins_data)} coins to database")
        return True
    except Exception as e:
        logger.error(f"Error saving top coins data: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def get_and_save_fear_greed_index(limit=5):
    """
    Получение и сохранение индекса страха и жадности.
    
    Args:
        limit: Количество дней для получения
    """
    try:
        logger.info(f"Fetching fear and greed index for last {limit} days...")
        
        # Получаем индекс страха и жадности с Alternative.me
        url = f"https://api.alternative.me/fng/?limit={limit}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if 'data' not in data or not data['data']:
            logger.error("Failed to fetch fear and greed index: empty response")
            return False
        
        logger.info(f"Fetched {len(data['data'])} fear and greed index records")
        
        # Сохраняем данные в базу
        for item in data['data']:
            value = int(item['value'])
            value_classification = item['value_classification']
            timestamp = int(item['timestamp'])
            
            # Преобразуем timestamp в дату
            date_obj = datetime.fromtimestamp(timestamp).date()
            
            # Проверяем, существует ли запись для этой даты
            query = """
            SELECT id FROM all_futures.fear_greed_index
            WHERE date = %s
            """
            result = execute_query(query, (date_obj,))
            
            if result and len(result) > 0:
                # Обновляем существующую запись
                query = """
                UPDATE all_futures.fear_greed_index
                SET value = %s, value_classification = %s, timestamp = %s
                WHERE date = %s
                """
                execute_query(
                    query, 
                    (value, value_classification, timestamp, date_obj),
                    fetch=False
                )
            else:
                # Вставляем новую запись
                query = """
                INSERT INTO all_futures.fear_greed_index 
                (date, value, value_classification, timestamp)
                VALUES (%s, %s, %s, %s)
                """
                execute_query(
                    query, 
                    (date_obj, value, value_classification, timestamp),
                    fetch=False
                )
        
        logger.info(f"Saved {len(data['data'])} fear and greed index records to database")
        return True
    except Exception as e:
        logger.error(f"Error saving fear and greed index: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def update_all_data():
    """
    Обновление всех данных в базе.
    """
    try:
        logger.info("Starting data update process...")
        
        # Инициализируем базу данных (создаем схему и таблицы, если они не существуют)
        initialize_database()
        
        # Обновляем данные
        market_history_result = get_and_save_market_history()
        top_coins_result = get_and_save_top_coins()
        fear_greed_result = get_and_save_fear_greed_index()
        
        # Проверяем результаты
        if market_history_result and top_coins_result and fear_greed_result:
            logger.info("All data updated successfully")
            return True
        else:
            logger.warning("Some data updates failed")
            return False
    except Exception as e:
        logger.error(f"Error updating all data: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def schedule_updates():
    """
    Настройка расписания обновления данных.
    """
    # Обновляем данные при запуске
    update_all_data()
    
    # Настраиваем расписание
    # Обновляем рыночные данные каждый час
    schedule.every(1).hours.do(get_and_save_market_history)
    
    # Обновляем данные о топ-монетах каждые 15 минут
    schedule.every(15).minutes.do(get_and_save_top_coins)
    
    # Обновляем индекс страха и жадности каждые 6 часов
    schedule.every(6).hours.do(get_and_save_fear_greed_index)
    
    # Полное обновление всех данных раз в день
    schedule.every().day.at("00:00").do(update_all_data)
    
    logger.info("Update schedule configured")
    
    # Запускаем цикл обновления
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Проверяем расписание каждую минуту
        except KeyboardInterrupt:
            logger.info("Update process interrupted by user")
            break
        except Exception as e:
            logger.error(f"Error in update loop: {str(e)}")
            logger.error(traceback.format_exc())
            time.sleep(300)  # При ошибке ждем 5 минут перед следующей попыткой

if __name__ == "__main__":
    try:
        logger.info("Starting data collector service")
        schedule_updates()
    except Exception as e:
        logger.error(f"Fatal error in data collector: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        # Закрываем соединения с базой данных
        close_connection_pool()
        logger.info("Data collector service stopped")
