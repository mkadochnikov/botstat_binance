#!/bin/bash

# Пути и параметры ( настройте под свой проект )
FASTAPI_DIR="/app"
STREAMLIT_DIR="/app"
FASTAPI_PORT=8008
STREAMLIT_PORT=8005

# Функция для перезапуска FastAPI
restart_fastapi() {
    echo "Останавливаю FastAPI..."
    pkill -f "uvicorn main:app --host 0.0.0.0 --port $FASTAPI_PORT"

    echo "Запускаю FastAPI..."
    cd "$FASTAPI_DIR" || exit
    nohup uvicorn main:app --host 0.0.0.0 --port $FASTAPI_PORT > fastapi.log 2>&1 &
    echo "FastAPI запущен на порту $FASTAPI_PORT"
}

# Функция для перезапуска Streamlit
restart_streamlit() {
    echo "Останавливаю Streamlit..."
    pkill -f "streamlit run app.py --server.port $STREAMLIT_PORT"

    echo "Запускаю Streamlit..."
    cd "$STREAMLIT_DIR" || exit
    nohup streamlit run app.py --server.port $STREAMLIT_PORT > streamlit.log 2>&1 &
    echo "Streamlit запущен на порту $STREAMLIT_PORT"
}

# Основной скрипт
echo "=== Перезапуск приложений ==="
restart_fastapi
restart_streamlit
echo "============================"
echo "Готово! Проверьте логи:"
echo "FastAPI: $FASTAPI_DIR/fastapi.log"
echo "Streamlit: $STREAMLIT_DIR/streamlit.log"