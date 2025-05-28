"""
Страница для отображения свечных графиков на основе данных из базы PostgreSQL.
Улучшенная версия с современным дизайном и адаптивной шириной.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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

# Цветовые схемы для графиков
CHART_COLORS = {
    'light': {
        'bg_color': '#FFFFFF',
        'plot_bg_color': '#F8F9FA',
        'grid_color': '#E9ECEF',
        'text_color': '#212529',
        'increasing_color': '#26A69A',
        'decreasing_color': '#EF5350',
        'volume_color': 'rgba(100, 181, 246, 0.5)',
        'volume_line_color': 'rgba(100, 181, 246, 1.0)',
        'axis_color': '#ADB5BD'
    },
    'dark': {
        'bg_color': '#1E1E1E',
        'plot_bg_color': '#2D2D2D',
        'grid_color': '#3D3D3D',
        'text_color': '#E0E0E0',
        'increasing_color': '#00C853',
        'decreasing_color': '#FF5252',
        'volume_color': 'rgba(66, 165, 245, 0.4)',
        'volume_line_color': 'rgba(66, 165, 245, 0.8)',
        'axis_color': '#757575'
    }
}

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
        
        # Проверяем наличие всех необходимых столбцов
        required_columns = ['open_time', 'open_price', 'high_price', 'low_price', 'close_price', 'volume']
        for col in required_columns:
            if col not in df.columns:
                st.error(f"Отсутствует столбец {col} в данных")
                return pd.DataFrame()
        
        # Преобразуем числовые столбцы в float
        for col in ['open_price', 'high_price', 'low_price', 'close_price', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Удаляем строки с пропущенными значениями
        df = df.dropna(subset=['open_price', 'high_price', 'low_price', 'close_price'])
        
        # Выводим информацию о данных для отладки
        st.sidebar.caption(f"Получено {len(df)} строк данных")
        if not df.empty:
            st.sidebar.caption(f"Диапазон дат: {df['open_time'].min()} - {df['open_time'].max()}")
        
        return df
    except Exception as e:
        st.error(f"Ошибка получения данных для графика: {str(e)}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def calculate_moving_averages(df, short_period=20, long_period=50):
    """
    Расчет скользящих средних для графика.
    
    Args:
        df: DataFrame с данными
        short_period: Период короткой скользящей средней
        long_period: Период длинной скользящей средней
        
    Returns:
        DataFrame: Дополненный DataFrame со скользящими средними
    """
    if not df.empty and 'close_price' in df.columns:
        df['MA_short'] = df['close_price'].rolling(window=short_period).mean()
        df['MA_long'] = df['close_price'].rolling(window=long_period).mean()
    return df

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
        
        # Выбор темы графика
        theme = st.selectbox(
            "Тема графика",
            options=["Светлая", "Тёмная"],
            index=0
        )
        
        # Определяем цветовую схему на основе выбранной темы
        color_scheme = CHART_COLORS['dark'] if theme == "Тёмная" else CHART_COLORS['light']
        
        # Выбор торговой пары
        selected_symbol = st.selectbox(
            "Выберите торговую пару",
            options=symbols,
            index=symbols.index("BTCUSDT") if "BTCUSDT" in symbols else 0
        )
        
        # Выбор временного диапазона
        col1, col2 = st.columns(2)
        with col1:
            # Устанавливаем начальную дату на 30 дней назад от текущей даты
            default_start_date = datetime.date(2023, 1, 1)
            start_date = st.date_input(
                "Начальная дата",
                value=default_start_date
            )
        with col2:
            # Устанавливаем конечную дату на текущую дату
            default_end_date = datetime.date(2023, 1, 31)
            end_date = st.date_input(
                "Конечная дата",
                value=default_end_date
            )
        
        # Преобразуем даты в datetime
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
        
        # Выводим информацию о выбранном диапазоне для отладки
        st.sidebar.caption(f"Запрос данных с {start_datetime} по {end_datetime}")
        
        # Выбор количества свечей
        max_candles = st.slider(
            "Максимальное количество свечей",
            min_value=100,
            max_value=5000,
            value=1000,
            step=100
        )
        
        # Дополнительные настройки графика
        show_ma = st.checkbox("Показать скользящие средние", value=True)
        
        if show_ma:
            ma_col1, ma_col2 = st.columns(2)
            with ma_col1:
                ma_short = st.number_input("Короткая MA", min_value=5, max_value=50, value=20, step=1)
            with ma_col2:
                ma_long = st.number_input("Длинная MA", min_value=20, max_value=200, value=50, step=5)
        
        # Настройки отображения
        show_volume = st.checkbox("Показать объем торгов", value=True)
        show_tooltips = st.checkbox("Расширенные подсказки", value=True)
        
        # Кнопка обновления
        refresh_button = st.button("Обновить график")
    
    # Основная область с графиком
    st.subheader(f"Свечной график {selected_symbol}")
    
    # Получаем данные для графика
    df = get_candlestick_data(selected_symbol, start_datetime, end_datetime, max_candles)
    
    if df.empty:
        st.warning("Нет данных для отображения. Попробуйте изменить параметры запроса.")
        return
    
    # Выводим первые несколько строк данных для отладки
    st.caption("Пример данных для построения графика:")
    st.write(df.head(3))
    
    # Рассчитываем скользящие средние, если включены
    if show_ma:
        df = calculate_moving_averages(df, ma_short, ma_long)
    
    # Создаем подграфики для свечей и объема
    if show_volume:
        fig = make_subplots(
            rows=2, 
            cols=1, 
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.8, 0.2]
        )
    else:
        fig = make_subplots(rows=1, cols=1)
    
    # Добавляем свечной график
    fig.add_trace(
        go.Candlestick(
            x=df['open_time'],
            open=df['open_price'],
            high=df['high_price'],
            low=df['low_price'],
            close=df['close_price'],
            name=selected_symbol,
            increasing_line_color=color_scheme['increasing_color'],
            decreasing_line_color=color_scheme['decreasing_color'],
            increasing_fillcolor=color_scheme['increasing_color'],
            decreasing_fillcolor=color_scheme['decreasing_color'],
            line=dict(width=1),
            opacity=1
        ),
        row=1, col=1
    )
    
    # Добавляем скользящие средние, если включены
    if show_ma and 'MA_short' in df.columns and 'MA_long' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['open_time'],
                y=df['MA_short'],
                name=f'MA {ma_short}',
                line=dict(color='rgba(255, 193, 7, 1)', width=1.5),
                opacity=0.8
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df['open_time'],
                y=df['MA_long'],
                name=f'MA {ma_long}',
                line=dict(color='rgba(33, 150, 243, 1)', width=1.5),
                opacity=0.8
            ),
            row=1, col=1
        )
    
    # Добавляем объем торгов, если включен
    if show_volume:
        # Определяем цвета для объема в зависимости от направления свечи
        colors = []
        for i in range(len(df)):
            if i > 0:
                if df['close_price'].iloc[i] > df['close_price'].iloc[i-1]:
                    colors.append(color_scheme['increasing_color'])
                else:
                    colors.append(color_scheme['decreasing_color'])
            else:
                colors.append(color_scheme['decreasing_color'])
        
        fig.add_trace(
            go.Bar(
                x=df['open_time'],
                y=df['volume'],
                name='Объем',
                marker=dict(
                    color=colors,
                    line=dict(
                        color=colors,
                        width=1
                    ),
                    opacity=0.7
                )
            ),
            row=2, col=1
        )
    
    # Настраиваем макет графика
    fig.update_layout(
        title=dict(
            text=f'{selected_symbol} - Свечной график',
            font=dict(size=24, color=color_scheme['text_color'])
        ),
        paper_bgcolor=color_scheme['bg_color'],
        plot_bgcolor=color_scheme['plot_bg_color'],
        xaxis_title='Время',
        yaxis_title='Цена',
        xaxis_rangeslider_visible=False,  # Отключаем ползунок внизу для экономии места
        height=700,  # Увеличиваем высоту для лучшего отображения
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color=color_scheme['text_color']),
            bgcolor='rgba(0,0,0,0)'
        ),
        margin=dict(l=10, r=10, t=50, b=10),  # Уменьшаем отступы для максимального использования пространства
        hovermode='x unified' if show_tooltips else 'closest',
        hoverlabel=dict(
            bgcolor=color_scheme['bg_color'],
            font_size=12,
            font_color=color_scheme['text_color']
        )
    )
    
    # Настраиваем оси
    fig.update_xaxes(
        showgrid=True,
        gridcolor=color_scheme['grid_color'],
        zeroline=False,
        showline=True,
        linewidth=1,
        linecolor=color_scheme['axis_color'],
        tickfont=dict(color=color_scheme['text_color']),
        title_font=dict(color=color_scheme['text_color'])
    )
    
    fig.update_yaxes(
        showgrid=True,
        gridcolor=color_scheme['grid_color'],
        zeroline=False,
        showline=True,
        linewidth=1,
        linecolor=color_scheme['axis_color'],
        tickfont=dict(color=color_scheme['text_color']),
        title_font=dict(color=color_scheme['text_color']),
        row=1, col=1
    )
    
    if show_volume:
        fig.update_yaxes(
            showgrid=True,
            gridcolor=color_scheme['grid_color'],
            zeroline=False,
            showline=True,
            linewidth=1,
            linecolor=color_scheme['axis_color'],
            tickfont=dict(color=color_scheme['text_color']),
            title_text='Объем',
            title_font=dict(color=color_scheme['text_color']),
            row=2, col=1
        )
    
    # Добавляем анимацию при загрузке
    fig.update_layout(
        transition_duration=500,
        transition=dict(
            duration=500,
            easing='cubic-in-out'
        )
    )
    
    # Отображаем график с шириной 100%
    st.plotly_chart(fig, use_container_width=True, theme=None)
    
    # Отображаем таблицу с данными
    with st.expander("Показать данные"):
        st.dataframe(df)
    
    # Добавляем информацию о последней свече
    if not df.empty:
        last_candle = df.iloc[-1]
        st.subheader("Информация о последней свече")
        
        # Стилизуем метрики
        col1, col2, col3, col4 = st.columns(4)
        
        # Определяем цвет для значений в зависимости от изменения цены
        price_change = last_candle['close_price'] - last_candle['open_price']
        price_color = "green" if price_change >= 0 else "red"
        
        col1.metric(
            "Открытие", 
            f"{last_candle['open_price']:.2f}"
        )
        
        col2.metric(
            "Максимум", 
            f"{last_candle['high_price']:.2f}"
        )
        
        col3.metric(
            "Минимум", 
            f"{last_candle['low_price']:.2f}"
        )
        
        col4.metric(
            "Закрытие", 
            f"{last_candle['close_price']:.2f}"
        )
        
        # Изменение цены
        price_change_pct = (price_change / last_candle['open_price']) * 100
        
        col1, col2 = st.columns(2)
        col1.metric(
            "Изменение", 
            f"{price_change:.2f}", 
            f"{price_change_pct:.2f}%",
            delta_color="normal"
        )
        
        col2.metric(
            "Объем", 
            f"{last_candle['volume']:.2f}"
        )

# Основная функция страницы
def main():
    # Настройка страницы
    st.set_page_config(
        page_title="Свечные графики криптовалют",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Добавляем CSS для улучшения внешнего вида
    st.markdown("""
    <style>
    .stApp {
        max-width: 100%;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3 {
        margin-bottom: 1rem;
    }
    .stMetric {
        background-color: rgba(255, 255, 255, 0.1);
        border-radius: 5px;
        padding: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
    }
    </style>
    """, unsafe_allow_html=True)
    
    render_candlestick_page()

if __name__ == "__main__":
    main()
