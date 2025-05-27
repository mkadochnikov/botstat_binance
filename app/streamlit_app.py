import streamlit as st
import pandas as pd
import requests
import time
import datetime
import os
import sys
import json
from typing import List, Dict, Any, Optional

# Добавляем родительскую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем модули страниц
try:
    from app.pages.home_page import render_home_page
    from app.pages.futures_charts import render_futures_charts_page
except ImportError as e:
    st.error(f"Не удалось импортировать модули страниц: {str(e)}")

# Настройка страницы Streamlit
st.set_page_config(
    page_title="Ultimate Crypto Analytics",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Скрываем меню и футер Streamlit
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Фиксируем боковое меню при прокрутке
fixed_sidebar_style = """
<style>
    .sidebar .sidebar-content {
        position: fixed;
        width: inherit;
    }
</style>
"""
st.markdown(fixed_sidebar_style, unsafe_allow_html=True)

# Основная функция приложения
def main():
    # Создаем боковую панель для навигации
    with st.sidebar:
        st.title("Crypto Analytics")
        
        # Выбор страницы
        page = st.radio(
            "Выберите страницу:",
            ["Главная", "Графики фьючерсов"]
        )
    
    # Отображаем выбранную страницу
    if page == "Главная":
        render_home_page()
    elif page == "Графики фьючерсов":
        render_futures_charts_page()

# Запуск приложения
if __name__ == "__main__":
    main()
