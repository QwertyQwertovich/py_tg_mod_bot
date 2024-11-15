
# Telegram Модератор Бот

Этот бот создан для автоматизации задач модерации в Telegram-чатах. Он предоставляет инструменты для управления предупреждениями, блокировками, назначением модераторов и других административных действий.

## Возможности

1. **Автоматическое управление активностью пользователей**:
   - Если пользователь отправляет более 10 сообщений за 3 минуты, он временно блокируется на 3 минуты.

2. **Команды**:
   - `/warn <причина>` — Выдать предупреждение пользователю (по ответу на его сообщение). После 3 предупреждений пользователь блокируется на неделю.
   - `/unwarn` — Снять предупреждение у пользователя.
   - `/ban <срок> <причина>` — Заблокировать пользователя на указанный срок:
     - `1д` — 1 день
     - `5ч` — 5 часов
     - `30м` — 30 минут
   - `/unban` — Разблокировать пользователя.
   - `/remove` — Удалить пользователя из чата.
   - `/mod` — Назначить пользователя модератором.
   - `/unmod` — Удалить пользователя из модераторов.

3. **Уведомления**:
   - Все действия отправляются администраторам в личные сообщения.

## Установка

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Создайте файл `settings.py` в директории проекта и добавьте туда:
   ```python
   api_key = "ВАШ_API_КЛЮЧ_БОТА"
   admins = [СПИСОК_ID_АДМИНИСТРАТОРОВ]
   chats = [СПИСОК_ID_ЧАТОВ_ГДЕ_БУДЕТ_РАБОТАТЬ_БОТ]
   ```

3. Запустите бота:
   ```bash
   python main.py
   ```

## Зависимости

- `aiogram` — Фреймворк для разработки Telegram-ботов.
- `aiosqlite` — Для хранения данных о предупреждениях и блокировках.

## Как работает бот

- Бот обрабатывает сообщения только из чатов, указанных в `settings.chats`.
- Все команды требуют, чтобы пользователь был администратором или модератором.
- Для управления активностью пользователей бот отслеживает количество сообщений за последние 3 минуты.

## Лицензия
CC BY-NC-SA 4.0
Текст: https://creativecommons.org/licenses/by-nc-sa/4.0/