import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var is not set")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

MENU = [
    ("Капучино", 180),
    ("Латте", 200),
    ("Американо", 150),
    ("Круассан", 120),
    ("Чизкейк", 250),
    ("Сэндвич с курицей", 280),
]

CAFE_NAME = "Демо Кафе"
CAFE_ADDRESS = "Бишкек, ул. Чуй 100"
CAFE_PHONE = "+996 555 12 34 56"

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Меню"), KeyboardButton(text="Заказать")],
        [KeyboardButton(text="Контакты"), KeyboardButton(text="Адрес")],
    ],
    resize_keyboard=True,
)

user_orders: dict[int, list[str]] = {}


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"Привет! Это бот {CAFE_NAME}.\n\n"
        "Выберите действие:",
        reply_markup=main_kb,
    )


@dp.message(F.text == "Меню")
async def show_menu(message: Message):
    lines = ["Наше меню:\n"]
    for name, price in MENU:
        lines.append(f"• {name} — {price} сом")
    await message.answer("\n".join(lines))


@dp.message(F.text == "Заказать")
async def start_order(message: Message):
    items = "\n".join(f"{i+1}. {name} — {price} сом" for i, (name, price) in enumerate(MENU))
    await message.answer(
        "Напишите номера позиций через запятую (например: 1, 3, 5)\n\n" + items
    )


@dp.message(F.text == "Контакты")
async def show_contacts(message: Message):
    await message.answer(f"Телефон: {CAFE_PHONE}\n{CAFE_NAME}")


@dp.message(F.text == "Адрес")
async def show_address(message: Message):
    await message.answer(f"{CAFE_NAME}\n{CAFE_ADDRESS}")


@dp.message(F.text.regexp(r"^[\d\s,]+$"))
async def handle_order(message: Message):
    try:
        nums = [int(x.strip()) for x in message.text.split(",") if x.strip()]
        picked = [MENU[n - 1] for n in nums if 1 <= n <= len(MENU)]
        if not picked:
            await message.answer("Не понял заказ. Попробуйте ещё раз.")
            return
        total = sum(p for _, p in picked)
        lines = ["Ваш заказ:"]
        for name, price in picked:
            lines.append(f"• {name} — {price} сом")
        lines.append(f"\nИтого: {total} сом")
        lines.append(f"\nДля подтверждения заказа позвоните: {CAFE_PHONE}")
        await message.answer("\n".join(lines))
    except (ValueError, IndexError):
        await message.answer("Не понял заказ. Используйте формат: 1, 2, 3")


@dp.message()
async def fallback(message: Message):
    await message.answer("Выберите кнопку внизу.", reply_markup=main_kb)


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
