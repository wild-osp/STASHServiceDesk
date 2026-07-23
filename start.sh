#!/bin/bash
echo "🚀 Запуск STASHServiceDesk..."

# Запуск бота в фоне
python orders_bot.py &

# Запуск API
uvicorn api:app --host 0.0.0.0 --port 3000

# Ожидание завершения процессов
wait
