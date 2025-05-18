import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Set
import websockets
from functools import wraps

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Базовые URL для Binance Futures WebSocket API
WS_BASE_URL = "wss://fstream.binance.com/ws"
WS_COMBINED_STREAM_URL = "wss://fstream.binance.com/stream"

# Кеш для хранения данных
cache = {}
CACHE_EXPIRY = 30  # секунды

# Максимальное количество повторных попыток при ошибках WebSocket
MAX_RETRIES = 3

class BinanceWebSocketClient:
    """Клиент для работы с Binance Futures WebSocket API"""
    
    def __init__(self):
        self.ws = None
        self.running = False
        self.subscriptions = set()
        self.klines_data = {}
        self.ticker_data = {}
        self.symbols = []
        self.last_symbols_update = 0
        self.symbols_update_interval = 3600  # 1 час
        self.connection_id = None
        self.message_handlers = {}
        self.reconnect_delay = 1
        
    async def connect(self):
        """Установка соединения с WebSocket"""
        if self.ws is not None and self.ws.open:
            return
        
        try:
            self.ws = await websockets.connect(WS_COMBINED_STREAM_URL)
            self.running = True
            self.reconnect_delay = 1  # Сбрасываем задержку после успешного подключения
            logger.info("Connected to Binance WebSocket")
            
            # Запускаем обработчик сообщений
            asyncio.create_task(self.message_handler())
        except Exception as e:
            logger.error(f"WebSocket connection error: {str(e)}")
            self.ws = None
            self.running = False
            
            # Увеличиваем задержку перед повторной попыткой (экспоненциальная задержка)
            await asyncio.sleep(self.reconnect_delay)
            self.reconnect_delay = min(self.reconnect_delay * 2, 60)  # Максимум 60 секунд
            
            # Повторная попытка подключения
            await self.connect()
    
    async def close(self):
        """Закрытие соединения с WebSocket"""
        if self.ws is not None and self.ws.open:
            self.running = False
            await self.ws.close()
            self.ws = None
            logger.info("Disconnected from Binance WebSocket")
    
    async def message_handler(self):
        """Обработчик входящих сообщений WebSocket"""
        while self.running and self.ws is not None and self.ws.open:
            try:
                message = await self.ws.recv()
                data = json.loads(message)
                
                # Обработка сообщений в зависимости от типа
                if 'stream' in data:
                    stream = data['stream']
                    stream_data = data['data']
                    
                    # Обработка данных свечей (klines)
                    if 'kline' in stream:
                        symbol, interval = self._parse_kline_stream(stream)
                        self._handle_kline_message(symbol, interval, stream_data)
                    
                    # Обработка данных тикеров (цены)
                    elif 'ticker' in stream:
                        self._handle_ticker_message(stream_data)
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed unexpectedly")
                self.ws = None
                self.running = False
                
                # Повторное подключение
                await self.connect()
                
                # Повторная подписка на все потоки
                await self._resubscribe()
                
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {str(e)}")
    
    async def _resubscribe(self):
        """Повторная подписка на все потоки после переподключения"""
        if not self.subscriptions:
            return
        
        try:
            # Формируем запрос на подписку для всех потоков
            subscribe_request = {
                "method": "SUBSCRIBE",
                "params": list(self.subscriptions),
                "id": int(time.time() * 1000)
            }
            
            await self.ws.send(json.dumps(subscribe_request))
            logger.info(f"Resubscribed to {len(self.subscriptions)} streams")
        except Exception as e:
            logger.error(f"Error resubscribing to streams: {str(e)}")
    
    def _parse_kline_stream(self, stream):
        """Парсинг имени потока свечей для получения символа и интервала"""
        # Формат: symbol@kline_interval
        parts = stream.split('@')
        symbol = parts[0].upper()
        interval = parts[1].replace('kline_', '')
        return symbol, interval
    
    def _handle_kline_message(self, symbol, interval, data):
        """Обработка сообщения со свечами"""
        kline = data['k']
        
        # Проверяем, завершена ли свеча
        is_closed = kline['x']
        
        # Формируем данные свечи
        kline_data = {
            "open_time": kline['t'],
            "open": float(kline['o']),
            "high": float(kline['h']),
            "low": float(kline['l']),
            "close": float(kline['c']),
            "volume": float(kline['v']),
            "close_time": kline['T'],
        }
        
        # Сохраняем данные в кеше
        key = f"{symbol}_{interval}"
        if key not in self.klines_data:
            self.klines_data[key] = []
        
        # Если свеча завершена, добавляем ее в историю
        if is_closed:
            # Проверяем, нет ли уже такой свечи (по времени открытия)
            existing_index = None
            for i, existing_kline in enumerate(self.klines_data[key]):
                if existing_kline["open_time"] == kline_data["open_time"]:
                    existing_index = i
                    break
            
            if existing_index is not None:
                # Обновляем существующую свечу
                self.klines_data[key][existing_index] = kline_data
            else:
                # Добавляем новую свечу
                self.klines_data[key].append(kline_data)
                
                # Ограничиваем количество хранимых свечей (например, 100)
                if len(self.klines_data[key]) > 100:
                    self.klines_data[key] = self.klines_data[key][-100:]
        
        # Если свеча не завершена, обновляем последнюю свечу
        else:
            # Если есть свечи и последняя имеет то же время открытия
            if self.klines_data[key] and self.klines_data[key][-1]["open_time"] == kline_data["open_time"]:
                self.klines_data[key][-1] = kline_data
            # Иначе добавляем новую незавершенную свечу
            else:
                self.klines_data[key].append(kline_data)
    
    def _handle_ticker_message(self, data):
        """Обработка сообщения с тикером (ценой)"""
        symbol = data['s']
        price = float(data['c'])  # Цена закрытия (текущая цена)
        
        # Сохраняем данные в кеше
        self.ticker_data[symbol] = price
    
    async def subscribe_klines(self, symbol, interval):
        """Подписка на поток свечей для символа и интервала"""
        await self.connect()
        
        stream_name = f"{symbol.lower()}@kline_{interval}"
        
        if stream_name in self.subscriptions:
            return
        
        try:
            subscribe_request = {
                "method": "SUBSCRIBE",
                "params": [stream_name],
                "id": int(time.time() * 1000)
            }
            
            await self.ws.send(json.dumps(subscribe_request))
            self.subscriptions.add(stream_name)
            logger.info(f"Subscribed to klines for {symbol} {interval}")
        except Exception as e:
            logger.error(f"Error subscribing to klines for {symbol} {interval}: {str(e)}")
    
    async def subscribe_ticker(self, symbol):
        """Подписка на поток тикера (цены) для символа"""
        await self.connect()
        
        stream_name = f"{symbol.lower()}@ticker"
        
        if stream_name in self.subscriptions:
            return
        
        try:
            subscribe_request = {
                "method": "SUBSCRIBE",
                "params": [stream_name],
                "id": int(time.time() * 1000)
            }
            
            await self.ws.send(json.dumps(subscribe_request))
            self.subscriptions.add(stream_name)
            logger.info(f"Subscribed to ticker for {symbol}")
        except Exception as e:
            logger.error(f"Error subscribing to ticker for {symbol}: {str(e)}")
    
    async def subscribe_all_tickers(self):
        """Подписка на поток всех тикеров (цен)"""
        await self.connect()
        
        stream_name = "!ticker@arr"
        
        if stream_name in self.subscriptions:
            return
        
        try:
            subscribe_request = {
                "method": "SUBSCRIBE",
                "params": [stream_name],
                "id": int(time.time() * 1000)
            }
            
            await self.ws.send(json.dumps(subscribe_request))
            self.subscriptions.add(stream_name)
            logger.info("Subscribed to all tickers")
        except Exception as e:
            logger.error(f"Error subscribing to all tickers: {str(e)}")
    
    async def unsubscribe(self, stream_name):
        """Отписка от потока"""
        if self.ws is None or not self.ws.open:
            return
        
        if stream_name not in self.subscriptions:
            return
        
        try:
            unsubscribe_request = {
                "method": "UNSUBSCRIBE",
                "params": [stream_name],
                "id": int(time.time() * 1000)
            }
            
            await self.ws.send(json.dumps(unsubscribe_request))
            self.subscriptions.remove(stream_name)
            logger.info(f"Unsubscribed from {stream_name}")
        except Exception as e:
            logger.error(f"Error unsubscribing from {stream_name}: {str(e)}")
    
    async def get_symbols(self) -> List[str]:
        """Получение списка всех доступных фьючерсных символов"""
        # Если прошло достаточно времени с последнего обновления, обновляем список символов
        current_time = time.time()
        if not self.symbols or (current_time - self.last_symbols_update > self.symbols_update_interval):
            try:
                # Для получения списка символов используем REST API, так как WebSocket не предоставляет такой функционал
                import aiohttp
                
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://fapi.binance.com/fapi/v1/exchangeInfo") as response:
                        if response.status != 200:
                            text = await response.text()
                            raise Exception(f"API error: {response.status} - {text}")
                        
                        data = await response.json()
                        self.symbols = [symbol["symbol"] for symbol in data["symbols"] if symbol["status"] == "TRADING"]
                        self.last_symbols_update = current_time
                        logger.info(f"Updated symbols list, found {len(self.symbols)} symbols")
            except Exception as e:
                logger.error(f"Error fetching symbols: {str(e)}")
                # Если не удалось получить список символов, возвращаем текущий список
                if not self.symbols:
                    raise
        
        return self.symbols
    
    async def get_klines(self, symbol: str, interval: str, limit: int = 30) -> List[Dict[str, Any]]:
        """Получение исторических данных свечей"""
        # Подписываемся на поток свечей, если еще не подписаны
        await self.subscribe_klines(symbol, interval)
        
        key = f"{symbol}_{interval}"
        
        # Если данных нет в кеше или их недостаточно, получаем исторические данные через REST API
        if key not in self.klines_data or len(self.klines_data[key]) < limit:
            try:
                # Используем REST API для получения исторических данных
                import aiohttp
                
                params = {
                    "symbol": symbol,
                    "interval": interval,
                    "limit": limit
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://fapi.binance.com/fapi/v1/klines", params=params) as response:
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
                        
                        self.klines_data[key] = formatted_klines
                        logger.info(f"Fetched {len(formatted_klines)} historical klines for {symbol} {interval}")
            except Exception as e:
                logger.error(f"Error fetching historical klines for {symbol} {interval}: {str(e)}")
                # Если не удалось получить исторические данные, возвращаем текущие данные
                if key not in self.klines_data:
                    self.klines_data[key] = []
        
        # Возвращаем данные из кеша (последние limit свечей)
        return self.klines_data[key][-limit:] if len(self.klines_data[key]) > limit else self.klines_data[key]
    
    async def get_current_price(self, symbol: Optional[str] = None) -> Dict[str, float]:
        """Получение текущей цены для символа или всех символов"""
        if symbol:
            # Подписываемся на поток тикера для конкретного символа
            await self.subscribe_ticker(symbol)
            
            # Если данных нет в кеше, ждем немного для получения данных
            if symbol not in self.ticker_data:
                await asyncio.sleep(1)
            
            # Если данных все еще нет, получаем через REST API
            if symbol not in self.ticker_data:
                try:
                    import aiohttp
                    
                    params = {"symbol": symbol}
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get("https://fapi.binance.com/fapi/v1/ticker/price", params=params) as response:
                            if response.status != 200:
                                text = await response.text()
                                raise Exception(f"API error: {response.status} - {text}")
                            
                            data = await response.json()
                            self.ticker_data[data["symbol"]] = float(data["price"])
                except Exception as e:
                    logger.error(f"Error fetching current price for {symbol}: {str(e)}")
                    # Если не удалось получить цену, возвращаем пустой словарь
                    return {}
            
            return {symbol: self.ticker_data.get(symbol, 0.0)}
        else:
            # Подписываемся на поток всех тикеров
            await self.subscribe_all_tickers()
            
            # Если данных нет в кеше, ждем немного для получения данных
            if not self.ticker_data:
                await asyncio.sleep(1)
            
            # Если данных все еще нет, получаем через REST API
            if not self.ticker_data:
                try:
                    import aiohttp
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get("https://fapi.binance.com/fapi/v1/ticker/price") as response:
                            if response.status != 200:
                                text = await response.text()
                                raise Exception(f"API error: {response.status} - {text}")
                            
                            data = await response.json()
                            for item in data:
                                self.ticker_data[item["symbol"]] = float(item["price"])
                except Exception as e:
                    logger.error(f"Error fetching all current prices: {str(e)}")
                    # Если не удалось получить цены, возвращаем текущие данные
            
            return self.ticker_data

# Создаем синглтон клиента
binance_client = BinanceWebSocketClient()
