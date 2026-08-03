#!/usr/bin/env python3
"""
Модуль для парсинга заказов из текста сообщений 1С
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any
from models import Order


class OrderParser:
    """Парсер заказов из текстовых сообщений"""
    
    @staticmethod
    def parse(text: str) -> Optional[Order]:
        """
        Парсит текст сообщения и возвращает объект заказа
        
        Args:
            text: Текст сообщения из Telegram
            
        Returns:
            Объект Order или None, если парсинг не удался
        """
        if not text or not isinstance(text, str):
            return None
        
        lines = text.strip().split('\n')
        order_data = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Парсим каждую строку
            if 'Номер заказа:' in line or 'Номер заказа' in line:
                parts = line.split(':', 1)
                if len(parts) > 1:
                    order_data['order_number'] = parts[1].strip()
                    
            elif 'Дата приема:' in line or 'Дата приема' in line:
                parts = line.split(':', 1)
                if len(parts) > 1:
                    order_data['date_raw'] = parts[1].strip()
                    order_data['date'] = OrderParser._parse_date(parts[1].strip())
                    
            elif 'Статус:' in line or 'Статус' in line:
                parts = line.split(':', 1)
                if len(parts) > 1:
                    order_data['status'] = parts[1].strip()
                    
            elif 'Приёмщик:' in line or 'Приёмщик' in line or 'Приемщик:' in line:
                parts = line.split(':', 1)
                if len(parts) > 1:
                    order_data['receiver'] = parts[1].strip()
                    
            elif 'Номер телефона:' in line or 'Номер телефона' in line or 'Телефон:' in line:
                parts = line.split(':', 1)
                if len(parts) > 1:
                    order_data['phone'] = parts[1].strip()
                    
            elif 'ФИО:' in line or 'ФИО' in line or 'Клиент:' in line:
                parts = line.split(':', 1)
                if len(parts) > 1:
                    order_data['client_name'] = parts[1].strip()
                    
            elif 'Устройство:' in line or 'Устройство' in line or 'Оборудование:' in line:
                parts = line.split(':', 1)
                if len(parts) > 1:
                    order_data['device'] = parts[1].strip()
                    
            elif 'Неисправность:' in line or 'Неисправность' in line or 'Проблема:' in line:
                parts = line.split(':', 1)
                if len(parts) > 1:
                    order_data['problem'] = parts[1].strip()
        
        # Проверяем, что обязательные поля есть
        if 'order_number' not in order_data:
            return None
        
        # Создаем объект заказа
        return Order(
            order_number=order_data.get('order_number'),
            date=order_data.get('date'),
            status=order_data.get('status'),
            receiver=order_data.get('receiver'),
            phone=order_data.get('phone'),
            client_name=order_data.get('client_name'),
            device=order_data.get('device'),
            problem=order_data.get('problem')
        )
    
    @staticmethod
    def _parse_date(date_str: str) -> Optional[str]:
        """Парсит дату из строки в формат YYYY-MM-DD"""
        if not date_str:
            return None
            
        try:
            date_match = re.search(r'(\d+)\s+([а-я]+)\s+(\d+)', date_str)
            if date_match:
                day = int(date_match.group(1))
                month_str = date_match.group(2).lower()
                year = int(date_match.group(3))
                
                months = {
                    'января': 1, 'февраля': 2, 'марта': 3,
                    'апреля': 4, 'мая': 5, 'июня': 6,
                    'июля': 7, 'августа': 8, 'сентября': 9,
                    'октября': 10, 'ноября': 11, 'декабря': 12
                }
                month = months.get(month_str)
                if month:
                    return f"{year}-{month:02d}-{day:02d}"
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def is_order_message(text: str) -> bool:
        """Проверяет, является ли сообщение заказом"""
        if not text:
            return False
        
        keywords = ['Номер заказа', 'Статус', 'Устройство', 'Неисправность']
        return all(keyword in text for keyword in keywords)


def test_parser():
    """Тестовая функция для проверки парсера"""
    test_text = """Номер заказа: 043904
Дата приема: 22 июля 2026 г.
Статус: Принят в ремонт
Приёмщик: STASH
Номер телефона: +375339175570
ФИО: Дмитрий
Устройство: Принтер Pantum 5100
Неисправность: Жуёт листы и странный звук при работе."""
    
    parser = OrderParser()
    order = parser.parse(test_text)
    
    if order:
        print("✅ Заказ успешно распарсен:")
        print(f"  Номер: {order.order_number}")
        print(f"  Дата: {order.date}")
        print(f"  Статус: {order.status}")
        print(f"  Приёмщик: {order.receiver}")
        print(f"  Телефон: {order.phone}")
        print(f"  Клиент: {order.client_name}")
        print(f"  Устройство: {order.device}")
        print(f"  Проблема: {order.problem}")
        print(f"\n  Является заказом: {parser.is_order_message(test_text)}")
    else:
        print("❌ Не удалось распарсить заказ")


if __name__ == "__main__":
    test_parser()
