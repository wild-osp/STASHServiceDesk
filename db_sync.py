#!/usr/bin/env python3
"""
Модуль для синхронизации базы данных с GitHub через API
"""

import os
import base64
import json
import requests
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DBSync:
    """Класс для синхронизации БД с GitHub через API"""
    
    def __init__(self, db_path='orders.db'):
        self.db_path = db_path
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.repo_owner = 'wild-osp'  # Ваш логин на GitHub
        self.repo_name = 'STASHServiceDesk'
        self.api_url = f'https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/contents/{self.db_path}'
        
        if not self.github_token:
            logger.warning("⚠️ GITHUB_TOKEN не найден! БД будет только локальной.")
    
    def pull_from_github(self):
        """
        Загружает БД из GitHub через API
        """
        if not self.github_token:
            logger.warning("⚠️ Пропуск загрузки: нет GITHUB_TOKEN")
            return False
        
        try:
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(self.api_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                content = base64.b64decode(data['content'])
                
                with open(self.db_path, 'wb') as f:
                    f.write(content)
                
                logger.info(f"✅ БД загружена из GitHub ({len(content)} байт)")
                
                # Проверяем, что файл не пустой
                if len(content) > 0:
                    return True
                else:
                    logger.warning("⚠️ Файл БД пустой, создаем новую")
                    return False
                    
            elif response.status_code == 404:
                logger.info("ℹ️ Файл БД не найден на GitHub, будет создан новый")
                return False
            else:
                logger.error(f"❌ Ошибка загрузки: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке БД: {e}")
            return False
    
    def push_to_github(self, commit_message=None):
        """
        Сохраняет БД в GitHub через API
        """
        if not self.github_token:
            logger.warning("⚠️ Пропуск сохранения: нет GITHUB_TOKEN")
            return False
        
        try:
            # Проверяем, существует ли файл
            if not os.path.exists(self.db_path):
                logger.warning(f"⚠️ Файл {self.db_path} не найден")
                return False
            
            # Читаем файл
            with open(self.db_path, 'rb') as f:
                content = base64.b64encode(f.read()).decode('utf-8')
            
            # Если нет сообщения, создаем автоматическое
            if commit_message is None:
                commit_message = f"Update database - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Проверяем, существует ли файл на GitHub
            response_get = requests.get(self.api_url, headers=headers)
            
            if response_get.status_code == 200:
                # Файл существует - обновляем
                sha = response_get.json()['sha']
                data = {
                    'message': commit_message,
                    'content': content,
                    'sha': sha
                }
                response = requests.put(self.api_url, headers=headers, json=data)
            else:
                # Файл не существует - создаем
                data = {
                    'message': commit_message,
                    'content': content
                }
                response = requests.put(self.api_url, headers=headers, json=data)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ БД сохранена в GitHub: {commit_message}")
                return True
            else:
                logger.error(f"❌ Ошибка сохранения: {response.status_code} - {response.text}")
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
            if not os.path.exists(self.db_path) or os.path.getsize(self.db_path) == 0:
                import sqlite3
                conn = sqlite3.connect(self.db_path)
                conn.close()
                logger.info(f"✅ Создан новый файл БД: {self.db_path}")
                
                # Сохраняем в GitHub (если есть токен)
                if self.github_token:
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
