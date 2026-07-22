#!/usr/bin/env python3
"""
Модуль для синхронизации базы данных с GitHub
"""

import os
import shutil
import subprocess
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DBSync:
    """Класс для синхронизации БД с GitHub"""
    
    def __init__(self, db_path='orders.db'):
        self.db_path = db_path
        self.backup_path = f'{db_path}.backup'
        
    def pull_from_github(self):
        """
        Загружает БД из GitHub перед запуском
        """
        try:
            # Проверяем, есть ли файл в репозитории
            if os.path.exists(self.db_path):
                # Создаем бэкап существующего файла (на случай ошибки)
                if os.path.exists(self.db_path):
                    shutil.copy2(self.db_path, self.backup_path)
                    logger.info(f"📋 Создан бэкап БД: {self.backup_path}")
            
            # Пытаемся получить файл из GitHub
            result = subprocess.run(
                ['git', 'checkout', '--', self.db_path],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            if result.returncode == 0:
                if os.path.exists(self.db_path):
                    logger.info(f"✅ БД загружена из GitHub: {self.db_path}")
                    return True
                else:
                    logger.warning(f"⚠️ Файл {self.db_path} не найден в репозитории")
                    return False
            else:
                logger.warning(f"⚠️ Не удалось загрузить БД из GitHub: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке БД: {e}")
            return False
    
    def push_to_github(self, commit_message=None):
        """
        Сохраняет БД в GitHub после изменений
        """
        try:
            # Проверяем, существует ли файл
            if not os.path.exists(self.db_path):
                logger.warning(f"⚠️ Файл {self.db_path} не найден для сохранения")
                return False
            
            # Если нет сообщения, создаем автоматическое
            if commit_message is None:
                commit_message = f"Update orders database - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Добавляем файл
            result_add = subprocess.run(
                ['git', 'add', self.db_path],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            if result_add.returncode != 0:
                logger.error(f"❌ Ошибка git add: {result_add.stderr}")
                return False
            
            # Коммитим
            result_commit = subprocess.run(
                ['git', 'commit', '-m', commit_message],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            if result_commit.returncode != 0:
                if "nothing to commit" in result_commit.stderr:
                    logger.info("ℹ️ Нет изменений для сохранения")
                    return True
                else:
                    logger.error(f"❌ Ошибка git commit: {result_commit.stderr}")
                    return False
            
            # Отправляем на GitHub
            result_push = subprocess.run(
                ['git', 'push', 'origin', 'main'],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            if result_push.returncode == 0:
                logger.info(f"✅ БД сохранена в GitHub: {commit_message}")
                return True
            else:
                logger.error(f"❌ Ошибка git push: {result_push.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении БД: {e}")
            return False
    
    def sync_on_startup(self):
        """
        Синхронизация при запуске бота
        """
        logger.info("🔄 Синхронизация БД с GitHub...")
        
        # Загружаем из GitHub
        success = self.pull_from_github()
        
        if not success:
            # Если файла нет, создаем новый
            if not os.path.exists(self.db_path):
                import sqlite3
                conn = sqlite3.connect(self.db_path)
                conn.close()
                logger.info(f"✅ Создан новый файл БД: {self.db_path}")
                
                # Сохраняем в GitHub
                self.push_to_github("Initial database creation")
        
        return True
    
    def sync_on_change(self, order_number=None):
        """
        Синхронизация после изменения данных
        """
        message = f"Update database - order #{order_number}" if order_number else "Update database"
        return self.push_to_github(message)


# Создаем глобальный экземпляр
db_sync = DBSync()
