# STASHServiceDesk

Система Service Desk для отслеживания заказов из 1С через Telegram.

## Проекты

- **STASHServiceDesk Orders Bot** - Telegram бот для получения заказов из группы
- **STASHServiceDesk Mini App** - Telegram Mini App для просмотра заказов

## Этап 1: Бот-логгер

Минимальный бот для проверки получения сообщений из группы.

### Установка

```bash
git clone [repository-url]
cd STASHServiceDesk
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows
pip install -r requirements.txt
