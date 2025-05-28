import pandas as pd
import numpy as np
from typing import Dict, List, Any, Union, Optional

def calculate_tr(high: float, low: float, prev_close: float) -> float:
    """
    Расчет True Range (TR)
    
    Args:
        high: Максимальная цена текущей свечи
        low: Минимальная цена текущей свечи
        prev_close: Цена закрытия предыдущей свечи
        
    Returns:
        float: Значение True Range
    """
    return max(
        high - low,
        abs(high - prev_close),
        abs(low - prev_close)
    )

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Расчет Average True Range (ATR) с использованием UDF
    
    Args:
        df: DataFrame с данными свечей (должен содержать колонки 'high', 'low', 'close')
        period: Период для расчета ATR
        
    Returns:
        pd.Series: Серия значений ATR
    """
    # Создаем копию DataFrame для избежания предупреждений
    df_copy = df.copy()
    
    # Создаем колонку с предыдущей ценой закрытия
    df_copy['prev_close'] = df_copy['close'].shift(1)
    
    # Рассчитываем TR для каждой свечи
    df_copy['tr'] = df_copy.apply(
        lambda row: calculate_tr(row['high'], row['low'], row['prev_close']) if not pd.isna(row['prev_close']) else row['high'] - row['low'],
        axis=1
    )
    
    # Рассчитываем ATR как простое скользящее среднее TR
    atr = df_copy['tr'].rolling(window=period).mean()
    
    return atr

def convert_klines_to_dataframe(klines: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Преобразование данных свечей из WebSocket в DataFrame
    
    Args:
        klines: Список словарей с данными свечей
        
    Returns:
        pd.DataFrame: DataFrame с данными свечей
    """
    df = pd.DataFrame(klines)
    
    # Переименовываем колонки для удобства
    df = df.rename(columns={
        'open_time': 'timestamp',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'volume': 'volume',
        'close_time': 'close_time'
    })
    
    return df

def calculate_atr_percent(atr_value: float, current_price: float) -> float:
    """
    Расчет ATR в процентах от текущей цены
    
    Args:
        atr_value: Значение ATR
        current_price: Текущая цена
        
    Returns:
        float: ATR в процентах
    """
    return (atr_value / current_price) * 100

def calculate_all_timeframes_atr(symbol: str, klines_data: Dict[str, List[Dict[str, Any]]], current_price: float, period: int = 14) -> Dict[str, Any]:
    """
    Расчет ATR для всех таймфреймов
    
    Args:
        symbol: Символ (пара)
        klines_data: Словарь с данными свечей для разных таймфреймов
        current_price: Текущая цена
        period: Период для расчета ATR
        
    Returns:
        Dict[str, Any]: Результаты расчета ATR по всем таймфреймам
    """
    result = {
        "symbol": symbol,
        "price": current_price,
        "timeframes": {}
    }
    
    for timeframe, klines in klines_data.items():
        # Преобразуем данные свечей в DataFrame
        df = convert_klines_to_dataframe(klines)
        
        # Если данных недостаточно для расчета ATR, пропускаем таймфрейм
        if len(df) < period + 1:
            continue
        
        # Рассчитываем ATR
        atr_series = calculate_atr(df, period)
        
        # Берем последнее значение ATR
        atr_value = atr_series.iloc[-1]
        
        # Рассчитываем ATR в процентах
        atr_percent = calculate_atr_percent(atr_value, current_price)
        
        # Определяем, является ли значение "горячим"
        is_hot = atr_percent >= 0.15
        
        # Сохраняем результаты
        result["timeframes"][timeframe] = {
            "atr": atr_value,
            "atr_percent": atr_percent,
            "is_hot": is_hot
        }
    
    return result

def convert_numpy_types(obj):
    """
    Рекурсивно преобразует numpy типы в стандартные Python типы для сериализации в JSON
    
    Args:
        obj: Объект для преобразования
        
    Returns:
        Объект с преобразованными типами
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    else:
        return obj
