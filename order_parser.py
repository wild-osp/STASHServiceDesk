#!/usr/bin/env python3
"""
STASHServiceDesk Orders Bot
С поддержкой синхронизации БД с GitHub
"""

import logging
import os
import sys
from datetime import datetime

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

from database import get_db
from order_parser import OrderParser
from models import Order
from db_sync import db_sync

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
    """Обработчик всех сообщений в группе"""
    message = update.effective_message
    chat = update.effective_chat
    
    if not message or chat.type not in ['group', 'supergroup']:
        return
    
    text = message.text or message.caption or ""
    if not text or not parser.is_order_message(text):
        return
    
    logger.info("=" * 80)
    logger.info("📦 ОБНАРУЖЕН ЗАКАЗ")
    logger.info(f"🆔 Chat ID: {chat.id}")
    logger.info(f"📌 Группа: {chat.title or 'Без названия'}")
    logger.info(f"🔢 Message ID: {message.message_id}")
    logger.info("-" * 40)
    
    order = parser.parse(text)
    if not order:
        logger.warning("❌ Не удалось распарсить заказ")
        return
    
    order.telegram_chat_id = str(chat.id)
    order.telegram_message_id = message.message_id
    order.telegram_message_date = datetime.fromtimestamp(message.date.timestamp()).isoformat()
    order.raw_message_text = text
    
    try:
        order_id = db.save_order(order)
        logger.info(f"✅ Заказ #{order.order_number} обработан (ID: {order_id})")
        logger.info(f"  Статус: {order.status}")
        logger.info(f"  Клиент: {order.client_name}")
        logger.info(f"  Устройство: {order.device}")
        
        stats = db.get_statistics()
        logger.info(f"📊 Всего заказов: {stats['total']}, сегодня: {stats['today']}")
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении заказа: {e}")
    
    logger.info("=" * 80)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
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
    """Обработчик команды /status"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите номер заказа.\n"
            "Использование: /status <номер_заказа>"
        )
        return
    
    order_number = context.args[0].strip()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE order_number = ?', (order_number,))
        order = cursor.fetchone()
        
        if not order:
            await update.message.reply_text(f"❌ Заказ #{order_number} не найден")
            return
        
        cursor.execute('''
            SELECT * FROM order_history 
            WHERE order_id = ? 
            ORDER BY changed_at DESC
        ''', (order['id'],))
        history = cursor.fetchall()
    
    response = f"📋 ИНФОРМАЦИЯ О ЗАКАЗЕ #{order_number}\n\n"
    response += f"📌 Статус: {order['status']}\n"
    response += f"👤 Клиент: {order['client_name']}\n"
    response += f"📱 Телефон: {order['phone']}\n"
    response += f"🖥️ Устройство: {order['device']}\n"
    response += f"👨‍💼 Приёмщик: {order['receiver']}\n"
    response += f"📅 Дата: {order['date']}\n"
    
    if order['problem']:
        response += f"\n🔧 Неисправность:\n{order['problem']}\n"
    
    if history:
        response += "\n📜 История статусов:\n"
        for record in history:
            changed_at = record['changed_at'][:16]
            response += f"  • {changed_at} - {record['status']}\n"
    
    await update.message.reply_text(response)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /search"""
    if not context.args:
        await update.message.reply_text(
            "🔍 Использование: /search <текст>\n"
            "Поиск по номеру, телефону, ФИО, устройству или неисправности"
        )
        return
    
    query = ' '.join(context.args)
    results = db.search_orders(query)
    
    if not results:
        await update.message.reply_text(f"❌ По запросу '{query}' ничего не найдено")
        return
    
    response = f"🔍 Результаты поиска по '{query}':\n\n"
    for order in results[:10]:
        response += f"📌 #{order['order_number']} - {order['status']}\n"
        response += f"   Клиент: {order['client_name']}\n"
        response += f"   Устройство: {order['device']}\n\n"
    
    if len(results) > 10:
        response += f"... и еще {len(results) - 10} результатов"
    
    await update.message.reply_text(response)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /stats"""
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
    """Обработчик команды /help"""
    await update.message.reply_text(
        "📚 ДОСТУПНЫЕ КОМАНДЫ\n\n"
        "/start - Главное меню\n"
        "/status <номер> - Информация о заказе\n"
        "/search <текст> - Поиск заказов\n"
        "/stats - Статистика\n"
        "/help - Помощь"
    )


async def sync_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /sync - принудительная синхронизация с GitHub"""
    await update.message.reply_text("🔄 Синхронизация с GitHub...")
    
    success = db_sync.push_to_github("Manual sync from bot")
    
    if success:
        await update.message.reply_text("✅ База данных синхронизирована с GitHub")
    else:
        await update.message.reply_text("❌ Ошибка синхронизации с GitHub")


def main():
    try:
        logger.info("=" * 60)
        logger.info("🚀 ЗАПУСК STASHServiceDesk Orders Bot")
        logger.info(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        # ⚡ СИНХРОНИЗАЦИЯ С GITHUB ПРИ ЗАПУСКЕ
        logger.info("🔄 Загрузка базы данных из GitHub...")
        db_sync.sync_on_startup()
        
        # Инициализация БД
        db.init_database()
        
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Команды
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("search", search_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("sync", sync_command))
        
        # Обработчик сообщений
        application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
        
        logger.info("✅ Бот успешно инициализирован")
        logger.info("📡 Начинаю прослушивание сообщений...")
        logger.info("📌 Команды: /start, /status, /search, /stats, /help, /sync")
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
