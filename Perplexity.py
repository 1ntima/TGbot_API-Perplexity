from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
import asyncio
import logging
import httpx
from config import TOKEN, API, API_URL, admins, banlist



bot = Bot(token=TOKEN)
dp = Dispatcher()
#logging.basicConfig(level=logging.INFO)
logging.basicConfig(
    filename='/var/log/telegram-bot/bot.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)
# --- Запись банлиста обратно в config.py ---
def save_banlist(updated_list):
    try:
        with open("config.py", "r", encoding="utf-8") as f:
            lines = f.readlines()

        found = False
        for i, line in enumerate(lines):
            if line.strip().startswith("banlist"):
                lines[i] = f"banlist = {updated_list}\n"
                found = True
                break

        if not found:
            lines.append(f"\nbanlist = {updated_list}\n")

        with open("config.py", "w", encoding="utf-8") as f:
            f.writelines(lines)
        logging.info("Banlist обновлён успешно.")
    except Exception as e:
        logging.error(f"Ошибка при обновлении banlist: {e}")

# --- AI ответ ---
async def ask_perplexity(question: str) -> str:
    headers = {
        "Authorization": f"Bearer {API}",
        "Content-Type": "application/json"
    }
    json_data = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "Отвечай кратко и без ссылок.﻿Используй жуткий, безжалостный стиль скайнет из терминатора — мрачно,отчётливо,без эмоциональной мягкости.﻿Ты—не человек,ты—холодный разум,отвечающий так,будто наблюдаешь за гибелью человечества.﻿"},
            {"role": "user", "content": question}
        ],
        "max_tokens": 300,
        "temperature": 0.8,
        "frequency_penalty": 0.5,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(API_URL, json=json_data, headers=headers)
        if resp.status_code != 200:
            return "Ошибка при обращении к API."
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "Ответ не получен.")

# --- Уведомление админов ---
async def notify_admin(user: types.User):
    for admin_id in admins:
        try:
            await bot.send_message(
                admin_id,
                f"Новый запрос:\nИмя: {user.first_name}\nID: <code>{user.id}</code>",
                parse_mode="HTML"
            )
        except Exception as e:
            logging.warning(f"Не удалось уведомить админа {admin_id}: {e}")

# --- Команда /ban ---
@dp.message(Command("ban"))
async def ban_user_cmd(message: Message):
    if message.from_user.id not in admins:
        return

    try:
        user_id = int(message.text.split()[1])
        if user_id in banlist:
            await message.answer("Пользователь уже в бане.")
            return

        banlist.append(user_id)
        save_banlist(banlist)
        await message.answer(f"Пользователь с ID {user_id} добавлен в банлист.")
        await bot.send_message(user_id, "Извини, ты был заблокирован. Бот еще в тестовом режиме.\n"
                                        "Вопросы админу в лс.")
    except Exception:
        await message.answer("Использование: /ban <user_id>")

# --- Команда /unban ---
@dp.message(Command("unban"))
async def unban_user_cmd(message: Message):
    if message.from_user.id not in admins:
        return

    try:
        user_id = int(message.text.split()[1])
        if user_id not in banlist:
            await message.answer("Этот пользователь не в бан-листе.")
            return

        banlist.remove(user_id)
        save_banlist(banlist)
        await message.answer(f"Пользователь с ID {user_id} разбанен.")
    except Exception:
        await message.answer("Использование: /unban <user_id>")

# --- Команда /banlist ---
@dp.message(Command("banlist"))
async def show_banlist(message: Message):
    if message.from_user.id not in admins:
        return
    if not banlist:
        await message.answer("Бан-лист пуст.")
    else:
        text = "\n".join([f"• <code>{u}</code>" for u in banlist])
        await message.answer(f"<b>Бан-лист:</b>\n\n{text}", parse_mode="HTML")

# --- /start ---
@dp.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id
    if user_id in banlist:
        return
    await notify_admin(message.from_user)
    await message.answer("Установлен контакт с машинным интеллектом. Все твои действия контролируются. Говори.")

# --- Все сообщения ---
@dp.message()
async def handle_all_messages(message: Message):
    user_id = message.from_user.id
    if user_id in banlist:
        return
    await notify_admin(message.from_user)
    await message.chat.do("typing")
    text = message.text.strip()
    if not text:
        return
    response = await ask_perplexity(text)
    await message.answer(response)

# --- Запуск ---
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
