#!/usr/bin/env python3
"""
Модуль-заглушка для синхронизации с GitHub.
Синхронизация отключена - все данные хранятся только локально.
"""

import logging

logger = logging.getLogger(__name__)


class DBSync:
    """
    Класс-заглушка для синхронизации БД с GitHub.
    Все методы ничего не делают.
    """
    
    def __init__(self, db_path=None):
        self.db_path = db_path
        logger.info("ℹ️ Синхронизация с GitHub ОТКЛЮЧЕНА (заглушка)")
    
    def pull_from_github(self):
        """Заглушка - ничего не делает"""
        logger.info("ℹ️ Загрузка из GitHub пропущена (синхронизация отключена)")
        return True
    
    def push_to_github(self, commit_message=None):
        """Заглушка - ничего не делает"""
        logger.info("ℹ️ Сохранение в GitHub пропущено (синхронизация отключена)")
        return True
    
    def sync_on_startup(self):
        """Заглушка - ничего не делает"""
        logger.info("ℹ️ Синхронизация при старте пропущена (синхронизация отключена)")
        return True
    
    def sync_on_change(self, order_number=None):
        """Заглушка - ничего не делает"""
        logger.info(f"ℹ️ Синхронизация при изменении заказа #{order_number} пропущена (синхронизация отключена)")
        return True


# Создаем глобальный экземпляр-заглушку
db_sync = DBSync()
