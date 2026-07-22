#!/usr/bin/env python3
"""
STASHServiceDesk Orders Bot
Этап 1: Логирование сообщений из Telegram-группы
"""

import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден в переменных окружения!")
    sys.exit(1)

# Разрешенные типы сообщений для логирования
ALLOWED_CONTENT_TYPES = [
    'text',
    'photo',
    'document',
    'voice',
    'video',
    'audio',
    'animation',
]


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик всех сообщений в группе
    """
    message = update.effective_message
    chat = update.effective_chat
    
    if not message:
        return
    
    # Логирование только сообщений из групп/супергрупп
    if chat.type not in ['group', 'supergroup']:
        return
    
    # Получение информации об отправителе
    sender_name = "Неизвестно"
    sender_username = "Нет username"
    
    if message.from_user:
        if message.from_user.full_name:
            sender_name = message.from_user.full_name
        if message.from_user.username:
            sender_username = f"@{message.from_user.username}"
    
    # Формирование данных для логирования
    log_data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'chat_id': chat.id,
        'chat_title': chat.title or "Без названия",
        'message_id': message.message_id,
        'sender_name': sender_name,
        'sender_username': sender_username,
        'message_type': 'text' if message.text else 'media',
        'message_date': datetime.fromtimestamp(message.date.timestamp()).strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    # Получение текста сообщения
    text = ""
    if message.text:
        text = message.text
    elif message.caption:
        text = message.caption
    elif message.document:
        text = f"[Документ: {message.document.file_name}]"
    elif message.photo:
        text = f"[Фото: {len(message.photo)} изображений]"
    
    # Вывод в лог
    logger.info("=" * 80)
    logger.info("📨 НОВОЕ СООБЩЕНИЕ ИЗ ГРУППЫ")
    logger.info(f"📅 Время получения: {log_data['timestamp']}")
    logger.info(f"🆔 Chat ID: {log_data['chat_id']}")
    logger.info(f"📌 Название группы: {log_data['chat_title']}")
    logger.info(f"🔢 Message ID: {log_data['message_id']}")
    logger.info(f"👤 Отправитель: {log_data['sender_name']}")
    logger.info(f"👤 Username: {log_data['sender_username']}")
    logger.info(f"📅 Дата сообщения: {log_data['message_date']}")
    logger.info(f"📝 Тип: {log_data['message_type']}")
    logger.info("-" * 80)
    
    if text:
        logger.info("📄 Текст сообщения:")
        logger.info(text)
    else:
        logger.info("📄 Текст сообщения отсутствует или это медиа-файл")
    
    logger.info("=" * 80)
    
    # Дополнительное логирование для отладки
    logger.debug(f"Полный объект message: {message}")


def main():
    """
    Основная функция запуска бота
    """
    try:
        logger.info("🚀 Запуск STASHServiceDesk Orders Bot (Этап 1)")
        logger.info(f"🤖 Используется токен: {BOT_TOKEN[:10]}...")
        
        # Создание приложения
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавление обработчика для всех сообщений
        message_handler = MessageHandler(
            filters.ALL & ~filters.COMMAND,
            handle_message
        )
        application.add_handler(message_handler)
        
        logger.info("✅ Бот успешно инициализирован")
        logger.info("📡 Начинаю прослушивание сообщений...")
        
        # Запуск бота
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
