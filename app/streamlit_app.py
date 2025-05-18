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

def get_all_symbols_atr(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Получение ATR для всех символов с отображением прогресса"""
    try:
        # Сначала получаем список всех символов для определения общего количества
        all_symbols = get_symbols()
        total_symbols = len(all_symbols)
        
        if total_symbols == 0:
            st.error("Не удалось получить список символов")
            return []
        
        # Создаем прогресс-бар
        progress_text = "Загрузка данных символов..."
        progress_bar = st.progress(0, text=progress_text)
        
        # Создаем всплывающее окно с информацией о прогрессе
        status_container = st.empty()
        
        # URL для запроса
        url = f"{API_BASE_URL}/all_symbols_atr"
        if limit is not None:
            url += f"?limit={limit}"
            total_symbols = min(total_symbols, limit)
        
        # Выполняем запрос с отслеживанием прогресса
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Инициализируем переменные для отслеживания прогресса
        data = []
        loaded_symbols = 0
        
        # Обрабатываем ответ построчно для отслеживания прогресса
        for line in response.iter_lines():
            if line:
                # Декодируем строку и добавляем в данные
                item = json.loads(line.decode('utf-8'))
                data.append(item)
                
                # Обновляем прогресс
                loaded_symbols += 1
                progress = min(loaded_symbols / total_symbols, 1.0)
                
                # Обновляем прогресс-бар и всплывающее окно
                progress_bar.progress(progress, text=f"{progress_text} ({loaded_symbols}/{total_symbols})")
                status_container.info(f"Загружено символов: {loaded_symbols} из {total_symbols} ({int(progress * 100)}%)")
                
                # Небольшая задержка для визуализации прогресса
                time.sleep(0.01)
        
        # Завершаем прогресс и очищаем всплывающее окно
        progress_bar.progress(1.0, text="Загрузка завершена!")
        time.sleep(1)  # Показываем завершенный прогресс-бар на 1 секунду
        progress_bar.empty()
        status_container.empty()
        
        # Показываем уведомление о завершении
        st.toast(f"Загрузка завершена! Загружено {loaded_symbols} символов.", icon="✅")
        
        return data
    except Exception as e:
        st.error(f"Ошибка при получении данных ATR: {str(e)}")
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

# Основная функция приложения
def main():
    # Заголовок приложения
    st.title("📊 Binance Futures ATR Monitor (WebSocket)")
    
    # Информация о WebSocket
    st.info("Это обновленная версия приложения, использующая WebSocket API Binance для получения данных в реальном времени без ограничений и банов.")
    
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
        
        # Кнопка обновления данных
        if st.button("Обновить данные"):
            st.session_state.last_update = time.time()
            st.session_state.force_refresh = True
    
    # Инициализация состояния сессии
    if 'last_update' not in st.session_state:
        st.session_state.last_update = 0
    if 'force_refresh' not in st.session_state:
        st.session_state.force_refresh = False
    
    # Проверка необходимости обновления данных
    current_time = time.time()
    time_since_update = current_time - st.session_state.last_update
    
    if time_since_update > REFRESH_INTERVAL or st.session_state.force_refresh:
        # Предупреждение о возможной задержке при загрузке всех символов
        if show_all_symbols:
            st.warning("Загрузка всех символов может занять некоторое время. Пожалуйста, подождите...")
        
        # Получаем данные ATR с отображением прогресса
        atr_data = get_all_symbols_atr(symbols_limit)
            
        if atr_data:
            # Создаем DataFrame
            df = create_atr_dataframe(atr_data)
            
            # Сохраняем данные в состоянии сессии
            st.session_state.df = df
            st.session_state.last_update = current_time
            st.session_state.force_refresh = False
    
    # Отображаем время последнего обновления
    last_update_time = datetime.datetime.fromtimestamp(st.session_state.last_update).strftime("%Y-%m-%d %H:%M:%S")
    st.info(f"Последнее обновление: {last_update_time}")
    
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
        st.warning("Нет данных для отображения. Нажмите 'Обновить данные'.")
    
    # Добавляем информацию о пороговом значении
    st.markdown(f"""
    ### Информация о цветовой маркировке:
    - 🟢 **Зеленый**: ATR% ≥ {ATR_THRESHOLD}% (HOT)
    - 🔴 **Красный**: ATR% < {ATR_THRESHOLD}% (OK)
    """)
    
    # Добавляем информацию о WebSocket
    st.markdown("""
    ### О WebSocket API
    Это приложение использует WebSocket API Binance для получения данных в реальном времени. Преимущества:
    - Нет ограничений на количество запросов
    - Нет необходимости в прокси
    - Данные обновляются автоматически
    - Более быстрая работа и меньшая нагрузка на сеть
    """)

# Запуск приложения
if __name__ == "__main__":
    main()
