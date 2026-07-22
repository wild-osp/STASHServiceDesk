#!/usr/bin/env python3
"""
Модели данных для заказов
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class Order:
    """Модель заказа"""
    order_number: str
    date: Optional[str] = None
    status: Optional[str] = None
    receiver: Optional[str] = None
    phone: Optional[str] = None
    client_name: Optional[str] = None
    device: Optional[str] = None
    problem: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_message_id: Optional[int] = None
    telegram_message_date: Optional[str] = None
    raw_message_text: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь для БД"""
        return {
            'order_number': self.order_number,
            'date': self.date,
            'status': self.status,
            'receiver': self.receiver,
            'phone': self.phone,
            'client_name': self.client_name,
            'device': self.device,
            'problem': self.problem,
            'telegram_chat_id': self.telegram_chat_id,
            'telegram_message_id': self.telegram_message_id,
            'telegram_message_date': self.telegram_message_date,
            'raw_message_text': self.raw_message_text,
            'created_at': self.created_at or datetime.now().isoformat(),
            'updated_at': self.updated_at or datetime.now().isoformat()
        }


@dataclass
class OrderHistory:
    """Модель истории изменений статуса"""
    order_id: int
    status: str
    changed_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'order_id': self.order_id,
            'status': self.status,
            'changed_at': self.changed_at or datetime.now().isoformat()
        }
