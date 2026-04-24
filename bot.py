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

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

CAFE_NAME = "☕ Кафе Дастан"
CAFE_ADDRESS = "Бишкек, ул. Чуй 100"
CAFE_PHONE = "+996 555 12 34 56"
CAFE_HOURS = "09:00 – 23:00 ежедневно"
MBANK_NUMBER = "+996 700 123 456"
MBANK_HOLDER = "ДАСТАН К."
SUPPORT_USERNAME = "@cafe_dastan_support"

DELIVERY_ZONES = {
    "pickup": ("🚶 Самовывоз", 0),
    "center": ("🏙 Центр города", 80),
    "mid": ("🏘 Средние районы", 150),
    "far": ("🌆 Окраины / Ю-3", 250),
}

PROMO_CODES = {
    "WELCOME10": 10,
    "DASTAN15": 15,
    "HAPPY20": 20,
    "FRIEND5": 5,
    "VIP30": 30,
}

SUBSCRIPTIONS = {
    "coffee_day": ("☕ Утренний кофе (30 дней)", 2500, "Американо или эспрессо каждый день"),
    "lunch_week": ("🥗 Ланч-абонемент (5 дней)", 1800, "Блюдо + напиток каждый будний день"),
    "sweet_month": ("🍰 Десертная подписка (30 дней)", 3500, "Десерт на выбор каждый день"),
}

POPULAR = ["Капучино", "Латте", "Чизкейк Нью-Йорк", "Круассан с шоколадом", "Цезарь с курицей"]

MENU = {
    "coffee": {"title": "☕ Кофе и напитки", "items": [
        ("Эспрессо", 120, "☕"), ("Американо", 150, "☕"), ("Капучино", 180, "🥛"),
        ("Латте", 200, "🥛"), ("Раф кофе", 220, "🥛"), ("Флэт уайт", 210, "🥛"),
        ("Горячий шоколад", 200, "🍫"), ("Чай зелёный", 100, "🍵"), ("Чай чёрный", 100, "🍵"),
    ]},
    "desserts": {"title": "🍰 Десерты", "items": [
        ("Круассан классический", 120, "🥐"), ("Круассан с шоколадом", 150, "🥐"),
        ("Чизкейк Нью-Йорк", 280, "🍰"), ("Тирамису", 300, "🍰"), ("Медовик", 250, "🍯"),
        ("Макаруны (3 шт)", 220, "🍬"), ("Печенье (набор)", 150, "🍪"),
    ]},
    "food": {"title": "🥗 Еда", "items": [
        ("Сэндвич с курицей", 280, "🥪"), ("Сэндвич с лососем", 350, "🥪"),
        ("Цезарь с курицей", 420, "🥗"), ("Паста Карбонара", 450, "🍝"),
        ("Паста с креветками", 520, "🍝"), ("Бургер говяжий", 480, "🍔"), ("Томатный суп", 280, "🍲"),
    ]},
}


def flat_menu():
    items = []
    for cat in MENU.values():
        items.extend(cat["items"])
    return items


def find_item(name):
    for item in flat_menu():
        if item[0] == name:
            return item
    return None


orders_db: dict[int, dict] = {}
pending_orders: dict[int, dict] = {}
order_counter = 1000
carts: dict[int, dict[str, int]] = defaultdict(dict)
bonus_points: dict[int, int] = defaultdict(int)
user_profile: dict[int, dict] = {}
user_orders: dict[int, list[int]] = defaultdict(list)
favorites: dict[int, set[str]] = defaultdict(set)
ratings: list[int] = []
ADMIN_IDS: set[int] = set()
awaiting_phone: set[int] = set()
awaiting_address: dict[int, int] = {}
user_promos: dict[int, int] = {}


def daily_special():
    seed = datetime.now().day
    random.seed(seed)
    item = random.choice(flat_menu())
    random.seed()
    return item


def cart_total(uid):
    total = 0
    for name, qty in carts[uid].items():
        item = find_item(name)
        if item:
            total += item[1] * qty
    return total


def main_kb_for(uid):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Меню"), KeyboardButton(text="🛒 Корзина")],
            [KeyboardButton(text="🔥 Популярное"), KeyboardButton(text="⭐ Бонусы")],
            [KeyboardButton(text="🎁 Промокод"), KeyboardButton(text="💎 Подписки")],
            [KeyboardButton(text="📜 Мои заказы"), KeyboardButton(text="❤️ Избранное")],
            [KeyboardButton(text="📞 Контакты"), KeyboardButton(text="💬 Поддержка")],
        ],
        resize_keyboard=True,
    )


def menu_categories_kb():
    btns = [[InlineKeyboardButton(text=cat["title"], callback_data=f"cat:{k}")] for k, cat in MENU.items()]
    btns.append([
        InlineKeyboardButton(text="🔥 Популярное", callback_data="popular"),
        InlineKeyboardButton(text="🛒 Корзина", callback_data="show_cart"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=btns)


def category_items_kb(cat_key, uid):
    cat = MENU[cat_key]
    btns = []
    for name, price, emoji in cat["items"]:
        fav = "❤️ " if name in favorites[uid] else ""
        btns.append([InlineKeyboardButton(text=f"{fav}{emoji} {name} — {price} сом", callback_data=f"add:{cat_key}:{name}")])
    btns.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="categories"),
        InlineKeyboardButton(text="🛒 Корзина", callback_data="show_cart"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=btns)


def cart_view_kb(uid):
    btns = []
    for name, qty in carts[uid].items():
        btns.append([
            InlineKeyboardButton(text="➖", callback_data=f"qty:-:{name}"),
            InlineKeyboardButton(text=f"{qty}×  {name[:20]}", callback_data="noop"),
            InlineKeyboardButton(text="➕", callback_data=f"qty:+:{name}"),
            InlineKeyboardButton(text="🗑", callback_data=f"qty:0:{name}"),
        ])
    extra = []
    if carts[uid]:
        extra.append(InlineKeyboardButton(text="✅ Оформить", callback_data="checkout"))
        extra.append(InlineKeyboardButton(text="🗑 Очистить", callback_data="clear_cart"))
    btns.append(extra) if extra else None
    btns.append([InlineKeyboardButton(text="📋 В меню", callback_data="categories")])
    return InlineKeyboardMarkup(inline_keyboard=btns)


def delivery_kb(order_id):
    btns = [[InlineKeyboardButton(
        text=f"{label}" + (f" — {fee} сом" if fee else " — бесплатно"),
        callback_data=f"delivery:{order_id}:{k}"
    )] for k, (label, fee) in DELIVERY_ZONES.items()]
    return InlineKeyboardMarkup(inline_keyboard=btns)


def payment_kb(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Я оплатил", callback_data=f"paid:{order_id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel:{order_id}")],
    ])


def rating_kb(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"{i}⭐", callback_data=f"rate:{order_id}:{i}") for i in range(1, 6)
    ]])


def status_kb(order_id, admin=False):
    if not admin:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍳 Готовится", callback_data=f"status:{order_id}:cooking")],
        [InlineKeyboardButton(text="🚴 В доставке", callback_data=f"status:{order_id}:delivery")],
        [InlineKeyboardButton(text="✅ Готово", callback_data=f"status:{order_id}:done")],
    ])


@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id
    name = message.from_user.first_name or "гость"
    is_new = uid not in user_profile
    user_profile[uid] = {"name": name, "username": message.from_user.username, "joined": datetime.now().isoformat()}
    if is_new:
        bonus_points[uid] += 50
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref_id = int(args[1][4:])
            if ref_id != uid and ref_id in user_profile:
                bonus_points[ref_id] += 100
                bonus_points[uid] += 100
        except ValueError:
            pass
    bonus_note = "\n🎁 <b>50 бонусов за регистрацию!</b>" if is_new else ""
    text = (
        f"{'Добро пожаловать' if is_new else 'С возвращением'}, <b>{name}</b>! 👋\n\n"
        f"<b>{CAFE_NAME}</b> — кофе, десерты и душа ❤️{bonus_note}\n\n"
        "🛒 Корзина с +/- количеством\n"
        "💳 Оплата МБанк онлайн\n"
        "🚚 Доставка или самовывоз\n"
        "⭐ Бонусы 5% с каждого заказа\n"
        "🎁 Промокоды • 💎 Подписки\n"
        "❤️ Избранное • 📜 История\n\n"
        "👇 Выбирайте:"
    )
    await message.answer(text, reply_markup=main_kb_for(uid))


@dp.message(F.text == "📋 Меню")
async def show_menu(message: Message):
    name, price, emoji = daily_special()
    disc = int(price * 0.85)
    await message.answer(
        f"<b>📋 Меню</b>\n\n🔥 Акция дня: {emoji} <b>{name}</b> — {disc} сом (было {price})\n\nВыберите категорию:",
        reply_markup=menu_categories_kb()
    )


@dp.callback_query(F.data == "categories")
async def cb_categories(call: CallbackQuery):
    await call.message.edit_text("<b>📋 Меню</b>\n\nВыберите категорию:", reply_markup=menu_categories_kb())
    await call.answer()


@dp.callback_query(F.data.startswith("cat:"))
async def cb_category(call: CallbackQuery):
    key = call.data.split(":")[1]
    cat = MENU.get(key)
    if not cat:
        await call.answer(); return
    await call.message.edit_text(
        f"<b>{cat['title']}</b>\n\nНажмите чтобы добавить в корзину:",
        reply_markup=category_items_kb(key, call.from_user.id)
    )
    await call.answer()


@dp.callback_query(F.data == "popular")
async def cb_popular(call: CallbackQuery):
    lines = ["<b>🔥 Популярные блюда</b>\n"]
    btns = []
    for name in POPULAR:
        item = find_item(name)
        if item:
            lines.append(f"{item[2]} {item[0]} — {item[1]} сом")
            btns.append([InlineKeyboardButton(text=f"➕ {item[0]}", callback_data=f"addname:{item[0]}")])
    btns.append([InlineKeyboardButton(text="🛒 Корзина", callback_data="show_cart"), InlineKeyboardButton(text="📋 Меню", callback_data="categories")])
    await call.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await call.answer()


@dp.callback_query(F.data.startswith("addname:"))
async def cb_addname(call: CallbackQuery):
    name = call.data[8:]
    item = find_item(name)
    if item:
        uid = call.from_user.id
        carts[uid][name] = carts[uid].get(name, 0) + 1
        await call.answer(f"✅ {name} добавлен в корзину")
    else:
        await call.answer("Не найдено")


@dp.callback_query(F.data.startswith("add:"))
async def cb_add(call: CallbackQuery):
    parts = call.data.split(":", 2)
    name = parts[2]
    uid = call.from_user.id
    carts[uid][name] = carts[uid].get(name, 0) + 1
    await call.answer(f"✅ {name} × {carts[uid][name]}")


@dp.callback_query(F.data.startswith("qty:"))
async def cb_qty(call: CallbackQuery):
    _, op, name = call.data.split(":", 2)
    uid = call.from_user.id
    cur = carts[uid].get(name, 0)
    if op == "+":
        carts[uid][name] = cur + 1
    elif op == "-":
        if cur > 1:
            carts[uid][name] = cur - 1
        else:
            carts[uid].pop(name, None)
    elif op == "0":
        carts[uid].pop(name, None)
    await render_cart(call.message, uid, edit=True)
    await call.answer()


@dp.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()


@dp.message(F.text == "🛒 Корзина")
async def msg_cart(message: Message):
    await render_cart(message, message.from_user.id)


@dp.callback_query(F.data == "show_cart")
async def cb_show_cart(call: CallbackQuery):
    await render_cart(call.message, call.from_user.id, edit=True)
    await call.answer()


async def render_cart(target, uid, edit=False):
    cart = carts.get(uid, {})
    if not cart:
        text = "<b>🛒 Корзина пуста</b>\n\nДобавьте товары из меню."
    else:
        lines = ["<b>🛒 Ваша корзина</b>\n"]
        total = 0
        for name, qty in cart.items():
            item = find_item(name)
            if item:
                sub = item[1] * qty
                total += sub
                lines.append(f"{item[2]} {name} × {qty} = {sub} сом")
        bonus_earn = int(total * 0.05)
        promo_discount = user_promos.get(uid, 0)
        if promo_discount:
            disc_amt = int(total * promo_discount / 100)
            lines.append(f"\nСкидка ({promo_discount}%): -{disc_amt} сом")
            total -= disc_amt
        lines.append(f"\n<b>Итого: {total} сом</b>")
        lines.append(f"⭐ Начислим {bonus_earn} бонусов")
        text = "\n".join(lines)
    kb = cart_view_kb(uid)
    try:
        if edit:
            await target.edit_text(text, reply_markup=kb)
        else:
            await target.answer(text, reply_markup=kb)
    except Exception:
        await target.answer(text, reply_markup=kb)


@dp.callback_query(F.data == "clear_cart")
async def cb_clear(call: CallbackQuery):
    carts[call.from_user.id] = {}
    await render_cart(call.message, call.from_user.id, edit=True)
    await call.answer("Корзина очищена")


@dp.callback_query(F.data == "checkout")
async def cb_checkout(call: CallbackQuery):
    global order_counter
    uid = call.from_user.id
    cart = carts.get(uid, {})
    if not cart:
        await call.answer("Корзина пуста", show_alert=True); return
    subtotal = cart_total(uid)
    disc = 0
    promo_pct = user_promos.get(uid, 0)
    if promo_pct:
        disc = int(subtotal * promo_pct / 100)
    order_counter += 1
    oid = order_counter
    pending_orders[oid] = {
        "user_id": uid, "username": call.from_user.username or call.from_user.first_name,
        "items": dict(cart), "subtotal": subtotal, "delivery_fee": 0, "delivery_type": None,
        "discount": disc, "promo_pct": promo_pct, "total": subtotal - disc,
        "status": "pending", "created_at": datetime.now().isoformat(), "phone": None,
    }
    user_promos.pop(uid, None)
    await call.message.edit_text(
        f"<b>📦 Заказ #{oid}</b>\n\nВыберите способ получения:",
        reply_markup=delivery_kb(oid)
    )
    await call.answer()


@dp.callback_query(F.data.startswith("delivery:"))
async def cb_delivery(call: CallbackQuery):
    _, oid_s, key = call.data.split(":")
    oid = int(oid_s)
    order = pending_orders.get(oid)
    if not order:
        await call.answer("Заказ не найден", show_alert=True); return
    label, fee = DELIVERY_ZONES[key]
    order["delivery_type"] = label
    order["delivery_fee"] = fee
    order["total"] = order["subtotal"] - order["discount"] + fee
    uid = call.from_user.id
    awaiting_phone.add(uid)
    pending_orders[oid]["waiting_phone_uid"] = uid
    await call.message.edit_text(
        f"<b>📦 Заказ #{oid}</b> — {label}\n\n"
        "📱 Отправьте ваш номер для подтверждения заказа:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="📱 Поделиться номером", callback_data=f"skip_phone:{oid}")
        ]])
    )
    awaiting_address[uid] = oid
    await call.answer()


@dp.callback_query(F.data.startswith("skip_phone:"))
async def cb_skip_phone(call: CallbackQuery):
    oid = int(call.data.split(":")[1])
    uid = call.from_user.id
    awaiting_phone.discard(uid)
    awaiting_address.pop(uid, None)
    await show_payment(call.message, oid)
    await call.answer()


async def show_payment(target, oid):
    order = pending_orders.get(oid)
    if not order:
        return
    lines = [f"<b>🧾 Заказ #{oid}</b>\n"]
    for name, qty in order["items"].items():
        item = find_item(name)
        if item:
            lines.append(f"{item[2]} {name} × {qty} = {item[1]*qty} сом")
    lines.append(f"\nПодытог: {order['subtotal']} сом")
    if order["discount"]:
        lines.append(f"Скидка: -{order['discount']} сом")
    if order["delivery_fee"]:
        lines.append(f"Доставка ({order['delivery_type']}): {order['delivery_fee']} сом")
    lines.append(f"\n<b>К оплате: {order['total']} сом</b>")
    lines.append(
        f"\n<b>💳 МБанк оплата</b>\n"
        f"Номер: <code>{MBANK_NUMBER}</code>\n"
        f"Получатель: {MBANK_HOLDER}\n"
        f"Сумма: <b>{order['total']} сом</b>\n"
        f"Комментарий: <code>Заказ #{oid}</code>"
    )
    try:
        await target.edit_text("\n".join(lines), reply_markup=payment_kb(oid))
    except Exception:
        await target.answer("\n".join(lines), reply_markup=payment_kb(oid))


@dp.callback_query(F.data.startswith("paid:"))
async def cb_paid(call: CallbackQuery):
    uid = call.from_user.id
    oid = int(call.data.split(":")[1])
    order = pending_orders.pop(oid, None)
    if not order:
        await call.answer("Заказ не найден", show_alert=True); return
    order["status"] = "cooking"
    orders_db[oid] = order
    user_orders[uid].append(oid)
    carts[uid] = {}
    earned = int(order["subtotal"] * 0.05)
    bonus_points[uid] += earned
    masked = CAFE_PHONE[:-4] + "XXXX"
    await call.message.edit_text(
        f"✅ <b>Оплата принята! Заказ #{oid}</b>\n\n"
        f"📤 Уведомление отправлено на <b>{masked}</b>\n"
        f"🍳 Статус: <b>Готовится</b>\n\n"
        f"⏳ Ожидайте звонка в течение <b>5 минут</b>\n"
        f"⭐ Начислено <b>{earned} бонусов</b> (баланс: {bonus_points[uid]})\n\n"
        "Оцените нас 👇",
        reply_markup=rating_kb(oid)
    )
    await call.answer("💳 Оплата принята!", show_alert=True)


@dp.callback_query(F.data.startswith("rate:"))
async def cb_rate(call: CallbackQuery):
    _, oid_s, stars_s = call.data.split(":")
    ratings.append(int(stars_s))
    await call.message.edit_text(
        f"🙏 Спасибо за оценку <b>{stars_s}⭐</b>!\n\n"
        "Ваше мнение помогает нам стать лучше ❤️"
    )
    await call.answer("Спасибо!")


@dp.callback_query(F.data.startswith("cancel:"))
async def cb_cancel(call: CallbackQuery):
    oid = int(call.data.split(":")[1])
    pending_orders.pop(oid, None)
    await call.message.edit_text(f"❌ Заказ <b>#{oid}</b> отменён.\n\nЖдём вас снова!")
    await call.answer()


@dp.callback_query(F.data.startswith("status:"))
async def cb_status(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Нет прав"); return
    _, oid_s, st = call.data.split(":")
    oid = int(oid_s)
    order = orders_db.get(oid)
    if not order:
        await call.answer("Не найдено"); return
    order["status"] = st
    labels = {"cooking": "🍳 Готовится", "delivery": "🚴 В доставке", "done": "✅ Готово"}
    try:
        uid = order["user_id"]
        await bot.send_message(uid, f"📦 <b>Заказ #{oid}</b>\nСтатус обновлён: <b>{labels.get(st, st)}</b>")
    except Exception:
        pass
    await call.answer(f"Статус обновлён: {labels.get(st, st)}")


@dp.message(F.text == "⭐ Бонусы")
async def msg_bonus(message: Message):
    uid = message.from_user.id
    pts = bonus_points[uid]
    me = await bot.get_me()
    ref = f"https://t.me/{me.username}?start=ref_{uid}"
    await message.answer(
        f"<b>⭐ Бонусный счёт</b>\n\n"
        f"Баланс: <b>{pts} бонусов</b> = {pts} сом\n\n"
        "<b>Как заработать:</b>\n"
        "• 5% кэшбек с каждого заказа\n"
        "• 50 бонусов за регистрацию\n"
        "• 100 бонусов за приглашение\n\n"
        f"<b>Ваша реф. ссылка:</b>\n{ref}"
    )


@dp.message(F.text == "🎁 Промокод")
async def msg_promo(message: Message):
    await message.answer(
        "<b>🎁 Промокод</b>\n\n"
        "Введите код в чат:\n<code>WELCOME10</code> / <code>DASTAN15</code> / <code>HAPPY20</code>\n\n"
        "Скидка применится к следующему заказу."
    )


@dp.message(F.text == "💎 Подписки")
async def msg_subscriptions(message: Message):
    lines = ["<b>💎 Абонементы</b>\n\nЕжемесячные подписки с выгодой до 40%:\n"]
    btns = []
    for key, (name, price, desc) in SUBSCRIPTIONS.items():
        lines.append(f"<b>{name}</b>\n{desc}\nЦена: {price} сом/мес\n")
        btns.append([InlineKeyboardButton(text=f"Оформить — {price} сом", callback_data=f"sub:{key}")])
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


@dp.callback_query(F.data.startswith("sub:"))
async def cb_sub(call: CallbackQuery):
    key = call.data.split(":")[1]
    name, price, desc = SUBSCRIPTIONS[key]
    await call.message.edit_text(
        f"<b>💎 {name}</b>\n\n{desc}\n\n"
        f"<b>Оплата: {price} сом</b>\n\n"
        f"💳 МБанк: <code>{MBANK_NUMBER}</code>\n"
        f"Получатель: {MBANK_HOLDER}\n"
        f"Комментарий: <code>Подписка {name}</code>\n\n"
        "После оплаты напишите боту — активируем вручную."
    )
    await call.answer()


@dp.message(F.text == "📜 Мои заказы")
async def msg_my_orders(message: Message):
    uid = message.from_user.id
    oids = user_orders.get(uid, [])
    if not oids:
        await message.answer("У вас пока нет заказов. Сделайте первый! 🛒"); return
    lines = ["<b>📜 История заказов</b>\n"]
    status_map = {"cooking": "🍳 Готовится", "delivery": "🚴 Едет", "done": "✅ Выполнен", "paid": "💳 Оплачен"}
    for oid in oids[-10:][::-1]:
        o = orders_db.get(oid, {})
        ts = o.get("created_at", "")[:16].replace("T", " ")
        st = status_map.get(o.get("status", ""), "•")
        lines.append(f"#{oid} — {o.get('total', 0)} сом — {st} — {ts}")
    await message.answer("\n".join(lines))


@dp.message(F.text == "❤️ Избранное")
async def msg_favorites(message: Message):
    uid = message.from_user.id
    favs = favorites.get(uid, set())
    if not favs:
        await message.answer("❤️ Избранное пусто.\n\nНажмите ❤️ на блюде в меню чтобы добавить."); return
    lines = ["<b>❤️ Избранное</b>\n"]
    btns = []
    for name in favs:
        item = find_item(name)
        if item:
            lines.append(f"{item[2]} {name} — {item[1]} сом")
            btns.append([InlineKeyboardButton(text=f"➕ {name}", callback_data=f"addname:{name}")])
    btns.append([InlineKeyboardButton(text="🛒 В корзину всё", callback_data="fav_all")])
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


@dp.callback_query(F.data == "fav_all")
async def cb_fav_all(call: CallbackQuery):
    uid = call.from_user.id
    for name in favorites.get(uid, set()):
        carts[uid][name] = carts[uid].get(name, 0) + 1
    await call.answer("Всё избранное добавлено в корзину!")
    await render_cart(call.message, uid, edit=True)


@dp.message(F.text == "📞 Контакты")
async def msg_contacts(message: Message):
    await message.answer(
        f"<b>📞 Контакты</b>\n\n"
        f"Телефон: <b>{CAFE_PHONE}</b>\n"
        f"Whatsapp: {CAFE_PHONE}\n"
        f"Instagram: @cafe_dastan\n"
        f"Адрес: {CAFE_ADDRESS}\n"
        f"Часы: {CAFE_HOURS}"
    )


@dp.message(F.text == "💬 Поддержка")
async def msg_support(message: Message):
    await message.answer(
        f"<b>💬 Поддержка</b>\n\n"
        f"Напишите нам напрямую:\n{SUPPORT_USERNAME}\n\n"
        "Или позвоните:\n"
        f"<b>{CAFE_PHONE}</b>\n\n"
        "Отвечаем в течение 15 минут ⏰"
    )


@dp.message(F.text == "🔥 Популярное")
async def msg_popular(message: Message):
    lines = ["<b>🔥 Популярные позиции</b>\n"]
    btns = []
    for name in POPULAR:
        item = find_item(name)
        if item:
            lines.append(f"{item[2]} {name} — {item[1]} сом")
            btns.append([InlineKeyboardButton(text=f"➕ {name} — {item[1]} сом", callback_data=f"addname:{name}")])
    btns.append([InlineKeyboardButton(text="🛒 Корзина", callback_data="show_cart")])
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    ADMIN_IDS.add(message.from_user.id)
    await message.answer(
        "✅ <b>Режим администратора</b>\n\n"
        "/stats — общая статистика\n"
        "/orders — последние заказы\n"
        "/revenue — выручка сегодня\n"
        "/broadcast — рассылка всем\n"
        "/setfav NAME — добавить в популярное\n\n"
        "Статусы заказов можно обновлять в /orders"
    )


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    total = len(orders_db)
    rev = sum(o["total"] for o in orders_db.values())
    avg = rev / total if total else 0
    avg_r = sum(ratings) / len(ratings) if ratings else 0
    await message.answer(
        f"<b>📊 Статистика</b>\n\n"
        f"Заказов всего: <b>{total}</b>\n"
        f"Выручка: <b>{rev} сом</b>\n"
        f"Средний чек: <b>{int(avg)} сом</b>\n"
        f"Рейтинг: <b>{avg_r:.1f}⭐</b> ({len(ratings)} оценок)\n"
        f"Клиентов: <b>{len(user_profile)}</b>\n"
        f"Ждут оплаты: <b>{len(pending_orders)}</b>"
    )


@dp.message(Command("orders"))
async def cmd_orders(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    if not orders_db:
        await message.answer("Заказов нет."); return
    last = sorted(orders_db.items(), reverse=True)[:10]
    lines = ["<b>📋 Последние заказы</b>\n"]
    for oid, o in last:
        ts = o["created_at"][:16].replace("T", " ")
        lines.append(f"#{oid} — {o['total']} сом — @{o['username']} — {ts}")
    status_btns = [[InlineKeyboardButton(text=f"#{oid} статус", callback_data=f"edit_status:{oid}")] for oid, _ in last[:5]]
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=status_btns) if status_btns else None)


@dp.callback_query(F.data.startswith("edit_status:"))
async def cb_edit_status(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Нет прав"); return
    oid = int(call.data.split(":")[1])
    await call.message.answer(f"Обновить статус заказа #{oid}:", reply_markup=status_kb(oid, admin=True))
    await call.answer()


@dp.message(Command("revenue"))
async def cmd_revenue(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    today = datetime.now().date().isoformat()
    today_o = [o for o in orders_db.values() if o["created_at"].startswith(today)]
    await message.answer(
        f"<b>💰 Выручка сегодня</b>\n\n"
        f"Заказов: {len(today_o)}\n"
        f"Сумма: <b>{sum(o['total'] for o in today_o)} сом</b>"
    )


@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /broadcast Текст сообщения"); return
    text = args[1]
    count = 0
    for uid in user_profile:
        try:
            await bot.send_message(uid, f"📢 <b>Новость от {CAFE_NAME}</b>\n\n{text}")
            count += 1
        except Exception:
            pass
    await message.answer(f"✅ Отправлено {count} пользователям")


@dp.message()
async def handle_any(message: Message):
    uid = message.from_user.id
    text = message.text.strip()
    upper = text.upper()

    if uid in awaiting_address:
        oid = awaiting_address.pop(uid)
        awaiting_phone.discard(uid)
        if oid in pending_orders:
            pending_orders[oid]["phone"] = text
        await show_payment(message, oid)
        return

    if upper in PROMO_CODES:
        pct = PROMO_CODES[upper]
        user_promos[uid] = pct
        await message.answer(
            f"✅ Промокод <b>{upper}</b> активирован!\n"
            f"Скидка <b>{pct}%</b> применится при оформлении 🛒"
        )
        return

    await message.answer("🤔 Используйте кнопки ниже 👇", reply_markup=main_kb_for(uid))


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
