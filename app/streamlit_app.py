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

# Импортируем модуль главной страницы
try:
    from pages.home_page import render_home_page
except ImportError:
    st.error("Не удалось импортировать модуль главной страницы")

# Настройка страницы Streamlit
st.set_page_config(
    page_title="Ultimate Crypto Analytics",
    page_icon="📊",
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
    # Отображаем только главную страницу
    render_home_page()

# Запуск приложения
if __name__ == "__main__":
    main()
