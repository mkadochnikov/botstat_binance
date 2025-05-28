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
    from pages.home_page import render_home_page
    from pages.candlestick_page import render_candlestick_page
except ImportError as e:
    st.error(f"Не удалось импортировать модули страниц: {str(e)}")

# Настройка страницы Streamlit
st.set_page_config(
    page_title="Ultimate Crypto Analytics",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"  # Изменено на expanded для отображения меню
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
    # Создаем боковое меню
    with st.sidebar:
        st.title("Crypto Analytics")
        st.markdown("---")
        
        # Опции меню
        page = st.radio(
            "Выберите страницу:",
            ["Главная", "Свечной график"],
            index=0,
            key="page_selection"
        )
    
    # Отображаем выбранную страницу
    if page == "Главная":
        render_home_page()
    elif page == "Свечной график":
        render_candlestick_page()

# Запуск приложения
if __name__ == "__main__":
    main()
