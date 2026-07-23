#!/usr/bin/env python3
import os
import threading
import subprocess
import time
from fastapi import FastAPI, HTTPException, Query, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from typing import Optional

DATA_DIR = os.getenv('DATA_DIR', '/app/data')
os.makedirs(DATA_DIR, exist_ok=True)
os.environ['DB_PATH'] = os.path.join(DATA_DIR, 'orders.db')

from database import get_db

# ============================================================
# ЗАПУСК БОТА ИЗ API
# ============================================================
def run_bot():
    """Запускает бота в отдельном процессе"""
    time.sleep(3)
    try:
        subprocess.Popen(["python", "orders_bot.py"])
        print("🚀 Бот запущен из API")
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")

# Запускаем бота в фоновом потоке
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
# АВТОРИЗАЦИЯ (упрощенная модель)
# ============================================================
async def get_current_user(
    x_user_role: str = Header(default='user'),
    x_user_id: str = Header(default='anonymous')
):
    """
    Проверяем роль пользователя.
    В реальном проекте тут должна быть JWT или проверка по Telegram ID.
    """
    return {"role": x_user_role, "user_id": x_user_id}

# ============================================================
# ЭНДПОИНТЫ
# ============================================================
@app.get("/")
async def root():
    return {"name": "STASHServiceDesk API", "status": "running", "timestamp": datetime.now().isoformat()}

@app.get("/app")
async def serve_app():
    return FileResponse("static/index.html")

# ---------- ЗАКАЗЫ (с проверкой роли) ----------
@app.get("/api/orders")
async def get_orders(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Получить список заказов с учетом прав пользователя"""
    try:
        if current_user["role"] == "admin":
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
            # Обычный пользователь — только свои заказы
            results = db.get_user_orders(current_user["user_id"], "user")
            total = len(results)
            if search:
                search_lower = search.lower()
                results = [o for o in results if 
                          search_lower in (o.get('order_number') or '').lower() or
                          search_lower in (o.get('client_name') or '').lower() or
                          search_lower in (o.get('phone') or '').lower()]
            results = results[offset:offset + limit]
        
        return JSONResponse({
            "success": True,
            "data": results,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total,
                "role": current_user["role"]
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/orders/{order_id}")
async def get_order(order_id: int, current_user: dict = Depends(get_current_user)):
    """Получить заказ по ID с историей статусов"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
            order = cursor.fetchone()
            
            if not order:
                raise HTTPException(status_code=404, detail="Заказ не найден")
            
            # Проверка прав: если не админ, проверяем, что заказ принадлежит пользователю
            if current_user["role"] != "admin":
                user_id = current_user["user_id"]
                phone = order['phone'] or ''
                client_name = order['client_name'] or ''
                if user_id not in phone and user_id not in client_name:
                    raise HTTPException(status_code=403, detail="Доступ запрещен")
            
            cursor.execute('''
                SELECT * FROM order_history 
                WHERE order_id = ? 
                ORDER BY changed_at DESC
            ''', (order_id,))
            history = [dict(row) for row in cursor.fetchall()]
            
            result = dict(order)
            result['history'] = history
            
            return JSONResponse({
                "success": True,
                "data": result
            })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/orders/by-number/{order_number}")
async def get_order_by_number(order_number: str, current_user: dict = Depends(get_current_user)):
    """Получить заказ по номеру"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM orders WHERE order_number = ?', (order_number,))
            order = cursor.fetchone()
            
            if not order:
                raise HTTPException(status_code=404, detail="Заказ не найден")
            
            # Проверка прав
            if current_user["role"] != "admin":
                user_id = current_user["user_id"]
                phone = order['phone'] or ''
                client_name = order['client_name'] or ''
                if user_id not in phone and user_id not in client_name:
                    raise HTTPException(status_code=403, detail="Доступ запрещен")
            
            order_id = order['id']
            
            cursor.execute('''
                SELECT * FROM order_history 
                WHERE order_id = ? 
                ORDER BY changed_at DESC
            ''', (order_id,))
            history = [dict(row) for row in cursor.fetchall()]
            
            result = dict(order)
            result['history'] = history
            
            return JSONResponse({
                "success": True,
                "data": result
            })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- СТАТИСТИКА ----------
@app.get("/api/statistics")
async def get_statistics(current_user: dict = Depends(get_current_user)):
    """Базовая статистика (доступна всем)"""
    try:
        if current_user["role"] == "admin":
            stats = db.get_statistics()
        else:
            # Для пользователя — статистика только по его заказам
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
        
        return JSONResponse({
            "success": True,
            "data": stats
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- АДМИНСКАЯ АНАЛИТИКА ----------
@app.get("/api/admin/dashboard")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    """Расширенная аналитика — только для администраторов"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Доступ запрещен. Требуются права администратора.")
    
    try:
        stats = db.get_detailed_stats()
        return JSONResponse({
            "success": True,
            "data": stats
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- ПОИСК ----------
@app.get("/api/search")
async def search_orders(
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Поиск заказов по всем полям"""
    try:
        if current_user["role"] == "admin":
            results = db.search_orders(q)
            total = len(results)
            results = results[:limit]
        else:
            # Поиск только среди своих заказов
            user_orders = db.get_user_orders(current_user["user_id"], "user")
            search_lower = q.lower()
            results = [o for o in user_orders if 
                      search_lower in (o.get('order_number') or '').lower() or
                      search_lower in (o.get('client_name') or '').lower() or
                      search_lower in (o.get('phone') or '').lower() or
                      search_lower in (o.get('device') or '').lower()]
            total = len(results)
            results = results[:limit]
        
        return JSONResponse({
            "success": True,
            "data": results,
            "total": total,
            "limit": limit
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- HEALTH ----------
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
