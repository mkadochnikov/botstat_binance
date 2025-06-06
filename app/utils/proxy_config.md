# Настройки прокси для Binance API

Для обхода ограничений и банов API Binance, вы можете добавить свои прокси-серверы в этот файл.

## Формат прокси

Добавьте ваши прокси в список PROXY_LIST в файле binance_client.py в следующем формате:

```python
PROXY_LIST = [
    "http://username:password@host:port",  # Прокси с аутентификацией
    "http://host:port",                    # Прокси без аутентификации
    "https://host:port",                   # HTTPS прокси
]
```

## Примеры

```python
PROXY_LIST = [
    "http://user:pass@proxy1.example.com:8080",
    "http://192.168.1.1:3128",
    "https://secure-proxy.example.com:443",
]
```

## Рекомендации

1. Используйте ротацию прокси для распределения нагрузки
2. Предпочтительно использовать прокси с высокой скоростью и стабильностью
3. Убедитесь, что ваши прокси разрешают доступ к домену binance.com
4. Для лучшей производительности используйте прокси, географически близкие к серверам Binance

## Настройка задержек

Если вы продолжаете получать ошибки ограничения запросов, вы можете увеличить задержки между запросами, изменив следующие параметры в файле binance_client.py:

```python
MIN_REQUEST_INTERVAL = 0.5  # минимальный интервал между запросами (секунды)
MAX_REQUEST_INTERVAL = 2.0  # максимальный интервал между запросами (секунды)
```

Увеличение этих значений снизит частоту запросов к API.
