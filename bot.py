import os
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var is not set")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

CAFE_NAME = "☕ Кафе Дастан"
CAFE_ADDRESS = "Бишкек, ул. Чуй 100"
CAFE_PHONE = "+996 555 12 34 56"
CAFE_HOURS = "09:00 – 23:00 ежедневно"
MBANK_NUMBER = "+996 700 123 456"
MBANK_HOLDER = "ДАСТАН К."

MENU = {
    "coffee": {
        "title": "☕ Кофе и напитки",
        "items": [
            ("Эспрессо", 120, "☕"),
            ("Американо", 150, "☕"),
            ("Капучино", 180, "🥛"),
            ("Латте", 200, "🥛"),
            ("Раф кофе", 220, "🥛"),
            ("Флэт уайт", 210, "🥛"),
            ("Горячий шоколад", 200, "🍫"),
            ("Чай зелёный", 100, "🍵"),
            ("Чай чёрный", 100, "🍵"),
        ],
    },
    "desserts": {
        "title": "🍰 Десерты",
        "items": [
            ("Круассан классический", 120, "🥐"),
            ("Круассан с шоколадом", 150, "🥐"),
            ("Чизкейк Нью-Йорк", 280, "🍰"),
            ("Тирамису", 300, "🍰"),
            ("Медовик", 250, "🍯"),
            ("Макаруны (3 шт)", 220, "🍬"),
            ("Печенье (набор)", 150, "🍪"),
        ],
    },
    "food": {
        "title": "🥗 Еда",
        "items": [
            ("Сэндвич с курицей", 280, "🥪"),
            ("Сэндвич с лососем", 350, "🥪"),
            ("Цезарь с курицей", 420, "🥗"),
            ("Паста Карбонара", 450, "🍝"),
            ("Паста с креветками", 520, "🍝"),
            ("Бургер говяжий", 480, "🍔"),
            ("Томатный суп", 280, "🍲"),
        ],
    },
}


def flat_menu():
    items = []
    for cat in MENU.values():
        items.extend(cat["items"])
    return items


orders_db: dict[int, dict] = {}
order_counter = 1000
pending_orders: dict[int, dict] = {}

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Меню"), KeyboardButton(text="🛒 Заказать")],
        [KeyboardButton(text="📞 Контакты"), KeyboardButton(text="📍 Адрес")],
        [KeyboardButton(text="🕒 Часы работы"), KeyboardButton(text="ℹ️ О нас")],
    ],
    resize_keyboard=True,
)


def menu_categories_kb():
    buttons = []
    for key, cat in MENU.items():
        buttons.append([InlineKeyboardButton(text=cat["title"], callback_data=f"cat:{key}")])
    buttons.append([InlineKeyboardButton(text="🛒 Сделать заказ", callback_data="order")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="categories")],
            [InlineKeyboardButton(text="🛒 Заказать", callback_data="order")],
        ]
    )


def payment_kb(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Я оплатил", callback_data=f"paid:{order_id}")],
            [InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"cancel:{order_id}")],
        ]
    )


@dp.message(CommandStart())
async def cmd_start(message: Message):
    name = message.from_user.first_name or "гость"
    text = (
        f"Привет, <b>{name}</b>! 👋\n\n"
        f"Добро пожаловать в <b>{CAFE_NAME}</b>\n\n"
        "Здесь вы можете:\n"
        "📋 Посмотреть наше меню\n"
        "🛒 Сделать заказ\n"
        "💳 Оплатить онлайн\n"
        "📞 Узнать контакты\n\n"
        "Выбирайте кнопки ниже 👇"
    )
    await message.answer(text, reply_markup=main_kb)


@dp.message(F.text == "📋 Меню")
async def show_menu_categories(message: Message):
    await message.answer(
        "<b>Наше меню</b>\n\nВыберите категорию:",
        reply_markup=menu_categories_kb(),
    )


@dp.callback_query(F.data == "categories")
async def back_to_categories(call: CallbackQuery):
    await call.message.edit_text(
        "<b>Наше меню</b>\n\nВыберите категорию:",
        reply_markup=menu_categories_kb(),
    )
    await call.answer()


@dp.callback_query(F.data.startswith("cat:"))
async def show_category(call: CallbackQuery):
    key = call.data.split(":")[1]
    cat = MENU.get(key)
    if not cat:
        await call.answer("Категория не найдена")
        return
    lines = [f"<b>{cat['title']}</b>\n"]
    for name, price, emoji in cat["items"]:
        lines.append(f"{emoji} {name} — <b>{price} сом</b>")
    await call.message.edit_text("\n".join(lines), reply_markup=back_kb())
    await call.answer()


@dp.callback_query(F.data == "order")
async def order_from_inline(call: CallbackQuery):
    await start_order(call.message)
    await call.answer()


@dp.message(F.text == "🛒 Заказать")
async def start_order(message: Message):
    lines = ["<b>🛒 Как сделать заказ</b>\n"]
    lines.append("Напишите номера через запятую: <code>1, 3, 5</code>\n")
    i = 1
    for cat in MENU.values():
        lines.append(f"\n<b>{cat['title']}</b>")
        for name, price, emoji in cat["items"]:
            lines.append(f"{i}. {emoji} {name} — {price} сом")
            i += 1
    await message.answer("\n".join(lines))


@dp.message(F.text == "📞 Контакты")
async def show_contacts(message: Message):
    text = (
        f"<b>📞 Наши контакты</b>\n\n"
        f"Телефон: <b>{CAFE_PHONE}</b>\n"
        f"Instagram: @cafe_dastan\n"
        f"Whatsapp: {CAFE_PHONE}"
    )
    await message.answer(text)


@dp.message(F.text == "📍 Адрес")
async def show_address(message: Message):
    text = (
        f"<b>📍 Где мы находимся</b>\n\n"
        f"{CAFE_NAME}\n"
        f"{CAFE_ADDRESS}\n\n"
        f"🅿️ Есть парковка\n"
        f"🚇 Остановка 'Филармония' — 2 мин пешком"
    )
    await message.answer(text)


@dp.message(F.text == "🕒 Часы работы")
async def show_hours(message: Message):
    text = (
        f"<b>🕒 Время работы</b>\n\n"
        f"{CAFE_HOURS}\n\n"
        f"Завтраки с 09:00 до 12:00 🍳\n"
        f"Ланч-меню с 12:00 до 16:00 🍽\n"
        f"Кофе-брейк с 16:00 до 23:00 ☕"
    )
    await message.answer(text)


@dp.message(F.text == "ℹ️ О нас")
async def show_about(message: Message):
    text = (
        f"<b>ℹ️ О {CAFE_NAME}</b>\n\n"
        "Уютное кафе в самом центре Бишкека ❤️\n\n"
        "• Свежая выпечка каждое утро\n"
        "• Зёрна прямой поставки из Эфиопии\n"
        "• Домашняя кухня\n"
        "• Веганские опции\n"
        "• Wi-Fi и тихие уголки для работы\n\n"
        "Ждём вас в гости!"
    )
    await message.answer(text)


@dp.message(F.text.regexp(r"^[\d\s,]+$"))
async def handle_order(message: Message):
    global order_counter
    try:
        items = flat_menu()
        nums = [int(x.strip()) for x in message.text.split(",") if x.strip()]
        picked = [items[n - 1] for n in nums if 1 <= n <= len(items)]
        if not picked:
            await message.answer("❌ Не понял заказ. Попробуйте ещё раз.")
            return
        total = sum(p for _, p, _ in picked)
        order_counter += 1
        order_id = order_counter
        pending_orders[order_id] = {
            "user_id": message.from_user.id,
            "username": message.from_user.username or message.from_user.first_name,
            "items": picked,
            "total": total,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
        }

        lines = [f"<b>🛒 Заказ #{order_id}</b>\n"]
        for name, price, emoji in picked:
            lines.append(f"{emoji} {name} — {price} сом")
        lines.append(f"\n<b>Итого: {total} сом</b>")
        lines.append(
            f"\n<b>💳 Оплата онлайн (МБанк)</b>\n"
            f"Номер: <code>{MBANK_NUMBER}</code>\n"
            f"Получатель: {MBANK_HOLDER}\n"
            f"Сумма: <b>{total} сом</b>\n"
            f"Комментарий: <code>Заказ #{order_id}</code>\n\n"
            f"После оплаты нажмите кнопку ниже 👇"
        )
        await message.answer("\n".join(lines), reply_markup=payment_kb(order_id))
    except (ValueError, IndexError):
        await message.answer("❌ Не понял. Формат: <code>1, 2, 3</code>")


@dp.callback_query(F.data.startswith("paid:"))
async def handle_paid(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    order = pending_orders.get(order_id)
    if not order:
        await call.answer("Заказ не найден")
        return

    order["status"] = "paid"
    orders_db[order_id] = order

    masked_phone = CAFE_PHONE[:-4] + "XXXX"
    text = (
        f"✅ <b>Спасибо за оплату!</b>\n\n"
        f"Заказ <b>#{order_id}</b> принят в обработку.\n\n"
        f"📤 Уведомление отправлено на номер <b>{masked_phone}</b>\n\n"
        f"⏳ Ожидайте звонка от кафе в течение <b>5 минут</b> для подтверждения.\n\n"
        f"Спасибо что выбрали {CAFE_NAME} ❤️"
    )
    await call.message.edit_text(text)
    await call.answer("Оплата принята!", show_alert=True)


@dp.callback_query(F.data.startswith("cancel:"))
async def handle_cancel(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    if order_id in pending_orders:
        pending_orders.pop(order_id)
    await call.message.edit_text(
        f"❌ Заказ <b>#{order_id}</b> отменён.\n\nЖдём вас снова!"
    )
    await call.answer("Заказ отменён")


@dp.message(Command("stats"))
async def admin_stats(message: Message):
    total_orders = len(orders_db)
    total_revenue = sum(o["total"] for o in orders_db.values())
    pending = len(pending_orders)
    text = (
        f"<b>📊 Статистика админа</b>\n\n"
        f"Оплаченных заказов: <b>{total_orders}</b>\n"
        f"Выручка всего: <b>{total_revenue} сом</b>\n"
        f"Ожидают оплату: <b>{pending}</b>"
    )
    await message.answer(text)


@dp.message(Command("orders"))
async def admin_orders(message: Message):
    if not orders_db:
        await message.answer("Заказов пока нет.")
        return
    last = sorted(orders_db.items(), key=lambda x: x[0], reverse=True)[:10]
    lines = ["<b>📋 Последние 10 заказов</b>\n"]
    for oid, o in last:
        ts = o["created_at"][:16].replace("T", " ")
        lines.append(f"#{oid} — {o['total']} сом — @{o['username']} — {ts}")
    await message.answer("\n".join(lines))


@dp.message()
async def fallback(message: Message):
    await message.answer(
        "🤔 Не понял команду. Выберите кнопку внизу 👇",
        reply_markup=main_kb,
    )


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
