#!/usr/bin/env python3
import os
import subprocess
import sys
import time


def run_bot():
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'bot.log')
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    return subprocess.Popen([sys.executable, '-u', 'orders_bot.py'], stdout=open(log_path, 'a'), stderr=subprocess.STDOUT)


def run_api():
    port = os.getenv('PORT', '3000')
    return subprocess.Popen([sys.executable, '-m', 'uvicorn', 'api:app', '--host', '0.0.0.0', '--port', port])


if __name__ == '__main__':
    print('🚀 Запуск STASHServiceDesk...')
    bot_proc = run_bot()
    api_proc = run_api()

    try:
        while True:
            if bot_proc.poll() is not None:
                print('⚠️ Бот завершился, перезапускаем...')
                bot_proc = run_bot()
            if api_proc.poll() is not None:
                print('⚠️ API завершился, перезапускаем...')
                api_proc = run_api()
            time.sleep(10)
    except KeyboardInterrupt:
        bot_proc.terminate()
        api_proc.terminate()
        bot_proc.wait(timeout=5)
        api_proc.wait(timeout=5)
