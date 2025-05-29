import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import psycopg2
from datetime import datetime, timedelta
import time
from plotly.subplots import make_subplots


# Текст описания торговых сессий
TRADING_SESSIONS_DESCRIPTION = """
# Описание торговых сессий

## 1. Азиатская сессия (Токио/Гонконг/Сингапур)

**Время:** 23:00 – 08:00 GMT

* **Особенности:**
  * Начало (23:00–02:00 GMT): Активность Японии (Токийская биржа) — возможны резкие движения из-за крупных ордеров.
  * Китай/Гонконг (02:00–06:00 GMT): Рост объема валютных пар с участием CNY, AUD, JPY.
  * Паттерны:
    * Консолидация перед открытием Европы.
    * Ложные пробои уровней из-за низкой ликвидности.
 
## 2. Переход Азия → Европа

**Время:** 08:00 – 09:00 GMT

* **Особенности:**
  * Закрытие азиатских бирж, начало работы европейских (Лондон, Франкфурт).
  * Часто возникают резкие скачки из-за накопленных ордеров.
* **Паттерны:**
  * Пробои уровней поддержки/сопротивления.
  * Формирование утренних гэпов (на фондовых рынках).
 
## 3. Европейская сессия (Лондон)

**Время:** 09:00 – 16:00 GMT

* **Пик активности:** 12:00–14:00 GMT (перекрытие с США).
* **Особенности:**
  * Высокая ликвидность на EUR, GBP, CHF.
  * Выход европейских макроэкономических данных (10:00–12:00 GMT).
* **Паттерны:**
  * Трендовые движения (например, импульсы на новостях).
  * Формирование "Лондонского пробоя".
 
## 4. Перекрытие Европа → США

**Время:** 13:30 – 16:00 GMT

* **Особенности:**
  * Открытие Нью-Йорка (13:30 GMT) + активность Лондона.
  * Самый волатильный период на Forex и фондовых рынках.
* **Паттерны:**
  * Сильные тренды (например, движение индекса S&P 500).
  * Ловушки для контратрендовых трейдеров.
 
## 5. Американская сессия (Нью-Йорк)

**Время:** 13:30 – 20:00 GMT

* **Пик активности:** 14:00–18:00 GMT.
* **Особенности:**
  * Влияние данных США (публикуются в 13:30–15:00 GMT).
  * Закрытие бирж в 20:00 GMT — возможны резкие движения.
* **Паттерны:**
  * "Фиксация прибыли" перед закрытием.
  * Формирование дневных максимумов/минимумов.
 
## 6. Тихая сессия (Азия/Тихий океан)

**Время:** 20:00 – 23:00 GMT

* **Особенности:**
  * Закрыты основные биржи (Нью-Йорк, Токио).
  * Низкая ликвидность, движение часто коррекционное.
* **Паттерны:**
  * Откаты после дневных трендов.
  * Ложные пробои (из-за манипуляций алгоритмов).
 
## Примеры повторяющихся паттернов:

* Утренний гэп (на открытии Европы/США) → часто закрывается в первые часы.
* Лондонский импульс (09:00–10:00 GMT) → начало тренда.
* Фиксация прибыли в 19:00–20:00 GMT → откаты перед закрытием США.
"""


# Настройка подключения к БД
def get_db_connection():
    return psycopg2.connect(
        host="46.252.251.117",
        port=4791,
        dbname="postgres",
        user="postgres",
        password="mysecretpassword"
    )


# Получение списка всех доступных торговых пар
def get_available_symbols():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'all_futures' 
            AND table_name LIKE '%_5M'
        """)
        tables = cur.fetchall()
        # Извлекаем имена символов из названий таблиц
        symbols = [table[0].split('_')[0] for table in tables]
        return sorted(set(symbols))  # Убираем дубликаты и сортируем
    except Exception as e:
        st.error(f"Ошибка при загрузке списка таблиц: {str(e)}")
        return []
    finally:
        conn.close()


# Получение диапазона дат для символа
def get_date_range(symbol):
    table_name = f"{symbol}_5M"
    conn = get_db_connection()
    try:
        query = f"""
            SELECT MIN(open_time), MAX(open_time)
            FROM all_futures."{table_name}"
        """
        df = pd.read_sql_query(query, conn)
        return df.iloc[0, 0], df.iloc[0, 1]
    except Exception as e:
        st.error(f"Ошибка при получении диапазона дат: {str(e)}")
        return None, None
    finally:
        conn.close()


# Загрузка данных из БД для выбранного периода
def load_candle_data(symbol, start_date, end_date):
    table_name = f"{symbol}_5M"

    conn = get_db_connection()
    try:
        query = f"""
            SELECT 
                open_time AS timestamp,
                open_price AS open,
                high_price AS high,
                low_price AS low,
                close_price AS close
            FROM all_futures."{table_name}"
            WHERE open_time BETWEEN %s AND %s
            ORDER BY open_time ASC
        """

        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        return df
    except Exception as e:
        st.error(f"Ошибка при загрузке данных: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()


# Загрузка данных Fear and Greed и интервалов из таблицы common_5m
def load_common_data(start_date, end_date):
    conn = get_db_connection()
    try:
        query = """
            SELECT 
                timestamp,
                fear_and_greed,
                "AS", "AE", "EU", "EA", "AM", "TS"
            FROM all_futures.common_5m
            WHERE timestamp BETWEEN %s AND %s
            ORDER BY timestamp ASC
        """

        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        return df
    except Exception as e:
        st.error(f"Ошибка при загрузке данных из common_5m: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()


def render_trade_sessions_page():
    """
    Отрисовка страницы торговых сессий
    """
    st.title("Торговые сессии")
    
    # Получаем список символов
    symbols = get_available_symbols()

    # Устанавливаем BTCUSDT как значение по умолчанию
    default_index = 0
    if 'BTCUSDT' in symbols:
        default_index = symbols.index('BTCUSDT')

    # Сайдбар для параметров
    st.sidebar.header("Параметры графика")
    symbol = st.sidebar.selectbox("Торговая пара", symbols, index=default_index)

    # Получаем диапазон дат для выбранного символа
    min_date, max_date = get_date_range(symbol)
    if min_date is None or max_date is None:
        st.error("Не удалось получить диапазон дат для выбранной торговой пары")
        st.stop()

    # Преобразуем в datetime
    min_date = pd.to_datetime(min_date)
    max_date = pd.to_datetime(max_date)

    # Инициализация состояния сессии
    if 'end_date' not in st.session_state:
        st.session_state.end_date = max_date
    if 'days_range' not in st.session_state:
        st.session_state.days_range = 7  # По умолчанию показываем 7 дней

    # Основная область
    st.sidebar.header("Управление периодом")
    st.sidebar.write(f"**Доступный диапазон дат:**")
    st.sidebar.write(f"Начало: {min_date.strftime('%Y-%m-%d')}")
    st.sidebar.write(f"Конец: {max_date.strftime('%Y-%m-%d')}")

    # Выбор количества дней для отображения
    days_range = st.sidebar.slider(
        "Количество дней для отображения",
        1, 365, st.session_state.days_range, 1,
        help="Выберите количество дней для отображения на графике"
    )

    # Добавляем ссылку "Описание торговых сессий" в левое меню
    st.sidebar.header("Информация")

    # Используем expander вместо dialog для совместимости
    with st.sidebar.expander("Описание торговых сессий"):
        st.markdown(TRADING_SESSIONS_DESCRIPTION)

    # Рассчитываем начальную дату на основе выбранного диапазона
    start_date = st.session_state.end_date - timedelta(days=days_range)

    # Загрузка данных
    with st.spinner('Загрузка данных...'):
        df = load_candle_data(symbol, start_date, st.session_state.end_date)
        common_df = load_common_data(start_date, st.session_state.end_date)

    if not df.empty:
        # Преобразование и сортировка данных
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        # Создаем график с двумя осями Y и синхронизированным масштабированием
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Добавляем свечной график на основную ось
        fig.add_trace(
            go.Candlestick(
                x=df['timestamp'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name=f'{symbol} 5M',
                showlegend=False
            ),
            secondary_y=False
        )

        # Добавляем график Fear and Greed и линии интервалов, если данные доступны
        if not common_df.empty:
            common_df['timestamp'] = pd.to_datetime(common_df['timestamp'])
            
            # Добавляем график Fear and Greed
            fig.add_trace(
                go.Scatter(
                    x=common_df['timestamp'],
                    y=common_df['fear_and_greed'],
                    mode='lines',
                    name='Fear and Greed',
                    line=dict(color='purple', width=1),
                    showlegend=False
                ),
                secondary_y=True
            )
            
            # Определяем цвета для линий интервалов
            interval_colors = {
                'AS': 'red',
                'AE': 'green',
                'EU': 'blue',
                'EA': 'orange',
                'AM': 'purple',
                'TS': 'cyan'
            }
            
            # Получаем минимальное значение для размещения линий внизу графика
            y_min = df['low'].min()
            
            # Словарь для отслеживания занятых временных интервалов и их вертикальных позиций
            occupied_intervals = []
            
            # Обработка каждого интервала
            for interval_name, color in interval_colors.items():
                # Находим все сегменты, где интервал активен
                segments = []
                start_idx = None
                
                for i in range(len(common_df)):
                    # Начало сегмента
                    if common_df[interval_name].iloc[i] == 1 and (i == 0 or common_df[interval_name].iloc[i-1] == 0):
                        start_idx = i
                    
                    # Конец сегмента
                    if start_idx is not None and (i == len(common_df) - 1 or common_df[interval_name].iloc[i+1] == 0):
                        segments.append((start_idx, i))
                        start_idx = None
                
                # Для каждого сегмента добавляем горизонтальную линию
                for start_idx, end_idx in segments:
                    start_time = common_df['timestamp'].iloc[start_idx]
                    end_time = common_df['timestamp'].iloc[end_idx]
                    
                    # Определяем вертикальную позицию для линии
                    position = 0
                    overlap = True
                    
                    # Ищем свободную позицию без наложений
                    while overlap:
                        overlap = False
                        for interval_start, interval_end, pos in occupied_intervals:
                            # Проверяем наложение с существующими интервалами на той же позиции
                            if position == pos and max(start_time, interval_start) <= min(end_time, interval_end):
                                overlap = True
                                break
                        
                        if overlap:
                            position += 1
                    
                    # Сохраняем интервал и его позицию
                    occupied_intervals.append((start_time, end_time, position))
                    
                    # Вычисляем вертикальную позицию для линии (смещение вниз)
                    y_position = y_min * (0.995 - 0.005 * position)
                    
                    # Добавляем горизонтальную линию для интервала
                    fig.add_trace(
                        go.Scatter(
                            x=[start_time, end_time],
                            y=[y_position, y_position],
                            mode='lines',
                            line=dict(color=color, width=2),
                            name=interval_name,
                            showlegend=False,
                            hoverinfo='text',
                            hovertext=f"{interval_name}: {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%Y-%m-%d %H:%M')}"
                        ),
                        secondary_y=False
                    )
                    
                    # Добавляем подпись к линии
                    fig.add_annotation(
                        x=start_time,
                        y=y_position,
                        text=interval_name,
                        showarrow=False,
                        font=dict(color=color, size=10),
                        yshift=-10
                    )

        # Настройка макета
        fig.update_layout(
            title=f'{symbol} - 5M | {start_date.strftime("%Y-%m-%d")} - {st.session_state.end_date.strftime("%Y-%m-%d")} | {len(df)} свечей',
            xaxis_title='Время',
            xaxis_rangeslider_visible=False,
            height=700,
            margin=dict(l=20, r=20, t=60, b=40),  # Увеличиваем нижний отступ для линий
            hovermode="x unified",
            showlegend=False,  # Убираем легенду
            # Синхронизация масштабирования осей
            yaxis=dict(
                scaleanchor="y2",
                scaleratio=1,
                constrain="domain"
            ),
            yaxis2=dict(
                scaleanchor="y",
                scaleratio=1,
                constrain="domain"
            )
        )

        # Настройка основной оси Y (цена) - справа
        fig.update_yaxes(
            title_text="Цена",
            side="right",
            secondary_y=False,
            spikemode='across',
            spikesnap='cursor'
        )

        # Настройка вторичной оси Y (Fear and Greed) - слева
        fig.update_yaxes(
            title_text="Fear and Greed",
            side="left",
            secondary_y=True,
            range=[1, 100],  # Диапазон от 1 до 100
            spikemode='across',
            spikesnap='cursor'
        )

        # Настройка оси X для корректного отображения дат
        fig.update_xaxes(
            type='date',
            tickformat='%Y-%m-%d %H:%M',
            spikemode='across',
            spikesnap='cursor'
        )

        # Отображение графика во всю ширину
        st.plotly_chart(fig, use_container_width=True)

        # Бегунок для выбора конечной даты прямо под графиком
        st.subheader("Регулировка периода отображения")

        # Преобразуем даты в timestamp для слайдера
        min_ts = time.mktime(min_date.timetuple())
        max_ts = time.mktime(max_date.timetuple())
        end_ts = time.mktime(st.session_state.end_date.timetuple())

        # Создаем слайдер с отображением конкретной даты
        # Используем кастомный формат для отображения даты
        new_end_ts = st.slider(
            "Выберите конечную дату периода",
            min_value=min_ts,
            max_value=max_ts,
            value=end_ts,
            step=timedelta(days=1).total_seconds(),
            key="date_slider"
        )

        # Конвертируем обратно в datetime
        new_end_date = datetime.fromtimestamp(new_end_ts)
        
        # Отображаем конкретную дату над бегунком
        st.markdown(
            f"""
            <div style="text-align: center; margin-top: -30px; font-size: 16px; font-weight: bold;">
                {new_end_date.strftime('%Y-%m-%d')}
            </div>
            """, 
            unsafe_allow_html=True
        )

        # Обновление конечной даты при изменении ползунка
        if new_end_date != st.session_state.end_date:
            st.session_state.end_date = new_end_date
            st.session_state.days_range = days_range
            st.rerun()

        # Информация о периоде
        st.caption(
            f"**Отображаемый период:** {start_date.strftime('%Y-%m-%d')} - {st.session_state.end_date.strftime('%Y-%m-%d')}")
        st.caption(f"**Всего свечей:** {len(df)} (примерно {len(df) / 288:.1f} дней)")

        # Отображение сырых данных
        expander = st.expander("Посмотреть сырые данные")
        with expander:
            st.dataframe(df.sort_values('timestamp', ascending=False).style.format({
                'open': '{:.8f}',
                'high': '{:.8f}',
                'low': '{:.8f}',
                'close': '{:.8f}'
            }))

        # Статус подключения
        st.sidebar.success(f"Данные загружены: {datetime.now().strftime('%H:%M:%S')}")
        st.sidebar.metric("Показано свечей", len(df))
    else:
        st.warning("Не удалось загрузить данные. Проверьте параметры подключения и название таблицы.")
