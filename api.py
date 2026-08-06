#!/usr/bin/env python3
import os
import time
import threading
import subprocess
import sys
from fastapi import FastAPI, HTTPException, Query, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import json

# ============================================================
# УСТАНОВКА ЧАСОВОГО ПОЯСА (Минск, UTC+3)
# ============================================================
os.environ['TZ'] = 'Europe/Minsk'
try:
    time.tzset()
    print(f"✅ Часовой пояс установлен: {time.tzname}")
except Exception as e:
    print(f"⚠️ Не удалось установить часовой пояс: {e}")

print(f"🕐 Текущее время API: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

DEFAULT_DATA_DIR = '/app/data'
FALLBACK_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

if os.path.exists('/app'):
    DATA_DIR = os.getenv('DATA_DIR', DEFAULT_DATA_DIR)
else:
    DATA_DIR = os.getenv('DATA_DIR', FALLBACK_DATA_DIR)

try:
    os.makedirs(DATA_DIR, exist_ok=True)
except OSError:
    DATA_DIR = FALLBACK_DATA_DIR
    os.makedirs(DATA_DIR, exist_ok=True)

os.environ['DB_PATH'] = os.path.join(DATA_DIR, 'orders.db')

from database import get_db, now_iso
from models import Order


# ============================================================
# FASTAPI APP
# ============================================================
app = FastAPI(title="STASHServiceDesk API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
db = get_db()

# ============================================================
# API-КЛЮЧ ДЛЯ ЗАЩИТЫ ЭНДПОИНТА (1С)
# ============================================================
API_KEY = os.getenv('API_KEY', 'STASH2024SecretKey!')

# ============================================================
# МОДЕЛЬ ДЛЯ ПРИЕМА ЗАКАЗА ИЗ 1С
# ============================================================
class OrderFrom1C(BaseModel):
    order_number: str
    date: Optional[str] = None
    status: str
    receiver: Optional[str] = None
    master: Optional[str] = None
    phone: Optional[str] = None
    client_name: Optional[str] = None
    device: Optional[str] = None
    problem: Optional[str] = None
    serial_number: Optional[str] = None
    cost: Optional[float] = None
    notes: Optional[str] = None

# ============================================================
# МОДЕЛЬ ДЛЯ ЗАДАЧ
# ============================================================
class TaskCreate(BaseModel):
    text: str
    priority: str = "Обычный"
    deadline: Optional[str] = None
    order_id: Optional[int] = None

class TaskReassign(BaseModel):
    new_executor_id: int

# ============================================================
# АВТОРИЗАЦИЯ
# ============================================================
import urllib.parse

async def get_current_user(
    x_tg_init_data: str = Header(default=None),
    x_user_id: str = Header(default=None)
):
    if not x_tg_init_data and not x_user_id:
        raise HTTPException(status_code=401, detail="Не авторизован: отсутствует X-TG-Init-Data")

    if not x_tg_init_data and x_user_id:
        telegram_id = x_user_id
        user = db.get_user(telegram_id)
        if not user:
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        return {
            "user_id": user['telegram_id'],
            "username": user['username'] or '',
            "full_name": user['full_name'] or '',
            "role": user['role'] or 'user',
            "master": user.get('master', '')
        }

    # Парсим initData для извлечения user_id
    # initData имеет формат key=value&key=value
    # Например: query_id=AAHdF6...&user=%7B%22id%22%3A12345%2C%22first_name%22%3A%22Test%22%2C%22last_name%22%3A%22User%22%2C%22username%22%3A%22testuser%22%2C%22language_code%22%3A%22en%22%2C%22is_premium%22%3Atrue%7D&auth_date=1671234567&hash=abcdef12345
    
    parsed_data = urllib.parse.parse_qs(x_tg_init_data)
    
    user_data_str = parsed_data.get('user', [None])[0]
    if not user_data_str:
        raise HTTPException(status_code=401, detail="Не авторизован: user данные отсутствуют в initData")
    
    try:
        user_data = json.loads(user_data_str)
        telegram_id = str(user_data.get('id'))
    except json.JSONDecodeError:
        raise HTTPException(status_code=401, detail="Не авторизован: некорректные user данные в initData")

    if not telegram_id:
        raise HTTPException(status_code=401, detail="Не авторизован: user_id отсутствует в initData")
    
    user = db.get_user(telegram_id)
    if not user:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    
    return {
        "user_id": user['telegram_id'],
        "username": user['username'] or '',
        "full_name": user['full_name'] or '',
        "role": user['role'] or 'user',
        "master": user.get('master', '')
    }

# ============================================================
# ЭНДПОИНТЫ
# ============================================================
@app.get("/")
async def root():
    return {"name": "STASHServiceDesk API", "status": "running", "timestamp": datetime.now().isoformat()}

@app.get("/app")
async def serve_app():
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(
            content=html_content,
            status_code=200,
            headers={
                "Content-Type": "text/html; charset=utf-8",
                "Content-Security-Policy": "default-src 'self' https:; script-src 'unsafe-inline' https:; style-src 'unsafe-inline' https:;",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Cache-Control": "no-cache, no-store, must-revalidate"
            }
        )
    except Exception as e:
        return HTMLResponse(content=f"<h1>Ошибка</h1><p>{str(e)}</p>", status_code=500)

@app.get("/api/auth/check")
async def check_user(
    current_user: dict = Depends(get_current_user)
):
    # Если get_current_user не вызвал HTTPException, значит пользователь авторизован
    return JSONResponse({
        "success": True,
        "user": {
            "id": current_user['user_id'],
            "username": current_user['username'],
            "full_name": current_user['full_name'],
            "role": current_user['role'],
            "master": current_user['master']
        }
    })

# ============================================================
# УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
# ============================================================
@app.get("/api/users")
async def get_users(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ['admin', 'superadmin']:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    users = db.get_all_users()
    return JSONResponse({"success": True, "data": users})

@app.get("/api/users/{telegram_id}")
async def get_user(telegram_id: str, current_user: dict = Depends(get_current_user)):
    """Получить данные пользователя по ID (только для суперадмина)"""
    if current_user["role"] != 'superadmin':
        raise HTTPException(status_code=403, detail="Только суперадмин может просматривать пользователей")
    
    user = db.get_user(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return JSONResponse({"success": True, "data": user})

@app.post("/api/users")
async def add_user(
    telegram_id: str,
    username: str = "",
    full_name: str = "",
    role: str = "user",
    master: str = "",
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in ['admin', 'superadmin']:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    
    if current_user["role"] == 'admin' and role != 'user':
        raise HTTPException(status_code=403, detail="Админ может назначать только роль 'user'")
    
    if not telegram_id:
        raise HTTPException(status_code=400, detail="telegram_id обязателен")
    
    existing = db.get_user(telegram_id)
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    
    success = db.add_user(telegram_id, username, full_name, role, master)
    if success:
        return JSONResponse({"success": True, "message": "Пользователь добавлен"})
    else:
        raise HTTPException(status_code=400, detail="Не удалось добавить пользователя")

@app.put("/api/users/{telegram_id}")
async def update_user(
    telegram_id: str,
    full_name: str = "",
    username: str = "",
    role: str = "",
    master: str = "",
    current_user: dict = Depends(get_current_user)
):
    """Обновить данные пользователя (только для суперадмина)"""
    print("=" * 60)
    print(f"🔍 update_user: telegram_id={telegram_id}")
    print(f"   full_name='{full_name}'")
    print(f"   username='{username}'")
    print(f"   role='{role}'")
    print(f"   master='{master}'")
    print("=" * 60)
    
    if current_user["role"] != 'superadmin':
        raise HTTPException(status_code=403, detail="Только суперадмин может редактировать пользователей")
    
    user = db.get_user(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    updates = {}
    if full_name and full_name != '':
        updates['full_name'] = full_name
    if username and username != '':
        updates['username'] = username
    if role and role in ['user', 'admin', 'superadmin']:
        updates['role'] = role
    
    if master is not None:
        updates['master'] = master if master != '' else None
    
    print(f"   updates: {updates}")
    
    if not updates:
        return JSONResponse({"success": True, "message": "Нет изменений"})
    
    success = db.update_user(telegram_id, updates)
    print(f"   success: {success}")
    
    if success:
        updated_user = db.get_user(telegram_id)
        print(f"   после обновления master='{updated_user.get('master')}'")
        return JSONResponse({"success": True, "message": "Пользователь обновлен"})
    else:
        raise HTTPException(status_code=400, detail="Не удалось обновить пользователя")

@app.put("/api/users/{telegram_id}/role")
async def update_user_role(
    telegram_id: str,
    new_role: str,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != 'superadmin':
        raise HTTPException(status_code=403, detail="Только суперадмин может менять роли")
    
    if not new_role in ['superadmin', 'admin', 'user']:
        raise HTTPException(status_code=400, detail="Недопустимая роль")
    
    if telegram_id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Нельзя изменить свою роль")
    
    success = db.update_user_role(telegram_id, new_role)
    if success:
        return JSONResponse({"success": True, "message": "Роль обновлена"})
    else:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

@app.delete("/api/users/{telegram_id}")
async def delete_user(
    telegram_id: str,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != 'superadmin':
        raise HTTPException(status_code=403, detail="Только суперадмин может удалять пользователей")
    
    if telegram_id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")
    
    success = db.delete_user(telegram_id)
    if success:
        return JSONResponse({"success": True, "message": "Пользователь удален"})
    else:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

# ============================================================
# УДАЛЕНИЕ ЗАКАЗА
# ============================================================
@app.delete("/api/orders/by-number/{order_number}")
async def delete_order_by_number(
    order_number: str,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in ['admin', 'superadmin']:
        raise HTTPException(status_code=403, detail="Только администратор может удалять заказы")
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM order_history 
            WHERE order_id IN (SELECT id FROM orders WHERE order_number = ?)
        ''', (order_number,))
        cursor.execute('DELETE FROM orders WHERE order_number = ?', (order_number,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        conn.commit()
    
    return JSONResponse({"success": True, "message": f"Заказ #{order_number} удален"})

# ============================================================
# ПРИЕМ ЗАКАЗОВ ИЗ 1С (С ОБРАБОТКОЙ МАСТЕРА)
# ============================================================
@app.post("/api/orders/from-1c")
async def receive_order_from_1c(
    order_data: OrderFrom1C,
    x_api_key: str = Header(...)
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Неверный API-ключ")
    try:
        # ============================================================
        # ОБРАБОТКА МАСТЕРА ИЗ 1С
        # ============================================================
        master_value = order_data.master
        
        # Если пришло None, "None" или пустая строка - значит мастера нет
        if master_value is None or master_value == 'None' or master_value == '':
            master_value = None
            print(f"⚠️ Мастер не указан в 1С")
        else:
            # Убираем лишние пробелы
            master_value = master_value.strip()
            print(f"✅ Мастер из 1С: '{master_value}'")
        
        print("=" * 60)
        print(f"📦 ПОЛУЧЕН ЗАКАЗ ИЗ 1С")
        print(f"   Номер: {order_data.order_number}")
        print(f"   Статус: '{order_data.status}'")
        print(f"   Мастер (сырое из 1С): '{order_data.master}'")
        print(f"   Мастер (после обработки): '{master_value}'")
        print(f"   Клиент: {order_data.client_name}")
        print(f"   Телефон: {order_data.phone}")
        print(f"   Устройство: {order_data.device}")
        print("=" * 60)
        
        existing = db.get_order(order_data.order_number)
        order = Order(
            order_number=order_data.order_number,
            date=order_data.date,
            status=order_data.status,
            receiver=order_data.receiver,
            master=master_value,
            phone=order_data.phone,
            client_name=order_data.client_name,
            device=order_data.device,
            problem=order_data.problem,
            telegram_chat_id="from_1c_api",
            telegram_message_id=0,
            telegram_message_date=now_iso(),
            raw_message_text=f"Отправлено из 1С через API: {order_data.order_number}"
        )
        order_id = db.save_order(order)
        action = "обновлен" if existing else "создан"
        print(f"✅ Заказ #{order_data.order_number} {action} из 1С (API)")
        return JSONResponse({
            "success": True,
            "message": f"Заказ #{order_data.order_number} {action}",
            "order_id": order_id,
            "action": action
        })
    except Exception as e:
        print(f"❌ Ошибка при приеме заказа из 1С: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# ЗАКАЗЫ
# ============================================================
@app.get("/api/orders")
async def get_orders(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    master: Optional[str] = None,
    status: Optional[str] = None,  # Add status parameter
    current_user: dict = Depends(get_current_user)
):
    try:
        if current_user["role"] in ['admin', 'superadmin']:
            results = db.get_all_orders_filtered(limit, offset, search, master, status) # New function to handle all filters
            total = db.count_all_orders_filtered(search, master, status) # New function to count filtered orders
        else:
            # For regular users, apply filters after fetching their specific orders
            user_orders = db.get_user_orders(current_user["user_id"], "user")
            
            if search:
                search_lower = search.lower()
                user_orders = [o for o in user_orders if search_lower in (o.get('order_number') or '').lower() or search_lower in (o.get('client_name') or '').lower() or search_lower in (o.get('phone') or '').lower()]
            
            if master:
                user_orders = [o for o in user_orders if o.get('master') == master]
            
            if status and status != 'all': # Apply status filter for regular users
                user_orders = [o for o in user_orders if o.get('status') == status]

            total = len(user_orders)
            results = user_orders[offset:offset + limit]
        
        return JSONResponse({
            "success": True,
            "data": results,
            "pagination": {"limit": limit, "offset": offset, "total": total, "role": current_user["role"]}
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/orders/{order_id}")
async def get_order(order_id: int, current_user: dict = Depends(get_current_user)):
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
            order = cursor.fetchone()
            if not order:
                raise HTTPException(status_code=404, detail="Заказ не найден")
            if current_user["role"] not in ['admin', 'superadmin']:
                user_id = current_user["user_id"]
                phone = order['phone'] or ''
                client_name = order['client_name'] or ''
                if user_id not in phone and user_id not in client_name:
                    raise HTTPException(status_code=403, detail="Доступ запрещен")
            cursor.execute('SELECT * FROM order_history WHERE order_id = ? ORDER BY changed_at DESC', (order_id,))
            history = [dict(row) for row in cursor.fetchall()]
            result = dict(order)
            result['history'] = history
            return JSONResponse({"success": True, "data": result})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/orders/by-number/{order_number}")
async def get_order_by_number(order_number: str, current_user: dict = Depends(get_current_user)):
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM orders WHERE order_number = ?', (order_number,))
            order = cursor.fetchone()
            if not order:
                raise HTTPException(status_code=404, detail="Заказ не найден")
            if current_user["role"] not in ['admin', 'superadmin']:
                user_id = current_user["user_id"]
                phone = order['phone'] or ''
                client_name = order['client_name'] or ''
                if user_id not in phone and user_id not in client_name:
                    raise HTTPException(status_code=403, detail="Доступ запрещен")
            order_id = order['id']
            cursor.execute('SELECT * FROM order_history WHERE order_id = ? ORDER BY changed_at DESC', (order_id,))
            history = [dict(row) for row in cursor.fetchall()]
            result = dict(order)
            result['history'] = history
            return JSONResponse({"success": True, "data": result})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# МАСТЕРА (С ЛОГАМИ)
# ============================================================
@app.get("/api/masters")
async def get_masters(current_user: dict = Depends(get_current_user)):
    """Получить список всех мастеров из поля master"""
    try:
        masters = db.get_masters()
        print(f"📋 API: Загружено мастеров: {len(masters)} - {masters}")
        return JSONResponse({"success": True, "data": masters})
    except Exception as e:
        print(f"❌ Ошибка получения мастеров: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# ПОДСЧЁТ ЗАКАЗОВ ПО СТАТУСАМ
# ============================================================
@app.get("/api/status-counts")
async def get_status_counts(current_user: dict = Depends(get_current_user)):
    """Получить количество заказов по статусам"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT status, COUNT(*) as count 
                FROM orders 
                GROUP BY status
                ORDER BY count DESC
            ''')
            status_counts = [dict(row) for row in cursor.fetchall()]
        return JSONResponse({"success": True, "data": status_counts})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# СТАТИСТИКА
# ============================================================
@app.get("/api/statistics")
async def get_statistics(current_user: dict = Depends(get_current_user)):
    try:
        if current_user["role"] in ['admin', 'superadmin']:
            stats = db.get_statistics()
        else:
            user_orders = db.get_user_orders(current_user["user_id"], "user")
            stats = {
                'total': len(user_orders),
                'today': len([o for o in user_orders if o.get('date') == datetime.now().strftime('%Y-%m-%d')]),
                'by_status': []
            }
            status_count = {}
            for o in user_orders:
                s = o.get('status', 'Без статуса')
                status_count[s] = status_count.get(s, 0) + 1
            stats['by_status'] = [{'status': k, 'count': v} for k, v in status_count.items()]
        return JSONResponse({"success": True, "data": stats})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# АДМИНСКАЯ АНАЛИТИКА
# ============================================================
@app.get("/api/admin/dashboard")
async def get_dashboard_stats(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in ['admin', 'superadmin']:
        raise HTTPException(status_code=403, detail="Доступ запрещен. Требуются права администратора.")
    try:
        stats = db.get_detailed_stats(month, year)
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            date_filter = ""
            params = []
            if month and year:
                date_filter = " WHERE strftime('%m', date) = ? AND strftime('%Y', date) = ?"
                params = [str(month).zfill(2), str(year)]
            
            cursor.execute(f'''
                SELECT master, COUNT(*) as count 
                FROM orders 
                WHERE master IS NOT NULL AND master != ''
                {date_filter.replace('WHERE', 'AND') if date_filter else ''}
                GROUP BY master
                ORDER BY count DESC
            ''', params)
            by_master = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute(f'''
                SELECT master, COUNT(*) as count 
                FROM orders 
                WHERE master IS NOT NULL AND master != ''
                AND status = 'Выдано (оплачено)'
                {date_filter.replace('WHERE', 'AND') if date_filter else ''}
                GROUP BY master
                ORDER BY count DESC
            ''', params)
            by_master_done = [dict(row) for row in cursor.fetchall()]
        
        return JSONResponse({
            "success": True,
            "data": {
                **stats,
                "by_master": by_master,
                "by_master_done": by_master_done
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# ПОИСК
# ============================================================
@app.get("/api/search")
async def search_orders(
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    try:
        if current_user["role"] in ['admin', 'superadmin']:
            results = db.search_orders(q)
            total = len(results)
            results = results[:limit]
        else:
            user_orders = db.get_user_orders(current_user["user_id"], "user")
            search_lower = q.lower()
            results = [o for o in user_orders if search_lower in (o.get('order_number') or '').lower() or search_lower in (o.get('client_name') or '').lower() or search_lower in (o.get('phone') or '').lower() or search_lower in (o.get('device') or '').lower()]
            total = len(results)
            results = results[:limit]
        return JSONResponse({"success": True, "data": results, "total": total, "limit": limit})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# ЗАДАЧИ (НОВЫЙ РАЗДЕЛ)
# ============================================================

@app.get("/api/tasks")
async def get_tasks(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Получить список задач"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            if status == 'completed':
                cursor.execute("""
                    SELECT id, task_text, author, completed_by, completion_time 
                    FROM completed_tasks 
                    ORDER BY id DESC 
                    LIMIT 100
                """)
                rows = cursor.fetchall()
                return JSONResponse({
                    "success": True,
                    "data": [dict(row) for row in rows],
                    "type": "completed"
                })
            else:
                # Активные задачи
                query = "SELECT * FROM pending_tasks ORDER BY id DESC"
                params = []
                
                if status == 'my':
                    query = "SELECT * FROM pending_tasks WHERE taken_by_id = ? ORDER BY id DESC"
                    params = [current_user['user_id']]
                elif status == 'pending':
                    query = "SELECT * FROM pending_tasks WHERE taken_by_id IS NULL ORDER BY id DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return JSONResponse({
                    "success": True,
                    "data": [dict(row) for row in rows],
                    "type": "pending"
                })
    except Exception as e:
        print(f"❌ Ошибка получения задач: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks")
async def create_task(
    task_data: TaskCreate,
    current_user: dict = Depends(get_current_user)
):
    """Создать новую задачу"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pending_tasks 
                (text, author, author_id, priority, deadline, order_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                task_data.text,
                current_user['full_name'],
                current_user['user_id'],
                task_data.priority,
                task_data.deadline,
                task_data.order_id,
                now_iso()
            ))
            task_id = cursor.lastrowid
            conn.commit()
            return JSONResponse({
                "success": True,
                "message": "Задача создана",
                "task_id": task_id
            })
    except Exception as e:
        print(f"❌ Ошибка создания задачи: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/tasks/{task_id}/take")
async def take_task(
    task_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Взять задачу в работу"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE pending_tasks 
                SET taken_by = ?, taken_by_id = ?, taken_at = ?
                WHERE id = ? AND taken_by_id IS NULL
            """, (current_user['full_name'], current_user['user_id'], now_iso(), task_id))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=400, detail="Задача уже взята или не найдена")
            conn.commit()
            return JSONResponse({"success": True, "message": "Задача взята в работу"})
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка взятия задачи: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/tasks/{task_id}/complete")
async def complete_task(
    task_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Завершить задачу"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pending_tasks WHERE id = ?", (task_id,))
            task = dict(cursor.fetchone())  # Преобразуем Row в dict
            if not task:
                raise HTTPException(status_code=404, detail="Задача не найдена")
            
            if task.get('taken_by_id') != current_user['user_id'] and current_user['role'] not in ['admin', 'superadmin']:
                raise HTTPException(status_code=403, detail="Вы не можете завершить эту задачу")
            
            cursor.execute("""
                INSERT INTO completed_tasks (task_text, author, completed_by, completion_time, order_id)
                VALUES (?, ?, ?, ?, ?)
            """, (task.get('text'), task.get('author'), current_user['full_name'], now_iso(), task.get('order_id')))
            
            # Удаляем из активных
            cursor.execute("DELETE FROM pending_tasks WHERE id = ?", (task_id,))
            conn.commit()
            return JSONResponse({"success": True, "message": "Задача завершена"})
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка завершения задачи: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/tasks/{task_id}")
async def delete_task(
    task_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Удалить задачу (только админ)"""
    if current_user["role"] not in ['admin', 'superadmin']:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pending_tasks WHERE id = ?", (task_id,))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Задача не найдена")
            conn.commit()
            return JSONResponse({"success": True, "message": "Задача удалена"})
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка удаления задачи: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/tasks/{task_id}/reassign")
async def reassign_task(
    task_id: int,
    reassign_data: TaskReassign,
    current_user: dict = Depends(get_current_user)
):
    """Переназначить задачу (только админ)"""
    if current_user["role"] not in ['admin', 'superadmin']:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    
    try:
        # Получаем нового исполнителя
        new_executor = db.get_user(str(reassign_data.new_executor_id))
        if not new_executor:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE pending_tasks 
                SET taken_by = ?, taken_by_id = ?, taken_at = ?
                WHERE id = ?
            """, (new_executor['full_name'], reassign_data.new_executor_id, now_iso(), task_id))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Задача не найдена")
            conn.commit()
            return JSONResponse({
                "success": True, 
                "message": f"Задача переназначена на {new_executor['full_name']}"
            })
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка переназначения задачи: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Отказаться от задачи (снять с себя)"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE pending_tasks 
                SET taken_by = NULL, taken_by_id = NULL, taken_at = NULL
                WHERE id = ? AND taken_by_id = ?
            """, (task_id, current_user['user_id']))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=400, detail="Вы не являетесь исполнителем этой задачи")
            conn.commit()
            return JSONResponse({"success": True, "message": "Вы отказались от задачи"})
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка отказа от задачи: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks/stats")
async def get_tasks_stats(current_user: dict = Depends(get_current_user)):
    """Получить статистику по задачам"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Всего активных задач
            cursor.execute("SELECT COUNT(*) FROM pending_tasks")
            total_pending = cursor.fetchone()[0]
            
            # Мои задачи
            cursor.execute("SELECT COUNT(*) FROM pending_tasks WHERE taken_by_id = ?", (current_user['user_id'],))
            my_tasks = cursor.fetchone()[0]
            
            # Доступные задачи
            cursor.execute("SELECT COUNT(*) FROM pending_tasks WHERE taken_by_id IS NULL")
            available_tasks = cursor.fetchone()[0]
            
            # Выполненные сегодня
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("SELECT COUNT(*) FROM completed_tasks WHERE completion_time LIKE ?", (today + '%',))
            completed_today = cursor.fetchone()[0]
            
            return JSONResponse({
                "success": True,
                "data": {
                    "total_pending": total_pending,
                    "my_tasks": my_tasks,
                    "available_tasks": available_tasks,
                    "completed_today": completed_today
                }
            })
    except Exception as e:
        print(f"❌ Ошибка получения статистики задач: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# HEALTH
# ============================================================
@app.get("/health")
async def health_check():
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.execute('SELECT COUNT(*) as count FROM orders')
            count = cursor.fetchone()['count']
        return JSONResponse({
            "status": "healthy",
            "database": "connected",
            "orders_count": count,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

# ============================================================
# ЗАПУСК ПРИ СТАРТЕ (в конце файла)
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=3000)
