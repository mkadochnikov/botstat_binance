import time
import asyncio
import logging
import random
from typing import Dict, List, Any, Optional, Union, Tuple
import aiohttp
import requests
from functools import wraps

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Базовый URL для Binance Futures API
BASE_URL = "https://fapi.binance.com"

# Кеш для хранения данных
cache = {}
CACHE_EXPIRY = 30  # секунды

# Настройки для предотвращения бана
MIN_REQUEST_INTERVAL = 0.5  # минимальный интервал между запросами (секунды)
MAX_REQUEST_INTERVAL = 2.0  # максимальный интервал между запросами (секунды)
RETRY_DELAY_MULTIPLIER = 2  # множитель задержки при повторных попытках
MAX_RETRIES = 3  # максимальное количество повторных попыток

# Список прокси (заполняется пользователем)
PROXY_LIST = [
    # Формат: "http://username:password@host:port" или "http://host:port"
    # Пример:
    # "http://user:pass@proxy1.example.com:8080",
    # "http://proxy2.example.com:8080",
]

# Кеш работоспособных прокси
WORKING_PROXIES = []
# Кеш неработоспособных прокси
FAILED_PROXIES = set()
# Время последней проверки прокси
LAST_PROXY_CHECK = 0
# Интервал повторной проверки неработоспособных прокси (в секундах)
PROXY_RETRY_INTERVAL = 300  # 5 минут


def cache_result(expiry=CACHE_EXPIRY):
    """Декоратор для кеширования результатов функций"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Создаем ключ кеша на основе аргументов функции
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Проверяем, есть ли данные в кеше и не истек ли срок их действия
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if time.time() - timestamp < expiry:
                    return result
            
            # Если данных нет в кеше или они устарели, вызываем функцию
            result = await func(*args, **kwargs)
            cache[cache_key] = (result, time.time())
            return result
        return wrapper
    return decorator


def retry(max_retries=MAX_RETRIES, initial_delay=1):
    """Декоратор для повторных попыток при ошибках API с адаптивной задержкой"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            current_delay = initial_delay
            
            while retries < max_retries:
                try:
                    # Добавляем случайную задержку перед каждым запросом для предотвращения бана
                    await asyncio.sleep(random.uniform(MIN_REQUEST_INTERVAL, MAX_REQUEST_INTERVAL))
                    return await func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    
                    # Проверяем, является ли ошибка баном по IP (код 418)
                    is_ip_ban = False
                    if isinstance(e, Exception) and "418" in str(e) and "banned" in str(e).lower():
                        is_ip_ban = True
                        logger.error(f"IP BAN detected: {str(e)}")
                    
                    if retries == max_retries:
                        logger.error(f"Failed after {max_retries} retries: {str(e)}")
                        raise
                    
                    # Увеличиваем задержку с каждой попыткой
                    if is_ip_ban:
                        # Если это бан по IP, используем более длительную задержку
                        retry_delay = current_delay * RETRY_DELAY_MULTIPLIER * 5
                    else:
                        retry_delay = current_delay * RETRY_DELAY_MULTIPLIER
                    
                    logger.warning(f"Retry {retries}/{max_retries} after error: {str(e)}")
                    logger.info(f"Waiting {retry_delay} seconds before next attempt...")
                    
                    await asyncio.sleep(retry_delay)
                    current_delay = retry_delay  # Увеличиваем задержку для следующей попытки
        return wrapper
    return decorator


async def check_proxy(proxy: str) -> bool:
    """
    Проверка работоспособности прокси
    
    Args:
        proxy: URL прокси-сервера
        
    Returns:
        bool: True, если прокси работает, иначе False
    """
    try:
        # Создаем временную сессию с прокси
        timeout = aiohttp.ClientTimeout(total=10)  # 10 секунд таймаут
        async with aiohttp.ClientSession(proxy=proxy, timeout=timeout) as session:
            # Пробуем сделать запрос к Binance
            async with session.get("https://fapi.binance.com/fapi/v1/ping") as response:
                if response.status == 200:
                    logger.info(f"Proxy {proxy} is working")
                    return True
                else:
                    logger.warning(f"Proxy {proxy} returned status {response.status}")
                    return False
    except Exception as e:
        logger.warning(f"Proxy {proxy} check failed: {str(e)}")
        return False


async def get_working_proxy() -> Optional[str]:
    """
    Получение работоспособного прокси
    
    Returns:
        Optional[str]: URL работоспособного прокси или None, если нет работающих прокси
    """
    global WORKING_PROXIES, FAILED_PROXIES, LAST_PROXY_CHECK
    
    # Если нет прокси в списке, возвращаем None
    if not PROXY_LIST:
        return None
    
    # Если есть работающие прокси, возвращаем случайный из них
    if WORKING_PROXIES:
        return random.choice(WORKING_PROXIES)
    
    # Проверяем, не пора ли повторно проверить неработающие прокси
    current_time = time.time()
    if current_time - LAST_PROXY_CHECK > PROXY_RETRY_INTERVAL:
        FAILED_PROXIES = set()  # Сбрасываем список неработающих прокси
        LAST_PROXY_CHECK = current_time
    
    # Проверяем все прокси, которые еще не проверены или не отмечены как неработающие
    for proxy in PROXY_LIST:
        if proxy not in FAILED_PROXIES:
            if await check_proxy(proxy):
                WORKING_PROXIES.append(proxy)
                return proxy
            else:
                FAILED_PROXIES.add(proxy)
    
    # Если нет работающих прокси, возвращаем None
    logger.warning("No working proxies found")
    return None


class BinanceClient:
    """Клиент для работы с Binance Futures API"""
    
    def __init__(self):
        self.session = None
        self.last_request_time = 0
        self.current_proxy = None
    
    async def _ensure_session(self):
        """Убеждаемся, что сессия aiohttp существует и использует работающий прокси"""
        if self.session is None or self.session.closed:
            # Пытаемся получить работающий прокси
            proxy = await get_working_proxy()
            
            if proxy:
                logger.info(f"Using proxy: {proxy}")
                try:
                    self.session = aiohttp.ClientSession(proxy=proxy)
                    self.current_proxy = proxy
                except Exception as e:
                    logger.error(f"Failed to create session with proxy {proxy}: {str(e)}")
                    # Если не удалось создать сессию с прокси, создаем без прокси
                    self.session = aiohttp.ClientSession()
                    self.current_proxy = None
            else:
                logger.info("No working proxies available, using direct connection")
                self.session = aiohttp.ClientSession()
                self.current_proxy = None
        
        return self.session
    
    async def close(self):
        """Закрываем сессию aiohttp"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _rate_limit_request(self):
        """Управление скоростью запросов для предотвращения бана"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        # Если прошло меньше минимального интервала, ждем
        if elapsed < MIN_REQUEST_INTERVAL:
            wait_time = MIN_REQUEST_INTERVAL - elapsed
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    async def _handle_proxy_error(self, e: Exception):
        """
        Обработка ошибок прокси
        
        Args:
            e: Исключение, вызванное ошибкой прокси
        """
        if self.current_proxy:
            logger.warning(f"Proxy error with {self.current_proxy}: {str(e)}")
            
            # Удаляем неработающий прокси из списка работающих
            if self.current_proxy in WORKING_PROXIES:
                WORKING_PROXIES.remove(self.current_proxy)
            
            # Добавляем в список неработающих
            FAILED_PROXIES.add(self.current_proxy)
            
            # Закрываем текущую сессию
            await self.close()
            
            # Сбрасываем текущий прокси
            self.current_proxy = None
    
    @retry(max_retries=MAX_RETRIES)
    @cache_result()
    async def get_symbols(self) -> List[str]:
        """Получение списка всех доступных фьючерсных символов"""
        await self._rate_limit_request()
        
        try:
            session = await self._ensure_session()
            
            async with session.get(f"{BASE_URL}/fapi/v1/exchangeInfo") as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"API error: {response.status} - {text}")
                
                data = await response.json()
                symbols = [symbol["symbol"] for symbol in data["symbols"] if symbol["status"] == "TRADING"]
                return symbols
        except aiohttp.ClientError as e:
            # Обрабатываем ошибки прокси
            await self._handle_proxy_error(e)
            # Повторно вызываем метод после обработки ошибки прокси
            return await self.get_symbols()
    
    @retry(max_retries=MAX_RETRIES)
    @cache_result()
    async def get_klines(self, symbol: str, interval: str, limit: int = 30) -> List[Dict[str, Any]]:
        """Получение исторических данных свечей"""
        await self._rate_limit_request()
        
        try:
            session = await self._ensure_session()
            
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
            
            async with session.get(f"{BASE_URL}/fapi/v1/klines", params=params) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"API error: {response.status} - {text}")
                
                data = await response.json()
                formatted_klines = []
                
                for kline in data:
                    formatted_klines.append({
                        "open_time": kline[0],
                        "open": float(kline[1]),
                        "high": float(kline[2]),
                        "low": float(kline[3]),
                        "close": float(kline[4]),
                        "volume": float(kline[5]),
                        "close_time": kline[6],
                    })
                
                return formatted_klines
        except aiohttp.ClientError as e:
            # Обрабатываем ошибки прокси
            await self._handle_proxy_error(e)
            # Повторно вызываем метод после обработки ошибки прокси
            return await self.get_klines(symbol, interval, limit)
    
    @retry(max_retries=MAX_RETRIES)
    @cache_result()
    async def get_current_price(self, symbol: Optional[str] = None) -> Dict[str, float]:
        """Получение текущей цены для символа или всех символов"""
        await self._rate_limit_request()
        
        try:
            session = await self._ensure_session()
            
            params = {}
            if symbol:
                params["symbol"] = symbol
            
            async with session.get(f"{BASE_URL}/fapi/v1/ticker/price", params=params) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"API error: {response.status} - {text}")
                
                data = await response.json()
                
                if isinstance(data, list):
                    return {item["symbol"]: float(item["price"]) for item in data}
                else:
                    return {data["symbol"]: float(data["price"])}
        except aiohttp.ClientError as e:
            # Обрабатываем ошибки прокси
            await self._handle_proxy_error(e)
            # Повторно вызываем метод после обработки ошибки прокси
            return await self.get_current_price(symbol)


# Создаем синглтон клиента
binance_client = BinanceClient()
