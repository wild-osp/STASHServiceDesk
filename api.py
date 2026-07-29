#!/usr/bin/env python3
import os
import threading
import subprocess
import time
from fastapi import FastAPI, HTTPException, Query, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import json

DATA_DIR = os.getenv('DATA_DIR', '/app/data')
os.makedirs(DATA_DIR, exist_ok=True)
os.environ['DB_PATH'] = os.path.join(DATA_DIR, 'orders.db')

from database import get_db
from models import Order

# ============================================================
# АВТОЗАПУСК БОТА ИЗ API
# ============================================================
def run_bot():
    """Запускает бота в отдельном процессе при старте API"""
    time.sleep(5)
    try:
        subprocess.Popen(["python", "orders_bot.py"])
        print("🚀 Бот автоматически запущен из API")
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")

bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

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
# АВТОРИЗАЦИЯ
# ============================================================
async def get_current_user(
    x_user_id: str = Header(default='anonymous')
):
    if x_user_id == 'anonymous':
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    user = db.get_user(x_user_id)
    if not user:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    
    return {
        "user_id": user['telegram_id'],
        "username": user['username'] or '',
        "full_name": user['full_name'] or '',
        "role": user['role'] or 'user',
        "master": user.get('master', ''),
        "phone": user.get('phone', '')
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
    x_user_id: str = Header(default='anonymous'),
    x_username: str = Header(default=''),
    x_full_name: str = Header(default='')
):
    if x_user_id == 'anonymous':
        raise HTTPException(status_code=401, detail="Не авторизован")
    user = db.get_user(x_user_id)
    if not user:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    return JSONResponse({
        "success": True,
        "user": {
            "id": user['telegram_id'],
            "username": user['username'] or '',
            "full_name": user['full_name'] or '',
            "role": user['role'] or 'user',
            "master": user.get('master', ''),
            "phone": user.get('phone', '')
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
    phone: str = "",
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
    success = db.add_user(telegram_id, username, full_name, role, master, phone)
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
    phone: str = "",
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != 'superadmin':
        raise HTTPException(status_code=403, detail="Только суперадмин может редактировать пользователей")
    user = db.get_user(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    updates = {}
    if full_name:
        updates['full_name'] = full_name
    if username:
        updates['username'] = username
    if role and role in ['user', 'admin', 'superadmin']:
        updates['role'] = role
    if master is not None:
        updates['master'] = master
    if phone is not None:
        updates['phone'] = phone
    if not updates:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")
    success = db.update_user(telegram_id, updates)
    if success:
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
        cursor.execute('DELETE FROM order_history WHERE order_id IN (SELECT id FROM orders WHERE order_number = ?)', (order_number,))
        cursor.execute('DELETE FROM orders WHERE order_number = ?', (order_number,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        conn.commit()
    return JSONResponse({"success": True, "message": f"Заказ #{order_number} удален"})

# ============================================================
# ПРИЕМ ЗАКАЗОВ ИЗ 1С - ОСНОВНОЙ (С ПОДРОБНЫМИ ЛОГАМИ)
# ============================================================
@app.post("/api/orders/from-1c")
async def receive_order_from_1c(
    order_data: OrderFrom1C,
    x_api_key: str = Header(...)
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Неверный API-ключ")
    try:
        print("=" * 70)
        print("📦 ПОЛУЧЕН ЗАКАЗ ИЗ 1С")
        print(f"   Номер: {order_data.order_number}")
        print(f"   Статус: '{order_data.status}'")
        print(f"   Клиент: {order_data.client_name}")
        print(f"   Телефон: {order_data.phone}")
        print(f"   Устройство: {order_data.device}")
        print(f"   Мастер: {order_data.master}")
        print("=" * 70)
        
        existing = db.get_order(order_data.order_number)
        if existing:
            print(f"📌 Заказ существует, текущий статус: '{existing.get('status')}'")
        else:
            print("📌 Новый заказ")
        
        order = Order(
            order_number=order_data.order_number,
            date=order_data.date,
            status=order_data.status,
            receiver=order_data.receiver,
            master=order_data.master,
            phone=order_data.phone,
            client_name=order_data.client_name,
            device=order_data.device,
            problem=order_data.problem,
            telegram_chat_id="from_1c_api",
            telegram_message_id=0,
            telegram_message_date=datetime.now().isoformat(),
            raw_message_text=f"Отправлено из 1С через API: {order_data.order_number}"
        )
        
        order_id = db.save_order(order)
        action = "обновлен" if existing else "создан"
        print(f"✅ Заказ #{order_data.order_number} {action} из 1С (API)")
        print("=" * 70)
        
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
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    master: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    try:
        if current_user["role"] in ['admin', 'superadmin']:
            if search:
                results = db.search_orders(search)
                total = len(results)
                results = results[offset:offset + limit]
            else:
                results = db.get_all_orders(limit, offset)
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT COUNT(*) as total FROM orders')
                    total = cursor.fetchone()['total']
        else:
            results = db.get_user_orders(current_user["user_id"], "user")
            total = len(results)
            if search:
                search_lower = search.lower()
                results = [o for o in results if search_lower in (o.get('order_number') or '').lower() or search_lower in (o.get('client_name') or '').lower() or search_lower in (o.get('phone') or '').lower()]
            results = results[offset:offset + limit]
        if master:
            results = [o for o in results if o.get('master') == master]
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
# МАСТЕРА
# ============================================================
@app.get("/api/masters")
async def get_masters(current_user: dict = Depends(get_current_user)):
    try:
        masters = db.get_masters()
        return JSONResponse({"success": True, "data": masters})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# ПОДСЧЁТ ЗАКАЗОВ ПО СТАТУСАМ
# ============================================================
@app.get("/api/status-counts")
async def get_status_counts(current_user: dict = Depends(get_current_user)):
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT status, COUNT(*) as count FROM orders GROUP BY status ORDER BY count DESC')
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
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ['admin', 'superadmin']:
        raise HTTPException(status_code=403, detail="Доступ запрещен. Требуются права администратора.")
    try:
        stats = db.get_detailed_stats()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT master, COUNT(*) as count FROM orders WHERE master IS NOT NULL AND master != "" GROUP BY master ORDER BY count DESC')
            by_master = [dict(row) for row in cursor.fetchall()]
            cursor.execute('SELECT master, COUNT(*) as count FROM orders WHERE master IS NOT NULL AND master != "" AND status = "Выдано (оплачено)" GROUP BY master ORDER BY count DESC')
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=3000)
