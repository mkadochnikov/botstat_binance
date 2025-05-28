import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random

def generate_test_candlestick_data(days=30):
    """
    Генерирует тестовые OHLC-данные для свечного графика
    
    Args:
        days (int): Количество дней для генерации данных
        
    Returns:
        pd.DataFrame: DataFrame с колонками date, open, high, low, close, volume
    """
    # Создаем даты
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Начальная цена
    base_price = 50000
    
    # Генерируем случайные данные для свечей
    data = []
    current_price = base_price
    
    for date in dates:
        # Случайное изменение цены в пределах ±5%
        price_change_percent = random.uniform(-0.05, 0.05)
        price_change = current_price * price_change_percent
        
        # Определяем open, close
        if random.random() > 0.5:  # 50% шанс на бычью или медвежью свечу
            open_price = current_price
            close_price = current_price + price_change
        else:
            open_price = current_price
            close_price = current_price - price_change
        
        # Определяем high, low
        high_price = max(open_price, close_price) * (1 + random.uniform(0.005, 0.02))
        low_price = min(open_price, close_price) * (1 - random.uniform(0.005, 0.02))
        
        # Объем торгов (случайный в диапазоне)
        volume = random.uniform(1000, 10000)
        
        # Добавляем данные
        data.append({
            'date': date,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
        
        # Обновляем текущую цену для следующей итерации
        current_price = close_price
    
    return pd.DataFrame(data)

def render_candlestick_page():
    """
    Отрисовка страницы со свечным графиком
    """
    st.title("Свечной график BTC/USDT")
    
    # Генерируем тестовые данные
    df = generate_test_candlestick_data(days=30)
    
    # Создаем свечной график с помощью Plotly
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='BTC/USDT'
    )])
    
    # Добавляем объемы как гистограмму внизу
    volume_colors = ['rgba(0, 150, 136, 0.3)' if row.close >= row.open else 'rgba(255, 82, 82, 0.3)' for _, row in df.iterrows()]
    
    fig.add_trace(go.Bar(
        x=df['date'],
        y=df['volume'],
        marker_color=volume_colors,
        name='Volume',
        yaxis='y2'
    ))
    
    # Настраиваем внешний вид графика - исправлена конфигурация
    fig.update_layout(
        title='BTC/USDT - Свечной график (тестовые данные)',
        xaxis_title='Дата',
        yaxis_title='Цена (USDT)',
        height=600,  # Высота графика
        margin=dict(l=0, r=0, t=50, b=0),  # Минимальные отступы для максимальной ширины
        
        # Настройка осей
        yaxis=dict(
            domain=[0.2, 1.0],  # Основной график занимает 80% высоты
            showgrid=True,
            gridcolor='rgba(230, 230, 230, 0.3)'
        ),
        yaxis2=dict(
            domain=[0, 0.2],  # Объемы занимают 20% высоты
            showgrid=False,
            title='Объем',
            titlefont=dict(color='rgba(100, 100, 100, 0.8)')
        ),
        
        # Настройка легенды
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        
        # Настройка фона и сетки
        plot_bgcolor='rgba(250, 250, 250, 1)',
        paper_bgcolor='rgba(250, 250, 250, 1)',
        xaxis=dict(
            showgrid=True,
            gridcolor='rgba(230, 230, 230, 0.3)',
            rangeslider=dict(visible=True)  # Добавляем ползунок для навигации
        )
        
        # Удалена проблемная настройка modebar, которая вызывала ошибку
    )
    
    # Отображаем график на всю ширину контейнера
    st.plotly_chart(fig, use_container_width=True)
    
    # Добавляем информационный блок под графиком
    with st.expander("Информация о графике"):
        st.markdown("""
        **Пояснение к графику:**
        - **Свечи**: Показывают движение цены за период (день)
            - Зеленая свеча: цена закрытия выше цены открытия (рост)
            - Красная свеча: цена закрытия ниже цены открытия (падение)
        - **Объемы**: Показывают объем торгов за каждый период
        - **Ползунок**: Позволяет изменять масштаб и перемещаться по графику
        
        **Примечание**: Данные на графике являются тестовыми и сгенерированы случайным образом.
        """)
    
    # Добавляем таблицу с данными под графиком
    with st.expander("Показать данные"):
        st.dataframe(
            df.rename(
                columns={
                    'date': 'Дата',
                    'open': 'Открытие',
                    'high': 'Максимум',
                    'low': 'Минимум',
                    'close': 'Закрытие',
                    'volume': 'Объем'
                }
            ).style.format({
                'Открытие': '${:.2f}',
                'Максимум': '${:.2f}',
                'Минимум': '${:.2f}',
                'Закрытие': '${:.2f}',
                'Объем': '{:.2f}'
            }),
            use_container_width=True
        )

# Если файл запущен напрямую, отображаем страницу
if __name__ == "__main__":
    render_candlestick_page()
