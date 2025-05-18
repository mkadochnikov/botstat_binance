import asyncio
import json
import logging
import random
import time
import traceback
from typing import Dict, List, Any, Optional, Set, Tuple, Union
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError
import requests
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('binance_websocket')

class BinanceWebSocketClient:
    """
    Клиент для работы с WebSocket API Binance
    """
    def __init__(self):
        self.ws = None
        self.running = False
        self.subscriptions = set()
        self.message_handler_task = None
        self.ws_lock = asyncio.Lock()  # Блокировка для синхронизации доступа к WebSocket
        self._recv_lock = asyncio.Lock()  # Отдельная блокировка для операций recv
        self.message_queue = asyncio.Queue()  # Очередь сообщений
        self.reconnect_delay = 1  # Начальная задержка для переподключения (в секундах)
        self.max_reconnect_delay = 300  # Максимальная задержка для переподключения (в секундах)
        self.last_connection_attempt = 0  # Время последней попытки подключения
        self.connection_cooldown = 10  # Минимальное время между попытками подключения (в секундах)
        self.subscription_rate_limit = 2  # Максимальное количество подписок в секунду
        self.subscription_batch_size = 1  # Количество символов в одной партии подписок
        self.subscription_batch_delay = 10  # Задержка между партиями подписок (в секундах)
        self.global_pause_interval = 5  # Количество партий, после которых делается глобальная пауза
        self.global_pause_duration = 30  # Длительность глобальной паузы (в секундах)
        self.too_many_requests_backoff = 15  # Множитель задержки при ошибке "Too many requests"
        self.initial_too_many_requests_pause = 60  # Начальная пауза при первой ошибке "Too many requests" (в секундах)
        self.too_many_requests_count = 0  # Счетчик ошибок "Too many requests"
        
        # Базовые URL для API Binance
        self.base_url = "https://fapi.binance.com"
        self.ws_url = "wss://fstream.binance.com/ws"
    
    async def connect(self) -> bool:
        """
        Установка соединения с WebSocket API Binance
        
        Returns:
            bool: True, если соединение установлено успешно, иначе False
        """
        # Проверяем, не слишком ли часто пытаемся подключиться
        current_time = time.time()
        if current_time - self.last_connection_attempt < self.connection_cooldown:
            logger.info(f"Соблюдаем cooldown период {self.connection_cooldown} секунд между попытками подключения")
            await asyncio.sleep(self.connection_cooldown)
        
        self.last_connection_attempt = time.time()
        
        try:
            async with self.ws_lock:
                if self.ws is not None:
                    try:
                        await self.ws.close()
                    except Exception as e:
                        logger.error(f"Error closing existing WebSocket connection: {str(e)}")
                
                logger.info("Connecting to Binance WebSocket...")
                self.ws = await websockets.connect(self.ws_url)
                self.running = True
                
                # Запускаем обработчик сообщений
                if self.message_handler_task is None or self.message_handler_task.done():
                    self.message_handler_task = asyncio.create_task(self.message_handler())
                
                logger.info("Connected to Binance WebSocket")
                return True
        except Exception as e:
            logger.error(f"Error connecting to Binance WebSocket: {str(e)}")
            self.running = False
            
            # Экспоненциальная задержка перед повторной попыткой
            await asyncio.sleep(self.reconnect_delay)
            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
            
            return False
    
    async def _is_connection_active(self) -> bool:
        """
        Проверка активности соединения
        
        Returns:
            bool: True, если соединение активно, иначе False
        """
        if self.ws is None:
            return False
        
        try:
            # Проверяем соединение с помощью ping
            async with self.ws_lock:
                pong_waiter = await self.ws.ping()
                await asyncio.wait_for(pong_waiter, timeout=5)
            return True
        except Exception:
            return False
    
    async def _safe_recv(self, timeout: float = 30) -> Optional[str]:
        """
        Безопасное получение сообщения с таймаутом и блокировкой
        
        Args:
            timeout: Таймаут в секундах
            
        Returns:
            Optional[str]: Полученное сообщение или None в случае ошибки
        """
        if self.ws is None:
            return None
        
        try:
            async with self._recv_lock:
                return await asyncio.wait_for(self.ws.recv(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for WebSocket message after {timeout} seconds")
            return None
        except ConnectionClosedError as e:
            logger.error(f"WebSocket connection closed while receiving: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error receiving WebSocket message: {str(e)}")
            return None
    
    async def message_handler(self):
        """
        Обработчик сообщений от WebSocket
        """
        logger.info("Starting WebSocket message handler")
        
        while self.running:
            try:
                # Проверяем активность соединения
                if not await self._is_connection_active():
                    logger.warning("WebSocket connection is not active, reconnecting...")
                    if await self.connect():
                        await self.resubscribe_all()
                    continue
                
                # Получаем сообщение
                message = await self._safe_recv()
                if message is None:
                    continue
                
                # Обрабатываем сообщение
                try:
                    data = json.loads(message)
                    await self.process_message(data)
                except json.JSONDecodeError:
                    logger.error(f"Error decoding JSON message: {message}")
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {str(e)}")
            except ConnectionClosedError as e:
                # Проверяем код ошибки
                if hasattr(e, 'code') and e.code == 1008:
                    self.too_many_requests_count += 1
                    backoff_time = self.initial_too_many_requests_pause if self.too_many_requests_count == 1 else self.reconnect_delay * self.too_many_requests_backoff
                    logger.warning(f"Too many requests error (code 1008), backing off for {backoff_time} seconds")
                    await asyncio.sleep(backoff_time)
                    self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
                else:
                    logger.error(f"WebSocket connection closed: {str(e)}")
                    await asyncio.sleep(self.reconnect_delay)
                    self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
                
                # Переподключаемся
                if await self.connect():
                    await self.resubscribe_all()
            except Exception as e:
                logger.error(f"Error in message handler: {str(e)}")
                logger.error(traceback.format_exc())
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
        
        logger.info("WebSocket message handler stopped")
    
    async def process_message(self, data: Dict[str, Any]):
        """
        Обработка полученного сообщения
        
        Args:
            data: Данные сообщения
        """
        # Помещаем сообщение в очередь для обработки
        await self.message_queue.put(data)
    
    async def subscribe(self, stream: str) -> bool:
        """
        Подписка на поток данных
        
        Args:
            stream: Название потока
            
        Returns:
            bool: True, если подписка выполнена успешно, иначе False
        """
        if not self.running or self.ws is None:
            if not await self.connect():
                return False
        
        try:
            # Проверяем, не подписаны ли мы уже на этот поток
            if stream in self.subscriptions:
                return True
            
            # Добавляем случайную задержку перед подпиской для предотвращения бана
            await asyncio.sleep(random.uniform(2.0, 5.0))
            
            # Формируем сообщение для подписки
            subscribe_msg = {
                "method": "SUBSCRIBE",
                "params": [stream],
                "id": int(time.time() * 1000)
            }
            
            # Отправляем сообщение
            async with self.ws_lock:
                await self.ws.send(json.dumps(subscribe_msg))
            
            # Добавляем поток в список подписок
            self.subscriptions.add(stream)
            logger.info(f"Subscribed to stream: {stream}")
            
            # Сбрасываем задержку переподключения при успешной подписке
            self.reconnect_delay = 1
            
            return True
        except Exception as e:
            logger.error(f"Error subscribing to stream {stream}: {str(e)}")
            return False
    
    async def unsubscribe(self, stream: str) -> bool:
        """
        Отписка от потока данных
        
        Args:
            stream: Название потока
            
        Returns:
            bool: True, если отписка выполнена успешно, иначе False
        """
        if not self.running or self.ws is None:
            return False
        
        try:
            # Проверяем, подписаны ли мы на этот поток
            if stream not in self.subscriptions:
                return True
            
            # Формируем сообщение для отписки
            unsubscribe_msg = {
                "method": "UNSUBSCRIBE",
                "params": [stream],
                "id": int(time.time() * 1000)
            }
            
            # Отправляем сообщение
            async with self.ws_lock:
                await self.ws.send(json.dumps(unsubscribe_msg))
            
            # Удаляем поток из списка подписок
            self.subscriptions.remove(stream)
            logger.info(f"Unsubscribed from stream: {stream}")
            
            return True
        except Exception as e:
            logger.error(f"Error unsubscribing from stream {stream}: {str(e)}")
            return False
    
    async def resubscribe_all(self) -> bool:
        """
        Повторная подписка на все потоки
        
        Returns:
            bool: True, если все подписки выполнены успешно, иначе False
        """
        if not self.running or self.ws is None:
            if not await self.connect():
                return False
        
        try:
            # Сохраняем текущие подписки
            current_subscriptions = list(self.subscriptions)
            self.subscriptions.clear()
            
            # Подписываемся на потоки с ограничением скорости
            success = True
            batch_count = 0
            
            # Разбиваем подписки на партии
            for i in range(0, len(current_subscriptions), self.subscription_batch_size):
                batch = current_subscriptions[i:i+self.subscription_batch_size]
                
                # Подписываемся на потоки в текущей партии
                for stream in batch:
                    if not await self.subscribe(stream):
                        success = False
                    
                    # Задержка между подписками в партии
                    await asyncio.sleep(1 / self.subscription_rate_limit)
                
                # Увеличиваем счетчик партий
                batch_count += 1
                
                # Делаем глобальную паузу после определенного количества партий
                if batch_count % self.global_pause_interval == 0:
                    logger.info(f"Making global pause for {self.global_pause_duration} seconds after {batch_count} batches")
                    await asyncio.sleep(self.global_pause_duration)
                else:
                    # Задержка между партиями
                    await asyncio.sleep(self.subscription_batch_delay)
            
            return success
        except Exception as e:
            logger.error(f"Error resubscribing to streams: {str(e)}")
            return False
    
    async def close(self):
        """
        Закрытие соединения с WebSocket
        """
        self.running = False
        
        # Отменяем задачу обработчика сообщений
        if self.message_handler_task is not None and not self.message_handler_task.done():
            self.message_handler_task.cancel()
            try:
                await self.message_handler_task
            except asyncio.CancelledError:
                pass
        
        # Закрываем соединение
        async with self.ws_lock:
            if self.ws is not None:
                try:
                    await self.ws.close()
                except Exception as e:
                    logger.error(f"Error closing WebSocket connection: {str(e)}")
                finally:
                    self.ws = None
        
        logger.info("WebSocket connection closed")
    
    async def get_symbols(self) -> List[str]:
        """
        Получение списка всех доступных фьючерсных символов
        
        Returns:
            List[str]: Список символов
        """
        try:
            # Используем REST API для получения списка символов
            url = f"{self.base_url}/fapi/v1/exchangeInfo"
            response = requests.get(url)
            response.raise_for_status()
            
            # Используем встроенный метод json() вместо requests.utils.parse_json
            data = response.json()
            symbols = [symbol["symbol"] for symbol in data["symbols"] if symbol["status"] == "TRADING"]
            
            return symbols
        except Exception as e:
            logger.error(f"Error fetching symbols: {str(e)}")
            raise Exception(f"API error: {str(e)}")
    
    async def get_klines(self, symbol: str, interval: str, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Получение исторических данных свечей
        
        Args:
            symbol: Символ (пара)
            interval: Интервал времени
            limit: Количество свечей
            
        Returns:
            List[Dict[str, Any]]: Список свечей с данными
        """
        try:
            # Используем REST API для получения исторических данных
            url = f"{self.base_url}/fapi/v1/klines"
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            # Преобразуем данные в удобный формат
            klines = []
            for k in response.json():
                kline = {
                    "open_time": k[0],
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "close_time": k[6],
                    "quote_volume": float(k[7]),
                    "trades": k[8],
                    "taker_buy_base": float(k[9]),
                    "taker_buy_quote": float(k[10])
                }
                klines.append(kline)
            
            return klines
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol} {interval}: {str(e)}")
            raise Exception(f"API error: {str(e)}")
    
    async def get_current_price(self, symbol: Optional[str] = None) -> Union[Dict[str, float], Dict[str, Dict[str, float]]]:
        """
        Получение текущей цены для символа или всех символов
        
        Args:
            symbol: Символ (пара) или None для всех символов
            
        Returns:
            Union[Dict[str, float], Dict[str, Dict[str, float]]]: Словарь с текущими ценами
        """
        try:
            # Используем REST API для получения текущих цен
            url = f"{self.base_url}/fapi/v1/ticker/price"
            if symbol is not None:
                params = {"symbol": symbol}
            else:
                params = {}
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            # Преобразуем данные в удобный формат
            if symbol is not None:
                data = response.json()
                return {data["symbol"]: float(data["price"])}
            else:
                data = response.json()
                return {item["symbol"]: float(item["price"]) for item in data}
        except Exception as e:
            logger.error(f"Error fetching current price: {str(e)}")
            raise Exception(f"API error: {str(e)}")

# Создаем экземпляр клиента
binance_client = BinanceWebSocketClient()
