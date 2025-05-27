"""
Модуль для отображения свечных графиков фьючерсов с наложением данных из common_5m.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('futures_charts.log', mode='a')
    ]
)
logger = logging.getLogger('futures_charts')

# Конфигурация базы данных
DB_HOST = "46.252.251.117"
DB_PORT = "4791"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "mysecretpassword"

# Кэширование подключения к базе данных
@st.cache_resource
def get_db_connection():
    """
    Создание подключения к базе данных PostgreSQL
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        logger.info("Успешное подключение к базе данных")
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {str(e)}")
        st.error(f"Ошибка подключения к базе данных: {str(e)}")
        return None

# Получение списка доступных символов
@st.cache_data(ttl=3600)
def get_available_symbols():
    """
    Получение списка доступных символов из схемы all_futures
    """
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        # Запрос для получения списка таблиц в схеме all_futures
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'all_futures' 
        AND table_name LIKE '%\_5M' ESCAPE '\\'
        ORDER BY table_name
        """
        
        cursor.execute(query)
        tables = cursor.fetchall()
        
        # Извлекаем имена символов из имен таблиц
        symbols = [table[0].replace('_5M', '') for table in tables]
        
        cursor.close()
        
        logger.info(f"Получено {len(symbols)} символов из базы данных")
        return symbols
    except Exception as e:
        logger.error(f"Ошибка при получении списка символов: {str(e)}")
        st.error(f"Ошибка при получении списка символов: {str(e)}")
        return []

# Получение данных свечей для выбранного символа
@st.cache_data(ttl=300)
def get_candle_data(symbol, limit=500):
    """
    Получение данных свечей для выбранного символа
    
    Args:
        symbol: Символ (например, BTCUSDT)
        limit: Количество последних свечей для получения
        
    Returns:
        DataFrame: Данные свечей
    """
    try:
        conn = get_db_connection()
        if not conn:
            return pd.DataFrame()
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Запрос для получения данных свечей
        query = f"""
        SELECT 
            open_time, 
            open_price, 
            high_price, 
            low_price, 
            close_price, 
            volume,
            close_time,
            quote_asset_volume
        FROM all_futures.{symbol}_5M
        ORDER BY open_time DESC
        LIMIT {limit}
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        cursor.close()
        
        if not rows:
            logger.warning(f"Нет данных для символа {symbol}")
            return pd.DataFrame()
        
        # Преобразуем результаты в DataFrame
        df = pd.DataFrame(rows)
        
        # Преобразуем строковые значения в числовые
        numeric_columns = ['open_price', 'high_price', 'low_price', 'close_price', 'volume', 'quote_asset_volume']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col])
        
        # Сортируем по времени (от старых к новым)
        df = df.sort_values('open_time')
        
        logger.info(f"Получено {len(df)} свечей для символа {symbol}")
        return df
    except Exception as e:
        logger.error(f"Ошибка при получении данных свечей для {symbol}: {str(e)}")
        st.error(f"Ошибка при получении данных свечей для {symbol}: {str(e)}")
        return pd.DataFrame()

# Получение данных из таблицы common_5m
@st.cache_data(ttl=300)
def get_common_data(limit=500):
    """
    Получение данных из таблицы common_5m
    
    Args:
        limit: Количество последних записей для получения
        
    Returns:
        DataFrame: Данные из таблицы common_5m
    """
    try:
        conn = get_db_connection()
        if not conn:
            return pd.DataFrame()
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Запрос для получения данных из common_5m
        query = f"""
        SELECT 
            timestamp, 
            fear_and_greed, 
            "AS", 
            "AE", 
            "EU", 
            "EA", 
            "AM", 
            "TS"
        FROM all_futures.common_5m
        ORDER BY timestamp DESC
        LIMIT {limit}
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        cursor.close()
        
        if not rows:
            logger.warning("Нет данных в таблице common_5m")
            return pd.DataFrame()
        
        # Преобразуем результаты в DataFrame
        df = pd.DataFrame(rows)
        
        # Сортируем по времени (от старых к новым)
        df = df.sort_values('timestamp')
        
        logger.info(f"Получено {len(df)} записей из таблицы common_5m")
        return df
    except Exception as e:
        logger.error(f"Ошибка при получении данных из common_5m: {str(e)}")
        st.error(f"Ошибка при получении данных из common_5m: {str(e)}")
        return pd.DataFrame()

def plot_candlestick_chart(symbol, candle_data, common_data):
    """
    Построение свечного графика с наложением данных из common_5m
    
    Args:
        symbol: Символ (например, BTCUSDT)
        candle_data: DataFrame с данными свечей
        common_data: DataFrame с данными из common_5m
        
    Returns:
        go.Figure: Объект графика Plotly
    """
    if candle_data.empty or common_data.empty:
        st.warning(f"Нет данных для построения графика {symbol}")
        return None
    
    # Создаем подграфики: основной график и график объемов
    fig = make_subplots(
        rows=2, 
        cols=1, 
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.8, 0.2],
        subplot_titles=(f"{symbol} Candlestick Chart", "Volume")
    )
    
    # Добавляем свечной график
    fig.add_trace(
        go.Candlestick(
            x=candle_data['open_time'],
            open=candle_data['open_price'],
            high=candle_data['high_price'],
            low=candle_data['low_price'],
            close=candle_data['close_price'],
            name="Price"
        ),
        row=1, col=1
    )
    
    # Добавляем график объемов
    colors = ['red' if row['open_price'] > row['close_price'] else 'green' for _, row in candle_data.iterrows()]
    
    fig.add_trace(
        go.Bar(
            x=candle_data['open_time'],
            y=candle_data['volume'],
            marker_color=colors,
            name="Volume"
        ),
        row=2, col=1
    )
    
    # Сопоставляем данные из common_5m с данными свечей по времени
    # Преобразуем timestamp из common_5m в формат open_time из candle_data
    common_data_aligned = pd.DataFrame()
    
    # Находим ближайшие значения timestamp для каждого open_time
    for index, row in candle_data.iterrows():
        open_time = row['open_time']
        # Находим ближайшую запись в common_data
        closest_idx = (common_data['timestamp'] - open_time).abs().idxmin()
        common_data_aligned = pd.concat([common_data_aligned, common_data.loc[[closest_idx]]])
    
    common_data_aligned.reset_index(drop=True, inplace=True)
    
    # Добавляем линию fear_and_greed на основной график (вторая ось Y)
    fig.add_trace(
        go.Scatter(
            x=candle_data['open_time'],
            y=common_data_aligned['fear_and_greed'],
            mode='lines',
            name="Fear & Greed",
            line=dict(color='purple', width=2),
            yaxis="y3"
        ),
        row=1, col=1
    )
    
    # Добавляем временные зоны как фоновые области
    time_zones = ["AS", "AE", "EU", "EA", "AM", "TS"]
    colors = ["rgba(255, 0, 0, 0.1)", "rgba(0, 255, 0, 0.1)", "rgba(0, 0, 255, 0.1)", 
              "rgba(255, 255, 0, 0.1)", "rgba(255, 0, 255, 0.1)", "rgba(0, 255, 255, 0.1)"]
    
    for i, zone in enumerate(time_zones):
        # Создаем маску для активных зон (значение 1)
        mask = common_data_aligned[zone] == 1
        
        if mask.any():
            # Находим непрерывные интервалы активности зоны
            intervals = []
            start_idx = None
            
            for j, active in enumerate(mask):
                if active and start_idx is None:
                    start_idx = j
                elif not active and start_idx is not None:
                    intervals.append((start_idx, j - 1))
                    start_idx = None
            
            # Добавляем последний интервал, если он не закрыт
            if start_idx is not None:
                intervals.append((start_idx, len(mask) - 1))
            
            # Добавляем фоновые области для каждого интервала
            for start, end in intervals:
                fig.add_vrect(
                    x0=candle_data['open_time'].iloc[start],
                    x1=candle_data['open_time'].iloc[end],
                    fillcolor=colors[i],
                    opacity=0.5,
                    layer="below",
                    line_width=0,
                    annotation_text=zone,
                    annotation_position="top left",
                    row=1, col=1
                )
    
    # Настраиваем вторую ось Y для fear_and_greed
    fig.update_layout(
        yaxis3=dict(
            title="Fear & Greed",
            titlefont=dict(color="purple"),
            tickfont=dict(color="purple"),
            anchor="x",
            overlaying="y",
            side="left",
            position=0.05
        )
    )
    
    # Настраиваем внешний вид графика
    fig.update_layout(
        title=f"{symbol} Chart with Fear & Greed Index and Time Zones",
        xaxis_title="Time",
        yaxis_title="Price",
        yaxis2_title="Volume",
        height=800,
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Настраиваем оси
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    
    return fig

def render_futures_charts_page():
    """
    Отрисовка страницы с графиками фьючерсов
    """
    # Настраиваем фиксированное меню слева
    st.markdown(
        """
        <style>
        .sidebar .sidebar-content {
            position: fixed;
            width: inherit;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Заголовок страницы
    st.title("Futures Candlestick Charts")
    
    # Получаем список доступных символов
    symbols = get_available_symbols()
    
    if not symbols:
        st.error("Не удалось получить список символов из базы данных")
        return
    
    # Создаем боковую панель для выбора символа
    with st.sidebar:
        st.header("Настройки")
        
        # Выбор символа
        selected_symbol = st.selectbox(
            "Выберите символ",
            options=symbols,
            index=0 if symbols else None
        )
        
        # Количество свечей для отображения
        candle_limit = st.slider(
            "Количество свечей",
            min_value=50,
            max_value=1000,
            value=200,
            step=50
        )
        
        # Кнопка обновления данных
        if st.button("Обновить данные"):
            # Очищаем кэш для получения свежих данных
            get_candle_data.clear()
            get_common_data.clear()
            st.success("Данные обновлены")
    
    # Основная область для отображения графика
    if selected_symbol:
        # Получаем данные свечей для выбранного символа
        candle_data = get_candle_data(selected_symbol, limit=candle_limit)
        
        # Получаем данные из common_5m
        common_data = get_common_data(limit=candle_limit)
        
        if candle_data.empty:
            st.warning(f"Нет данных свечей для символа {selected_symbol}")
        elif common_data.empty:
            st.warning("Нет данных в таблице common_5m")
        else:
            # Строим и отображаем график
            fig = plot_candlestick_chart(selected_symbol, candle_data, common_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
                
                # Добавляем пояснение к графику
                st.markdown("""
                **Пояснение к графику:**
                - **Свечи**: Показывают цены открытия, закрытия, максимума и минимума
                - **Объем**: Отображается на нижнем графике
                - **Fear & Greed**: Индекс страха и жадности (фиолетовая линия, шкала слева)
                - **Временные зоны**: Отображаются как цветные области на графике
                  - AS: Азия (красный)
                  - AE: Азия-Европа (зеленый)
                  - EU: Европа (синий)
                  - EA: Европа-Америка (желтый)
                  - AM: Америка (фиолетовый)
                  - TS: Тихоокеанская сессия (голубой)
                """)
                
                # Добавляем таблицу с последними данными
                with st.expander("Показать последние данные"):
                    # Объединяем данные свечей и common_5m
                    last_candles = candle_data.tail(10).reset_index(drop=True)
                    last_common = common_data_aligned.tail(10).reset_index(drop=True) if 'common_data_aligned' in locals() else common_data.tail(10).reset_index(drop=True)
                    
                    # Отображаем данные свечей
                    st.subheader("Последние свечи")
                    st.dataframe(
                        last_candles[['open_time', 'open_price', 'high_price', 'low_price', 'close_price', 'volume']],
                        use_container_width=True
                    )
                    
                    # Отображаем данные common_5m
                    st.subheader("Последние данные common_5m")
                    st.dataframe(
                        last_common[['timestamp', 'fear_and_greed', 'AS', 'AE', 'EU', 'EA', 'AM', 'TS']],
                        use_container_width=True
                    )
    else:
        st.info("Выберите символ в боковой панели для отображения графика")
