"""
Скрипт для периодического обновления данных ATR в базе данных.
Запускается отдельно от основного приложения.
"""
import requests
import time
import logging
import argparse
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("update_db.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("update_db")

# Константы
API_BASE_URL = "http://localhost:8008"  # URL FastAPI сервера на порту 8008
DEFAULT_INTERVAL = 3 * 60 * 60  # 3 часа в секундах

def update_database():
    """
    Запуск обновления базы данных через API
    
    Returns:
        bool: Успешность операции
    """
    try:
        logger.info("Запуск обновления базы данных...")
        
        # Отправляем запрос на обновление базы данных
        response = requests.get(f"{API_BASE_URL}/update_database")
        response.raise_for_status()
        data = response.json()
        
        if data["status"] == "ok":
            logger.info("Обновление базы данных запущено успешно")
            return True
        else:
            logger.error(f"Ошибка при запуске обновления базы данных: {data}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при запуске обновления базы данных: {str(e)}")
        return False

def get_last_update_time():
    """
    Получение времени последнего обновления данных в базе
    
    Returns:
        str: Время последнего обновления в формате ISO или None
    """
    try:
        response = requests.get(f"{API_BASE_URL}/last_update_time")
        response.raise_for_status()
        data = response.json()
        
        if data["status"] == "ok":
            return data["last_update"]
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении времени последнего обновления: {str(e)}")
        return None

def check_api_availability():
    """
    Проверка доступности API
    
    Returns:
        bool: Доступность API
    """
    try:
        response = requests.get(f"{API_BASE_URL}/")
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"API недоступен: {str(e)}")
        return False

def main():
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description='Скрипт для периодического обновления данных ATR в базе данных')
    parser.add_argument('--interval', type=int, default=DEFAULT_INTERVAL,
                        help=f'Интервал обновления в секундах (по умолчанию {DEFAULT_INTERVAL} секунд = 3 часа)')
    parser.add_argument('--once', action='store_true',
                        help='Запустить обновление один раз и выйти')
    args = parser.parse_args()
    
    logger.info(f"Запуск скрипта обновления с интервалом {args.interval} секунд")
    
    # Проверяем доступность API
    if not check_api_availability():
        logger.error("API недоступен. Убедитесь, что сервер запущен.")
        return
    
    # Если указан флаг --once, запускаем обновление один раз и выходим
    if args.once:
        logger.info("Запуск однократного обновления")
        update_database()
        return
    
    # Бесконечный цикл для периодического обновления
    try:
        while True:
            # Получаем время последнего обновления
            last_update_iso = get_last_update_time()
            
            if last_update_iso:
                # Преобразуем ISO строку в datetime объект
                last_update = datetime.fromisoformat(last_update_iso)
                
                # Вычисляем, сколько времени прошло с последнего обновления
                now = datetime.now()
                time_diff = now - last_update
                
                # Если прошло меньше интервала, ждем
                if time_diff.total_seconds() < args.interval:
                    seconds_to_wait = args.interval - time_diff.total_seconds()
                    logger.info(f"Последнее обновление было {time_diff.total_seconds()} секунд назад. "
                                f"Ожидание {seconds_to_wait} секунд до следующего обновления.")
                    time.sleep(seconds_to_wait)
            
            # Запускаем обновление
            update_success = update_database()
            
            if update_success:
                logger.info(f"Обновление выполнено успешно. Следующее обновление через {args.interval} секунд.")
            else:
                logger.warning(f"Обновление не удалось. Повторная попытка через {args.interval} секунд.")
            
            # Ждем до следующего обновления
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("Скрипт остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка в основном цикле: {str(e)}")

if __name__ == "__main__":
    main()
