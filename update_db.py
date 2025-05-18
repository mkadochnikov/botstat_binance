#!/usr/bin/env python3
"""
Скрипт для обновления данных ATR в базе данных.
Запускается вручную для обновления данных в таблице crypto.binance_atr.
Рекомендуется запускать каждые 3 часа для поддержания актуальности данных.
"""
import os
import sys
import time
import argparse
import logging
import requests
import datetime
import traceback
from typing import Optional, Dict, Any

# Настройка расширенного логирования
# Получаем абсолютный путь к директории проекта
project_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(project_dir, 'update_db.log')

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
logger = logging.getLogger('update_db')
logger.info(f"Update DB script initialized. Log file: {log_file}")

# Константы
API_BASE_URL = "http://localhost:8008"  # URL FastAPI сервера
DEFAULT_LIMIT = None  # По умолчанию обрабатываем все символы


def get_last_update_time() -> Optional[str]:
    """
    Получение времени последнего обновления данных в базе.
    
    Returns:
        Optional[str]: Время последнего обновления в ISO формате или None
    """
    try:
        logger.info(f"Getting last update time from API: {API_BASE_URL}/last_update_time")
        response = requests.get(f"{API_BASE_URL}/last_update_time")
        response.raise_for_status()
        data = response.json()
        
        logger.debug(f"Last update time response: {data}")
        
        if data["status"] == "ok":
            logger.info(f"Last update time: {data['last_update']}")
            return data["last_update"]
        
        logger.warning(f"No last update time available: {data}")
        return None
    except Exception as e:
        logger.error(f"Error getting last update time: {str(e)}")
        logger.error(traceback.format_exc())
        return None


def trigger_database_update(limit: Optional[int] = None) -> bool:
    """
    Запуск обновления базы данных.
    
    Args:
        limit: Ограничение количества символов
        
    Returns:
        bool: True, если обновление запущено успешно, иначе False
    """
    try:
        url = f"{API_BASE_URL}/update_database"
        if limit is not None:
            url += f"?limit={limit}"
            
        logger.info(f"Triggering database update: {url}")
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        logger.debug(f"Update database response: {data}")
        
        if data["status"] == "ok":
            logger.info("Database update triggered successfully")
            return True
        
        logger.error(f"Error triggering database update: {data}")
        return False
    except Exception as e:
        logger.error(f"Error triggering database update: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def format_time_ago(last_update_iso: Optional[str]) -> str:
    """
    Форматирование времени последнего обновления для отображения.
    
    Args:
        last_update_iso: Время последнего обновления в ISO формате
        
    Returns:
        str: Отформатированная строка с временем последнего обновления
    """
    if not last_update_iso:
        return "Нет данных"
    
    try:
        # Преобразуем ISO строку в datetime объект
        last_update = datetime.datetime.fromisoformat(last_update_iso)
        
        # Форматируем время
        formatted_time = last_update.strftime("%Y-%m-%d %H:%M:%S")
        
        # Вычисляем, сколько времени прошло с последнего обновления
        now = datetime.datetime.now()
        time_diff = now - last_update
        
        # Форматируем разницу во времени
        if time_diff.days > 0:
            time_ago = f"{time_diff.days} дней назад"
        elif time_diff.seconds >= 3600:
            hours = time_diff.seconds // 3600
            time_ago = f"{hours} часов назад"
        elif time_diff.seconds >= 60:
            minutes = time_diff.seconds // 60
            time_ago = f"{minutes} минут назад"
        else:
            time_ago = f"{time_diff.seconds} секунд назад"
        
        return f"{formatted_time} ({time_ago})"
    except Exception as e:
        logger.error(f"Error formatting time: {str(e)}")
        logger.error(traceback.format_exc())
        return f"Ошибка форматирования времени: {str(e)}"


def wait_for_update_completion(timeout: int = 300, check_interval: int = 10) -> bool:
    """
    Ожидание завершения обновления базы данных.
    
    Args:
        timeout: Максимальное время ожидания в секундах
        check_interval: Интервал проверки в секундах
        
    Returns:
        bool: True, если обновление завершено успешно, иначе False
    """
    logger.info(f"Waiting for update completion (timeout: {timeout} sec)...")
    
    # Получаем время последнего обновления перед запуском
    initial_update_time = get_last_update_time()
    logger.debug(f"Initial update time: {initial_update_time}")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Получаем текущее время последнего обновления
        current_update_time = get_last_update_time()
        logger.debug(f"Current update time: {current_update_time}")
        
        # Если время обновления изменилось, значит обновление завершено
        if current_update_time and current_update_time != initial_update_time:
            logger.info(f"Update completed successfully. New update time: {format_time_ago(current_update_time)}")
            return True
        
        # Ждем перед следующей проверкой
        elapsed = int(time.time() - start_time)
        logger.info(f"Waiting... Elapsed: {elapsed} sec of {timeout} sec")
        time.sleep(check_interval)
    
    logger.error(f"Update timeout ({timeout} sec)")
    return False


def test_api_connection() -> bool:
    """
    Проверка соединения с API.
    
    Returns:
        bool: True, если соединение успешно, иначе False
    """
    try:
        logger.info(f"Testing API connection: {API_BASE_URL}")
        response = requests.get(f"{API_BASE_URL}/")
        response.raise_for_status()
        data = response.json()
        
        logger.debug(f"API connection test response: {data}")
        
        if data["status"] == "ok":
            logger.info("API connection test successful")
            return True
        
        logger.warning(f"API connection test failed: {data}")
        return False
    except Exception as e:
        logger.error(f"API connection test failed: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def main():
    """
    Основная функция скрипта.
    """
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description='Обновление данных ATR в базе данных')
    parser.add_argument('--limit', type=int, default=DEFAULT_LIMIT, help='Ограничение количества символов')
    parser.add_argument('--wait', action='store_true', help='Ожидать завершения обновления')
    parser.add_argument('--timeout', type=int, default=300, help='Таймаут ожидания в секундах')
    parser.add_argument('--test', action='store_true', help='Только проверить соединение с API')
    args = parser.parse_args()
    
    # Выводим информацию о текущих настройках
    logger.info(f"Starting database update with parameters: limit={args.limit}, wait={args.wait}, timeout={args.timeout}, test={args.test}")
    
    # Если указан флаг тестирования, только проверяем соединение
    if args.test:
        if test_api_connection():
            logger.info("API connection test passed")
            sys.exit(0)
        else:
            logger.error("API connection test failed")
            sys.exit(1)
    
    # Получаем время последнего обновления
    last_update_time = get_last_update_time()
    if last_update_time:
        logger.info(f"Last database update: {format_time_ago(last_update_time)}")
    else:
        logger.warning("Could not get last update time")
    
    # Запускаем обновление базы данных
    success = trigger_database_update(args.limit)
    
    if not success:
        logger.error("Failed to trigger database update")
        sys.exit(1)
    
    # Если указан флаг ожидания, ждем завершения обновления
    if args.wait:
        if wait_for_update_completion(args.timeout):
            logger.info("Database update completed successfully")
        else:
            logger.error("Failed to wait for database update completion")
            sys.exit(1)
    else:
        logger.info("Database update triggered in background mode")
    
    logger.info("Script completed")


if __name__ == "__main__":
    main()
