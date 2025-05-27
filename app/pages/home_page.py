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
def get_fear_greed_index(limit=5):
    """
    Получение индекса страха и жадности с Alternative.me
    """
    try:
        url = f"https://api.alternative.me/fng/?limit={limit}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Возвращаем все данные за указанный период
        result = []
        for item in data['data']:
            result.append({
                'value': int(item['value']),
                'value_classification': item['value_classification'],
                'timestamp': int(item['timestamp'])
            })
        return result
    except Exception as e:
        st.error(f"Ошибка при получении индекса страха и жадности: {str(e)}")
        # Возвращаем фиктивные данные в случае ошибки
        return [
            {'value': 74, 'value_classification': 'Greed', 'timestamp': int(time.time())},
            {'value': 73, 'value_classification': 'Greed', 'timestamp': int(time.time()) - 86400},
            {'value': 71, 'value_classification': 'Greed', 'timestamp': int(time.time()) - 172800},
            {'value': 70, 'value_classification': 'Greed', 'timestamp': int(time.time()) - 259200},
            {'value': 68, 'value_classification': 'Greed', 'timestamp': int(time.time()) - 345600}
        ]

@st.cache_data(ttl=3600)  # Кэшируем на 1 час
def get_historical_market_cap():
    """
    Получение исторических данных о капитализации и объеме торгов рынка
    """
    try:
        # Импортируем модуль для получения данных
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from data_fetcher import fetch_market_data
        
        # Получаем данные
        data = fetch_market_data()
        
        # Преобразуем строки дат в объекты datetime
        dates = [datetime.datetime.strptime(date_str, "%Y-%m-%d") for date_str in data["dates"]]
        
        return {
            'dates': dates,
            'caps': data["caps"],
            'volumes': data["volumes"]
        }
    except Exception as e:
        st.error(f"Ошибка при получении исторических данных о капитализации: {str(e)}")
        # В случае ошибки возвращаем пустые списки
        return {
            'dates': [],
            'caps': [],
            'volumes': []
        }

def render_home_page():
    """
    Отрисовка главной страницы дашборда
    """
    st.title("Crypto Analytics")
    
    # Создаем две колонки для верстки с новым соотношением
    col1, col2 = st.columns([0.67, 0.33])
    
    with col1:
        # Криптопузыри (Bubble Chart) вместо тепловой карты
        st.subheader("Криптопузыри")
        
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
        
        # Fear & Greed Index с использованием нативных компонентов Streamlit
        # Получаем данные за последние 5 дней
        fear_greed_data = get_fear_greed_index(limit=5)
        
        # Текущее значение (первый элемент в списке)
        current_fear_greed = fear_greed_data[0]
        fear_value = current_fear_greed['value']
        fear_label = current_fear_greed['value_classification']
        
        # Отображаем заголовок с текущим состоянием в скобках и значение без отступа
        st.markdown(f"""
        <h3>Fear & Greed Index ({fear_label})</h3>
        <h1 style='font-size: 60px; font-weight: bold; margin-top: -15px;'>{fear_value}</h1>
        """, unsafe_allow_html=True)
        
        # Функция для определения цвета и текста в зависимости от значения
        def get_fear_greed_color_and_text(value):
            if value <= 25:
                return "red", "Extreme Fear"
            elif value <= 45:
                return "orange", "Fear"
            elif value <= 55:
                return "yellow", "Neutral"
            elif value <= 75:
                return "lightgreen", "Greed"
            else:
                return "green", "Extreme Greed"
        
        # Определяем цвет и текст для текущего значения
        fear_color, fear_text = get_fear_greed_color_and_text(fear_value)
        
        # Создаем прогресс-бар для визуализации с динамическим цветом
        st.markdown(
            f"""
            <div style="width:100%; background-color:#f0f0f0; border-radius:3px;">
                <div style="width:{fear_value}%; background-color:{fear_color}; height:20px; border-radius:3px; text-align:center; line-height:20px; color:white;">
                    {fear_value} - {fear_text}
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # Заменяем легенду на значения за последние 5 дней
        st.markdown("### Last 5 days:")
        
        # Отображаем данные за последние 5 дней с цветовой индикацией
        for i, day_data in enumerate(fear_greed_data):
            day_value = day_data['value']
            day_color, day_text = get_fear_greed_color_and_text(day_value)
            
            # Форматируем дату из timestamp
            day_date = datetime.datetime.fromtimestamp(day_data['timestamp']).strftime('%Y-%m-%d')
            
            # Отображаем значение с цветовой индикацией
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; margin-bottom:5px;">
                    <div style="width:100px;">{day_date}:</div>
                    <div style="width:40px; text-align:right; margin-right:10px;">{day_value}</div>
                    <div style="flex-grow:1; background-color:#f0f0f0; border-radius:3px;">
                        <div style="width:{day_value}%; background-color:{day_color}; height:10px; border-radius:3px;"></div>
                    </div>
                    <div style="width:100px; margin-left:10px; font-size:12px;">{day_text}</div>
                </div>
                """, 
                unsafe_allow_html=True
            )
        
        # Добавляем отступ между блоками Fear & Greed Index и Доминирование BTC
        st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
        
        # Доминирование BTC с использованием нативных компонентов Streamlit
        st.subheader("Доминирование BTC")
        
        # Получаем данные
        global_data = get_market_global_data()
        btc_dominance = global_data['market_cap_percentage']['btc']
        eth_dominance = global_data['market_cap_percentage']['eth']
        other_dominance = 100 - btc_dominance - eth_dominance
        
        # Отображаем значение крупным шрифтом, как в Fear & Greed Index
        st.markdown(f"<h1 style='font-size: 60px; font-weight: bold;'>{btc_dominance:.2f}%</h1>", unsafe_allow_html=True)
        
        # Отображаем изменение
        st.markdown(f"<p style='color: {'red' if global_data['market_cap_change_percentage_24h_usd'] < 0 else 'green'};'>{global_data['market_cap_change_percentage_24h_usd']:.2f}%</p>", unsafe_allow_html=True)
        
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
    
    # Общая капитализация и объём торгов - растянутый на всю ширину экрана
    st.subheader("Общая капитализация и объём торгов")
    
    # Получаем исторические данные о капитализации и объеме
    historical_data = get_historical_market_cap()
    
    # Получаем последние значения капитализации и объема
    latest_cap = historical_data['caps'][-1]
    latest_volume = historical_data['volumes'][-1]
    
    # Отображаем значения в стиле Fear & Greed Index
    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
            <div style="flex: 1; padding-right: 20px;">
                <div style="font-size: 20px; font-weight: bold;">Капитализация</div>
                <div style="font-size: 60px; font-weight: bold; color: #1E88E5;">${latest_cap/1e12:.2f}T</div>
            </div>
            <div style="flex: 1; padding-left: 20px;">
                <div style="font-size: 20px; font-weight: bold;">Объём торгов</div>
                <div style="font-size: 60px; font-weight: bold; color: #4CAF50;">${latest_volume/1e9:.2f}B</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Создаем DataFrame для графика с двумя метриками
    chart_data = pd.DataFrame({
        'Дата': historical_data['dates'],
        'Капитализация': historical_data['caps'],
        'Объём торгов': historical_data['volumes']
    })
    
    # Используем matplotlib для создания графика с двумя осями Y
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.ticker import FuncFormatter
    
    # Создаем фигуру и оси
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # Убираем черную рамку вокруг графика
    for spine in ax1.spines.values():
        spine.set_visible(False)
    
    # Настраиваем первую ось Y (капитализация)
    color1 = '#1E88E5'
    ax1.set_xlabel('')
    ax1.set_ylabel('Капитализация (USD)', color=color1, fontsize=12)
    line1, = ax1.plot(chart_data['Дата'], chart_data['Капитализация'], color=color1, linewidth=2.5, label='Капитализация')
    ax1.tick_params(axis='y', labelcolor=color1)
    
    # Форматируем метки оси Y для капитализации (триллионы)
    def trillions(x, pos):
        return f'${x/1e12:.1f}T'
    
    ax1.yaxis.set_major_formatter(FuncFormatter(trillions))
    
    # Создаем вторую ось Y (объем торгов)
    ax2 = ax1.twinx()
    # Убираем черную рамку и для второй оси
    for spine in ax2.spines.values():
        spine.set_visible(False)
        
    color2 = '#4CAF50'
    ax2.set_ylabel('Объём торгов (USD)', color=color2, fontsize=12)
    line2, = ax2.plot(chart_data['Дата'], chart_data['Объём торгов'], color=color2, linewidth=2.5, label='Объём торгов')
    ax2.tick_params(axis='y', labelcolor=color2)
    
    # Форматируем метки оси Y для объема торгов (миллиарды)
    def billions(x, pos):
        return f'${x/1e9:.1f}B'
    
    ax2.yaxis.set_major_formatter(FuncFormatter(billions))
    
    # Форматируем ось X (даты)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.xticks(rotation=45)
    
    # Добавляем сетку
    ax1.grid(True, linestyle='--', alpha=0.7)
    
    # Настраиваем внешний вид
    fig.tight_layout()
    
    # Отображаем график в Streamlit
    st.pyplot(fig)
    
    # Добавляем пояснение
    st.markdown("""
    <div style="text-align: center; padding: 10px; background-color: #f8f9fa; border-radius: 5px;">
        <p>График показывает динамику капитализации (синяя линия, левая шкала) и объема торгов (зеленая линия, правая шкала) за последний год.</p>
    </div>
    """, unsafe_allow_html=True)
