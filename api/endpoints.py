from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import List, Dict, Any, Optional
import logging
import time
from datetime import datetime

from app.utils.binance_websocket_client import binance_client
from app.utils.atr_calculator import calculate_all_timeframes_atr, convert_numpy_types
from app.utils.logger import atr_logger

# Создаем FastAPI приложение
app = FastAPI(
    title="Binance Futures ATR API (WebSocket)",
    description="API для получения данных и расчета ATR с Binance Futures через WebSocket",
    version="2.0.0"
)

# Добавляем CORS middleware для доступа из Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Поддерживаемые таймфреймы
SUPPORTED_TIMEFRAMES = ["1m", "3m", "5m", "15m", "1h"]
ATR_PERIOD = 14  # Период для расчета ATR


@app.get("/")
async def root():
    """Корневой эндпоинт для проверки работоспособности API"""
    return {
        "status": "ok",
        "message": "Binance Futures ATR API (WebSocket) is running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/symbols", response_model=List[str])
async def get_symbols():
    """
    Получение списка всех доступных фьючерсных символов
    
    Returns:
        List[str]: Список символов
    """
    try:
        symbols = await binance_client.get_symbols()
        return symbols
    except Exception as e:
        atr_logger.log_error(f"Error fetching symbols: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch symbols: {str(e)}")


@app.get("/klines")
async def get_klines(
    symbol: str = Query(..., description="Символ, например BTCUSDT"),
    interval: str = Query(..., description="Интервал, например 1m, 3m, 5m, 15m, 1h"),
    limit: int = Query(30, description="Количество свечей (макс. 1000)")
):
    """
    Получение исторических данных свечей через WebSocket
    
    Args:
        symbol: Символ (пара)
        interval: Интервал времени
        limit: Количество свечей
        
    Returns:
        List[Dict]: Список свечей с данными
    """
    try:
        klines = await binance_client.get_klines(symbol, interval, limit)
        return klines
    except Exception as e:
        atr_logger.log_error(f"Error fetching klines for {symbol} {interval}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch klines: {str(e)}")


@app.get("/atr")
async def get_atr(
    symbol: str = Query(..., description="Символ, например BTCUSDT"),
    period: int = Query(ATR_PERIOD, description="Период для расчета ATR")
):
    """
    Расчет ATR для всех таймфреймов с использованием WebSocket данных
    
    Args:
        symbol: Символ (пара)
        period: Период для расчета ATR
        
    Returns:
        Dict: Результаты расчета ATR по всем таймфреймам
    """
    try:
        # Получаем текущую цену через WebSocket
        price_data = await binance_client.get_current_price(symbol)
        if symbol not in price_data:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
        
        current_price = price_data[symbol]
        
        # Получаем данные свечей для всех таймфреймов через WebSocket
        klines_data = {}
        for timeframe in SUPPORTED_TIMEFRAMES:
            # Для расчета ATR нам нужно period+1 свечей
            klines = await binance_client.get_klines(symbol, timeframe, period + 10)
            klines_data[timeframe] = klines
        
        # Рассчитываем ATR для всех таймфреймов
        atr_results = calculate_all_timeframes_atr(symbol, klines_data, current_price, period)
        
        # Логируем результаты
        atr_logger.log_symbol_results(symbol, atr_results)
        
        # Преобразуем numpy типы для корректной сериализации в JSON
        return convert_numpy_types(atr_results)
    except Exception as e:
        atr_logger.log_error(f"Error calculating ATR for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate ATR: {str(e)}")


@app.get("/all_symbols_atr")
async def get_all_symbols_atr(
    limit: Optional[int] = Query(None, description="Ограничение количества символов (None для всех символов)"),
    period: int = Query(ATR_PERIOD, description="Период для расчета ATR")
):
    """
    Получение ATR для всех символов с использованием WebSocket данных
    
    Args:
        limit: Ограничение количества символов (None для всех символов)
        period: Период для расчета ATR
        
    Returns:
        List[Dict]: Список результатов расчета ATR по всем символам
    """
    try:
        # Получаем список символов
        all_symbols = await binance_client.get_symbols()
        
        # Если лимит не указан, используем все символы
        symbols_to_process = all_symbols if limit is None else all_symbols[:limit]
        
        atr_logger.log_info(f"Processing {len(symbols_to_process)} symbols via WebSocket...")
        
        # Получаем текущие цены для всех символов через WebSocket
        all_prices = await binance_client.get_current_price()
        
        # Создаем задачи для параллельного выполнения
        tasks = []
        for symbol in symbols_to_process:
            tasks.append(get_atr(symbol, period))
        
        # Выполняем задачи параллельно с ограничением на количество одновременных задач
        # Это предотвращает перегрузку и ошибки из-за слишком большого количества запросов
        chunk_size = 20  # Обрабатываем по 20 символов за раз
        results = []
        
        for i in range(0, len(tasks), chunk_size):
            chunk_tasks = tasks[i:i+chunk_size]
            chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)
            results.extend(chunk_results)
            
            # Небольшая пауза между чанками
            if i + chunk_size < len(tasks):
                await asyncio.sleep(1)
        
        # Фильтруем результаты, исключая ошибки
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                atr_logger.log_error(f"Error processing symbol: {str(result)}")
            else:
                valid_results.append(result)
        
        atr_logger.log_info(f"Successfully processed {len(valid_results)} out of {len(symbols_to_process)} symbols via WebSocket")
        return valid_results
    except Exception as e:
        atr_logger.log_error(f"Error processing all symbols via WebSocket: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process all symbols: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Действия при запуске приложения"""
    # Подключаемся к WebSocket Binance
    await binance_client.connect()
    atr_logger.log_info("Connected to Binance WebSocket")


@app.on_event("shutdown")
async def shutdown_event():
    """Действия при остановке приложения"""
    # Закрываем соединение с WebSocket Binance
    await binance_client.close()
    atr_logger.log_info("Disconnected from Binance WebSocket")
