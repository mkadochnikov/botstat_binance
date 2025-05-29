"""
Модуль для интеграции функций чтения данных из PostgreSQL в основное приложение.
Заменяет прямые вызовы API на чтение из базы данных.
"""
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
    from app.pages.trade_sessions import render_trade_sessions_page
except ImportError:
    st.error("Не удалось импортировать модули страниц")

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

# Основная функция приложения
def main():
    # Добавляем меню для переключения между страницами
    page = st.sidebar.radio(
        "Выберите страницу:",
        ["Индексы", "Торговые сессии"],
        index=0,  # По умолчанию выбрана первая страница
        key="page_selection"
    )
    
    # Отображаем выбранную страницу
    if page == "Индексы":
        render_home_page()
    elif page == "Торговые сессии":
        render_trade_sessions_page()

# Запуск приложения
if __name__ == "__main__":
    main()
