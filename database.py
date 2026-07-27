#!/usr/bin/env python3
"""
Модуль для работы с базой данных SQLite
С поддержкой синхронизации с GitHub и таблицей пользователей
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
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.getenv('DB_PATH', '/app/data/orders.db')
        self.db_path = db_path
        self.init_database()
        self.init_users_table()
    
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
                    master TEXT,
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
            
            cursor.execute('SELECT COUNT(*) as count FROM orders')
            count = cursor.fetchone()['count']
            print(f"✅ База данных готова: {self.db_path} ({count} заказов)")
    
    # ============================================================
    # ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ
    # ============================================================
    def init_users_table(self):
        """Создает таблицу пользователей"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id TEXT UNIQUE NOT NULL,
                    username TEXT,
                    full_name TEXT,
                    role TEXT DEFAULT 'user',
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            conn.commit()
            print("✅ Таблица пользователей создана")

    def get_user(self, telegram_id: str) -> Optional[Dict[str, Any]]:
        """Получает пользователя по Telegram ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Получает всех пользователей"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users ORDER BY role DESC, full_name')
            return [dict(row) for row in cursor.fetchall()]

    def add_user(self, telegram_id: str, username: str, full_name: str, role: str = 'user') -> bool:
        """Добавляет нового пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO users (telegram_id, username, full_name, role, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (telegram_id, username, full_name, role, datetime.now().isoformat(), datetime.now().isoformat()))
                conn.commit()
                print(f"✅ Пользователь {full_name} добавлен с ролью {role}")
                return True
            except sqlite3.IntegrityError:
                print(f"⚠️ Пользователь {telegram_id} уже существует")
                return False

    def update_user(self, telegram_id: str, updates: Dict[str, Any]) -> bool:
        """Обновляет данные пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [telegram_id]
            cursor.execute(f'''
                UPDATE users SET {set_clause}, updated_at = ?
                WHERE telegram_id = ?
            ''', values + [datetime.now().isoformat()])
            conn.commit()
            return cursor.rowcount > 0

    def update_user_role(self, telegram_id: str, new_role: str) -> bool:
        """Обновляет роль пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET role = ?, updated_at = ?
                WHERE telegram_id = ?
            ''', (new_role, datetime.now().isoformat(), telegram_id))
            conn.commit()
            if cursor.rowcount > 0:
                print(f"✅ Роль пользователя {telegram_id} изменена на {new_role}")
                return True
            return False

    def delete_user(self, telegram_id: str) -> bool:
        """Удаляет пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM users WHERE telegram_id = ?', (telegram_id,))
            conn.commit()
            if cursor.rowcount > 0:
                print(f"✅ Пользователь {telegram_id} удален")
                return True
            return False
    
    # ============================================================
    # МЕТОДЫ ДЛЯ ЗАКАЗОВ
    # ============================================================
    def save_order(self, order: Order) -> Optional[int]:
        """Сохраняет или обновляет заказ и синхронизирует с GitHub"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT id, status FROM orders WHERE order_number = ?',
                (order.order_number,)
            )
            existing = cursor.fetchone()
            
            if existing:
                order_id = existing['id']
                old_status = existing['status']
                
                cursor.execute('''
                    UPDATE orders SET
                        date = ?,
                        status = ?,
                        receiver = ?,
                        master = ?,
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
                    order.master,
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
                db_sync.sync_on_change(order.order_number)
                return order_id
            else:
                cursor.execute('''
                    INSERT INTO orders (
                        order_number, date, status, receiver, master,
                        phone, client_name, device, problem,
                        telegram_chat_id, telegram_message_id,
                        telegram_message_date, raw_message_text,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    order.order_number,
                    order.date,
                    order.status,
                    order.receiver,
                    order.master,
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
                db_sync.sync_on_change(order.order_number)
                return order_id
    
    def get_order(self, order_number: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM orders WHERE order_number = ?',
                (order_number,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_order_by_id(self, order_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_order_history(self, order_id: int) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM order_history 
                WHERE order_id = ? 
                ORDER BY changed_at DESC
            ''', (order_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def search_orders(self, query: str) -> List[Dict[str, Any]]:
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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM orders 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict[str, Any]:
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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT date, COUNT(*) as count 
                FROM orders 
                WHERE date IS NOT NULL 
                GROUP BY date 
                ORDER BY date DESC 
                LIMIT 7
            ''')
            orders_by_day = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute('''
                SELECT AVG(julianday(updated_at) - julianday(created_at)) as avg_days
                FROM orders 
                WHERE status IN ('Готово', 'Выдано (оплачено)', 'Выдано (не оплачено)')
            ''')
            avg_repair_time = cursor.fetchone()['avg_days'] or 0
            
            cursor.execute('''
                SELECT problem, COUNT(*) as count 
                FROM orders 
                WHERE problem IS NOT NULL AND problem != ''
                GROUP BY problem 
                ORDER BY count DESC 
                LIMIT 5
            ''')
            top_problems = [dict(row) for row in cursor.fetchall()]
            
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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if role == 'admin' or role == 'superadmin':
                cursor.execute('SELECT * FROM orders ORDER BY created_at DESC LIMIT 200')
            else:
                cursor.execute('''
                    SELECT * FROM orders 
                    WHERE phone LIKE ? OR client_name LIKE ? 
                    ORDER BY created_at DESC 
                    LIMIT 200
                ''', (f'%{user_id}%', f'%{user_id}%'))
            
            return [dict(row) for row in cursor.fetchall()]

    # ============================================================
    # МЕТОДЫ ДЛЯ МАСТЕРОВ
    # ============================================================
    def get_masters(self) -> List[str]:
        """Получает список всех мастеров из поля master"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT master as name 
                FROM orders 
                WHERE master IS NOT NULL AND master != ''
                ORDER BY master
            ''')
            return [row['name'] for row in cursor.fetchall()]
    
    def get_orders_by_master(self, master: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM orders 
                WHERE master = ? 
                ORDER BY created_at DESC
            ''', (master,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_master_stats(self) -> Dict[str, Any]:
        """Получает статистику по мастерам (из поля master)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT master, COUNT(*) as count 
                FROM orders 
                WHERE master IS NOT NULL AND master != ''
                GROUP BY master
                ORDER BY count DESC
            ''')
            all_stats = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute('''
                SELECT master, COUNT(*) as count 
                FROM orders 
                WHERE master IS NOT NULL AND master != ''
                AND status = 'Выдано (оплачено)'
                GROUP BY master
                ORDER BY count DESC
            ''')
            done_stats = [dict(row) for row in cursor.fetchall()]
            
            return {
                "all": all_stats,
                "done": done_stats
            }


# Синглтон
_db_instance = None

def get_db() -> Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
