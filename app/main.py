import uvicorn
import sys
import os
import logging

# Добавляем родительскую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.endpoints import app

# Настройка логирования для FastAPI
@app.on_event("startup")
async def startup_event():
    """Действия при запуске приложения"""
    # Инициализируем логгер
    from app.utils.binance_websocket_client import logger
    logger.info("FastAPI application starting, initializing WebSocket logger")
    
    # Проверяем наличие лог-файла
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_file = os.path.join(project_dir, 'binance_websocket.log')
    logger.info(f"Log file path: {log_file}")
    
    if os.path.exists(log_file):
        logger.info(f"Log file exists, size: {os.path.getsize(log_file)} bytes")
    else:
        logger.warning(f"Log file does not exist yet, will be created on first log entry")
    
    # Проверяем права на запись
    try:
        with open(log_file, 'a') as f:
            f.write("[STARTUP] FastAPI application started\n")
        logger.info("Successfully wrote to log file")
    except Exception as e:
        logger.error(f"Error writing to log file: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8008)  # Изменен порт на 8008
