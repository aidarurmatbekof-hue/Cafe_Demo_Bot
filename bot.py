import os
import asyncio
import logging
import random
from datetime import datetime
from collections import defaultdict
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

DELIVERY_ZONES = {
    "center": ("Центр города", 80),
    "mid": ("Средние районы", 150),
    "far": ("Окраины / Ю-3", 250),
    "pickup": ("Самовывоз", 0),
}

PROMO_CODES = {
    "WELCOME10": 10,
    "DASTAN15": 15,
    "HAPPY20": 20,
    "FRIEND5": 5,
}

BONUS_RATE = 0.05
BONUS_COST = 1

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
pending_orders: dict[int, dict] = {}
order_counter = 1000
carts: dict[int, list[tuple[str, int, str]]] = defaultdict(list)
bonus_points: dict[int, int] = defaultdict(int)
user_profile: dict[int, dict] = {}
user_orders: dict[int, list[int]] = defaultdict(list)
ratings: list[int] = []
ADMIN_IDS: set[int] = set()


def daily_special():
    items = flat_menu()
    seed = datetime.now().day
    random.seed(seed)
    item = random.choice(items)
    random.seed()
    return item


main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Меню"), KeyboardButton(text="🛒 Корзина")],
        [KeyboardButton(text="⭐ Бонусы"), KeyboardButton(text="🎁 Промокод")],
        [KeyboardButton(text="📜 Мои заказы"), KeyboardButton(text="🔥 Акция дня")],
        [KeyboardButton(text="📞 Контакты"), KeyboardButton(text="ℹ️ О нас")],
    ],
    resize_keyboard=True,
)


def menu_categories_kb():
    buttons = []
    for key, cat in MENU.items():
        buttons.append([InlineKeyboardButton(text=cat["title"], callback_data=f"cat:{key}")])
    buttons.append([InlineKeyboardButton(text="🛒 Корзина", callback_data="show_cart")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def category_items_kb(cat_key: str):
    cat = MENU[cat_key]
    items = cat["items"]
    buttons = []
    for idx, (name, price, emoji) in enumerate(items):
        buttons.append([
            InlineKeyboardButton(
                text=f"{emoji} {name} — {price} сом",
                callback_data=f"add:{cat_key}:{idx}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ К категориям", callback_data="categories"),
        InlineKeyboardButton(text="🛒 Корзина", callback_data="show_cart"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cart_kb(user_id: int):
    buttons = []
    cart = carts.get(user_id, [])
    if cart:
        buttons.append([InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout")])
        buttons.append([InlineKeyboardButton(text="🗑 Очистить", callback_data="clear_cart")])
    buttons.append([InlineKeyboardButton(text="📋 В меню", callback_data="categories")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def delivery_kb(order_id: int):
    buttons = []
    for key, (label, price) in DELIVERY_ZONES.items():
        txt = f"{label}" + (f" — {price} сом" if price else " — бесплатно")
        buttons.append([InlineKeyboardButton(text=txt, callback_data=f"delivery:{order_id}:{key}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_kb(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Я оплатил", callback_data=f"paid:{order_id}")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel:{order_id}")],
        ]
    )


def rating_kb(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=f"{i}⭐", callback_data=f"rate:{order_id}:{i}")
            for i in range(1, 6)
        ]]
    )


@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id
    name = message.from_user.first_name or "гость"
    is_new = uid not in user_profile
    user_profile[uid] = {
        "name": name,
        "username": message.from_user.username,
        "joined": datetime.now().isoformat(),
    }
    if is_new:
        bonus_points[uid] = 50

    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref_id = int(args[1][4:])
            if ref_id != uid and ref_id in user_profile:
                bonus_points[ref_id] += 100
                bonus_points[uid] += 100
        except ValueError:
            pass

    welcome = "Привет" if not is_new else "Добро пожаловать"
    bonus_msg = f"\n🎁 Вам начислено <b>50 бонусов</b> за регистрацию!" if is_new else ""
    text = (
        f"{welcome}, <b>{name}</b>! 👋\n\n"
        f"<b>{CAFE_NAME}</b> — кофе, десерты и душа ❤️\n"
        f"{bonus_msg}\n\n"
        "Что умеет бот:\n"
        "🛒 Приём заказов с корзиной\n"
        "💳 Оплата онлайн (МБанк)\n"
        "🚚 Доставка или самовывоз\n"
        "⭐ Бонусы за каждый заказ (5%)\n"
        "🎁 Промокоды и акции\n"
        "📜 История заказов\n\n"
        "Выбирайте кнопки ниже 👇"
    )
    await message.answer(text, reply_markup=main_kb)


@dp.message(F.text == "📋 Меню")
async def show_menu_categories(message: Message):
    special = daily_special()
    text = (
        "<b>Наше меню</b>\n\n"
        f"🔥 <b>Акция дня:</b> {special[2]} {special[0]} — {special[1]} сом (скидка 15%)\n\n"
        "Выберите категорию:"
    )
    await message.answer(text, reply_markup=menu_categories_kb())


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
    await call.message.edit_text(
        f"<b>{cat['title']}</b>\n\nНажмите чтобы добавить в корзину:",
        reply_markup=category_items_kb(key),
    )
    await call.answer()


@dp.callback_query(F.data.startswith("add:"))
async def add_to_cart(call: CallbackQuery):
    _, cat_key, idx = call.data.split(":")
    item = MENU[cat_key]["items"][int(idx)]
    carts[call.from_user.id].append(item)
    await call.answer(f"✅ {item[0]} добавлен в корзину")


@dp.message(F.text == "🛒 Корзина")
async def show_cart_message(message: Message):
    await render_cart(message, message.from_user.id)


@dp.callback_query(F.data == "show_cart")
async def show_cart_cb(call: CallbackQuery):
    await render_cart(call.message, call.from_user.id, edit=True)
    await call.answer()


async def render_cart(target: Message, uid: int, edit: bool = False):
    cart = carts.get(uid, [])
    if not cart:
        text = "<b>🛒 Корзина пуста</b>\n\nДобавьте товары из меню."
    else:
        lines = ["<b>🛒 Ваша корзина</b>\n"]
        counts = defaultdict(lambda: [0, 0, ""])
        for name, price, emoji in cart:
            counts[name][0] += 1
            counts[name][1] = price
            counts[name][2] = emoji
        total = 0
        for name, (qty, price, emoji) in counts.items():
            subtotal = qty * price
            total += subtotal
            lines.append(f"{emoji} {name} × {qty} — {subtotal} сом")
        lines.append(f"\n<b>Итого: {total} сом</b>")
        lines.append(f"⭐ Вы получите {int(total * BONUS_RATE)} бонусов")
        text = "\n".join(lines)
    if edit:
        try:
            await target.edit_text(text, reply_markup=cart_kb(uid))
        except Exception:
            await target.answer(text, reply_markup=cart_kb(uid))
    else:
        await target.answer(text, reply_markup=cart_kb(uid))


@dp.callback_query(F.data == "clear_cart")
async def clear_cart(call: CallbackQuery):
    carts[call.from_user.id] = []
    await call.message.edit_text("🗑 Корзина очищена.", reply_markup=cart_kb(call.from_user.id))
    await call.answer("Корзина очищена")


@dp.callback_query(F.data == "checkout")
async def checkout(call: CallbackQuery):
    global order_counter
    uid = call.from_user.id
    cart = carts.get(uid, [])
    if not cart:
        await call.answer("Корзина пуста", show_alert=True)
        return
    subtotal = sum(p for _, p, _ in cart)
    order_counter += 1
    order_id = order_counter
    pending_orders[order_id] = {
        "user_id": uid,
        "username": call.from_user.username or call.from_user.first_name,
        "items": list(cart),
        "subtotal": subtotal,
        "delivery_fee": 0,
        "delivery_type": None,
        "discount": 0,
        "promo": None,
        "bonus_used": 0,
        "total": subtotal,
        "status": "pending_delivery",
        "created_at": datetime.now().isoformat(),
    }
    await call.message.edit_text(
        f"<b>🚚 Заказ #{order_id}</b>\n\nВыберите способ получения:",
        reply_markup=delivery_kb(order_id),
    )
    await call.answer()


@dp.callback_query(F.data.startswith("delivery:"))
async def set_delivery(call: CallbackQuery):
    _, oid, key = call.data.split(":")
    order_id = int(oid)
    order = pending_orders.get(order_id)
    if not order:
        await call.answer("Заказ не найден", show_alert=True)
        return
    label, fee = DELIVERY_ZONES[key]
    order["delivery_type"] = label
    order["delivery_fee"] = fee
    order["total"] = order["subtotal"] + fee - order["discount"] - order["bonus_used"]

    lines = [f"<b>🧾 Заказ #{order_id}</b>\n"]
    counts = defaultdict(lambda: [0, 0, ""])
    for name, price, emoji in order["items"]:
        counts[name][0] += 1
        counts[name][1] = price
        counts[name][2] = emoji
    for name, (qty, price, emoji) in counts.items():
        lines.append(f"{emoji} {name} × {qty} — {qty * price} сом")
    lines.append(f"\nПодытог: {order['subtotal']} сом")
    lines.append(f"Доставка ({label}): {fee} сом")
    if order["discount"]:
        lines.append(f"Скидка промокод: -{order['discount']} сом")
    if order["bonus_used"]:
        lines.append(f"Бонусы: -{order['bonus_used']} сом")
    lines.append(f"\n<b>Итого к оплате: {order['total']} сом</b>")
    lines.append(
        f"\n<b>💳 Оплата онлайн (МБанк)</b>\n"
        f"Номер: <code>{MBANK_NUMBER}</code>\n"
        f"Получатель: {MBANK_HOLDER}\n"
        f"Сумма: <b>{order['total']} сом</b>\n"
        f"Комментарий: <code>Заказ #{order_id}</code>"
    )
    await call.message.edit_text("\n".join(lines), reply_markup=payment_kb(order_id))
    await call.answer()


@dp.callback_query(F.data.startswith("paid:"))
async def handle_paid(call: CallbackQuery):
    uid = call.from_user.id
    order_id = int(call.data.split(":")[1])
    order = pending_orders.pop(order_id, None)
    if not order:
        await call.answer("Заказ не найден", show_alert=True)
        return
    order["status"] = "paid"
    orders_db[order_id] = order
    user_orders[uid].append(order_id)
    carts[uid] = []
    earned = int(order["subtotal"] * BONUS_RATE)
    bonus_points[uid] += earned

    masked_phone = CAFE_PHONE[:-4] + "XXXX"
    text = (
        f"✅ <b>Спасибо за оплату!</b>\n\n"
        f"Заказ <b>#{order_id}</b> принят. Сумма: {order['total']} сом\n\n"
        f"📤 Уведомление отправлено на номер <b>{masked_phone}</b>\n\n"
        f"⏳ Ожидайте звонка в течение <b>5 минут</b>.\n\n"
        f"⭐ Начислено <b>{earned} бонусов</b> (баланс: {bonus_points[uid]})\n\n"
        f"Оцените заказ 👇"
    )
    await call.message.edit_text(text, reply_markup=rating_kb(order_id))
    await call.answer("Оплата принята!", show_alert=True)


@dp.callback_query(F.data.startswith("rate:"))
async def handle_rating(call: CallbackQuery):
    _, oid, stars = call.data.split(":")
    ratings.append(int(stars))
    await call.message.edit_text(
        f"Спасибо за оценку <b>{stars}⭐</b>!\n\n"
        f"Ваше мнение важно для нас ❤️\n\n"
        f"Напишите /start чтобы продолжить."
    )
    await call.answer("Спасибо!")


@dp.callback_query(F.data.startswith("cancel:"))
async def handle_cancel(call: CallbackQuery):
    oid = int(call.data.split(":")[1])
    pending_orders.pop(oid, None)
    await call.message.edit_text(f"❌ Заказ <b>#{oid}</b> отменён.")
    await call.answer("Отменено")


@dp.message(F.text == "⭐ Бонусы")
async def show_bonus(message: Message):
    uid = message.from_user.id
    pts = bonus_points[uid]
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start=ref_{uid}"
    text = (
        f"<b>⭐ Ваш бонусный счёт</b>\n\n"
        f"Баланс: <b>{pts} бонусов</b>\n"
        f"1 бонус = 1 сом скидки\n\n"
        f"💰 <b>Как заработать:</b>\n"
        f"• 5% от каждого заказа\n"
        f"• 100 бонусов за приглашение друга\n"
        f"• 50 бонусов за регистрацию\n\n"
        f"👥 <b>Ваша ссылка:</b>\n{ref_link}"
    )
    await message.answer(text)


@dp.message(F.text == "🎁 Промокод")
async def promo_hint(message: Message):
    await message.answer(
        "<b>🎁 Введите промокод</b>\n\n"
        "Напишите код в чат, например:\n<code>WELCOME10</code>\n\n"
        "Скидка применится к следующему заказу."
    )


@dp.message(F.text == "📜 Мои заказы")
async def my_orders(message: Message):
    uid = message.from_user.id
    oids = user_orders.get(uid, [])
    if not oids:
        await message.answer("У вас пока нет заказов.")
        return
    lines = ["<b>📜 История заказов</b>\n"]
    for oid in oids[-10:]:
        o = orders_db.get(oid)
        if not o:
            continue
        ts = o["created_at"][:16].replace("T", " ")
        lines.append(f"#{oid} — {o['total']} сом — {ts}")
    await message.answer("\n".join(lines))


@dp.message(F.text == "🔥 Акция дня")
async def show_special(message: Message):
    name, price, emoji = daily_special()
    discount_price = int(price * 0.85)
    text = (
        f"<b>🔥 Акция дня</b>\n\n"
        f"{emoji} <b>{name}</b>\n"
        f"Было: {price} сом\n"
        f"Сегодня: <b>{discount_price} сом</b>\n"
        f"Экономия: {price - discount_price} сом (15%)\n\n"
        f"Акция действует до 23:00."
    )
    await message.answer(text)


@dp.message(F.text == "📞 Контакты")
async def show_contacts(message: Message):
    text = (
        f"<b>📞 Наши контакты</b>\n\n"
        f"Телефон: <b>{CAFE_PHONE}</b>\n"
        f"Whatsapp: {CAFE_PHONE}\n"
        f"Instagram: @cafe_dastan\n"
        f"Адрес: {CAFE_ADDRESS}\n"
        f"Часы: {CAFE_HOURS}"
    )
    await message.answer(text)


@dp.message(F.text == "ℹ️ О нас")
async def show_about(message: Message):
    avg = sum(ratings) / len(ratings) if ratings else 0
    text = (
        f"<b>ℹ️ О {CAFE_NAME}</b>\n\n"
        "Уютное кафе в центре Бишкека ❤️\n\n"
        "• Свежая выпечка каждое утро\n"
        "• Зёрна прямой поставки из Эфиопии\n"
        "• Домашняя кухня, веганские опции\n"
        "• Wi-Fi, тихие уголки для работы\n"
        "• Доставка по Бишкеку\n\n"
    )
    if avg:
        text += f"⭐ Рейтинг от клиентов: <b>{avg:.1f}</b> ({len(ratings)} оценок)\n\n"
    text += "Ждём вас в гости!"
    await message.answer(text)


@dp.message(Command("admin"))
async def admin_login(message: Message):
    ADMIN_IDS.add(message.from_user.id)
    await message.answer("✅ Вы теперь админ. Команды: /stats /orders /revenue")


@dp.message(Command("stats"))
async def admin_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    total = len(orders_db)
    revenue = sum(o["total"] for o in orders_db.values())
    avg_check = revenue / total if total else 0
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    text = (
        f"<b>📊 Статистика</b>\n\n"
        f"Заказов: <b>{total}</b>\n"
        f"Выручка: <b>{revenue} сом</b>\n"
        f"Средний чек: <b>{int(avg_check)} сом</b>\n"
        f"Рейтинг: <b>{avg_rating:.1f}⭐</b> ({len(ratings)} оценок)\n"
        f"Клиентов: <b>{len(user_profile)}</b>\n"
        f"Ожидают оплаты: <b>{len(pending_orders)}</b>"
    )
    await message.answer(text)


@dp.message(Command("orders"))
async def admin_orders(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if not orders_db:
        await message.answer("Заказов нет.")
        return
    last = sorted(orders_db.items(), key=lambda x: x[0], reverse=True)[:10]
    lines = ["<b>📋 Последние 10 заказов</b>\n"]
    for oid, o in last:
        ts = o["created_at"][:16].replace("T", " ")
        lines.append(f"#{oid} — {o['total']} сом — @{o['username']} — {ts}")
    await message.answer("\n".join(lines))


@dp.message(Command("revenue"))
async def admin_revenue(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    today = datetime.now().date().isoformat()
    today_orders = [o for o in orders_db.values() if o["created_at"].startswith(today)]
    today_revenue = sum(o["total"] for o in today_orders)
    await message.answer(
        f"<b>💰 Выручка сегодня</b>\n\n"
        f"Заказов: {len(today_orders)}\n"
        f"Сумма: <b>{today_revenue} сом</b>"
    )


@dp.message()
async def handle_text(message: Message):
    text = message.text.strip().upper()
    uid = message.from_user.id
    if text in PROMO_CODES:
        pct = PROMO_CODES[text]
        cart = carts.get(uid, [])
        if not cart:
            await message.answer(f"✅ Промокод <b>{text}</b> активирован ({pct}%). Добавьте товары в корзину.")
            return
        subtotal = sum(p for _, p, _ in cart)
        discount = int(subtotal * pct / 100)
        await message.answer(
            f"✅ Промокод <b>{text}</b> применён!\n"
            f"Скидка: <b>{discount} сом</b> ({pct}% от {subtotal})\n\n"
            f"Откройте 🛒 Корзину и оформите заказ."
        )
        return
    await message.answer(
        "🤔 Не понял. Используйте кнопки ниже 👇",
        reply_markup=main_kb,
    )


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
