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
def get_ohlc_data(symbol='BTC', vs_currency='usdt', timeframe='1h', limit=100):
    """
    Получение OHLC данных для построения графика
    """
    try:
        # Используем ccxt для получения данных
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(f'{symbol.upper()}/{vs_currency.upper()}', timeframe, limit=limit)
        
        # Преобразуем данные в DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        return df
    except Exception as e:
        st.error(f"Ошибка при получении OHLC данных: {str(e)}")
        # Возвращаем фиктивные данные в случае ошибки
        timestamps = pd.date_range(end=pd.Timestamp.now(), periods=limit, freq=timeframe)
        
        # Генерируем случайные данные для примера
        base_price = 50000 if symbol.upper() == 'BTC' else 3000 if symbol.upper() == 'ETH' else 100
        noise = np.random.normal(0, 1, limit)
        trend = np.linspace(0, 5, limit)
        
        close_prices = base_price + base_price * 0.1 * noise + base_price * 0.05 * trend
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': close_prices * (1 + np.random.normal(0, 0.01, limit)),
            'high': close_prices * (1 + abs(np.random.normal(0, 0.02, limit))),
            'low': close_prices * (1 - abs(np.random.normal(0, 0.02, limit))),
            'close': close_prices,
            'volume': np.random.uniform(base_price * 1000, base_price * 10000, limit)
        })
        
        return df

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
def get_volatility_heatmap(top_n=20):
    """
    Получение данных для тепловой карты волатильности
    """
    try:
        # Получаем данные о топ-монетах
        df = get_top_coins(limit=top_n)
        
        # Создаем матрицу для тепловой карты
        symbols = df['symbol'].tolist()
        changes = df['price_change_percentage_24h'].tolist()
        
        return {
            'symbols': symbols,
            'changes': changes
        }
    except Exception as e:
        st.error(f"Ошибка при получении данных для тепловой карты: {str(e)}")
        # Возвращаем фиктивные данные в случае ошибки
        symbols = ['BTC', 'ETH', 'USDT', 'BNB', 'SOL', 'XRP', 'USDC', 'ADA', 'AVAX', 'DOGE',
                  'DOT', 'MATIC', 'SHIB', 'TRX', 'TON', 'LINK', 'UNI', 'ATOM', 'LTC', 'BCH']
        
        return {
            'symbols': symbols[:top_n],
            'changes': np.random.normal(0, 5, top_n)
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
    
    # Создаем две колонки для верстки
    col1, col2 = st.columns([0.65, 0.35])
    
    with col1:
        # ❶ Верхняя панель метрик (3 колонки)
        st.subheader("📈 Рыночные метрики")
        
        # Получаем данные
        global_data = get_market_global_data()
        fear_greed = get_fear_greed_index()
        
        # Отображаем метрики в трех колонках
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        
        with metric_col1:
            btc_dominance = global_data['market_cap_percentage']['btc']
            st.metric(
                label="Доминирование BTC",
                value=f"{btc_dominance:.2f}%",
                delta=f"{global_data['market_cap_change_percentage_24h_usd']:.2f}%"
            )
        
        with metric_col2:
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
                height=150,
                margin=dict(l=10, r=10, t=10, b=10)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with metric_col3:
            total_market_cap = global_data['total_market_cap']['usd']
            total_volume = global_data['total_volume']['usd']
            
            st.metric(
                label="Общая капитализация",
                value=f"${total_market_cap / 1e12:.2f}T",
                delta=f"Vol: ${total_volume / 1e9:.2f}B"
            )
        
        # ❷ Основной график (Plotly)
        st.subheader("📊 Ценовой график")
        
        # Выбор параметров графика
        chart_col1, chart_col2, chart_col3 = st.columns(3)
        
        with chart_col1:
            selected_symbol = st.selectbox(
                "Выберите актив",
                options=["BTC", "ETH", "SOL", "BNB", "XRP"],
                index=0
            )
        
        with chart_col2:
            selected_timeframe = st.selectbox(
                "Выберите таймфрейм",
                options=["15m", "1h", "4h", "1d"],
                index=1
            )
        
        with chart_col3:
            show_indicators = st.checkbox("Показать индикаторы", value=True)
        
        # Получаем данные для графика
        ohlc_data = get_ohlc_data(symbol=selected_symbol, timeframe=selected_timeframe)
        
        # Создаем график
        fig = go.Figure()
        
        # Добавляем свечи
        fig.add_trace(go.Candlestick(
            x=ohlc_data['timestamp'],
            open=ohlc_data['open'],
            high=ohlc_data['high'],
            low=ohlc_data['low'],
            close=ohlc_data['close'],
            name=selected_symbol
        ))
        
        # Добавляем индикаторы, если выбрано
        if show_indicators:
            # SMA 50
            sma50 = ohlc_data['close'].rolling(window=50).mean()
            fig.add_trace(go.Scatter(
                x=ohlc_data['timestamp'],
                y=sma50,
                name="SMA 50",
                line=dict(color='blue', width=1)
            ))
            
            # SMA 200
            sma200 = ohlc_data['close'].rolling(window=min(200, len(ohlc_data))).mean()
            fig.add_trace(go.Scatter(
                x=ohlc_data['timestamp'],
                y=sma200,
                name="SMA 200",
                line=dict(color='red', width=1)
            ))
            
            # RSI
            delta = ohlc_data['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            # Создаем второй y-axis для RSI
            fig.add_trace(go.Scatter(
                x=ohlc_data['timestamp'],
                y=rsi,
                name="RSI",
                line=dict(color='purple', width=1),
                yaxis="y2"
            ))
        
        # Настраиваем макет графика
        fig.update_layout(
            title=f"{selected_symbol}/USDT - {selected_timeframe}",
            xaxis_title="Время",
            yaxis_title="Цена (USDT)",
            height=500,
            xaxis_rangeslider_visible=False,
            yaxis2=dict(
                title="RSI",
                overlaying="y",
                side="right",
                range=[0, 100]
            ) if show_indicators else None
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # ❸ Heatmap волатильности (Plotly)
        st.subheader("🔥 Тепловая карта волатильности (24ч)")
        
        # Получаем данные для тепловой карты
        heatmap_data = get_volatility_heatmap()
        
        # Создаем DataFrame для тепловой карты
        heatmap_df = pd.DataFrame({
            'symbol': heatmap_data['symbols'],
            'change': heatmap_data['changes']
        })
        
        # Создаем тепловую карту
        fig = px.treemap(
            heatmap_df,
            path=['symbol'],
            values=abs(heatmap_df['change']),
            color='change',
            color_continuous_scale='RdYlGn',
            color_continuous_midpoint=0
        )
        
        fig.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=0, b=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # ❹ Топ-10 монет (таблица с сортировкой)
        st.subheader("📊 Топ-10 криптоактивов")
        
        # Получаем данные о топ-монетах
        df = get_top_coins()[['symbol', 'name', 'current_price', 'price_change_percentage_24h', 'total_volume', 'market_cap']]
        df.columns = ['Symbol', 'Name', 'Price', '24h %', 'Volume', 'Market Cap']
        
        # Отображаем таблицу с форматированием
        st.dataframe(
            df.style.format({
                'Price': '${:.2f}',
                '24h %': '{:.2f}%',
                'Volume': '${:,.0f}',
                'Market Cap': '${:,.0f}'
            }).applymap(color_percent, subset=['24h %']),
            height=300,
            use_container_width=True
        )
        
        # ❺ Глубина рынка (ордербук)
        st.subheader("📚 Глубина рынка (Ордербук)")
        
        # Выбор пары для ордербука
        orderbook_symbol = st.selectbox(
            "Выберите пару",
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
            
            # Отображаем таблицу
            st.dataframe(
                bids_df.style.format({
                    'Цена': '${:.2f}',
                    'Объем': '{:.4f}',
                    'Сумма': '${:.2f}'
                }),
                height=200,
                use_container_width=True
            )
        
        with ob_col2:
            st.markdown("### Продажи (Asks)")
            
            # Форматируем данные
            asks_df = orderbook['asks'].copy()
            asks_df.columns = ['Цена', 'Объем']
            asks_df['Сумма'] = asks_df['Цена'] * asks_df['Объем']
            
            # Отображаем таблицу
            st.dataframe(
                asks_df.style.format({
                    'Цена': '${:.2f}',
                    'Объем': '{:.4f}',
                    'Сумма': '${:.2f}'
                }),
                height=200,
                use_container_width=True
            )
        
        # Отображаем время последнего обновления
        last_update = datetime.datetime.fromtimestamp(orderbook['timestamp'] / 1000)
        st.caption(f"Последнее обновление: {last_update.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # ❻ Фьючерсы (финансирование, OI)
        st.subheader("🔄 Ставки финансирования (Funding Rates)")
        
        # Получаем данные о ставках финансирования
        funding_df = get_funding_rates()
        
        # Создаем график
        fig = px.bar(
            funding_df,
            x='symbol',
            y='rate',
            color='rate',
            color_continuous_scale='RdYlGn',
            color_continuous_midpoint=0,
            labels={'rate': 'Ставка (%)', 'symbol': 'Символ'}
        )
        
        fig.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Отображаем время последнего обновления
        if not funding_df.empty:
            last_update = datetime.datetime.fromtimestamp(funding_df['timestamp'].iloc[0] / 1000)
            st.caption(f"Последнее обновление: {last_update.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    render_home_page()
