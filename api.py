#!/usr/bin/env python3
"""
STASHServiceDesk API
REST API для Telegram Mini App
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
from datetime import datetime
from typing import Optional

from database import get_db

app = FastAPI(
    title="STASHServiceDesk API",
    description="API для управления заказами сервисного центра",
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = get_db()


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "name": "STASHServiceDesk API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/orders")
async def get_orders(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None
):
    """Получить список заказов"""
    try:
        if search:
            results = db.search_orders(search)
            total = len(results)
            results = results[offset:offset + limit]
        else:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM orders 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
                results = [dict(row) for row in cursor.fetchall()]
                cursor.execute('SELECT COUNT(*) as total FROM orders')
                total = cursor.fetchone()['total']
        
        return JSONResponse({
            "success": True,
            "data": results,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/orders/{order_id}")
async def get_order(order_id: int):
    """Получить заказ по ID"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
            order = cursor.fetchone()
            
            if not order:
                raise HTTPException(status_code=404, detail="Заказ не найден")
            
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
async def get_order_by_number(order_number: str):
    """Получить заказ по номеру"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM orders WHERE order_number = ?', (order_number,))
            order = cursor.fetchone()
            
            if not order:
                raise HTTPException(status_code=404, detail="Заказ не найден")
            
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


@app.get("/api/statistics")
async def get_statistics():
    """Получить статистику"""
    try:
        stats = db.get_statistics()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT receiver, COUNT(*) as count 
                FROM orders 
                WHERE receiver IS NOT NULL
                GROUP BY receiver
                ORDER BY count DESC
            ''')
            by_receiver = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute('''
                SELECT device, COUNT(*) as count 
                FROM orders 
                WHERE device IS NOT NULL
                GROUP BY device
                ORDER BY count DESC
                LIMIT 10
            ''')
            by_device = [dict(row) for row in cursor.fetchall()]
        
        return JSONResponse({
            "success": True,
            "data": {
                **stats,
                "by_receiver": by_receiver,
                "by_device": by_device
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search")
async def search_orders(
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=100)
):
    """Поиск заказов"""
    try:
        results = db.search_orders(q)
        results = results[:limit]
        
        return JSONResponse({
            "success": True,
            "data": results,
            "total": len(results)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Проверка состояния API"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
        
        return JSONResponse({
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
