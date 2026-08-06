#!/bin/bash
set -euo pipefail

echo "🚀 Запуск STASHServiceDesk..."
PORT="${PORT:-3000}"

python -u orders_bot.py > /tmp/stash_orders_bot.log 2>&1 &
BOT_PID=$!
echo "🤖 Бот запущен (PID $BOT_PID)"

cleanup() {
    echo "🛑 Остановка сервисов..."
    kill "$BOT_PID" 2>/dev/null || true
    wait "$BOT_PID" 2>/dev/null || true
}
trap cleanup EXIT

exec python -m uvicorn api:app --host 0.0.0.0 --port "$PORT"
