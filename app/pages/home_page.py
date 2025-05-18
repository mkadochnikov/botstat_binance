import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import requests
import time
import datetime
import ccxt
import os
import sys
import json
from typing import List, Dict, Any, Optional, Tuple

# Настройка кэширования данных
@st.cache_data(ttl=60)
def get_top_coins(limit=10):
    """
    Получение данных о топ-криптовалютах с CoinGecko
    """
    try:
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
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"Ошибка при получении данных о топ-криптовалютах: {str(e)}")
        # Возвращаем фиктивные данные в случае ошибки
        return pd.DataFrame({
            'symbol': ['BTC', 'ETH', 'USDT', 'BNB', 'SOL', 'XRP', 'USDC', 'ADA', 'AVAX', 'DOGE'],
            'current_price': [50000, 3000, 1, 400, 100, 0.5, 1, 0.4, 30, 0.1],
            'price_change_percentage_24h': [2.5, 1.8, 0.1, -1.2, 5.6, -2.3, 0.0, 3.2, -4.1, 1.5],
            'total_volume': [30000000000, 15000000000, 80000000000, 2000000000, 1500000000, 
                            1000000000, 900000000, 800000000, 700000000, 600000000],
            'market_cap': [900000000000, 350000000000, 80000000000, 60000000000, 40000000000,
                          30000000000, 25000000000, 15000000000, 10000000000, 8000000000],
            'name': ['Bitcoin', 'Ethereum', 'Tether', 'Binance Coin', 'Solana', 'Ripple', 
                    'USD Coin', 'Cardano', 'Avalanche', 'Dogecoin'],
            'image': [''] * 10
        })

@st.cache_data(ttl=60)
def get_market_global_data():
    """
    Получение глобальных рыночных данных с CoinGecko
    """
    try:
        url = "https://api.coingecko.com/api/v3/global"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()['data']
    except Exception as e:
        st.error(f"Ошибка при получении глобальных рыночных данных: {str(e)}")
        # Возвращаем фиктивные данные в случае ошибки
        return {
            'total_market_cap': {'usd': 2000000000000},
            'total_volume': {'usd': 100000000000},
            'market_cap_percentage': {'btc': 45.5, 'eth': 18.2},
            'market_cap_change_percentage_24h_usd': 2.5
        }

@st.cache_data(ttl=60)
def get_fear_greed_index():
    """
    Получение индекса страха и жадности с Alternative.me
    """
    try:
        url = "https://api.alternative.me/fng/"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return {
            'value': int(data['data'][0]['value']),
            'value_classification': data['data'][0]['value_classification'],
            'timestamp': data['data'][0]['timestamp']
        }
    except Exception as e:
        st.error(f"Ошибка при получении индекса страха и жадности: {str(e)}")
        # Возвращаем фиктивные данные в случае ошибки
        return {
            'value': 50,
            'value_classification': 'Neutral',
            'timestamp': int(time.time())
        }

@st.cache_data(ttl=60)
def get_orderbook(symbol='BTC', vs_currency='USDT', limit=10):
    """
    Получение данных ордербука с Binance
    """
    try:
        exchange = ccxt.binance()
        orderbook = exchange.fetch_order_book(f'{symbol.upper()}/{vs_currency.upper()}', limit=limit)
        
        # Преобразуем данные в DataFrame
        bids_df = pd.DataFrame(orderbook['bids'], columns=['price', 'amount'])
        asks_df = pd.DataFrame(orderbook['asks'], columns=['price', 'amount'])
        
        return {
            'bids': bids_df,
            'asks': asks_df,
            'timestamp': orderbook['timestamp']
        }
    except Exception as e:
        st.error(f"Ошибка при получении данных ордербука: {str(e)}")
        # Возвращаем фиктивные данные в случае ошибки
        base_price = 50000 if symbol.upper() == 'BTC' else 3000 if symbol.upper() == 'ETH' else 100
        
        bids = [[base_price * (1 - i * 0.001), np.random.uniform(0.1, 5.0)] for i in range(limit)]
        asks = [[base_price * (1 + i * 0.001), np.random.uniform(0.1, 5.0)] for i in range(limit)]
        
        return {
            'bids': pd.DataFrame(bids, columns=['price', 'amount']),
            'asks': pd.DataFrame(asks, columns=['price', 'amount']),
            'timestamp': int(time.time() * 1000)
        }

@st.cache_data(ttl=60)
def get_funding_rates(limit=10):
    """
    Получение ставок финансирования с Binance Futures
    """
    try:
        exchange = ccxt.binance({
            'options': {
                'defaultType': 'future',
            }
        })
        
        funding_rates = exchange.fetch_funding_rates()
        
        # Преобразуем данные в DataFrame
        data = []
        for symbol, info in funding_rates.items():
            if '/USDT' in symbol:
                data.append({
                    'symbol': symbol.replace('/USDT', ''),
                    'rate': info['fundingRate'] * 100,  # в процентах
                    'timestamp': info['timestamp']
                })
        
        df = pd.DataFrame(data)
        df = df.sort_values('rate', ascending=False)
        
        return df.head(limit)
    except Exception as e:
        st.error(f"Ошибка при получении ставок финансирования: {str(e)}")
        # Возвращаем фиктивные данные в случае ошибки
        symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'AVAX', 'DOGE', 'DOT', 'MATIC']
        
        return pd.DataFrame({
            'symbol': symbols[:limit],
            'rate': np.random.normal(0.01, 0.05, limit),
            'timestamp': [int(time.time() * 1000)] * limit
        })

@st.cache_data(ttl=60)
def get_volatility_heatmap():
    """
    Получение данных для тепловой карты волатильности с CryptoCompare API
    """
    try:
        # Получаем данные о топ-20 монетах с CoinGecko для тепловой карты
        top_coins = get_top_coins(limit=20)
        
        # Используем реальные данные изменения цены за 24 часа
        symbols = top_coins['symbol'].tolist()
        changes = top_coins['price_change_percentage_24h'].tolist()
        
        # Добавляем данные из CryptoCompare для BTC
        try:
            url = "https://min-api.cryptocompare.com/data/v2/histoday"
            params = {
                'fsym': 'BTC',
                'tsym': 'USD',
                'limit': 30
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data['Response'] == 'Success':
                # Получаем данные о ценах за последние 30 дней
                prices_data = data['Data']['Data']
                
                # Добавляем данные о BTC за последние дни
                for i in range(1, min(8, len(prices_data))):
                    prev_close = prices_data[i-1]['close']
                    curr_close = prices_data[i]['close']
                    
                    # Рассчитываем процентное изменение
                    if prev_close > 0:
                        percent_change = ((curr_close - prev_close) / prev_close) * 100
                    else:
                        percent_change = 0
                    
                    # Форматируем дату
                    timestamp = prices_data[i]['time']
                    date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                    
                    # Добавляем в список символов и изменений
                    symbols.append(f"BTC-{date_str}")
                    changes.append(percent_change)
        except Exception as e:
            st.warning(f"Не удалось получить исторические данные BTC: {str(e)}")
        
        # Добавляем искусственные экстремальные значения для лучшей цветовой дифференциации
        # Это гарантирует, что цветовая шкала будет иметь достаточный диапазон
        symbols.append("_max_value_")
        changes.append(10.0)  # Максимальное положительное значение
        
        symbols.append("_min_value_")
        changes.append(-10.0)  # Максимальное отрицательное значение
        
        return {
            'symbols': symbols,
            'changes': changes
        }
    except Exception as e:
        st.error(f"Ошибка при получении данных для тепловой карты: {str(e)}")
        # Возвращаем фиктивные данные в случае ошибки
        symbols = ['BTC', 'ETH', 'USDT', 'BNB', 'SOL', 'XRP', 'USDC', 'ADA', 'AVAX', 'DOGE',
                  'DOT', 'MATIC', 'SHIB', 'TRX', 'TON', 'LINK', 'UNI', 'ATOM', 'LTC', 'BCH']
        
        # Генерируем разнообразные изменения для визуализации
        changes = []
        for _ in range(len(symbols)):
            # Генерируем значения от -10 до +10 с большей вероятностью экстремальных значений
            change = np.random.choice([-1, 1]) * (np.random.random() * 10)
            changes.append(change)
        
        # Добавляем искусственные экстремальные значения для лучшей цветовой дифференциации
        symbols.append("_max_value_")
        changes.append(10.0)
        
        symbols.append("_min_value_")
        changes.append(-10.0)
        
        return {
            'symbols': symbols,
            'changes': changes
        }

def color_percent(val):
    """
    Функция для окрашивания процентных значений
    """
    if isinstance(val, (int, float)):
        color = 'green' if val >= 0 else 'red'
        return f'color: {color}'
    return ''

def render_home_page():
    """
    Отрисовка главной страницы дашборда
    """
    st.title("🏠 Ultimate Crypto Analytics")
    
    # Создаем две колонки для верстки с новым соотношением
    col1, col2 = st.columns([0.67, 0.33])
    
    with col1:
        # ❶ Топ-10 криптоактивов (перемещено влево)
        st.subheader("📊 Топ-10 криптоактивов")
        
        # Получаем данные о топ-монетах
        df = get_top_coins()[['symbol', 'name', 'current_price', 'price_change_percentage_24h', 'total_volume', 'market_cap']]
        df.columns = ['Symbol', 'Name', 'Price', '24h %', 'Volume', 'Market Cap']
        
        # Сбрасываем индекс и начинаем нумерацию с 1
        df = df.reset_index(drop=True)
        df.index = df.index + 1
        
        # Отображаем таблицу с форматированием (без слайдера и без высоты)
        # Заменяем устаревший метод applymap на map
        st.dataframe(
            df.style.format({
                'Price': '${:.2f}',
                '24h %': '{:.2f}%',
                'Volume': '${:,.0f}',
                'Market Cap': '${:,.0f}'
            }).map(color_percent, subset=['24h %']),
            use_container_width=True
        )
        
        # ❷ Глубина рынка (ордербук) - перемещено влево
        st.subheader("📚 Глубина рынка (Ордербук)")
        
        # Выбор пары для ордербука (без слайдера)
        orderbook_symbol = st.selectbox(
            label="Выберите торговую пару",
            options=["BTC/USDT", "ETH/USDT"],
            index=0
        )
        
        symbol, vs_currency = orderbook_symbol.split('/')
        
        # Получаем данные ордербука
        orderbook = get_orderbook(symbol=symbol, vs_currency=vs_currency)
        
        # Создаем две колонки для отображения ордербука
        ob_col1, ob_col2 = st.columns(2)
        
        with ob_col1:
            st.markdown("### Покупки (Bids)")
            
            # Форматируем данные
            bids_df = orderbook['bids'].copy()
            bids_df.columns = ['Цена', 'Объем']
            bids_df['Сумма'] = bids_df['Цена'] * bids_df['Объем']
            
            # Сбрасываем индекс и начинаем нумерацию с 1
            bids_df = bids_df.reset_index(drop=True)
            bids_df.index = bids_df.index + 1
            
            # Отображаем таблицу без высоты
            st.dataframe(
                bids_df.style.format({
                    'Цена': '${:.2f}',
                    'Объем': '{:.4f}',
                    'Сумма': '${:.2f}'
                }),
                use_container_width=True
            )
        
        with ob_col2:
            st.markdown("### Продажи (Asks)")
            
            # Форматируем данные
            asks_df = orderbook['asks'].copy()
            asks_df.columns = ['Цена', 'Объем']
            asks_df['Сумма'] = asks_df['Цена'] * asks_df['Объем']
            
            # Сбрасываем индекс и начинаем нумерацию с 1
            asks_df = asks_df.reset_index(drop=True)
            asks_df.index = asks_df.index + 1
            
            # Отображаем таблицу без высоты
            st.dataframe(
                asks_df.style.format({
                    'Цена': '${:.2f}',
                    'Объем': '{:.4f}',
                    'Сумма': '${:.2f}'
                }),
                use_container_width=True
            )
        
        # ❸ Heatmap волатильности (Plotly) с новыми данными
        st.subheader("🔥 Тепловая карта волатильности (24ч)")
        
        # Получаем данные для тепловой карты с нового API
        heatmap_data = get_volatility_heatmap()
        
        # Создаем DataFrame для тепловой карты
        heatmap_df = pd.DataFrame({
            'symbol': heatmap_data['symbols'],
            'change': heatmap_data['changes']
        })
        
        # Удаляем искусственные экстремальные значения перед отображением
        heatmap_df = heatmap_df[~heatmap_df['symbol'].isin(['_max_value_', '_min_value_'])]
        
        # Определяем минимальное и максимальное значения для цветовой шкалы
        min_change = -10
        max_change = 10
        
        # Создаем тепловую карту с улучшенной визуализацией
        fig = px.treemap(
            heatmap_df,
            path=['symbol'],
            values=abs(heatmap_df['change']) + 1,  # Добавляем 1, чтобы даже малые изменения были видны
            color='change',
            color_continuous_scale='RdYlGn',
            color_continuous_midpoint=0,
            range_color=[min_change, max_change],  # Устанавливаем фиксированный диапазон для цветовой шкалы
            title="Изменение цены за 24ч (%)"
        )
        
        fig.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=30, b=0)
        )
        
        # Добавляем текст с процентами изменения
        fig.update_traces(
            textinfo="label+text",
            text=[f"{x:.1f}%" for x in heatmap_df['change']],
            hovertemplate='<b>%{label}</b><br>Изменение: %{customdata:.2f}%<extra></extra>',
            customdata=heatmap_df['change']
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Правая колонка - метрики в столбик
        
        # ❹ Fear & Greed Index
        st.subheader("😱 Fear & Greed Index")
        
        # Получаем данные
        fear_greed = get_fear_greed_index()
        fear_value = fear_greed['value']
        fear_label = fear_greed['value_classification']
        
        # Определяем цвет индикатора
        if fear_value <= 25:
            fear_color = "red"
        elif fear_value <= 45:
            fear_color = "orange"
        elif fear_value <= 55:
            fear_color = "yellow"
        elif fear_value <= 75:
            fear_color = "light green"
        else:
            fear_color = "green"
        
        st.metric(
            label=f"Fear & Greed Index ({fear_label})",
            value=fear_value,
            delta=None
        )
        
        # Создаем индикатор
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=fear_value,
            domain={'x': [0, 1], 'y': [0, 1]},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': fear_color},
                'steps': [
                    {'range': [0, 25], 'color': 'rgba(255, 0, 0, 0.3)'},
                    {'range': [25, 45], 'color': 'rgba(255, 165, 0, 0.3)'},
                    {'range': [45, 55], 'color': 'rgba(255, 255, 0, 0.3)'},
                    {'range': [55, 75], 'color': 'rgba(144, 238, 144, 0.3)'},
                    {'range': [75, 100], 'color': 'rgba(0, 128, 0, 0.3)'}
                ]
            }
        ))
        
        fig.update_layout(
            height=200,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # ❺ Доминирование BTC
        st.subheader("🏆 Доминирование BTC")
        
        # Получаем данные
        global_data = get_market_global_data()
        btc_dominance = global_data['market_cap_percentage']['btc']
        
        st.metric(
            label="Доминирование BTC",
            value=f"{btc_dominance:.2f}%",
            delta=f"{global_data['market_cap_change_percentage_24h_usd']:.2f}%"
        )
        
        # Создаем круговую диаграмму для визуализации доминирования
        dominance_data = {
            'Актив': ['Bitcoin', 'Ethereum', 'Другие'],
            'Доля': [
                global_data['market_cap_percentage']['btc'],
                global_data['market_cap_percentage']['eth'],
                100 - global_data['market_cap_percentage']['btc'] - global_data['market_cap_percentage']['eth']
            ]
        }
        
        dominance_df = pd.DataFrame(dominance_data)
        
        fig = px.pie(
            dominance_df,
            values='Доля',
            names='Актив',
            color_discrete_sequence=['#F7931A', '#627EEA', '#8C8C8C']
        )
        
        fig.update_layout(
            height=200,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # ❻ Общая капитализация
        st.subheader("💰 Общая капитализация")
        
        total_market_cap = global_data['total_market_cap']['usd']
        total_volume = global_data['total_volume']['usd']
        
        st.metric(
            label="Общая капитализация",
            value=f"${total_market_cap / 1e12:.2f}T",
            delta=f"Vol: ${total_volume / 1e9:.2f}B"
        )
        
        # Добавляем график изменения капитализации (фиктивные данные)
        dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq='D')
        cap_values = [total_market_cap * (1 + np.random.normal(0, 0.02)) for _ in range(30)]
        
        cap_df = pd.DataFrame({
            'Дата': dates,
            'Капитализация': cap_values
        })
        
        fig = px.line(
            cap_df,
            x='Дата',
            y='Капитализация',
            color_discrete_sequence=['#1E88E5']
        )
        
        fig.update_layout(
            height=200,
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis=dict(
                tickformat='$.2s'
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
