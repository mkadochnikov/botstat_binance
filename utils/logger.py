import logging
import sys
import time
from datetime import datetime
from typing import Dict, Any

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger("atr_logger")

class ATRLogger:
    """Логгер для ATR расчетов с цветным форматированием"""
    
    def __init__(self):
        self.logger = logger
    
    def log_info(self, message: str):
        """Логирование информационного сообщения"""
        self.logger.info(message)
    
    def log_error(self, message: str):
        """Логирование ошибки"""
        self.logger.error(message)
    
    def log_symbol_results(self, symbol: str, results: Dict[str, Any]):
        """Логирование результатов расчета ATR для символа"""
        self.logger.info(f"Processing {symbol} via WebSocket:")
        
        for timeframe, data in results.get("timeframes", {}).items():
            atr_percent = data.get("atr_percent", 0)
            is_hot = atr_percent >= 0.15
            
            # Маркируем значения
            marker = "HOT" if is_hot else "OK"
            
            self.logger.info(f"  {timeframe} ATR {atr_percent:.2f}%...{marker}")

# Создаем синглтон логгера
atr_logger = ATRLogger()
