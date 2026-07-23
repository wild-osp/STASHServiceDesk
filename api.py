#!/usr/bin/env python3
import os
import threading
import subprocess
import time
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from typing import Optional

DATA_DIR = os.getenv('DATA_DIR', '/app/data')
os.makedirs(DATA_DIR, exist_ok=True)
os.environ['DB_PATH'] = os.path.join(DATA_DIR, 'orders.db')

from database import get_db

# Функция для запуска бота
def run_bot():
    """Запускает бота в отдельном процессе"""
    time.sleep(3)  # Ждем, пока API запустится
    print("🚀 Запуск бота из API...")
    subprocess.Popen(["python", "orders_bot.py"])

# Запускаем бота в фоновом потоке
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

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

@app.get("/")
async def root():
    return {"name": "STASHServiceDesk API", "status": "running", "timestamp": datetime.now().isoformat()}

@app.get("/app")
async def serve_app():
    return FileResponse("static/index.html")

@app.get("/api/orders")
async def get_orders(limit: int = Query(50), offset: int = Query(0), search: Optional[str] = None):
    try:
        if search:
            results = db.search_orders(search)
            total = len(results)
            results = results[offset:offset + limit]
        else:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM orders ORDER BY created_at DESC LIMIT ? OFFSET ?', (limit, offset))
                results = [dict(row) for row in cursor.fetchall()]
                cursor.execute('SELECT COUNT(*) as total FROM orders')
                total = cursor.fetchone()['total']
        return JSONResponse({"success": True, "data": results, "pagination": {"limit": limit, "offset": offset, "total": total}})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/orders/{order_id}")
async def get_order(order_id: int):
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
            order = cursor.fetchone()
            if not order:
                raise HTTPException(status_code=404, detail="Заказ не найден")
            cursor.execute('SELECT * FROM order_history WHERE order_id = ? ORDER BY changed_at DESC', (order_id,))
            history = [dict(row) for row in cursor.fetchall()]
            result = dict(order)
            result['history'] = history
            return JSONResponse({"success": True, "data": result})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/statistics")
async def get_statistics():
    try:
        stats = db.get_statistics()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT receiver, COUNT(*) as count FROM orders WHERE receiver IS NOT NULL GROUP BY receiver ORDER BY count DESC')
            by_receiver = [dict(row) for row in cursor.fetchall()]
            cursor.execute('SELECT device, COUNT(*) as count FROM orders WHERE device IS NOT NULL GROUP BY device ORDER BY count DESC LIMIT 10')
            by_device = [dict(row) for row in cursor.fetchall()]
        return JSONResponse({"success": True, "data": {**stats, "by_receiver": by_receiver, "by_device": by_device}})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search")
async def search_orders(q: str = Query(...), limit: int = Query(50)):
    try:
        results = db.search_orders(q)
        total = len(results)
        results = results[:limit]
        return JSONResponse({"success": True, "data": results, "total": total})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.execute('SELECT COUNT(*) as count FROM orders')
            count = cursor.fetchone()['count']
        return JSONResponse({"status": "healthy", "database": "connected", "orders_count": count, "timestamp": datetime.now().isoformat()})
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "database": "disconnected", "error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=3000)
