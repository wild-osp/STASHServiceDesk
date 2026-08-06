#!/usr/bin/env python3
"""
Модуль для работы с базой данных SQLite
"""

import sqlite3
import os
import time
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from models import Order, OrderHistory
from db_sync import db_sync

# ============================================================
# УСТАНОВКА ЧАСОВОГО ПОЯСА ДЛЯ DATABASE (Минск, UTC+3)
# ============================================================
os.environ['TZ'] = 'Europe/Minsk'
try:
    time.tzset()
except:
    pass

def now_iso():
    """Возвращает текущее время в Минске в формате ISO"""
    return datetime.now().isoformat()


class Database:
    """Класс для управления базой данных заказов"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.getenv('DB_PATH', '/app/data/orders.db')
        self.db_path = db_path
        self.init_database()
        self.init_users_table()
        self.ensure_master_column()
        self.clean_master_values()
    
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
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_master ON orders(master)')
            
            conn.commit()
            
            cursor.execute('SELECT COUNT(*) as count FROM orders')
            count = cursor.fetchone()['count']
            print(f"✅ База данных готова: {self.db_path} ({count} заказов)")
    
    def init_users_table(self):
        """Создает таблицу пользователей с полем master"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id TEXT UNIQUE NOT NULL,
                    username TEXT,
                    full_name TEXT,
                    role TEXT DEFAULT 'user',
                    master TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            conn.commit()
            print("✅ Таблица пользователей создана")
    
    def ensure_master_column(self):
        """Проверяет и добавляет колонку master, если её нет"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(users)")
                columns = [row['name'] for row in cursor.fetchall()]
                
                if 'master' not in columns:
                    print("🔧 Добавляем колонку master в таблицу users...")
                    cursor.execute("ALTER TABLE users ADD COLUMN master TEXT")
                    conn.commit()
                    print("✅ Колонка master успешно добавлена")
                else:
                    print("✅ Колонка master уже существует")
        except Exception as e:
            print(f"⚠️ Ошибка при проверке/добавлении колонки master: {e}")

    def clean_master_values(self):
        """Очищает записи 'None' в поле master"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE orders SET master = NULL WHERE master = 'None' OR master = ''")
                conn.commit()
                count = cursor.rowcount
                if count > 0:
                    print(f"🧹 Очищено {count} записей с мастером 'None'")
        except Exception as e:
            print(f"⚠️ Ошибка при очистке master: {e}")

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

    def add_user(self, telegram_id: str, username: str, full_name: str, role: str = 'user', master: str = '') -> bool:
        """Добавляет нового пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO users (telegram_id, username, full_name, role, master, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (telegram_id, username, full_name, role, master, now_iso(), now_iso()))
                conn.commit()
                print(f"✅ Пользователь {full_name} добавлен с ролью {role} и мастером {master}")
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
            ''', values + [now_iso()])
            conn.commit()
            return cursor.rowcount > 0

    def update_user_role(self, telegram_id: str, new_role: str) -> bool:
        """Обновляет роль пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET role = ?, updated_at = ?
                WHERE telegram_id = ?
            ''', (new_role, now_iso(), telegram_id))
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
    # ОСНОВНОЙ МЕТОД СОХРАНЕНИЯ ЗАКАЗА (С ЗАЩИТОЙ МАСТЕРА)
    # ============================================================
    def save_order(self, order: Order) -> Optional[int]:
        """Сохраняет или обновляет заказ"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # ============================================================
            # ОБРАБОТКА МАСТЕРА: "None" → None
            # ============================================================
            master_value = order.master
            if master_value == 'None' or master_value == '' or master_value is None:
                master_value = None
            
            print("=" * 60)
            print(f"📦 СОХРАНЕНИЕ ЗАКАЗА #{order.order_number}")
            print(f"   Мастер из заказа: '{master_value}'")
            
            cursor.execute(
                'SELECT id, status, master FROM orders WHERE order_number = ?',
                (order.order_number,)
            )
            existing = cursor.fetchone()
            
            if existing:
                order_id = existing['id']
                old_status = existing['status']
                old_master = existing['master'] or ''
                
                print(f"   Старый статус: '{old_status}'")
                print(f"   Старый мастер: '{old_master}'")
                print(f"   Новый статус: '{order.status}'")
                print(f"   Новый мастер: '{master_value}'")
                
                # ============================================================
                # ЗАЩИТА: НЕ ЗАТИРАЕМ МАСТЕРА ПУСТЫМ ЗНАЧЕНИЕМ
                # ============================================================
                # Если пришло None (мастер не указан), а в БД уже есть мастер - 
                # НЕ обновляем мастера, оставляем старого
                if master_value is None and old_master and old_master != 'None':
                    print(f"⚠️ Защита: мастер не будет обновлен (в БД уже есть '{old_master}')")
                    master_to_save = old_master
                else:
                    master_to_save = master_value
                
                print(f"   Мастер для сохранения: '{master_to_save}'")
                
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
                    master_to_save,
                    order.phone,
                    order.client_name,
                    order.device,
                    order.problem,
                    order.telegram_chat_id,
                    order.telegram_message_id,
                    order.telegram_message_date,
                    order.raw_message_text,
                    now_iso(),
                    order.order_number
                ))
                
                # Записываем историю если статус изменился
                if order.status and old_status != order.status:
                    print(f"📝 Записываем историю: '{old_status}' → '{order.status}'")
                    cursor.execute('''
                        INSERT INTO order_history (order_id, status, changed_at)
                        VALUES (?, ?, ?)
                    ''', (order_id, order.status, now_iso()))
                    conn.commit()
                    print(f"✅ История записана")
                else:
                    if order.status == old_status:
                        print(f"ℹ️ Статус не изменился")
                    else:
                        print(f"⚠️ Статус пустой")
                
                # Логируем изменение мастера
                if master_to_save != old_master:
                    print(f"👨‍🔧 Мастер изменен: '{old_master}' → '{master_to_save}'")
                else:
                    print(f"👨‍🔧 Мастер не изменился")
                
                conn.commit()
                print(f"✅ Заказ #{order.order_number} обновлен")
                print("=" * 60)
                return order_id
            else:
                # Новый заказ - сохраняем мастера как есть
                print(f"📝 Создание нового заказа #{order.order_number}")
                print(f"   Мастер: '{master_value}'")
                print(f"   Статус: '{order.status}'")
                print(f"   Клиент: '{order.client_name}'")
                print(f"   Телефон: '{order.phone}'")
                print(f"   Устройство: '{order.device}'")
                
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
                    master_value,
                    order.phone,
                    order.client_name,
                    order.device,
                    order.problem,
                    order.telegram_chat_id,
                    order.telegram_message_id,
                    order.telegram_message_date,
                    order.raw_message_text,
                    now_iso(),
                    now_iso()
                ))
                
                order_id = cursor.lastrowid
                
                if order.status:
                    print(f"📝 Записываем начальный статус '{order.status}'")
                    cursor.execute('''
                        INSERT INTO order_history (order_id, status, changed_at)
                        VALUES (?, ?, ?)
                    ''', (order_id, order.status, now_iso()))
                    conn.commit()
                    print(f"✅ Начальный статус записан")
                
                conn.commit()
                print(f"✅ Новый заказ #{order.order_number} сохранен")
                print("=" * 60)
                return order_id
    
    def get_order(self, order_number: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM orders WHERE order_number = ?', (order_number,))
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
            ''', (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, search_pattern))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_orders(self, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM orders ORDER BY created_at DESC LIMIT ? OFFSET ?', (limit, offset))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_orders_filtered(self, limit: int = 50, offset: int = 0, search: Optional[str] = None, master: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Получает заказы с фильтрацией по поиску, мастеру и статусу"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            conditions = []
            params = []
            
            if search:
                search_pattern = f'%{search}%'
                conditions.append('(order_number LIKE ? OR phone LIKE ? OR client_name LIKE ? OR device LIKE ?)')
                params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
            
            if master:
                conditions.append('master = ?')
                params.append(master)
            
            if status and status != 'all':
                conditions.append('status = ?')
                params.append(status)
            
            where_clause = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
            
            cursor.execute(f'SELECT * FROM orders{where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?', params + [limit, offset])
            return [dict(row) for row in cursor.fetchall()]
    
    def count_all_orders_filtered(self, search: Optional[str] = None, master: Optional[str] = None, status: Optional[str] = None) -> int:
        """Считает количество заказов с фильтрацией"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            conditions = []
            params = []
            
            if search:
                search_pattern = f'%{search}%'
                conditions.append('(order_number LIKE ? OR phone LIKE ? OR client_name LIKE ? OR device LIKE ?)')
                params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
            
            if master:
                conditions.append('master = ?')
                params.append(master)
            
            if status and status != 'all':
                conditions.append('status = ?')
                params.append(status)
            
            where_clause = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
            
            cursor.execute(f'SELECT COUNT(*) as count FROM orders{where_clause}', params)
            return cursor.fetchone()['count']
    
    def get_statistics(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as total FROM orders')
            total = cursor.fetchone()['total']
            cursor.execute('SELECT status, COUNT(*) as count FROM orders GROUP BY status ORDER BY count DESC')
            by_status = [dict(row) for row in cursor.fetchall()]
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('SELECT COUNT(*) as today FROM orders WHERE date = ?', (today,))
            today_count = cursor.fetchone()['today']
            return {'total': total, 'today': today_count, 'by_status': by_status}
    
    def get_detailed_stats(self, month: int = None, year: int = None) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            date_filter = ""
            params = []
            if month and year:
                date_filter = " WHERE strftime('%m', date) = ? AND strftime('%Y', date) = ?"
                params = [str(month).zfill(2), str(year)]
            cursor.execute(f'''
                SELECT date, COUNT(*) as count 
                FROM orders 
                {date_filter}
                GROUP BY date 
                ORDER BY date DESC 
                LIMIT 7
            ''', params)
            orders_by_day = [dict(row) for row in cursor.fetchall()]
            cursor.execute(f'''
                SELECT AVG(julianday(updated_at) - julianday(created_at)) as avg_days
                FROM orders 
                WHERE status IN ('Готово', 'Выдано (оплачено)', 'Выдано (не оплачено)')
                {date_filter.replace('WHERE', 'AND') if date_filter else ''}
            ''', params)
            avg_repair_time = cursor.fetchone()['avg_days'] or 0
            cursor.execute(f'''
                SELECT problem, COUNT(*) as count 
                FROM orders 
                WHERE problem IS NOT NULL AND problem != ''
                {date_filter.replace('WHERE', 'AND') if date_filter else ''}
                GROUP BY problem 
                ORDER BY count DESC 
                LIMIT 5
            ''', params)
            top_problems = [dict(row) for row in cursor.fetchall()]
            cursor.execute(f'''
                SELECT status, COUNT(*) as count 
                FROM orders 
                {date_filter}
                GROUP BY status
            ''', params)
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
            if role in ['admin', 'superadmin']:
                cursor.execute('SELECT * FROM orders ORDER BY created_at DESC LIMIT 200')
            else:
                cursor.execute('SELECT * FROM orders WHERE phone LIKE ? OR client_name LIKE ? ORDER BY created_at DESC LIMIT 200', (f'%{user_id}%', f'%{user_id}%'))
            return [dict(row) for row in cursor.fetchall()]

    # ============================================================
    # МЕТОДЫ ДЛЯ МАСТЕРОВ
    # ============================================================
    def get_masters(self) -> List[str]:
        """Получает список всех мастеров из заказов (исключая None)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT master as name 
                FROM orders 
                WHERE master IS NOT NULL AND master != '' AND master != 'None'
                ORDER BY master
            ''')
            masters = [row['name'] for row in cursor.fetchall()]
            print(f"📋 Загружено мастеров из заказов: {len(masters)} - {masters}")
            return masters
    
    def get_orders_by_master(self, master: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM orders WHERE master = ? ORDER BY created_at DESC', (master,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_master_stats(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT master, COUNT(*) as count FROM orders WHERE master IS NOT NULL AND master != "" AND master != "None" GROUP BY master ORDER BY count DESC')
            all_stats = [dict(row) for row in cursor.fetchall()]
            cursor.execute('SELECT master, COUNT(*) as count FROM orders WHERE master IS NOT NULL AND master != "" AND master != "None" AND status = "Выдано (оплачено)" GROUP BY master ORDER BY count DESC')
            done_stats = [dict(row) for row in cursor.fetchall()]
            return {"all": all_stats, "done": done_stats}


# Синглтон
_db_instance = None

def get_db() -> Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
