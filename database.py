#!/usr/bin/env python3
"""
Модуль для работы с базой данных SQLite
Поддержка хранения в GitHub
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from models import Order, OrderHistory


class Database:
    """Класс для управления базой данных заказов"""
    
    def __init__(self, db_path: str = 'orders.db'):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Получает соединение с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Инициализирует структуру базы данных (если БД не существует)"""
        # Проверяем, существует ли файл БД
        db_exists = os.path.exists(self.db_path)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица заказов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_number TEXT UNIQUE NOT NULL,
                    date TEXT,
                    status TEXT,
                    receiver TEXT,
                    phone TEXT,
                    client_name TEXT,
                    device TEXT,
                    problem TEXT,
                    telegram_chat_id TEXT,
                    telegram_message_id INTEGER,
                    telegram_message_date TEXT,
                    raw_message_text TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            # Таблица истории статусов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS order_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    changed_at TEXT NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE
                )
            ''')
            
            # Индексы для быстрого поиска
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_number ON orders(order_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_phone ON orders(phone)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_client_name ON orders(client_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_device ON orders(device)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON orders(status)')
            
            conn.commit()
            
            if db_exists:
                print(f"✅ База данных подключена: {self.db_path}")
                # Проверяем количество заказов
                cursor.execute('SELECT COUNT(*) as count FROM orders')
                count = cursor.fetchone()['count']
                print(f"📊 В базе данных {count} заказов")
            else:
                print(f"✅ База данных создана: {self.db_path}")
    
    def save_order(self, order: Order) -> Optional[int]:
        """Сохраняет или обновляет заказ"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем, существует ли заказ
            cursor.execute(
                'SELECT id, status FROM orders WHERE order_number = ?',
                (order.order_number,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Обновляем существующий заказ
                order_id = existing['id']
                old_status = existing['status']
                
                cursor.execute('''
                    UPDATE orders SET
                        date = ?,
                        status = ?,
                        receiver = ?,
                        phone = ?,
                        client_name = ?,
                        device = ?,
                        problem = ?,
                        telegram_chat_id = ?,
                        telegram_message_id = ?,
                        telegram_message_date = ?,
                        raw_message_text = ?,
                        updated_at = ?
                    WHERE order_number = ?
                ''', (
                    order.date,
                    order.status,
                    order.receiver,
                    order.phone,
                    order.client_name,
                    order.device,
                    order.problem,
                    order.telegram_chat_id,
                    order.telegram_message_id,
                    order.telegram_message_date,
                    order.raw_message_text,
                    datetime.now().isoformat(),
                    order.order_number
                ))
                
                # Если статус изменился, сохраняем в историю
                if order.status and old_status != order.status:
                    cursor.execute('''
                        INSERT INTO order_history (order_id, status, changed_at)
                        VALUES (?, ?, ?)
                    ''', (
                        order_id,
                        order.status,
                        datetime.now().isoformat()
                    ))
                
                conn.commit()
                print(f"✅ Заказ #{order.order_number} обновлен")
                return order_id
            else:
                # Создаем новый заказ
                cursor.execute('''
                    INSERT INTO orders (
                        order_number, date, status, receiver, phone,
                        client_name, device, problem,
                        telegram_chat_id, telegram_message_id,
                        telegram_message_date, raw_message_text,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    order.order_number,
                    order.date,
                    order.status,
                    order.receiver,
                    order.phone,
                    order.client_name,
                    order.device,
                    order.problem,
                    order.telegram_chat_id,
                    order.telegram_message_id,
                    order.telegram_message_date,
                    order.raw_message_text,
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                
                order_id = cursor.lastrowid
                
                # Сохраняем начальный статус в историю
                if order.status:
                    cursor.execute('''
                        INSERT INTO order_history (order_id, status, changed_at)
                        VALUES (?, ?, ?)
                    ''', (
                        order_id,
                        order.status,
                        datetime.now().isoformat()
                    ))
                
                conn.commit()
                print(f"✅ Новый заказ #{order.order_number} сохранен")
                return order_id
    
    def get_order(self, order_number: str) -> Optional[Dict[str, Any]]:
        """Получает заказ по номеру"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM orders WHERE order_number = ?',
                (order_number,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_order_history(self, order_id: int) -> List[Dict[str, Any]]:
        """Получает историю изменений статуса заказа"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM order_history WHERE order_id = ? ORDER BY changed_at DESC',
                (order_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def search_orders(self, query: str) -> List[Dict[str, Any]]:
        """Поиск заказов по различным полям"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            search_pattern = f'%{query}%'
            cursor.execute('''
                SELECT * FROM orders WHERE
                    order_number LIKE ? OR
                    phone LIKE ? OR
                    client_name LIKE ? OR
                    device LIKE ? OR
                    problem LIKE ? OR
                    receiver LIKE ?
                ORDER BY created_at DESC
                LIMIT 100
            ''', (
                search_pattern, search_pattern, search_pattern,
                search_pattern, search_pattern, search_pattern
            ))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получает статистику по заказам"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Общее количество
            cursor.execute('SELECT COUNT(*) as total FROM orders')
            total = cursor.fetchone()['total']
            
            # По статусам
            cursor.execute('''
                SELECT status, COUNT(*) as count 
                FROM orders 
                GROUP BY status
                ORDER BY count DESC
            ''')
            by_status = [dict(row) for row in cursor.fetchall()]
            
            # За сегодня
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute(
                'SELECT COUNT(*) as today FROM orders WHERE date = ?',
                (today,)
            )
            today_count = cursor.fetchone()['today']
            
            return {
                'total': total,
                'today': today_count,
                'by_status': by_status
            }


# Синглтон для использования в боте
_db_instance = None

def get_db() -> Database:
    """Возвращает экземпляр базы данных (синглтон)"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
