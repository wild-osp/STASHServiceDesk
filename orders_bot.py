#!/usr/bin/env python3
"""
STASHServiceDesk Orders Bot
Основной бот для обработки заказов
"""

import logging
import os
import sys
from datetime import datetime

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from database import get_db
from order_parser import OrderParser
from models import Order

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден в переменных окружения!")
    sys.exit(1)

# Инициализация компонентов
db = get_db()
parser = OrderParser()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик всех сообщений в группе
    """
    message = update.effective_message
    chat = update.effective_chat
    
    if not message:
        return
    
    # Только группы и супергруппы
    if chat.type not in ['group', 'supergroup']:
        return
    
    # Получаем текст сообщения
    text = message.text or message.caption or ""
    
    if not text:
        return
    
    # Проверяем, является ли сообщение заказом
    if not parser.is_order_message(text):
        logger.info(f"⏭️ Пропущено (не заказ): {text[:50]}...")
        return
    
    logger.info("=" * 80)
    logger.info("📦 ОБНАРУЖЕН ЗАКАЗ")
    logger.info(f"🆔 Chat ID: {chat.id}")
    logger.info(f"📌 Группа: {chat.title or 'Без названия'}")
    logger.info(f"🔢 Message ID: {message.message_id}")
    logger.info("-" * 40)
    
    # Парсим заказ
    order = parser.parse(text)
    
    if not order:
        logger.warning("❌ Не удалось распарсить заказ")
        logger.info(f"📄 Текст:\n{text}")
        logger.info("=" * 80)
        return
    
    # Добавляем Telegram-данные
    order.telegram_chat_id = str(chat.id)
    order.telegram_message_id = message.message_id
    order.telegram_message_date = datetime.fromtimestamp(message.date.timestamp()).isoformat()
    order.raw_message_text = text
    
    # Сохраняем в БД
    try:
        order_id = db.save_order(order)
        
        logger.info(f"✅ Заказ #{order.order_number} обработан (ID: {order_id})")
        logger.info(f"  Статус: {order.status}")
        logger.info(f"  Клиент: {order.client_name}")
        logger.info(f"  Устройство: {order.device}")
        
        # Получаем статистику
        stats = db.get_statistics()
        logger.info(f"📊 Всего заказов: {stats['total']}, сегодня: {stats['today']}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении заказа: {e}")
    
    logger.info("=" * 80)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /start
    """
    user = update.effective_user
    chat = update.effective_chat
    
    logger.info(f"📨 Команда /start от {user.full_name} (ID: {user.id}) в чате {chat.id}")
    
    # Получаем статистику
    stats = db.get_statistics()
    
    await update.message.reply_text(
        "🤖 STASHServiceDesk Orders Bot\n"
        "📦 Система учета заказов\n\n"
        f"📊 Всего заказов: {stats['total']}\n"
        f"📅 Сегодня: {stats['today']}\n\n"
        "📌 Доступные команды:\n"
        "/status <номер> - Информация о заказе\n"
        "/search <текст> - Поиск заказов\n"
        "/stats - Статистика"
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /status - информация о заказе по номеру
    Использование: /status 043906
    """
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите номер заказа.\n"
            "Использование: /status <номер_заказа>\n"
            "Например: /status 043906"
        )
        return
    
    order_number = context.args[0].strip()
    
    # Ищем заказ
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE order_number = ?', (order_number,))
        order = cursor.fetchone()
        
        if not order:
            await update.message.reply_text(f"❌ Заказ #{order_number} не найден")
            return
        
        # Получаем историю статусов
        cursor.execute('''
            SELECT * FROM order_history 
            WHERE order_id = ? 
            ORDER BY changed_at DESC
        ''', (order['id'],))
        history = cursor.fetchall()
    
    # Формируем ответ
    response = f"📋 ИНФОРМАЦИЯ О ЗАКАЗЕ #{order_number}\n\n"
    response += f"📌 Статус: {order['status']}\n"
    response += f"👤 Клиент: {order['client_name']}\n"
    response += f"📱 Телефон: {order['phone']}\n"
    response += f"🖥️ Устройство: {order['device']}\n"
    response += f"👨‍💼 Приёмщик: {order['receiver']}\n"
    response += f"📅 Дата: {order['date']}\n"
    
    if order['problem']:
        response += f"\n🔧 Неисправность:\n{order['problem']}\n"
    
    # История статусов
    if history:
        response += "\n📜 История статусов:\n"
        for record in history:
            changed_at = record['changed_at'][:16]  # YYYY-MM-DD HH:MM
            response += f"  • {changed_at} - {record['status']}\n"
    
    await update.message.reply_text(response)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /search - поиск заказов
    Использование: /search текст
    """
    if not context.args:
        await update.message.reply_text(
            "🔍 Использование: /search <текст>\n"
            "Поиск по номеру, телефону, ФИО, устройству или неисправности\n"
            "Например: /search Xiaomi"
        )
        return
    
    query = ' '.join(context.args)
    results = db.search_orders(query)
    
    if not results:
        await update.message.reply_text(f"❌ По запросу '{query}' ничего не найдено")
        return
    
    # Формируем ответ
    response = f"🔍 Результаты поиска по '{query}':\n\n"
    for order in results[:10]:  # Показываем первые 10
        response += f"📌 #{order['order_number']} - {order['status']}\n"
        response += f"   Клиент: {order['client_name']}\n"
        response += f"   Устройство: {order['device']}\n\n"
    
    if len(results) > 10:
        response += f"... и еще {len(results) - 10} результатов"
    
    await update.message.reply_text(response)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /stats - статистика
    """
    stats = db.get_statistics()
    
    response = "📊 СТАТИСТИКА ЗАКАЗОВ\n\n"
    response += f"📦 Всего заказов: {stats['total']}\n"
    response += f"📅 Сегодня: {stats['today']}\n\n"
    response += "📌 По статусам:\n"
    
    if stats['by_status']:
        for status in stats['by_status']:
            response += f"  • {status['status']}: {status['count']}\n"
    else:
        response += "  • Нет заказов\n"
    
    await update.message.reply_text(response)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /help - помощь
    """
    await update.message.reply_text(
        "📚 ДОСТУПНЫЕ КОМАНДЫ\n\n"
        "/start - Главное меню\n"
        "/status <номер> - Информация о заказе\n"
        "/search <текст> - Поиск заказов\n"
        "/stats - Статистика\n"
        "/help - Помощь\n\n"
        "📌 Примеры:\n"
        "/status 043906\n"
        "/search Xiaomi\n"
        "/search Новицкий"
    )


def main():
    """
    Основная функция запуска бота
    """
    try:
        logger.info("=" * 60)
        logger.info("🚀 ЗАПУСК STASHServiceDesk Orders Bot")
        logger.info(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        # Инициализация БД
        logger.info("📂 Инициализация базы данных...")
        db.init_database()
        
        # Создание приложения
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавление обработчиков команд
        application.add_handler(MessageHandler(filters.COMMAND & filters.Regex('^/start$'), start_command))
        application.add_handler(MessageHandler(filters.COMMAND & filters.Regex('^/status$'), status_command))
        application.add_handler(MessageHandler(filters.COMMAND & filters.Regex('^/search$'), search_command))
        application.add_handler(MessageHandler(filters.COMMAND & filters.Regex('^/stats$'), stats_command))
        application.add_handler(MessageHandler(filters.COMMAND & filters.Regex('^/help$'), help_command))
        
        # Обработчик всех остальных сообщений
        application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
        
        logger.info("✅ Бот успешно инициализирован")
        logger.info("📡 Начинаю прослушивание сообщений...")
        logger.info("📌 Доступные команды: /start, /status, /search, /stats, /help")
        logger.info("=" * 60)
        
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
