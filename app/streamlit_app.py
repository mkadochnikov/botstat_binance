import streamlit as st
import pandas as pd
import requests
import time
import datetime
import csv
import io
import os
import sys
import json
from typing import List, Dict, Any, Optional

# Добавляем родительскую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настройка страницы Streamlit
st.set_page_config(
    page_title="Binance Futures ATR Monitor (WebSocket)",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Константы
API_BASE_URL = "http://localhost:8008"  # URL FastAPI сервера на порту 8008
TIMEFRAMES = ["1m", "3m", "5m", "15m", "1h"]
REFRESH_INTERVAL = 30  # секунды
ATR_THRESHOLD = 0.15  # порог для выделения "горячих" значений

# Функции для взаимодействия с API
def get_symbols() -> List[str]:
    """Получение списка всех доступных фьючерсных символов"""
    try:
        response = requests.get(f"{API_BASE_URL}/symbols")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Ошибка при получении списка символов: {str(e)}")
        return []

def get_last_update_time() -> Optional[str]:
    """Получение времени последнего обновления данных в базе"""
    try:
        response = requests.get(f"{API_BASE_URL}/last_update_time")
        response.raise_for_status()
        data = response.json()
        
        if data["status"] == "ok":
            return data["last_update"]
        return None
    except Exception as e:
        st.error(f"Ошибка при получении времени последнего обновления: {str(e)}")
        return None

def trigger_database_update(limit: Optional[int] = None) -> bool:
    """Запуск обновления базы данных"""
    try:
        url = f"{API_BASE_URL}/update_database"
        if limit is not None:
            url += f"?limit={limit}"
            
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if data["status"] == "ok":
            return True
        return False
    except Exception as e:
        st.error(f"Ошибка при запуске обновления базы данных: {str(e)}")
        return False

def get_all_symbols_atr(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Получение ATR для всех символов из базы данных с отображением прогресса"""
    try:
        # Создаем прогресс-бар
        progress_text = "Загрузка данных из базы данных..."
        progress_bar = st.progress(0, text=progress_text)
        
        # Создаем всплывающее окно с информацией о прогрессе
        status_container = st.empty()
        status_container.info("Загрузка данных из базы данных...")
        
        # URL для запроса (всегда получаем данные из БД)
        url = f"{API_BASE_URL}/all_symbols_atr?from_db=true"
        if limit is not None:
            url += f"&limit={limit}"
        
        # Выполняем запрос
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Обновляем прогресс-бар и всплывающее окно
        progress_bar.progress(1.0, text="Загрузка завершена!")
        status_container.success(f"Загружено {len(data)} символов из базы данных")
        
        # Небольшая задержка для визуализации прогресса
        time.sleep(1)
        
        # Очищаем прогресс-бар и всплывающее окно
        progress_bar.empty()
        status_container.empty()
        
        # Показываем уведомление о завершении
        st.toast(f"Загрузка завершена! Загружено {len(data)} символов.", icon="✅")
        
        return data
    except Exception as e:
        st.error(f"Ошибка при получении данных ATR из базы данных: {str(e)}")
        return []

# Функция для создания DataFrame из данных ATR
def create_atr_dataframe(atr_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """Создание DataFrame из данных ATR для отображения в таблице"""
    rows = []
    
    for item in atr_data:
        row = {
            "Символ": item["symbol"],
            "Цена": round(item["price"], 4)
        }
        
        # Добавляем значения ATR% для каждого таймфрейма
        for timeframe in TIMEFRAMES:
            if timeframe in item["timeframes"]:
                row[f"ATR {timeframe} (%)"] = item["timeframes"][timeframe]["atr_percent"]
                row[f"HOT {timeframe}"] = item["timeframes"][timeframe]["is_hot"]
            else:
                row[f"ATR {timeframe} (%)"] = 0.0
                row[f"HOT {timeframe}"] = False
        
        rows.append(row)
    
    # Создаем DataFrame
    df = pd.DataFrame(rows)
    return df

# Функция для условного форматирования
def apply_conditional_formatting(df: pd.DataFrame) -> pd.DataFrame.style:
    """Применение условного форматирования к DataFrame"""
    # Создаем стиль
    style = df.style
    
    # Функция для определения цвета фона ячейки
    def highlight_atr(val, column):
        if "ATR" in column and isinstance(val, (int, float)):
            if val >= ATR_THRESHOLD:
                return 'background-color: #c6efce'  # зеленый
            else:
                return 'background-color: #ffc7ce'  # красный
        return ''
    
    # Применяем форматирование к каждой ячейке
    for col in df.columns:
        if "ATR" in col:
            style = style.applymap(lambda x: highlight_atr(x, col), subset=[col])
    
    # Форматируем числовые значения
    for col in df.columns:
        if "ATR" in col:
            style = style.format({col: "{:.2f}"})
        elif col == "Цена":
            style = style.format({col: "{:.4f}"})
    
    return style

# Функция для экспорта данных в CSV
def export_to_csv(df: pd.DataFrame) -> str:
    """Экспорт данных в CSV файл"""
    # Создаем временную метку для имени файла
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"binance_atr_{timestamp}.csv"
    
    # Создаем копию DataFrame для экспорта
    export_df = df.copy()
    
    # Добавляем колонки с цветовыми метками
    for timeframe in TIMEFRAMES:
        col_name = f"ATR {timeframe} (%)"
        if col_name in export_df.columns:
            export_df[f"Метка {timeframe}"] = export_df.apply(
                lambda row: "HOT" if row[col_name] >= ATR_THRESHOLD else "OK", 
                axis=1
            )
    
    # Преобразуем DataFrame в CSV
    csv_buffer = io.StringIO()
    export_df.to_csv(csv_buffer, index=False)
    
    return csv_buffer.getvalue(), filename

# Функция для форматирования времени последнего обновления
def format_last_update_time(last_update_iso: Optional[str]) -> str:
    """Форматирование времени последнего обновления для отображения"""
    if not last_update_iso:
        return "Нет данных"
    
    try:
        # Преобразуем ISO строку в datetime объект
        last_update = datetime.datetime.fromisoformat(last_update_iso)
        
        # Форматируем время
        formatted_time = last_update.strftime("%Y-%m-%d %H:%M:%S")
        
        # Вычисляем, сколько времени прошло с последнего обновления
        now = datetime.datetime.now()
        time_diff = now - last_update
        
        # Форматируем разницу во времени
        if time_diff.days > 0:
            time_ago = f"{time_diff.days} дней назад"
        elif time_diff.seconds >= 3600:
            hours = time_diff.seconds // 3600
            time_ago = f"{hours} часов назад"
        elif time_diff.seconds >= 60:
            minutes = time_diff.seconds // 60
            time_ago = f"{minutes} минут назад"
        else:
            time_ago = f"{time_diff.seconds} секунд назад"
        
        return f"{formatted_time} ({time_ago})"
    except Exception as e:
        return f"Ошибка форматирования времени: {str(e)}"

# Основная функция приложения
def main():
    # Заголовок приложения
    st.title("📊 Binance Futures ATR Monitor (WebSocket)")
    
    # Информация о WebSocket
    st.info("Это обновленная версия приложения, использующая базу данных PostgreSQL для хранения и получения данных ATR.")
    
    # Боковая панель с настройками
    with st.sidebar:
        st.header("Настройки")
        
        # Опция для выбора всех символов или ограниченного количества
        show_all_symbols = st.checkbox("Показать все доступные символы", value=True)
        
        # Выбор количества символов для отображения (если не выбраны все)
        symbols_limit = None
        if not show_all_symbols:
            symbols_limit = st.slider(
                "Количество символов", 
                min_value=5, 
                max_value=100, 
                value=30, 
                step=5
            )
        
        # Кнопка обновления данных в базе
        if st.button("Обновить данные в базе"):
            st.session_state.force_update_db = True
        
        # Кнопка обновления отображения
        if st.button("Обновить отображение"):
            st.session_state.force_refresh = True
    
    # Инициализация состояния сессии
    if 'last_update' not in st.session_state:
        st.session_state.last_update = 0
    if 'force_refresh' not in st.session_state:
        st.session_state.force_refresh = False
    if 'force_update_db' not in st.session_state:
        st.session_state.force_update_db = False
    
    # Проверка необходимости обновления базы данных
    if st.session_state.force_update_db:
        st.info("Запуск обновления базы данных...")
        
        # Запускаем обновление базы данных
        success = trigger_database_update(symbols_limit)
        
        if success:
            st.success("Обновление базы данных запущено успешно. Это может занять некоторое время.")
        else:
            st.error("Ошибка при запуске обновления базы данных.")
        
        # Сбрасываем флаг
        st.session_state.force_update_db = False
        
        # Устанавливаем флаг для обновления отображения через некоторое время
        st.session_state.force_refresh = True
    
    # Получаем время последнего обновления
    last_update_iso = get_last_update_time()
    formatted_last_update = format_last_update_time(last_update_iso)
    
    # Отображаем время последнего обновления
    st.info(f"Последнее обновление базы данных: {formatted_last_update}")
    
    # Проверка необходимости обновления отображения
    current_time = time.time()
    time_since_update = current_time - st.session_state.last_update
    
    if time_since_update > REFRESH_INTERVAL or st.session_state.force_refresh:
        # Предупреждение о возможной задержке при загрузке всех символов
        if show_all_symbols:
            st.warning("Загрузка всех символов может занять некоторое время. Пожалуйста, подождите...")
        
        # Получаем данные ATR из базы данных с отображением прогресса
        atr_data = get_all_symbols_atr(symbols_limit)
            
        if atr_data:
            # Создаем DataFrame
            df = create_atr_dataframe(atr_data)
            
            # Сохраняем данные в состоянии сессии
            st.session_state.df = df
            st.session_state.last_update = current_time
            st.session_state.force_refresh = False
    
    # Отображаем таблицу с данными, если они есть
    if 'df' in st.session_state and not st.session_state.df.empty:
        # Показываем количество отображаемых символов
        st.success(f"Отображается {len(st.session_state.df)} символов")
        
        # Применяем условное форматирование
        styled_df = apply_conditional_formatting(st.session_state.df)
        
        # Отображаем таблицу
        st.dataframe(styled_df, use_container_width=True)
        
        # Кнопка экспорта в CSV
        if st.button("Export to CSV"):
            csv_data, filename = export_to_csv(st.session_state.df)
            
            # Создаем кнопку для скачивания
            st.download_button(
                label="Скачать CSV",
                data=csv_data,
                file_name=filename,
                mime="text/csv"
            )
    else:
        st.warning("Нет данных для отображения. Нажмите 'Обновить отображение' или 'Обновить данные в базе'.")
    
    # Добавляем информацию о пороговом значении
    st.markdown(f"""
    ### Информация о цветовой маркировке:
    - 🟢 **Зеленый**: ATR% ≥ {ATR_THRESHOLD}% (HOT)
    - 🔴 **Красный**: ATR% < {ATR_THRESHOLD}% (OK)
    """)
    
    # Добавляем информацию о новой архитектуре
    st.markdown("""
    ### О новой архитектуре
    Это приложение использует базу данных PostgreSQL для хранения и получения данных ATR:
    - Данные рассчитываются и сохраняются в базу данных
    - Фронтенд получает данные из базы данных
    - Отображается время последнего обновления данных
    - Обновление данных происходит по запросу пользователя
    """)

# Запуск приложения
if __name__ == "__main__":
    main()
