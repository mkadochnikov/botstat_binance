import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import os

# Настройки
COIN_IDS = [
    "bitcoin", "ethereum", "tether", "binancecoin",
    "solana", "ripple", "usd-coin", "cardano",
    "dogecoin", "polkadot"
]

def get_coin_data(coin_id, days=365):
    """Получение дневных данных за указанный период"""
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {
        "vs_currency": "usd",
        "days": days,
        "interval": "daily"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Ошибка при получении данных для {coin_id}: {str(e)}")
        return None

def process_weekly_data(coin_data):
    """Агрегация дневных данных в недельные"""
    all_data = []
    
    for coin_id, data in coin_data.items():
        if not data:
            continue
            
        # Создаем DataFrame для монеты
        df = pd.DataFrame({
            "date": [datetime.utcfromtimestamp(x[0]/1000) for x in data["prices"]],
            "market_cap": [x[1] for x in data["market_caps"]],
            "volume": [x[1] for x in data["total_volumes"]]
        })
        
        # Группируем по неделям
        df["week"] = df["date"].dt.to_period("W").dt.start_time
        weekly_df = df.groupby("week").agg({
            "market_cap": "mean",  # Средняя капитализация за неделю
            "volume": "sum"         # Суммарный объем за неделю
        }).reset_index()
        
        weekly_df["coin"] = coin_id
        all_data.append(weekly_df)
    
    # Объединяем данные всех монет
    combined_df = pd.concat(all_data)
    
    # Агрегируем топ-10
    final_df = combined_df.groupby("week").agg({
        "market_cap": "sum",
        "volume": "sum"
    }).reset_index()
    
    return final_df.rename(columns={
        "market_cap": "total_market_cap",
        "volume": "total_volume"
    })

def fetch_market_data(cache_file="/tmp/crypto_weekly_metrics.json", force_refresh=False):
    """
    Получает данные о капитализации и объеме торгов.
    Использует кэширование для уменьшения количества запросов к API.
    
    Args:
        cache_file: Путь к файлу кэша
        force_refresh: Принудительное обновление данных
        
    Returns:
        dict: Словарь с датами, капитализацией и объемами
    """
    # Проверяем наличие кэша и его актуальность
    if not force_refresh and os.path.exists(cache_file):
        try:
            # Проверяем возраст файла (не старше 24 часов)
            file_age = time.time() - os.path.getmtime(cache_file)
            if file_age < 24 * 3600:  # 24 часа в секундах
                with open(cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Ошибка при чтении кэша: {str(e)}")
    
    # Получаем данные
    coin_data = {}
    for coin_id in COIN_IDS:
        print(f"Получаем данные для {coin_id}...")
        data = get_coin_data(coin_id)
        coin_data[coin_id] = data
        time.sleep(1.5)  # Соблюдаем лимиты API
    
    # Обрабатываем данные
    result_df = process_weekly_data(coin_data)
    
    # Преобразуем даты в строки для JSON
    result_df['week'] = result_df['week'].dt.strftime('%Y-%m-%d')
    
    # Формируем результат
    result = {
        "dates": result_df['week'].tolist(),
        "caps": result_df['total_market_cap'].tolist(),
        "volumes": result_df['total_volume'].tolist()
    }
    
    # Сохраняем в кэш
    try:
        with open(cache_file, 'w') as f:
            json.dump(result, f)
    except Exception as e:
        print(f"Ошибка при сохранении кэша: {str(e)}")
    
    return result

if __name__ == "__main__":
    # Тестовый запуск
    result = fetch_market_data(force_refresh=True)
    print(f"Получено {len(result['dates'])} записей")
    print(f"Первая дата: {result['dates'][0]}")
    print(f"Последняя дата: {result['dates'][-1]}")
