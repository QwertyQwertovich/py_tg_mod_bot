import logging
import asyncio
import re
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ChatPermissions
from aiogram.filters import Command, CommandObject
import aiosqlite
from collections import defaultdict
from datetime import datetime, timedelta

from settings import api_key, admins, chats # Не забудьте создать settings.py, в котором будет api_key, admins[], chats[]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=api_key)
dp = Dispatcher()


# Инициализация базы данных
DB_PATH = "moderation.db"

# Глобальные переменные
moderators = set()  # Список модераторов
message_history = defaultdict(list)
old_cooldown = 0
user_messages = defaultdict(list)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            user_id INTEGER PRIMARY KEY,
            warns INTEGER DEFAULT 0
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS bans (
            user_id INTEGER PRIMARY KEY,
            until TIMESTAMP
        )""")
        await db.commit()


# Проверка, является ли пользователь админом или модератором
def is_admin(user_id):
    return user_id in admins or user_id in moderators


# Утилита для хранения данных
async def get_warn_count(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT warns FROM warnings WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0


async def increment_warn(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO warnings (user_id, warns) VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET warns = warns + 1",
            (user_id,)
        )
        await db.commit()


async def reset_warn(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM warnings WHERE user_id = ?", (user_id,))
        await db.commit()


async def ban_user_in_db(user_id, until):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO bans (user_id, until) VALUES (?, ?)", (user_id, until))
        await db.commit()


async def unban_user_in_db(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM bans WHERE user_id = ?", (user_id,))
        await db.commit()


async def notify_admins(text: str):
    for admin in admins:
        try:
            await bot.send_message(admin, text)
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение админу {admin}: {e}")


# Команда /warn
@dp.message(Command("warn"), F.reply_to_message, F.chat.id.in_(chats))
async def warn_user(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return await message.reply("У вас нет прав на выполнение этой команды.")
    target_user = message.reply_to_message.from_user
    await increment_warn(target_user.id)
    warns = await get_warn_count(target_user.id)
    reason = command.args or "Без указания причины"
    await message.reply(
        f"{target_user.full_name} получил предупреждение. Причина: {reason}. Количество предупреждений: {warns}"
    )
    await notify_admins(
        f"Пользователь {target_user.full_name} ({target_user.id}) получил предупреждение в чате {message.chat.title}. Причина: {reason}. Количество предупреждений: {warns}")
    if warns >= 3:
        until = datetime.now() + timedelta(days=30)
        await ban_user_in_db(target_user.id, until)
        await message.chat.restrict(
            target_user.id, ChatPermissions(can_send_messages=False), until_date=until
        )
        await message.reply(f"{target_user.full_name} заблокирован на неделю из-за 3 предупреждений.")
        await notify_admins(
            f"Пользователь {target_user.full_name} ({target_user.id}) заблокирован на неделю в чате {message.chat.title} из-за 3 предупреждений.")


# Команда /unwarn
@dp.message(Command("unwarn"), F.reply_to_message, F.chat.id.in_(chats))
async def unwarn_user(message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply("У вас нет прав на выполнение этой команды.")
    target_user = message.reply_to_message.from_user
    await reset_warn(target_user.id)
    await message.reply(f"С {target_user.full_name} сняты все предупреждения.")


# Команда /ban
@dp.message(Command("ban"), F.reply_to_message, F.chat.id.in_(chats))
async def ban_user(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return await message.reply("У вас нет прав на выполнение этой команды.")
    target_user = message.reply_to_message.from_user
    args = command.args.split(" ", 1)
    duration = args[0].lower()
    reason = args[1] if len(args) > 1 else "Без указания причины"

    match = re.match(r"(\d+)([дчм])", duration)
    if not match:
        return await message.reply("Неверный формат срока. Используйте: `<число><срок>` (например, 7д, 5ч, 30м).")
    amount, unit = int(match[1]), match[2]
    if unit == "д":
        until = datetime.now() + timedelta(days=amount)
    elif unit == "ч":
        until = datetime.now() + timedelta(hours=amount)
    elif unit == "м":
        until = datetime.now() + timedelta(minutes=amount)
    else:
        return await message.reply("Неверный срок.")

    await ban_user_in_db(target_user.id, until)
    await message.chat.restrict(
        target_user.id, ChatPermissions(can_send_messages=False), until_date=until
    )
    await message.reply(f"{target_user.full_name} заблокирован на {duration}. Причина: {reason}")
    await notify_admins(
        f"Пользователь {target_user.full_name} ({target_user.id}) заблокирован на {duration} в чате {message.chat.title}. Причина: {reason}.")


# Команда /unban
@dp.message(Command("unban"), F.reply_to_message, F.chat.id.in_(chats))
async def unban_user(message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply("У вас нет прав на выполнение этой команды.")
    target_user = message.reply_to_message.from_user
    await unban_user_in_db(target_user.id)
    await message.chat.restrict(target_user.id, ChatPermissions(can_send_messages=True))
    await message.reply(f"{target_user.full_name} разблокирован.")
    await notify_admins(
        f"Пользователь {target_user.full_name} ({target_user.id}) разблокирован в чате {message.chat.title}.")


# Команда /remove
@dp.message(Command("remove"), F.reply_to_message, F.chat.id.in_(chats))
async def remove_user(message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply("У вас нет прав на выполнение этой команды.")
    target_user = message.reply_to_message.from_user
    try:
        await bot.ban_chat_member(message.chat.id, target_user.id)
        await message.reply(f"{target_user.full_name} удален из чата.")
        await notify_admins(
            f"Пользователь {target_user.full_name} ({target_user.id}) удален из чата {message.chat.title}.")
    except Exception as e:
        await message.reply(f"Не удалось удалить {target_user.full_name}. Ошибка: {e}")


# Команда /mod
@dp.message(Command("mod"), F.reply_to_message, F.chat.id.in_(chats))
async def add_moderator(message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply("Только администраторы могут добавлять модераторов.")
    target_user = message.reply_to_message.from_user
    moderators.add(target_user.id)
    await message.reply(f"{target_user.full_name} добавлен в модераторы.")
    await notify_admins(
        f"Пользователь {target_user.full_name} ({target_user.id}) добавлен в модераторы чата {message.chat.title}.")


@dp.message(Command("unmod"), F.reply_to_message, F.chat.id.in_(chats))
async def remove_moderator(message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply("Только администраторы могут удалять модераторов.")
    target_user = message.reply_to_message.from_user
    if target_user.id in moderators:
        moderators.remove(target_user.id)
        await message.reply(f"{target_user.full_name} удален из модераторов.")
        await notify_admins(
            f"Пользователь {target_user.full_name} ({target_user.id}) удален из модераторов чата {message.chat.title}.")
    else:
        await message.reply(f"{target_user.full_name} не является модератором.")


async def check_user_activity(user_id, chat_id):
    now = datetime.now()
    # Очищаем старые сообщения
    user_messages[user_id] = [msg_time for msg_time in user_messages[user_id] if now - msg_time <= timedelta(minutes=3)]
    # Проверяем количество сообщений за 3 минуты
    if len(user_messages[user_id]) > 10:
        until = now + timedelta(minutes=3)
        await bot.restrict_chat_member(
            chat_id,
            user_id,
            ChatPermissions(can_send_messages=False),
            until_date=until
        )
        await bot.send_message(
            chat_id,
            f"Пользователь был автоматически временно заблокирован на 3 минуты за превышение лимита сообщений.  "
        )
        # Очищаем сообщения пользователя, чтобы не сработало повторно
        user_messages[user_id] = []

# Обработчик сообщений
@dp.message(F.chat.id.in_(chats))
async def track_messages(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    now = datetime.now()

    # Добавляем сообщение пользователя в список
    user_messages[user_id].append(now)

    # Проверяем активность пользователя
    await check_user_activity(user_id, chat_id)


# Старт бота
async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
