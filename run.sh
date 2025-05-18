#!/bin/bash

# Скрипт для запуска приложения Binance ATR Monitor с WebSocket

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Запуск Binance Futures ATR Monitor (WebSocket)${NC}"

# Проверяем наличие необходимых пакетов
echo -e "${GREEN}Проверка зависимостей...${NC}"
pip install -r app/requirements.txt

# Запускаем FastAPI сервер в фоновом режиме с явным указанием порта 8008
echo -e "${GREEN}Запуск FastAPI сервера на порту 8008...${NC}"
cd "$(dirname "$0")"
python -m uvicorn app.api.endpoints:app --host 0.0.0.0 --port 8008 &
FASTAPI_PID=$!

# Ждем запуска сервера
echo -e "${YELLOW}Ожидание запуска сервера...${NC}"
sleep 3

# Запускаем Streamlit на порту 8005
echo -e "${GREEN}Запуск Streamlit интерфейса на порту 8005...${NC}"
streamlit run app/streamlit_app.py --server.port=8005

# При завершении работы Streamlit, останавливаем FastAPI сервер
echo -e "${YELLOW}Завершение работы...${NC}"
kill $FASTAPI_PID

echo -e "${GREEN}Готово!${NC}"
