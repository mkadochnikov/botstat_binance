import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import time
import datetime
import os
import sys
import json
from typing import List, Dict, Any, Optional, Tuple

# Настройка кэширования данных
@st.cache_data(ttl=60)
def get_top_coins(limit=20):
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
            'symbol': ['BTC', 'ETH', 'USDT', 'BNB', 'SOL', 'XRP', 'USDC', 'ADA', 'AVAX', 'DOGE',
                      'DOT', 'MATIC', 'SHIB', 'TRX', 'TON', 'LINK', 'UNI', 'ATOM', 'LTC', 'BCH'],
            'current_price': [50000, 3000, 1, 400, 100, 0.5, 1, 0.4, 30, 0.1, 
                             15, 0.8, 0.00001, 0.1, 2, 15, 8, 10, 80, 300],
            'price_change_percentage_24h': [2.5, 1.8, 0.1, -1.2, 5.6, -2.3, 0.0, 3.2, -4.1, 1.5,
                                           -0.8, 2.1, 4.5, -1.7, 3.3, 0.9, -2.8, 1.1, -0.5, 2.2],
            'total_volume': [30000000000, 15000000000, 80000000000, 2000000000, 1500000000, 
                            1000000000, 900000000, 800000000, 700000000, 600000000,
                            500000000, 450000000, 400000000, 350000000, 300000000,
                            250000000, 200000000, 150000000, 100000000, 50000000],
            'market_cap': [900000000000, 350000000000, 80000000000, 60000000000, 40000000000,
                          30000000000, 25000000000, 15000000000, 10000000000, 8000000000,
                          7000000000, 6000000000, 5000000000, 4000000000, 3000000000,
                          2500000000, 2000000000, 1500000000, 1000000000, 500000000],
            'name': ['Bitcoin', 'Ethereum', 'Tether', 'Binance Coin', 'Solana', 'Ripple', 
                    'USD Coin', 'Cardano', 'Avalanche', 'Dogecoin', 'Polkadot', 'Polygon',
                    'Shiba Inu', 'Tron', 'Toncoin', 'Chainlink', 'Uniswap', 'Cosmos', 
                    'Litecoin', 'Bitcoin Cash'],
            'image': [''] * 20
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
            'market_cap_percentage': {'btc': 60.79, 'eth': 18.2},
            'market_cap_change_percentage_24h_usd': -1.45
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
            'value': 74,
            'value_classification': 'Greed',
            'timestamp': int(time.time())
        }

@st.cache_data(ttl=60)
def get_historical_market_cap():
    """
    Получение исторических данных о капитализации рынка
    """
    try:
        # В реальном приложении здесь должен быть запрос к API
        # Для примера генерируем фиктивные данные
        end_date = datetime.datetime.now()
        dates = [end_date - datetime.timedelta(days=x) for x in range(30)]
        dates.reverse()
        
        # Начальная капитализация
        base_cap = 2000000000000
        
        # Генерируем данные с трендом роста
        caps = []
        for i in range(30):
            # Добавляем тренд роста и случайные колебания
            trend_factor = 1 + (i * 0.01)  # Увеличение на 1% каждый день
            random_factor = np.random.normal(1, 0.02)  # Случайные колебания ±2%
            cap = base_cap * trend_factor * random_factor
            caps.append(cap)
        
        return {
            'dates': dates,
            'caps': caps
        }
    except Exception as e:
        st.error(f"Ошибка при получении исторических данных о капитализации: {str(e)}")
        # Возвращаем фиктивные данные в случае ошибки
        end_date = datetime.datetime.now()
        dates = [end_date - datetime.timedelta(days=x) for x in range(30)]
        dates.reverse()
        caps = [2000000000000 * (1 + (i * 0.01)) for i in range(30)]
        return {
            'dates': dates,
            'caps': caps
        }

def render_home_page():
    """
    Отрисовка главной страницы дашборда
    """
    st.title("🏠 Ultimate Crypto Analytics")
    
    # Создаем две колонки для верстки с новым соотношением
    col1, col2 = st.columns([0.67, 0.33])
    
    with col1:
        # Криптопузыри (Bubble Chart) вместо тепловой карты
        st.subheader("🔮 Криптопузыри")
        
        # Получаем данные о топ-20 монетах
        df = get_top_coins(limit=20)
        
        # Создаем DataFrame для визуализации
        bubble_df = df[['symbol', 'name', 'current_price', 'price_change_percentage_24h', 'market_cap', 'total_volume']]
        
        # Определяем цвета для пузырей на основе процентного изменения
        colors = []
        for change in bubble_df['price_change_percentage_24h']:
            if change >= 3:
                colors.append('#00FF00')  # Ярко-зеленый для сильного роста
            elif change > 0:
                colors.append('#90EE90')  # Светло-зеленый для умеренного роста
            elif change > -3:
                colors.append('#FFA07A')  # Светло-красный для умеренного падения
            else:
                colors.append('#FF0000')  # Ярко-красный для сильного падения
        
        bubble_df['color'] = colors
        
        # Создаем пузырьковую диаграмму с помощью Plotly
        fig = px.scatter(
            bubble_df,
            x='total_volume',
            y='price_change_percentage_24h',
            size='market_cap',
            color='symbol',
            hover_name='name',
            text='symbol',
            size_max=60,
            title="Криптопузыри: размер = капитализация, положение = объем и % изменения"
        )
        
        # Настраиваем внешний вид
        fig.update_traces(
            textposition='top center',
            marker=dict(
                sizemode='area',
                sizeref=2.*max(bubble_df['market_cap'])/(60.**2),
                line=dict(width=2, color='DarkSlateGrey')
            )
        )
        
        fig.update_layout(
            height=600,
            xaxis=dict(
                title="Объем торгов за 24ч (USD)",
                type='log',
                showgrid=True
            ),
            yaxis=dict(
                title="Изменение цены за 24ч (%)",
                showgrid=True
            ),
            showlegend=False
        )
        
        # Отображаем график
        st.plotly_chart(fig, use_container_width=True)
        
        # Добавляем пояснение к диаграмме
        st.markdown("""
        **Пояснение к диаграмме:**
        - **Размер пузыря**: Рыночная капитализация (Market Cap)
        - **Положение по X**: Объем торгов за 24ч (Volume)
        - **Положение по Y**: Изменение цены за 24ч (%)
        - **Цвет**: Уникальный для каждой криптовалюты
        """)
        
        # Добавляем таблицу с данными под диаграммой для справки
        with st.expander("Показать данные"):
            st.dataframe(
                bubble_df[['symbol', 'name', 'current_price', 'price_change_percentage_24h', 'market_cap', 'total_volume']].rename(
                    columns={
                        'symbol': 'Символ',
                        'name': 'Название',
                        'current_price': 'Цена (USD)',
                        'price_change_percentage_24h': 'Изменение за 24ч (%)',
                        'market_cap': 'Капитализация (USD)',
                        'total_volume': 'Объем за 24ч (USD)'
                    }
                ).style.format({
                    'Цена (USD)': '${:.2f}',
                    'Изменение за 24ч (%)': '{:.2f}%',
                    'Капитализация (USD)': '${:,.0f}',
                    'Объем за 24ч (USD)': '${:,.0f}'
                }),
                use_container_width=True
            )
    
    with col2:
        # Правая колонка - метрики в столбик
        
        # ❹ Fear & Greed Index с использованием нативных компонентов Streamlit
        st.subheader("😱 Fear & Greed Index")
        
        # Получаем данные
        fear_greed = get_fear_greed_index()
        fear_value = fear_greed['value']
        fear_label = fear_greed['value_classification']
        
        # Отображаем метрику
        st.metric(
            label=f"Fear & Greed Index ({fear_label})",
            value=fear_value,
            delta=None
        )
        
        # Создаем индикатор с помощью Streamlit
        # Определяем цвет и метку в зависимости от значения
        if fear_value <= 25:
            fear_color = "red"
            fear_text = "Extreme Fear"
        elif fear_value <= 45:
            fear_color = "orange"
            fear_text = "Fear"
        elif fear_value <= 55:
            fear_color = "yellow"
            fear_text = "Neutral"
        elif fear_value <= 75:
            fear_color = "lightgreen"
            fear_text = "Greed"
        else:
            fear_color = "green"
            fear_text = "Extreme Greed"
        
        # Создаем прогресс-бар для визуализации
        st.progress(fear_value/100, text=f"{fear_value} - {fear_text}")
        
        # Добавляем цветовую шкалу для наглядности
        cols = st.columns(5)
        with cols[0]:
            st.markdown(f'<div style="background-color:red;height:10px;border-radius:3px;"></div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align:center;font-size:10px;">0-25</div>', unsafe_allow_html=True)
        with cols[1]:
            st.markdown(f'<div style="background-color:orange;height:10px;border-radius:3px;"></div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align:center;font-size:10px;">26-45</div>', unsafe_allow_html=True)
        with cols[2]:
            st.markdown(f'<div style="background-color:yellow;height:10px;border-radius:3px;"></div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align:center;font-size:10px;">46-55</div>', unsafe_allow_html=True)
        with cols[3]:
            st.markdown(f'<div style="background-color:lightgreen;height:10px;border-radius:3px;"></div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align:center;font-size:10px;">56-75</div>', unsafe_allow_html=True)
        with cols[4]:
            st.markdown(f'<div style="background-color:green;height:10px;border-radius:3px;"></div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align:center;font-size:10px;">76-100</div>', unsafe_allow_html=True)
        
        # ❺ Доминирование BTC с использованием нативных компонентов Streamlit
        st.subheader("🏆 Доминирование BTC")
        
        # Получаем данные
        global_data = get_market_global_data()
        btc_dominance = global_data['market_cap_percentage']['btc']
        eth_dominance = global_data['market_cap_percentage']['eth']
        other_dominance = 100 - btc_dominance - eth_dominance
        
        # Отображаем метрику
        st.metric(
            label="Доминирование BTC",
            value=f"{btc_dominance:.2f}%",
            delta=f"{global_data['market_cap_change_percentage_24h_usd']:.2f}%"
        )
        
        # Создаем данные для круговой диаграммы
        dominance_data = pd.DataFrame({
            'Категория': ['Bitcoin', 'Ethereum', 'Другие'],
            'Процент': [btc_dominance, eth_dominance, other_dominance]
        })
        
        # Отображаем круговую диаграмму с помощью Streamlit
        st.bar_chart(
            dominance_data,
            x='Категория',
            y='Процент',
            use_container_width=True
        )
        
        # ❻ Общая капитализация с использованием нативных компонентов Streamlit
        st.subheader("💰 Общая капитализация")
        
        total_market_cap = global_data['total_market_cap']['usd']
        total_volume = global_data['total_volume']['usd']
        
        # Отображаем метрику
        st.metric(
            label="Общая капитализация",
            value=f"${total_market_cap / 1e12:.2f}T",
            delta=f"Vol: ${total_volume / 1e9:.2f}B"
        )
        
        # Получаем исторические данные о капитализации
        historical_data = get_historical_market_cap()
        
        # Создаем DataFrame для графика
        cap_df = pd.DataFrame({
            'Дата': historical_data['dates'],
            'Капитализация': historical_data['caps']
        })
        
        # Используем st.line_chart для создания линейного графика
        st.line_chart(
            cap_df,
            x='Дата',
            y='Капитализация',
            use_container_width=True
        )
