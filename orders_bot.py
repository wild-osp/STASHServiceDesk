#!/usr/bin/env python3
"""
STASHServiceDesk Orders Bot
Этап 1: Логирование сообщений из Telegram-группы
"""

import logging
import os
import sys
from datetime import datetime

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация - токен берется из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден в переменных окружения!")
    logger.error("Пожалуйста, установите переменную окружения BOT_TOKEN")
    sys.exit(1)


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
        logger.debug(f"Пропущено сообщение из чата типа: {chat.type}")
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
    else:
        # Логируем другие типы сообщений
        logger.info(f"📨 Получено сообщение типа: {message.effective_attachment}")
        text = f"[Сообщение типа: {type(message).__name__}]"
    
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
        logger.info("📄 Текст сообщения отсутствует")
    
    logger.info("=" * 80)
    
    # Дополнительное логирование для отладки (если нужно)
    # logger.debug(f"Полный объект message: {message.to_dict()}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /start для активации бота в группе
    """
    await update.message.reply_text(
        "🤖 Бот STASHServiceDesk Orders Bot запущен!\n"
        "Я буду логировать все сообщения в этой группе.\n"
        "Для проверки работы отправьте любое сообщение."
    )
    logger.info(f"📨 Получена команда /start от пользователя {update.effective_user.full_name}")


def main():
    """
    Основная функция запуска бота
    """
    try:
        logger.info("=" * 60)
        logger.info("🚀 ЗАПУСК STASHServiceDesk Orders Bot")
        logger.info(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"🤖 Токен: {BOT_TOKEN[:15]}...{BOT_TOKEN[-5:]}")
        logger.info("=" * 60)
        
        # Создание приложения
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавление обработчиков
        # 1. Обработчик команды /start
        application.add_handler(MessageHandler(filters.COMMAND & filters.Regex('^/start$'), start_command))
        
        # 2. Обработчик для всех сообщений (кроме команд)
        message_handler = MessageHandler(
            filters.ALL & ~filters.COMMAND,
            handle_message
        )
        application.add_handler(message_handler)
        
        logger.info("✅ Бот успешно инициализирован")
        logger.info("📡 Начинаю прослушивание сообщений...")
        logger.info("💡 Убедитесь, что бот имеет права администратора в группе")
        logger.info("💡 Для активации отправьте /start в группе")
        logger.info("=" * 60)
        
        # Запуск бота
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
