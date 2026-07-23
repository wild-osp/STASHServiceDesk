#!/usr/bin/env python3
import subprocess
import time
import threading
import os

def run_bot():
    time.sleep(2)
    subprocess.Popen(["python", "orders_bot.py"])

def run_api():
    subprocess.Popen(["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "3000"])

if __name__ == "__main__":
    print("🚀 Запуск STASHServiceDesk...")
    
    # Запускаем бота в потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем API
    run_api()
    
    # Держим процесс живым
    while True:
        time.sleep(60)
