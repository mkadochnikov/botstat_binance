import uvicorn
import sys
import os

# Добавляем родительскую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.endpoints import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8008)  # Изменен порт на 8008
