#!/usr/bin/env python3
"""
Модуль для работы с базой данных SQLite
С поддержкой синхронизации с GitHub
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from models import Order, OrderHistory
from db_sync import db_sync


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
        """Инициализирует структуру базы данных"""
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
            
            # Индексы
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_number ON orders(order_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_phone ON orders(phone)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_client_name ON orders(client_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_device ON orders(device)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON orders(status)')
            
            conn.commit()
            
            # Проверяем количество заказов
            cursor.execute('SELECT COUNT(*) as count FROM orders')
            count = cursor.fetchone()['count']
            print(f"✅ База данных готова: {self.db_path} ({count} заказов)")
    
    def save_order(self, order: Order) -> Optional[int]:
        """Сохраняет или обновляет заказ и синхронизирует с GitHub"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем существование
            cursor.execute(
                'SELECT id, status FROM orders WHERE order_number = ?',
                (order.order_number,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Обновляем
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
                
                # Синхронизация с GitHub
                db_sync.sync_on_change(order.order_number)
                
                return order_id
            else:
                # Создаем новый
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
                
                # Синхронизация с GitHub
                db_sync.sync_on_change(order.order_number)
                
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
    
    def get_order_by_id(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Получает заказ по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_order_history(self, order_id: int) -> List[Dict[str, Any]]:
        """Получает историю изменений статуса заказа"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM order_history 
                WHERE order_id = ? 
                ORDER BY changed_at DESC
            ''', (order_id,))
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
    
    def get_all_orders(self, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        """Получает все заказы с пагинацией"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM orders 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получает базовую статистику по заказам"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) as total FROM orders')
            total = cursor.fetchone()['total']
            
            cursor.execute('''
                SELECT status, COUNT(*) as count 
                FROM orders 
                GROUP BY status
                ORDER BY count DESC
            ''')
            by_status = [dict(row) for row in cursor.fetchall()]
            
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
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """Расширенная статистика для дашборда"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Заказы по дням (последние 7 дней)
            cursor.execute('''
                SELECT date, COUNT(*) as count 
                FROM orders 
                WHERE date IS NOT NULL 
                GROUP BY date 
                ORDER BY date DESC 
                LIMIT 7
            ''')
            orders_by_day = [dict(row) for row in cursor.fetchall()]
            
            # 2. Среднее время ремонта (в днях) для завершенных заказов
            cursor.execute('''
                SELECT AVG(julianday(updated_at) - julianday(created_at)) as avg_days
                FROM orders 
                WHERE status IN ('Готово', 'Выдано (оплачено)', 'Выдано (не оплачено)')
            ''')
            avg_repair_time = cursor.fetchone()['avg_days'] or 0
            
            # 3. Топ-5 самых частых неисправностей
            cursor.execute('''
                SELECT problem, COUNT(*) as count 
                FROM orders 
                WHERE problem IS NOT NULL AND problem != ''
                GROUP BY problem 
                ORDER BY count DESC 
                LIMIT 5
            ''')
            top_problems = [dict(row) for row in cursor.fetchall()]
            
            # 4. Статусы с количеством и процентами
            cursor.execute('''
                SELECT status, COUNT(*) as count 
                FROM orders 
                GROUP BY status
            ''')
            status_counts = [dict(row) for row in cursor.fetchall()]
            total = sum(s['count'] for s in status_counts)
            for s in status_counts:
                s['percent'] = round((s['count'] / total * 100), 1) if total > 0 else 0

            return {
                "orders_by_day": orders_by_day,
                "avg_repair_time": round(avg_repair_time, 1),
                "top_problems": top_problems,
                "status_counts": status_counts,
                "total_orders": total
            }
    
    def get_user_orders(self, user_id: str, role: str = 'user') -> List[Dict[str, Any]]:
        """Получить заказы с учетом роли пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if role == 'admin':
                # Админ видит все заказы
                cursor.execute('SELECT * FROM orders ORDER BY created_at DESC LIMIT 200')
            else:
                # Обычный пользователь видит только свои заказы (по номеру телефона или имени)
                cursor.execute('''
                    SELECT * FROM orders 
                    WHERE phone LIKE ? OR client_name LIKE ? 
                    ORDER BY created_at DESC 
                    LIMIT 200
                ''', (f'%{user_id}%', f'%{user_id}%'))
            
            return [dict(row) for row in cursor.fetchall()]


# Синглтон
_db_instance = None

def get_db() -> Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
