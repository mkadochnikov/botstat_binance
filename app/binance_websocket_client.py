import asyncio
import json
import logging
import random
import time
import traceback
import sys
import os
from typing import Dict, List, Any, Optional, Set, Tuple, Union
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError
import requests
from datetime import datetime

# Настройка расширенного логирования с явным указанием пути к файлу
# Получаем абсолютный путь к директории проекта
project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
log_file = os.path.join(project_dir, 'binance_websocket.log')

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
logger = logging.getLogger('binance_websocket')
logger.info(f"Logging initialized. Log file: {log_file}")

class BinanceWebSocketClient:
    """
    Клиент для работы с WebSocket API Binance
    """
    def __init__(self):
        logger.info("Initializing BinanceWebSocketClient")
        self.ws_connections = {}  # Словарь для хранения соединений по потокам
        self.running = False
        self.subscriptions = set()
        self.message_handlers = {}  # Словарь для хранения обработчиков сообщений по потокам
        self.reconnect_delay = 1  # Начальная задержка для переподключения (в секундах)
        self.max_reconnect_delay = 300  # Максимальная задержка для переподключения (в секундах)
        self.last_connection_attempt = 0  # Время последней попытки подключения
        self.connection_cooldown = 10  # Минимальное время между попытками подключения (в секундах)
        
        # Базовые URL для API Binance
        self.base_url = "https://fapi.binance.com"
        self.ws_base_url = "wss://fstream.binance.com/ws"
        logger.info(f"BinanceWebSocketClient initialized with base_url={self.base_url}, ws_base_url={self.ws_base_url}")
    
    async def connect_to_stream(self, stream: str) -> bool:
        """
        Установка прямого соединения с конкретным потоком WebSocket API Binance
        
        Args:
            stream: Название потока (например, 'btcusdt@kline_1m')
            
        Returns:
            bool: True, если соединение установлено успешно, иначе False
        """
        logger.debug(f"Connect to stream method called for stream: {stream}")
        
        # Проверяем, не слишком ли часто пытаемся подключиться
        current_time = time.time()
        if current_time - self.last_connection_attempt < self.connection_cooldown:
            logger.info(f"Соблюдаем cooldown период {self.connection_cooldown} секунд между попытками подключения")
            await asyncio.sleep(self.connection_cooldown)
        
        self.last_connection_attempt = time.time()
        logger.debug(f"Last connection attempt updated to {self.last_connection_attempt}")
        
        try:
            # Формируем URL для прямого подключения к потоку
            stream_url = f"{self.ws_base_url}/{stream}"
            logger.info(f"Connecting directly to stream URL: {stream_url}")
            
            # Закрываем существующее соединение, если оно есть
            if stream in self.ws_connections and self.ws_connections[stream] is not None:
                logger.debug(f"Closing existing connection for stream: {stream}")
                try:
                    await self.ws_connections[stream].close()
                    logger.debug(f"Existing connection for stream {stream} closed successfully")
                except Exception as e:
                    logger.error(f"Error closing existing connection for stream {stream}: {str(e)}")
                    logger.debug(f"Connection close error details: {traceback.format_exc()}")
            
            # Устанавливаем новое соединение
            try:
                self.ws_connections[stream] = await websockets.connect(stream_url)
                logger.info(f"Successfully connected to stream: {stream}")
                
                # Запускаем обработчик сообщений для этого потока
                if stream not in self.message_handlers or self.message_handlers[stream].done():
                    logger.debug(f"Creating new message handler for stream: {stream}")
                    self.message_handlers[stream] = asyncio.create_task(self.stream_message_handler(stream))
                    logger.debug(f"Message handler created for stream: {stream}")
                
                # Добавляем поток в список подписок
                self.subscriptions.add(stream)
                logger.debug(f"Added stream to subscriptions: {stream}")
                
                self.running = True
                return True
            except Exception as e:
                logger.error(f"Failed to connect to stream {stream}: {str(e)}")
                logger.debug(f"Connection error details: {traceback.format_exc()}")
                return False
        except Exception as e:
            logger.error(f"Error in connect_to_stream for {stream}: {str(e)}")
            logger.debug(f"Connect error details: {traceback.format_exc()}")
            
            # Экспоненциальная задержка перед повторной попыткой
            logger.debug(f"Sleeping for reconnect_delay={self.reconnect_delay} seconds")
            await asyncio.sleep(self.reconnect_delay)
            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
            logger.debug(f"Updated reconnect_delay to {self.reconnect_delay}")
            
            return False
    
    async def stream_message_handler(self, stream: str):
        """
        Обработчик сообщений для конкретного потока
        
        Args:
            stream: Название потока
        """
        logger.info(f"Starting message handler for stream: {stream}")
        
        while self.running and stream in self.ws_connections:
            try:
                # Получаем сообщение
                ws = self.ws_connections.get(stream)
                if ws is None:
                    logger.warning(f"WebSocket connection for stream {stream} is None, reconnecting...")
                    if await self.connect_to_stream(stream):
                        logger.debug(f"Reconnection to stream {stream} successful")
                    else:
                        logger.warning(f"Reconnection to stream {stream} failed")
                        await asyncio.sleep(self.reconnect_delay)
                        self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
                    continue
                
                logger.debug(f"Waiting for message from stream: {stream}")
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=30)
                    logger.debug(f"Received message from stream {stream} (length: {len(message)})")
                    
                    # Обрабатываем сообщение
                    try:
                        data = json.loads(message)
                        logger.debug(f"Message from stream {stream} parsed as JSON successfully")
                        await self.process_message(data, stream)
                    except json.JSONDecodeError:
                        logger.error(f"Error decoding JSON message from stream {stream}: {message[:100]}...")
                    except Exception as e:
                        logger.error(f"Error processing message from stream {stream}: {str(e)}")
                        logger.debug(f"Message processing error details: {traceback.format_exc()}")
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout waiting for WebSocket message from stream {stream} after 30 seconds")
                    # Проверяем соединение и переподключаемся при необходимости
                    try:
                        pong_waiter = await ws.ping()
                        await asyncio.wait_for(pong_waiter, timeout=5)
                        logger.debug(f"Ping-pong successful for stream {stream}, connection is active")
                    except Exception:
                        logger.warning(f"Ping test failed for stream {stream}, reconnecting...")
                        if await self.connect_to_stream(stream):
                            logger.debug(f"Reconnection to stream {stream} successful")
                        else:
                            logger.warning(f"Reconnection to stream {stream} failed")
                except ConnectionClosedError as e:
                    logger.error(f"WebSocket connection closed for stream {stream}: {str(e)}")
                    logger.debug(f"Connection closed error details: {traceback.format_exc()}")
                    
                    # Переподключаемся
                    logger.debug(f"Attempting to reconnect to stream {stream}")
                    if await self.connect_to_stream(stream):
                        logger.debug(f"Reconnection to stream {stream} successful")
                    else:
                        logger.warning(f"Reconnection to stream {stream} failed")
                        await asyncio.sleep(self.reconnect_delay)
                        self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
                except Exception as e:
                    logger.error(f"Error receiving message from stream {stream}: {str(e)}")
                    logger.debug(f"Receive error details: {traceback.format_exc()}")
                    await asyncio.sleep(1)  # Небольшая пауза перед следующей попыткой
            except Exception as e:
                logger.error(f"Error in stream_message_handler for {stream}: {str(e)}")
                logger.debug(f"Handler error details: {traceback.format_exc()}")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
        
        logger.info(f"Message handler for stream {stream} stopped")
    
    async def process_message(self, data: Dict[str, Any], stream: str = None):
        """
        Обработка полученного сообщения
        
        Args:
            data: Данные сообщения
            stream: Название потока, из которого получено сообщение
        """
        # Логируем тип сообщения для диагностики
        if isinstance(data, dict):
            if 'e' in data:
                logger.debug(f"Processing message of type: {data.get('e')} from stream: {stream}")
            elif 'result' in data:
                logger.debug(f"Processing response message with result: {data.get('result')} from stream: {stream}")
            elif 'id' in data:
                logger.debug(f"Processing message with id: {data.get('id')} from stream: {stream}")
            else:
                logger.debug(f"Processing message from stream {stream}: {str(data)[:100]}...")
        else:
            logger.debug(f"Processing non-dict message from stream {stream}: {str(data)[:100]}...")
        
        # Здесь можно добавить логику обработки сообщений
        # Например, сохранение данных в базу данных или передача их другим компонентам
    
    async def subscribe(self, symbol: str, interval: str) -> bool:
        """
        Подписка на поток свечей для указанного символа и интервала
        
        Args:
            symbol: Символ (пара), например 'btcusdt'
            interval: Интервал свечей (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
            
        Returns:
            bool: True, если подписка выполнена успешно, иначе False
        """
        logger.debug(f"Subscribe called for symbol: {symbol}, interval: {interval}")
        
        # Формируем название потока
        stream = f"{symbol.lower()}@kline_{interval}"
        logger.debug(f"Formed stream name: {stream}")
        
        # Проверяем, не подписаны ли мы уже на этот поток
        if stream in self.subscriptions:
            logger.debug(f"Already subscribed to stream: {stream}")
            return True
        
        # Подключаемся к потоку напрямую
        return await self.connect_to_stream(stream)
    
    async def unsubscribe(self, symbol: str, interval: str) -> bool:
        """
        Отписка от потока свечей
        
        Args:
            symbol: Символ (пара)
            interval: Интервал свечей
            
        Returns:
            bool: True, если отписка выполнена успешно, иначе False
        """
        logger.debug(f"Unsubscribe called for symbol: {symbol}, interval: {interval}")
        
        # Формируем название потока
        stream = f"{symbol.lower()}@kline_{interval}"
        logger.debug(f"Formed stream name: {stream}")
        
        # Проверяем, подписаны ли мы на этот поток
        if stream not in self.subscriptions:
            logger.debug(f"Not subscribed to stream: {stream}")
            return True
        
        try:
            # Закрываем соединение
            if stream in self.ws_connections and self.ws_connections[stream] is not None:
                logger.debug(f"Closing connection for stream: {stream}")
                try:
                    await self.ws_connections[stream].close()
                    logger.debug(f"Connection for stream {stream} closed successfully")
                except Exception as e:
                    logger.error(f"Error closing connection for stream {stream}: {str(e)}")
                    logger.debug(f"Connection close error details: {traceback.format_exc()}")
            
            # Отменяем задачу обработчика сообщений
            if stream in self.message_handlers and not self.message_handlers[stream].done():
                logger.debug(f"Cancelling message handler for stream: {stream}")
                self.message_handlers[stream].cancel()
                try:
                    await self.message_handlers[stream]
                except asyncio.CancelledError:
                    logger.debug(f"Message handler for stream {stream} cancelled successfully")
                except Exception as e:
                    logger.error(f"Error cancelling message handler for stream {stream}: {str(e)}")
                    logger.debug(f"Handler cancellation error details: {traceback.format_exc()}")
            
            # Удаляем поток из словарей
            if stream in self.ws_connections:
                del self.ws_connections[stream]
            if stream in self.message_handlers:
                del self.message_handlers[stream]
            
            # Удаляем поток из списка подписок
            self.subscriptions.remove(stream)
            logger.info(f"Unsubscribed from stream: {stream}")
            
            return True
        except Exception as e:
            logger.error(f"Error unsubscribing from stream {stream}: {str(e)}")
            logger.debug(f"Unsubscription error details: {traceback.format_exc()}")
            return False
    
    async def resubscribe_all(self) -> bool:
        """
        Переподписка на все потоки после переподключения
        
        Returns:
            bool: True, если все переподписки выполнены успешно, иначе False
        """
        logger.info(f"Resubscribing to all streams: {len(self.subscriptions)} streams")
        if not self.subscriptions:
            logger.debug("No streams to resubscribe")
            return True
        
        # Копируем список подписок, так как он может изменяться во время итерации
        streams = list(self.subscriptions)
        self.subscriptions.clear()
        logger.debug(f"Cleared subscriptions list, will resubscribe to {len(streams)} streams")
        
        # Переподписываемся на все потоки
        success = True
        for stream in streams:
            logger.debug(f"Resubscribing to stream: {stream}")
            if not await self.connect_to_stream(stream):
                logger.warning(f"Failed to resubscribe to stream: {stream}")
                success = False
            
            # Делаем небольшую паузу между подписками
            await asyncio.sleep(1)
        
        logger.info(f"Resubscription completed with success={success}")
        return success
    
    async def close(self):
        """
        Закрытие всех соединений с WebSocket
        """
        logger.info("Closing all WebSocket connections")
        self.running = False
        logger.debug("Set running=False")
        
        try:
            # Закрываем все соединения
            for stream, ws in list(self.ws_connections.items()):
                if ws is not None:
                    logger.debug(f"Closing connection for stream: {stream}")
                    try:
                        await ws.close()
                        logger.debug(f"Connection for stream {stream} closed successfully")
                    except Exception as e:
                        logger.error(f"Error closing connection for stream {stream}: {str(e)}")
                        logger.debug(f"Connection close error details: {traceback.format_exc()}")
            
            # Отменяем все задачи обработчиков сообщений
            for stream, task in list(self.message_handlers.items()):
                if not task.done():
                    logger.debug(f"Cancelling message handler for stream: {stream}")
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        logger.debug(f"Message handler for stream {stream} cancelled successfully")
                    except Exception as e:
                        logger.error(f"Error cancelling message handler for stream {stream}: {str(e)}")
                        logger.debug(f"Handler cancellation error details: {traceback.format_exc()}")
            
            # Очищаем словари
            self.ws_connections.clear()
            self.message_handlers.clear()
            self.subscriptions.clear()
            
            logger.info("All WebSocket connections closed successfully")
        except Exception as e:
            logger.error(f"Error closing WebSocket connections: {str(e)}")
            logger.debug(f"Close error details: {traceback.format_exc()}")
    
    async def get_symbols(self) -> List[str]:
        """
        Получение списка всех доступных фьючерсных символов
        
        Returns:
            List[str]: Список символов
        """
        logger.info("Getting list of all available futures symbols")
        try:
            # Используем REST API для получения списка символов
            url = f"{self.base_url}/fapi/v1/exchangeInfo"
            logger.debug(f"Making request to {url}")
            
            response = requests.get(url)
            logger.debug(f"Response status code: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Error getting exchange info: {response.text}")
                return []
            
            data = response.json()
            logger.debug("Response parsed as JSON successfully")
            
            # Фильтруем только активные символы
            symbols = [symbol["symbol"] for symbol in data["symbols"] if symbol["status"] == "TRADING"]
            logger.info(f"Got {len(symbols)} active trading symbols")
            
            return symbols
        except Exception as e:
            logger.error(f"Error getting symbols: {str(e)}")
            logger.debug(f"Get symbols error details: {traceback.format_exc()}")
            return []
    
    async def get_current_price(self, symbol: str) -> Dict[str, float]:
        """
        Получение текущей цены для символа
        
        Args:
            symbol: Символ (пара)
            
        Returns:
            Dict[str, float]: Словарь с текущими ценами
        """
        logger.debug(f"Getting current price for symbol: {symbol}")
        try:
            # Используем REST API для получения текущей цены
            url = f"{self.base_url}/fapi/v1/ticker/price?symbol={symbol}"
            logger.debug(f"Making request to {url}")
            
            response = requests.get(url)
            logger.debug(f"Response status code: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Error getting price for {symbol}: {response.text}")
                return {}
            
            data = response.json()
            logger.debug("Response parsed as JSON successfully")
            
            # Возвращаем словарь с ценой
            price = float(data["price"])
            logger.debug(f"Current price for {symbol}: {price}")
            
            return {symbol: price}
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {str(e)}")
            logger.debug(f"Get current price error details: {traceback.format_exc()}")
            return {}
    
    async def get_klines(self, symbol: str, interval: str, limit: int = 500) -> List[List[Any]]:
        """
        Получение исторических свечей для символа
        
        Args:
            symbol: Символ (пара)
            interval: Интервал свечей (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
            limit: Количество свечей (максимум 1000)
            
        Returns:
            List[List[Any]]: Список свечей
        """
        logger.debug(f"Getting klines for symbol: {symbol}, interval: {interval}, limit: {limit}")
        try:
            # Используем REST API для получения исторических свечей
            url = f"{self.base_url}/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
            logger.debug(f"Making request to {url}")
            
            response = requests.get(url)
            logger.debug(f"Response status code: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Error getting klines for {symbol}: {response.text}")
                return []
            
            data = response.json()
            logger.debug(f"Got {len(data)} klines for {symbol} with interval {interval}")
            
            return data
        except Exception as e:
            logger.error(f"Error getting klines for {symbol}: {str(e)}")
            logger.debug(f"Get klines error details: {traceback.format_exc()}")
            return []

# Создаем глобальный экземпляр клиента
binance_client = BinanceWebSocketClient()
