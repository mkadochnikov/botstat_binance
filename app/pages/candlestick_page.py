"""
Страница для отображения свечных графиков на основе данных из базы PostgreSQL.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
from typing import List, Dict, Any, Optional

# Конфигурация базы данных
DB_HOST = "46.252.251.117"
DB_PORT = "4791"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "mysecretpassword"
DB_SCHEMA = "all_futures"  # Используем схему all_futures

def connect_to_db():
    """
    Подключение к базе данных PostgreSQL.
    
    Returns:
        Connection: Объект соединения с базой данных
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        st.error(f"Ошибка подключения к базе данных: {str(e)}")
        return None

def get_available_symbols():
    """
    Получение списка доступных торговых пар из базы данных.
    
    Returns:
        List[str]: Список доступных символов
    """
    conn = None
    try:
        conn = connect_to_db()
        if not conn:
            return []
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s AND table_name LIKE %s
            ORDER BY table_name
        """, (DB_SCHEMA, '%\_5M'))
        
        tables = [row[0] for row in cursor.fetchall()]
        # Извлекаем символы из имен таблиц (убираем _5M)
        symbols = [table[:-3] for table in tables if table.endswith('_5M')]
        return symbols
    except Exception as e:
        st.error(f"Ошибка получения списка символов: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

def get_candlestick_data(symbol, start_date, end_date, limit=1000):
    """
    Получение данных для свечного графика.
    
    Args:
        symbol: Символ торговой пары
        start_date: Начальная дата
        end_date: Конечная дата
        limit: Максимальное количество свечей
        
    Returns:
        DataFrame: Данные для построения графика
    """
    conn = None
    try:
        conn = connect_to_db()
        if not conn:
            return pd.DataFrame()
        
        table_name = f"{symbol}_5M"
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(f"""
            SELECT 
                open_time,
                open_price,
                high_price,
                low_price,
                close_price,
                volume
            FROM "{DB_SCHEMA}"."{table_name}"
            WHERE open_time BETWEEN %s AND %s
            ORDER BY open_time
            LIMIT %s
        """, (start_date, end_date, limit))
        
        rows = cursor.fetchall()
        df = pd.DataFrame(rows)
        
        # Преобразуем числовые столбцы в float
        for col in ['open_price', 'high_price', 'low_price', 'close_price', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col])
        
        return df
    except Exception as e:
        st.error(f"Ошибка получения данных для графика: {str(e)}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def render_candlestick_page():
    """
    Отображение страницы со свечными графиками.
    """
    st.title("Свечные графики криптовалют")
    
    # Получаем список доступных символов
    symbols = get_available_symbols()
    
    if not symbols:
        st.error("Не удалось получить список доступных торговых пар")
        return
    
    # Боковая панель с настройками
    with st.sidebar:
        st.header("Настройки графика")
        
        # Выбор торговой пары
        selected_symbol = st.selectbox(
            "Выберите торговую пару",
            options=symbols,
            index=symbols.index("BTCUSDT") if "BTCUSDT" in symbols else 0
        )
        
        # Выбор временного диапазона
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Начальная дата",
                value=datetime.date.today() - datetime.timedelta(days=7)
            )
        with col2:
            end_date = st.date_input(
                "Конечная дата",
                value=datetime.date.today()
            )
        
        # Преобразуем даты в datetime
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
        
        # Выбор количества свечей
        max_candles = st.slider(
            "Максимальное количество свечей",
            min_value=100,
            max_value=5000,
            value=1000,
            step=100
        )
        
        # Кнопка обновления
        refresh_button = st.button("Обновить график")
    
    # Основная область с графиком
    st.subheader(f"Свечной график {selected_symbol}")
    
    # Получаем данные для графика
    df = get_candlestick_data(selected_symbol, start_datetime, end_datetime, max_candles)
    
    if df.empty:
        st.warning("Нет данных для отображения. Попробуйте изменить параметры запроса.")
        return
    
    # Создаем свечной график с помощью Plotly
    fig = go.Figure(data=[go.Candlestick(
        x=df['open_time'],
        open=df['open_price'],
        high=df['high_price'],
        low=df['low_price'],
        close=df['close_price'],
        name=selected_symbol
    )])
    
    # Добавляем объем торгов внизу графика
    fig.add_trace(go.Bar(
        x=df['open_time'],
        y=df['volume'],
        name='Объем',
        marker_color='rgba(0, 0, 255, 0.5)',
        yaxis='y2'
    ))
    
    # Настраиваем макет графика
    fig.update_layout(
        title=f'{selected_symbol} - Свечной график',
        xaxis_title='Время',
        yaxis_title='Цена',
        xaxis_rangeslider_visible=False,  # Отключаем ползунок внизу для экономии места
        height=600,
        yaxis2=dict(
            title='Объем',
            overlaying='y',
            side='right',
            showgrid=False
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Отображаем график
    st.plotly_chart(fig, use_container_width=True)
    
    # Отображаем таблицу с данными
    with st.expander("Показать данные"):
        st.dataframe(df)
    
    # Добавляем информацию о последней свече
    if not df.empty:
        last_candle = df.iloc[-1]
        st.subheader("Информация о последней свече")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Открытие", f"{last_candle['open_price']:.2f}")
        col2.metric("Максимум", f"{last_candle['high_price']:.2f}")
        col3.metric("Минимум", f"{last_candle['low_price']:.2f}")
        col4.metric("Закрытие", f"{last_candle['close_price']:.2f}")
        
        # Изменение цены
        price_change = last_candle['close_price'] - last_candle['open_price']
        price_change_pct = (price_change / last_candle['open_price']) * 100
        
        col1, col2 = st.columns(2)
        col1.metric("Изменение", f"{price_change:.2f}", f"{price_change_pct:.2f}%")
        col2.metric("Объем", f"{last_candle['volume']:.2f}")

# Основная функция страницы
def main():
    render_candlestick_page()

if __name__ == "__main__":
    main()
