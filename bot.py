import os
import asyncio
import logging
import random
from datetime import datetime, timedelta
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

CAFE_NAME = "🍽 Кафе Дастан"
CAFE_ADDRESS = "Бишкек, ул. Чуй 100"
CAFE_PHONE = "+996 555 12 34 56"
CAFE_HOURS = "09:00 – 23:00 ежедневно"
MBANK_NUMBER = "+996 700 123 456"
MBANK_HOLDER = "ДАСТАН К."
SUPPORT_USERNAME = "@cafe_dastan_support"

BRANCHES = {
    "center": ("🏙 Чуй 100 (центр)", "Чуй 100, Бишкек"),
    "djal": ("🌆 Джал 15", "Джал мкр, 15"),
    "vostok": ("🌇 Восток-5", "Восток-5, ул. Юсупова 12"),
}

DELIVERY_ZONES = {
    "pickup": ("🚶 Самовывоз", 0),
    "center": ("🏙 Центр города", 80),
    "mid": ("🏘 Средние районы", 150),
    "far": ("🌆 Окраины / Ю-3", 250),
}

PROMO_CODES = {
    "WELCOME10": 10, "DASTAN15": 15, "HAPPY20": 20, "FRIEND5": 5, "VIP30": 30,
    "SUSHI25": 25, "PIZZA15": 15,
}

SUBSCRIPTIONS = {
    "coffee_day": ("☕ Утренний кофе (30 дней)", 2500, "Американо или эспрессо каждый день"),
    "lunch_week": ("🥗 Ланч-абонемент (5 дней)", 1800, "Блюдо + напиток каждый будний день"),
    "sweet_month": ("🍰 Десертная подписка (30 дней)", 3500, "Десерт на выбор каждый день"),
    "sushi_week": ("🍣 Суши-неделя (7 дней)", 4900, "Ролл на выбор каждый день"),
}

POPULAR = ["Капучино", "Филадельфия (8 шт)", "Маргарита", "Том Ям", "Цезарь с курицей"]

SPIN_PRIZES = [10, 20, 30, 50, 75, 100, 150, 200, 300]

VIP_TIERS = [
    (0, "🥉 Bronze", 0),
    (1000, "🥈 Silver", 2),
    (5000, "🥇 Gold", 5),
    (15000, "💎 Platinum", 10),
]

CHALLENGES = {
    "3_orders": ("Закажи 3 раза за неделю", 3, 500),
    "5000_spent": ("Потрать 5000 сом за месяц", 5000, 1000),
}

MENU = {
    "coffee": {"title": "☕ Кофе и напитки", "items": [
        ("Эспрессо", 120, "☕"), ("Американо", 150, "☕"), ("Капучино", 180, "🥛"),
        ("Латте", 200, "🥛"), ("Раф кофе", 220, "🥛"), ("Флэт уайт", 210, "🥛"),
        ("Горячий шоколад", 200, "🍫"), ("Чай зелёный", 100, "🍵"), ("Чай чёрный", 100, "🍵"),
        ("Матча латте", 280, "🍵"), ("Какао", 180, "🍫"),
    ]},
    "cold": {"title": "🍹 Холодные напитки", "items": [
        ("Лимонад домашний", 180, "🍋"), ("Мохито б/а", 250, "🍃"),
        ("Апельсиновый фреш", 280, "🍊"), ("Морковный фреш", 250, "🥕"),
        ("Смузи ягодный", 320, "🫐"), ("Смузи тропический", 320, "🥭"),
        ("Айс латте", 230, "🧊"), ("Милкшейк шоколад", 300, "🥤"),
        ("Боба чай", 280, "🧋"),
    ]},
    "breakfast": {"title": "🍳 Завтраки", "items": [
        ("Овсянка с ягодами", 220, "🥣"), ("Гранола с йогуртом", 280, "🥣"),
        ("Омлет с овощами", 250, "🍳"), ("Яичница с беконом", 290, "🍳"),
        ("Сырники со сметаной", 260, "🥞"), ("Панкейки с кленовым сиропом", 280, "🥞"),
        ("Авокадо-тост", 320, "🥑"), ("Блины с икрой", 420, "🥞"),
    ]},
    "asian": {"title": "🍜 Паназиатская", "items": [
        ("Том Ям с креветками", 520, "🍲"), ("Фо Бо", 480, "🍜"),
        ("Рамен с курицей", 450, "🍜"), ("Рамен с говядиной", 520, "🍜"),
        ("Пад Тай", 420, "🍤"), ("Курица терияки с рисом", 450, "🍗"),
        ("Мисо суп", 220, "🍲"), ("Вок с овощами", 350, "🥘"),
    ]},
    "sushi": {"title": "🍣 Суши и роллы", "items": [
        ("Филадельфия (8 шт)", 520, "🍣"), ("Калифорния (8 шт)", 450, "🍣"),
        ("Сяке маки (6 шт)", 380, "🍣"), ("Унаги маки (6 шт)", 420, "🍣"),
        ("Сет Новичок (24 шт)", 1200, "🍱"), ("Сет Премиум (32 шт)", 1850, "🍱"),
        ("Нигири лосось (2 шт)", 280, "🍣"), ("Темпура ролл (8 шт)", 580, "🍣"),
    ]},
    "chinese": {"title": "🥡 Китайская кухня", "items": [
        ("Кунг Пао с курицей", 420, "🌶"), ("Говядина в кисло-сладком", 480, "🍜"),
        ("Жареный рис с овощами", 280, "🍚"), ("Жареный рис с курицей", 350, "🍚"),
        ("Лапша удон с курицей", 380, "🍜"), ("Димсамы (6 шт)", 380, "🥟"),
        ("Утка по-пекински (порция)", 650, "🦆"), ("Спринг роллы (4 шт)", 280, "🥠"),
    ]},
    "pizza": {"title": "🍕 Пицца", "items": [
        ("Маргарита", 450, "🍕"), ("Пепперони", 520, "🍕"),
        ("4 сыра", 550, "🍕"), ("Гавайская", 520, "🍕"),
        ("Мясная", 620, "🍕"), ("Вегетарианская", 480, "🍕"),
        ("Морская", 680, "🍕"), ("BBQ куриная", 580, "🍕"),
    ]},
    "food": {"title": "🥗 Европейская", "items": [
        ("Сэндвич с курицей", 280, "🥪"), ("Сэндвич с лососем", 350, "🥪"),
        ("Цезарь с курицей", 420, "🥗"), ("Цезарь с креветками", 520, "🥗"),
        ("Греческий салат", 380, "🥗"), ("Паста Карбонара", 450, "🍝"),
        ("Паста с креветками", 520, "🍝"), ("Бургер говяжий", 480, "🍔"),
        ("Томатный суп", 280, "🍲"),
    ]},
    "desserts": {"title": "🍰 Десерты", "items": [
        ("Круассан классический", 120, "🥐"), ("Круассан с шоколадом", 150, "🥐"),
        ("Чизкейк Нью-Йорк", 280, "🍰"), ("Тирамису", 300, "🍰"),
        ("Медовик", 250, "🍯"), ("Макаруны (3 шт)", 220, "🍬"),
        ("Печенье (набор)", 150, "🍪"), ("Мороженое 3 шарика", 180, "🍨"),
        ("Брауни", 220, "🍫"),
    ]},
}

COMBOS = {
    "coffee_croissant": {
        "title": "☕ Утренний набор",
        "desc": "Капучино + круассан классический",
        "items": ["Капучино", "Круассан классический"],
        "price": 260,
        "saving": 40,
    },
    "sushi_set_drink": {
        "title": "🍣 Суши-сет + напиток",
        "desc": "Сет Новичок + лимонад на выбор",
        "items": ["Сет Новичок (24 шт)", "Лимонад домашний"],
        "price": 1280,
        "saving": 100,
    },
    "pizza_party": {
        "title": "🍕 Пицца-пати",
        "desc": "Маргарита + Пепперони + 2 лимонада",
        "items": ["Маргарита", "Пепперони", "Лимонад домашний", "Лимонад домашний"],
        "price": 1180,
        "saving": 150,
    },
    "asian_lunch": {
        "title": "🍜 Азиатский ланч",
        "desc": "Рамен с курицей + спринг роллы + чай зелёный",
        "items": ["Рамен с курицей", "Спринг роллы (4 шт)", "Чай зелёный"],
        "price": 790,
        "saving": 40,
    },
    "family_feast": {
        "title": "👨‍👩‍👧 Семейный набор",
        "desc": "2× Бургер + 2× картошка (Цезарь) + 2× Пепси (лимонад)",
        "items": ["Бургер говяжий", "Бургер говяжий", "Цезарь с курицей", "Лимонад домашний", "Лимонад домашний"],
        "price": 1850,
        "saving": 230,
    },
}

COFFEE_OPTIONS = {
    "milk": [("Обычное", 0), ("Безлактозное", 30), ("Миндальное", 50), ("Кокосовое", 50), ("Овсяное", 50)],
    "sugar": [("Без сахара", 0), ("1 ложка", 0), ("2 ложки", 0), ("Сироп карамель", 40), ("Сироп ваниль", 40)],
    "size": [("Маленький (200мл)", 0), ("Средний (300мл)", 30), ("Большой (400мл)", 60)],
}

COFFEE_NAMES = {"Эспрессо", "Американо", "Капучино", "Латте", "Раф кофе", "Флэт уайт", "Горячий шоколад", "Матча латте", "Какао", "Айс латте"}


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


def find_cat_for(name):
    for k, cat in MENU.items():
        for it in cat["items"]:
            if it[0] == name:
                return k
    return None


orders_db: dict[int, dict] = {}
pending_orders: dict[int, dict] = {}
order_counter = 1000
carts: dict[int, dict[str, int]] = defaultdict(dict)
bonus_points: dict[int, int] = defaultdict(int)
user_profile: dict[int, dict] = {}
user_orders: dict[int, list[int]] = defaultdict(list)
user_total_spent: dict[int, int] = defaultdict(int)
user_branch: dict[int, str] = {}
favorites: dict[int, set[str]] = defaultdict(set)
ratings: list[int] = []
ADMIN_IDS: set[int] = set()
awaiting_phone: dict[int, int] = {}
user_promos: dict[int, int] = {}
last_spin: dict[int, str] = {}
reservations: list[dict] = []
awaiting_reservation: dict[int, dict] = {}
awaiting_search: set[int] = set()
coffee_customize: dict[int, dict] = {}
weekly_challenge: dict[int, int] = defaultdict(int)


def vip_tier(uid):
    spent = user_total_spent[uid]
    tier = VIP_TIERS[0]
    for t in VIP_TIERS:
        if spent >= t[0]:
            tier = t
    return tier


def daily_special():
    seed = datetime.now().day
    random.seed(seed)
    item = random.choice(flat_menu())
    random.seed()
    return item


def cart_subtotal(uid):
    total = 0
    for name, qty in carts[uid].items():
        item = find_item(name)
        if item:
            total += item[1] * qty
        elif name.startswith("COMBO:"):
            combo = COMBOS.get(name[6:])
            if combo:
                total += combo["price"] * qty
        elif name.startswith("CUSTOM:"):
            # custom coffee: CUSTOM:base|milk|sugar|size = stored price in carts value as extra
            parts = name[7:].split("|")
            if len(parts) == 4:
                base_name, milk_extra, sugar_extra, size_extra = parts
                base = find_item(base_name)
                if base:
                    total += (base[1] + int(milk_extra) + int(sugar_extra) + int(size_extra)) * qty
    return total


def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Меню"), KeyboardButton(text="🎁 Комбо")],
            [KeyboardButton(text="🛒 Корзина"), KeyboardButton(text="🔥 Популярное")],
            [KeyboardButton(text="🔎 Поиск"), KeyboardButton(text="🏪 Филиал")],
            [KeyboardButton(text="⭐ Бонусы"), KeyboardButton(text="🎁 Промокод")],
            [KeyboardButton(text="🎰 Колесо удачи"), KeyboardButton(text="🏆 Челлендж")],
            [KeyboardButton(text="💎 Подписки"), KeyboardButton(text="🪑 Бронь")],
            [KeyboardButton(text="📜 Заказы"), KeyboardButton(text="❤️ Избранное")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💬 Поддержка")],
        ],
        resize_keyboard=True,
    )


def menu_categories_kb():
    btns = []
    keys = list(MENU.keys())
    # Two columns
    for i in range(0, len(keys), 2):
        row = []
        for k in keys[i:i+2]:
            row.append(InlineKeyboardButton(text=MENU[k]["title"], callback_data=f"cat:{k}"))
        btns.append(row)
    btns.append([
        InlineKeyboardButton(text="🎁 Комбо", callback_data="combos"),
        InlineKeyboardButton(text="🔥 Топ", callback_data="popular"),
    ])
    btns.append([InlineKeyboardButton(text="🛒 Корзина", callback_data="show_cart")])
    return InlineKeyboardMarkup(inline_keyboard=btns)


def category_items_kb(cat_key, uid):
    cat = MENU[cat_key]
    btns = []
    for name, price, emoji in cat["items"]:
        is_fav = name in favorites[uid]
        heart = "💖" if is_fav else "🤍"
        is_custom = name in COFFEE_NAMES
        if is_custom:
            btns.append([
                InlineKeyboardButton(text=f"{emoji} {name} — {price} сом", callback_data=f"add:{name}"),
                InlineKeyboardButton(text="⚙️", callback_data=f"custom:{name}"),
                InlineKeyboardButton(text=heart, callback_data=f"fav:{name}"),
            ])
        else:
            btns.append([
                InlineKeyboardButton(text=f"{emoji} {name} — {price} сом", callback_data=f"add:{name}"),
                InlineKeyboardButton(text=heart, callback_data=f"fav:{name}"),
            ])
    btns.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="categories"),
        InlineKeyboardButton(text="🛒 Корзина", callback_data="show_cart"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=btns)


def combos_kb():
    btns = []
    for key, c in COMBOS.items():
        btns.append([InlineKeyboardButton(text=f"{c['title']} — {c['price']} сом", callback_data=f"combo_view:{key}")])
    btns.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="categories")])
    return InlineKeyboardMarkup(inline_keyboard=btns)


def cart_view_kb(uid):
    btns = []
    for name in list(carts[uid].keys()):
        qty = carts[uid][name]
        display = name
        if name.startswith("COMBO:"):
            c = COMBOS.get(name[6:])
            if c:
                display = c["title"]
        elif name.startswith("CUSTOM:"):
            base = name[7:].split("|")[0]
            display = f"{base} (кастом)"
        btns.append([
            InlineKeyboardButton(text="➖", callback_data=f"qty:-:{name[:40]}"),
            InlineKeyboardButton(text=f"{qty}× {display[:22]}", callback_data="noop"),
            InlineKeyboardButton(text="➕", callback_data=f"qty:+:{name[:40]}"),
            InlineKeyboardButton(text="🗑", callback_data=f"qty:0:{name[:40]}"),
        ])
    if carts[uid]:
        btns.append([
            InlineKeyboardButton(text="✅ Оформить", callback_data="checkout"),
            InlineKeyboardButton(text="🗑 Очистить", callback_data="clear_cart"),
        ])
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


def branch_kb():
    btns = [[InlineKeyboardButton(text=label, callback_data=f"branch:{k}")] for k, (label, _) in BRANCHES.items()]
    return InlineKeyboardMarkup(inline_keyboard=btns)


def reservation_time_kb():
    times = ["12:00", "13:00", "14:00", "18:00", "19:00", "20:00", "21:00"]
    btns = [[InlineKeyboardButton(text=t, callback_data=f"rtime:{t}")] for t in times]
    return InlineKeyboardMarkup(inline_keyboard=btns)


def reservation_guests_kb():
    btns = [[InlineKeyboardButton(text=f"{i}", callback_data=f"rguests:{i}") for i in range(1, 5)]]
    btns.append([InlineKeyboardButton(text=f"{i}", callback_data=f"rguests:{i}") for i in range(5, 9)])
    return InlineKeyboardMarkup(inline_keyboard=btns)


def reservation_date_kb():
    today = datetime.now().date()
    btns = []
    for i in range(7):
        d = today + timedelta(days=i)
        label = "Сегодня" if i == 0 else "Завтра" if i == 1 else d.strftime("%d.%m (%a)")
        btns.append([InlineKeyboardButton(text=label, callback_data=f"rdate:{d.isoformat()}")])
    return InlineKeyboardMarkup(inline_keyboard=btns)


def coffee_customize_kb(uid, base_name):
    state = coffee_customize.get(uid, {"base": base_name, "milk": 0, "sugar": 0, "size": 0})
    coffee_customize[uid] = state
    btns = []
    btns.append([InlineKeyboardButton(text="🥛 Молоко", callback_data="custom_sec:milk")])
    btns.append([InlineKeyboardButton(text="🍯 Сахар / сироп", callback_data="custom_sec:sugar")])
    btns.append([InlineKeyboardButton(text="📏 Размер", callback_data="custom_sec:size")])
    base = find_item(base_name)
    extras = sum([COFFEE_OPTIONS[k][state[k]][1] for k in ["milk", "sugar", "size"]])
    final_price = base[1] + extras if base else 0
    btns.append([InlineKeyboardButton(text=f"✅ Добавить — {final_price} сом", callback_data="custom_confirm")])
    btns.append([InlineKeyboardButton(text="❌ Отмена", callback_data="categories")])
    return InlineKeyboardMarkup(inline_keyboard=btns)


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
    tier = vip_tier(uid)
    branch = BRANCHES.get(user_branch.get(uid, "center"))[0]
    text = (
        f"{'Добро пожаловать' if is_new else 'С возвращением'}, <b>{name}</b>! 👋\n"
        f"Статус: <b>{tier[1]}</b> • Филиал: {branch}{bonus_note}\n\n"
        f"<b>{CAFE_NAME}</b> — 9 кухонь мира под одной крышей 🌍\n\n"
        "☕ Кофе • 🍳 Завтраки • 🍣 Суши\n"
        "🥡 Китай • 🍜 Азия • 🍕 Пицца\n"
        "🥗 Европа • 🍰 Десерты • 🍹 Напитки\n\n"
        "🎁 Комбо • ⚙️ Кастом кофе • 🏆 Челлендж\n"
        "🎰 Колесо • 💎 Подписки • 🪑 Бронь\n\n"
        "👇 Выбирайте:"
    )
    await message.answer(text, reply_markup=main_kb())


@dp.message(F.text == "📋 Меню")
async def show_menu(message: Message):
    name, price, emoji = daily_special()
    disc = int(price * 0.85)
    await message.answer(
        f"<b>📋 Меню — 9 категорий</b>\n\n🔥 Акция дня: {emoji} <b>{name}</b> — {disc} сом (было {price})\n\nВыберите категорию:",
        reply_markup=menu_categories_kb()
    )


@dp.callback_query(F.data == "categories")
async def cb_categories(call: CallbackQuery):
    try:
        await call.message.edit_text("<b>📋 Меню — 9 категорий</b>\n\nВыберите:", reply_markup=menu_categories_kb())
    except Exception:
        await call.message.answer("<b>📋 Меню</b>", reply_markup=menu_categories_kb())
    await call.answer()


@dp.callback_query(F.data.startswith("cat:"))
async def cb_category(call: CallbackQuery):
    key = call.data.split(":")[1]
    cat = MENU.get(key)
    if not cat:
        await call.answer(); return
    try:
        await call.message.edit_text(
            f"<b>{cat['title']}</b>\n\nТап на блюдо — в корзину\n⚙️ — кастомизация (кофе)\n🤍 — в избранное",
            reply_markup=category_items_kb(key, call.from_user.id)
        )
    except Exception:
        pass
    await call.answer()


@dp.callback_query(F.data.startswith("fav:"))
async def cb_fav_toggle(call: CallbackQuery):
    name = call.data[4:]
    uid = call.from_user.id
    if name in favorites[uid]:
        favorites[uid].remove(name)
        await call.answer(f"💔 убрано из избранного")
    else:
        favorites[uid].add(name)
        await call.answer(f"💖 в избранном!")
    cat_key = find_cat_for(name)
    if cat_key:
        try:
            await call.message.edit_reply_markup(reply_markup=category_items_kb(cat_key, uid))
        except Exception:
            pass


@dp.callback_query(F.data.startswith("custom:"))
async def cb_custom_start(call: CallbackQuery):
    name = call.data[7:]
    uid = call.from_user.id
    coffee_customize[uid] = {"base": name, "milk": 0, "sugar": 0, "size": 0}
    try:
        await call.message.edit_text(
            f"<b>⚙️ Кастомизация: {name}</b>\n\nНастройте ваш напиток:",
            reply_markup=coffee_customize_kb(uid, name)
        )
    except Exception:
        pass
    await call.answer()


@dp.callback_query(F.data.startswith("custom_sec:"))
async def cb_custom_section(call: CallbackQuery):
    section = call.data.split(":")[1]
    uid = call.from_user.id
    state = coffee_customize.get(uid)
    if not state:
        await call.answer("Начните заново"); return
    labels = {"milk": "🥛 Молоко", "sugar": "🍯 Сахар/сироп", "size": "📏 Размер"}
    btns = []
    for i, (label, price) in enumerate(COFFEE_OPTIONS[section]):
        mark = "✅ " if state[section] == i else ""
        extra = f" (+{price} сом)" if price else ""
        btns.append([InlineKeyboardButton(text=f"{mark}{label}{extra}", callback_data=f"custom_set:{section}:{i}")])
    btns.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"custom:{state['base']}")])
    try:
        await call.message.edit_text(
            f"<b>{labels[section]}</b>\n\nВыберите опцию:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
        )
    except Exception:
        pass
    await call.answer()


@dp.callback_query(F.data.startswith("custom_set:"))
async def cb_custom_set(call: CallbackQuery):
    _, section, idx = call.data.split(":")
    uid = call.from_user.id
    state = coffee_customize.get(uid)
    if not state:
        await call.answer("Начните заново"); return
    state[section] = int(idx)
    try:
        await call.message.edit_text(
            f"<b>⚙️ Кастомизация: {state['base']}</b>",
            reply_markup=coffee_customize_kb(uid, state["base"])
        )
    except Exception:
        pass
    await call.answer("✅ Сохранено")


@dp.callback_query(F.data == "custom_confirm")
async def cb_custom_confirm(call: CallbackQuery):
    uid = call.from_user.id
    state = coffee_customize.pop(uid, None)
    if not state:
        await call.answer("Ошибка"); return
    base = state["base"]
    m = COFFEE_OPTIONS["milk"][state["milk"]][1]
    s = COFFEE_OPTIONS["sugar"][state["sugar"]][1]
    sz = COFFEE_OPTIONS["size"][state["size"]][1]
    custom_key = f"CUSTOM:{base}|{m}|{s}|{sz}"
    carts[uid][custom_key] = carts[uid].get(custom_key, 0) + 1
    base_item = find_item(base)
    total_price = base_item[1] + m + s + sz if base_item else 0
    try:
        await call.message.edit_text(
            f"✅ <b>{base} (кастом) — {total_price} сом</b>\n\n"
            f"🥛 {COFFEE_OPTIONS['milk'][state['milk']][0]}\n"
            f"🍯 {COFFEE_OPTIONS['sugar'][state['sugar']][0]}\n"
            f"📏 {COFFEE_OPTIONS['size'][state['size']][0]}\n\n"
            "Добавлено в корзину 🛒"
        )
    except Exception:
        pass
    await call.answer("В корзине!")


@dp.message(F.text == "🎁 Комбо")
async def msg_combos(message: Message):
    await show_combos(message)


@dp.callback_query(F.data == "combos")
async def cb_combos(call: CallbackQuery):
    try:
        await call.message.edit_text(combos_text(), reply_markup=combos_kb())
    except Exception:
        await call.message.answer(combos_text(), reply_markup=combos_kb())
    await call.answer()


def combos_text():
    lines = ["<b>🎁 Комбо-наборы</b>\n\nВыгоднее чем по отдельности:\n"]
    for key, c in COMBOS.items():
        lines.append(f"<b>{c['title']}</b>")
        lines.append(f"{c['desc']}")
        lines.append(f"Цена: <b>{c['price']} сом</b> (экономия {c['saving']} сом)\n")
    return "\n".join(lines)


async def show_combos(message):
    await message.answer(combos_text(), reply_markup=combos_kb())


@dp.callback_query(F.data.startswith("combo_view:"))
async def cb_combo_view(call: CallbackQuery):
    key = call.data.split(":")[1]
    c = COMBOS.get(key)
    if not c:
        await call.answer("Не найдено"); return
    lines = [f"<b>{c['title']}</b>\n", c["desc"], "\n<b>В наборе:</b>"]
    for name in c["items"]:
        item = find_item(name)
        if item:
            lines.append(f"  {item[2]} {name}")
    lines.append(f"\nЦена: <b>{c['price']} сом</b>")
    lines.append(f"Вы экономите: {c['saving']} сом ✅")
    btns = [[
        InlineKeyboardButton(text=f"➕ В корзину — {c['price']} сом", callback_data=f"combo_add:{key}"),
    ], [InlineKeyboardButton(text="⬅️ К комбо", callback_data="combos")]]
    try:
        await call.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    except Exception:
        pass
    await call.answer()


@dp.callback_query(F.data.startswith("combo_add:"))
async def cb_combo_add(call: CallbackQuery):
    key = call.data.split(":")[1]
    uid = call.from_user.id
    combo_key = f"COMBO:{key}"
    carts[uid][combo_key] = carts[uid].get(combo_key, 0) + 1
    await call.answer(f"✅ {COMBOS[key]['title']} в корзине")


@dp.callback_query(F.data == "popular")
async def cb_popular(call: CallbackQuery):
    lines = ["<b>🔥 Популярные блюда</b>\n"]
    btns = []
    for name in POPULAR:
        item = find_item(name)
        if item:
            lines.append(f"{item[2]} {item[0]} — {item[1]} сом")
            btns.append([InlineKeyboardButton(text=f"➕ {item[0]}", callback_data=f"add:{item[0]}")])
    btns.append([InlineKeyboardButton(text="🛒 Корзина", callback_data="show_cart"),
                 InlineKeyboardButton(text="📋 Меню", callback_data="categories")])
    try:
        await call.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    except Exception:
        await call.message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await call.answer()


@dp.callback_query(F.data.startswith("add:"))
async def cb_add(call: CallbackQuery):
    name = call.data[4:]
    item = find_item(name)
    if not item:
        await call.answer("Не найдено"); return
    uid = call.from_user.id
    carts[uid][name] = carts[uid].get(name, 0) + 1
    await call.answer(f"✅ {name} × {carts[uid][name]}")


@dp.callback_query(F.data.startswith("qty:"))
async def cb_qty(call: CallbackQuery):
    _, op, name_prefix = call.data.split(":", 2)
    uid = call.from_user.id
    full_name = None
    for k in carts[uid]:
        if k.startswith(name_prefix[:40]):
            full_name = k; break
    if not full_name:
        await call.answer("Не найдено"); return
    cur = carts[uid].get(full_name, 0)
    if op == "+":
        carts[uid][full_name] = cur + 1
    elif op == "-":
        if cur > 1:
            carts[uid][full_name] = cur - 1
        else:
            carts[uid].pop(full_name, None)
    elif op == "0":
        carts[uid].pop(full_name, None)
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
        text = "<b>🛒 Корзина пуста</b>\n\nДобавьте товары из меню 📋"
    else:
        lines = ["<b>🛒 Ваша корзина</b>\n"]
        subtotal = 0
        for name, qty in cart.items():
            if name.startswith("COMBO:"):
                c = COMBOS.get(name[6:])
                if c:
                    sub = c["price"] * qty
                    subtotal += sub
                    lines.append(f"🎁 {c['title']} × {qty} = {sub} сом")
            elif name.startswith("CUSTOM:"):
                parts = name[7:].split("|")
                if len(parts) == 4:
                    base_name, m, s, sz = parts
                    base = find_item(base_name)
                    if base:
                        p = base[1] + int(m) + int(s) + int(sz)
                        sub = p * qty
                        subtotal += sub
                        lines.append(f"⚙️ {base_name} (кастом) × {qty} = {sub} сом")
            else:
                item = find_item(name)
                if item:
                    sub = item[1] * qty
                    subtotal += sub
                    lines.append(f"{item[2]} {name} × {qty} = {sub} сом")
        lines.append(f"\nПодытог: <b>{subtotal} сом</b>")
        promo_pct = user_promos.get(uid, 0)
        total = subtotal
        if promo_pct:
            disc = int(subtotal * promo_pct / 100)
            total -= disc
            lines.append(f"Промокод -{promo_pct}%: −{disc} сом")
        tier = vip_tier(uid)
        if tier[2] > 0:
            vip_disc = int(subtotal * tier[2] / 100)
            total -= vip_disc
            lines.append(f"{tier[1]} -{tier[2]}%: −{vip_disc} сом")
        lines.append(f"\n<b>Итого: {total} сом</b>")
        lines.append(f"⭐ Начислим {int(subtotal * 0.05)} бонусов")
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
    user_promos.pop(call.from_user.id, None)
    await render_cart(call.message, call.from_user.id, edit=True)
    await call.answer("Корзина очищена")


@dp.callback_query(F.data == "checkout")
async def cb_checkout(call: CallbackQuery):
    global order_counter
    uid = call.from_user.id
    cart = carts.get(uid, {})
    if not cart:
        await call.answer("Корзина пуста", show_alert=True); return
    subtotal = cart_subtotal(uid)
    promo_pct = user_promos.get(uid, 0)
    tier = vip_tier(uid)
    promo_disc = int(subtotal * promo_pct / 100) if promo_pct else 0
    vip_disc = int(subtotal * tier[2] / 100) if tier[2] else 0
    total_after_disc = subtotal - promo_disc - vip_disc
    order_counter += 1
    oid = order_counter
    pending_orders[oid] = {
        "user_id": uid, "username": call.from_user.username or call.from_user.first_name,
        "items": dict(cart), "subtotal": subtotal, "delivery_fee": 0, "delivery_type": None,
        "discount": promo_disc + vip_disc, "promo_pct": promo_pct, "vip_disc": vip_disc,
        "total": total_after_disc, "status": "pending",
        "created_at": datetime.now().isoformat(), "phone": None,
        "branch": user_branch.get(uid, "center"),
    }
    user_promos.pop(uid, None)
    try:
        await call.message.edit_text(
            f"<b>📦 Заказ #{oid}</b>\n\nВыберите способ получения:",
            reply_markup=delivery_kb(oid)
        )
    except Exception:
        await call.message.answer(
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
    awaiting_phone[uid] = oid
    try:
        await call.message.edit_text(
            f"<b>📦 Заказ #{oid}</b> — {label}\n\n"
            "📱 Напишите ваш номер телефона для подтверждения\n"
            "(или пропустите)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Пропустить ➡️", callback_data=f"skip_phone:{oid}")
            ]])
        )
    except Exception:
        pass
    await call.answer()


@dp.callback_query(F.data.startswith("skip_phone:"))
async def cb_skip_phone(call: CallbackQuery):
    oid = int(call.data.split(":")[1])
    awaiting_phone.pop(call.from_user.id, None)
    await show_payment(call.message, oid)
    await call.answer()


async def show_payment(target, oid):
    order = pending_orders.get(oid)
    if not order:
        return
    lines = [f"<b>🧾 Заказ #{oid}</b>"]
    branch = BRANCHES.get(order.get("branch", "center"))
    if branch:
        lines.append(f"🏪 Филиал: {branch[0]}")
    lines.append("")
    for name, qty in order["items"].items():
        if name.startswith("COMBO:"):
            c = COMBOS.get(name[6:])
            if c:
                lines.append(f"🎁 {c['title']} × {qty} = {c['price']*qty} сом")
        elif name.startswith("CUSTOM:"):
            parts = name[7:].split("|")
            if len(parts) == 4:
                base_name, m, s, sz = parts
                base = find_item(base_name)
                if base:
                    p = base[1] + int(m) + int(s) + int(sz)
                    lines.append(f"⚙️ {base_name} (кастом) × {qty} = {p*qty} сом")
        else:
            item = find_item(name)
            if item:
                lines.append(f"{item[2]} {name} × {qty} = {item[1]*qty} сом")
    lines.append(f"\nПодытог: {order['subtotal']} сом")
    if order["discount"]:
        lines.append(f"Скидка: -{order['discount']} сом")
    if order["delivery_fee"]:
        lines.append(f"Доставка ({order['delivery_type']}): {order['delivery_fee']} сом")
    lines.append(f"\n<b>К оплате: {order['total']} сом</b>")
    if order.get("phone"):
        lines.append(f"📱 Телефон: {order['phone']}")
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
    user_total_spent[uid] += order["total"]
    carts[uid] = {}
    earned = int(order["subtotal"] * 0.05)
    bonus_points[uid] += earned
    weekly_challenge[uid] += 1
    if weekly_challenge[uid] == CHALLENGES["3_orders"][1]:
        bonus_points[uid] += CHALLENGES["3_orders"][2]
    masked = CAFE_PHONE[:-4] + "XXXX"
    tier = vip_tier(uid)
    challenge_note = ""
    if weekly_challenge[uid] == CHALLENGES["3_orders"][1]:
        challenge_note = f"\n🏆 <b>Челлендж пройден! +{CHALLENGES['3_orders'][2]} бонусов!</b>"
    await call.message.edit_text(
        f"✅ <b>Оплата принята! Заказ #{oid}</b>\n\n"
        f"📤 Уведомление отправлено на <b>{masked}</b>\n"
        f"🍳 Статус: <b>Готовится</b>\n\n"
        f"⏳ Ожидайте звонка в течение <b>5 минут</b>\n"
        f"⭐ Начислено <b>{earned} бонусов</b> (баланс: {bonus_points[uid]})\n"
        f"👑 Статус: <b>{tier[1]}</b>{challenge_note}\n\n"
        "Оцените нас 👇",
        reply_markup=rating_kb(oid)
    )
    await call.answer("💳 Оплата принята!", show_alert=True)


@dp.callback_query(F.data.startswith("rate:"))
async def cb_rate(call: CallbackQuery):
    _, oid_s, stars_s = call.data.split(":")
    ratings.append(int(stars_s))
    try:
        await call.message.edit_text(
            f"🙏 Спасибо за оценку <b>{stars_s}⭐</b>!\n\n"
            "Ваше мнение помогает нам стать лучше ❤️\n\n"
            "Напишите /start для продолжения."
        )
    except Exception:
        pass
    await call.answer("Спасибо!")


@dp.callback_query(F.data.startswith("cancel:"))
async def cb_cancel(call: CallbackQuery):
    oid = int(call.data.split(":")[1])
    pending_orders.pop(oid, None)
    try:
        await call.message.edit_text(f"❌ Заказ <b>#{oid}</b> отменён.\n\nЖдём вас снова!")
    except Exception:
        pass
    await call.answer()


@dp.message(F.text == "🏪 Филиал")
async def msg_branch(message: Message):
    uid = message.from_user.id
    current = BRANCHES.get(user_branch.get(uid, "center"))
    await message.answer(
        f"<b>🏪 Выбор филиала</b>\n\n"
        f"Текущий: <b>{current[0]}</b>\n"
        f"Адрес: {current[1]}\n\n"
        "Выберите филиал:",
        reply_markup=branch_kb()
    )


@dp.callback_query(F.data.startswith("branch:"))
async def cb_branch(call: CallbackQuery):
    key = call.data.split(":")[1]
    uid = call.from_user.id
    user_branch[uid] = key
    label, addr = BRANCHES[key]
    try:
        await call.message.edit_text(
            f"✅ <b>Филиал выбран</b>\n\n"
            f"🏪 {label}\n"
            f"📍 {addr}\n\n"
            "Все следующие заказы — отсюда."
        )
    except Exception:
        pass
    await call.answer("Филиал выбран!")


@dp.message(F.text == "⭐ Бонусы")
async def msg_bonus(message: Message):
    uid = message.from_user.id
    pts = bonus_points[uid]
    me = await bot.get_me()
    ref = f"https://t.me/{me.username}?start=ref_{uid}"
    tier = vip_tier(uid)
    await message.answer(
        f"<b>⭐ Бонусный счёт</b>\n\n"
        f"Баланс: <b>{pts} бонусов</b> = {pts} сом\n"
        f"Статус: <b>{tier[1]}</b> (скидка {tier[2]}%)\n\n"
        "<b>Как заработать:</b>\n"
        "• 5% кэшбек с каждого заказа\n"
        "• 50 бонусов за регистрацию\n"
        "• 100 бонусов за приглашение\n"
        "• 🎰 Колесо удачи — раз в день\n"
        "• 🏆 Челленджи недели\n\n"
        f"<b>Ваша реф. ссылка:</b>\n{ref}"
    )


@dp.message(F.text == "🏆 Челлендж")
async def msg_challenge(message: Message):
    uid = message.from_user.id
    c_name, c_target, c_reward = CHALLENGES["3_orders"]
    progress = weekly_challenge[uid]
    bar = "▓" * min(progress, c_target) + "░" * max(0, c_target - progress)
    done = "✅ Выполнено! " if progress >= c_target else ""
    await message.answer(
        f"<b>🏆 Челленджи недели</b>\n\n"
        f"<b>{c_name}</b>\n"
        f"Прогресс: {bar} {progress}/{c_target}\n"
        f"Награда: <b>{c_reward} бонусов</b>\n"
        f"{done}\n"
        "Делай заказы — получай бонусы!"
    )


@dp.message(F.text == "🎰 Колесо удачи")
async def msg_spin(message: Message):
    uid = message.from_user.id
    today = datetime.now().date().isoformat()
    if last_spin.get(uid) == today:
        await message.answer("🎰 Вы уже крутили сегодня! Возвращайтесь завтра 🌅")
        return
    prize = random.choice(SPIN_PRIZES)
    bonus_points[uid] += prize
    last_spin[uid] = today
    await message.answer(
        f"🎰 <b>Колесо удачи!</b>\n\n"
        f"Крутится... 🎲\n\n"
        f"🎉 Вам выпало: <b>+{prize} бонусов!</b>\n\n"
        f"Баланс: <b>{bonus_points[uid]} бонусов</b>\n\n"
        "Возвращайтесь завтра 🎁"
    )


@dp.message(F.text == "🎁 Промокод")
async def msg_promo(message: Message):
    await message.answer(
        "<b>🎁 Промокод</b>\n\n"
        "Введите код:\n"
        "<code>WELCOME10</code> — 10%\n"
        "<code>DASTAN15</code> — 15%\n"
        "<code>SUSHI25</code> — 25% на суши\n"
        "<code>PIZZA15</code> — 15% на пиццу\n"
        "<code>VIP30</code> — 30%\n\n"
        "Скидка применится к текущей корзине."
    )


@dp.message(F.text == "💎 Подписки")
async def msg_subscriptions(message: Message):
    lines = ["<b>💎 Абонементы</b>\n\nВыгода до 40%:\n"]
    btns = []
    for key, (name, price, desc) in SUBSCRIPTIONS.items():
        lines.append(f"<b>{name}</b>\n{desc}\nЦена: {price} сом\n")
        btns.append([InlineKeyboardButton(text=f"Оформить — {price} сом", callback_data=f"sub:{key}")])
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


@dp.callback_query(F.data.startswith("sub:"))
async def cb_sub(call: CallbackQuery):
    key = call.data.split(":")[1]
    name, price, desc = SUBSCRIPTIONS[key]
    try:
        await call.message.edit_text(
            f"<b>💎 {name}</b>\n\n{desc}\n\n"
            f"<b>Оплата: {price} сом</b>\n\n"
            f"💳 МБанк: <code>{MBANK_NUMBER}</code>\n"
            f"Получатель: {MBANK_HOLDER}\n"
            f"Комментарий: <code>Подписка {name}</code>\n\n"
            "После оплаты напишите боту."
        )
    except Exception:
        pass
    await call.answer()


@dp.message(F.text == "📜 Заказы")
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
    last_oid = oids[-1]
    btns = [[InlineKeyboardButton(text=f"🔁 Повторить #{last_oid}", callback_data=f"reorder:{last_oid}")]]
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


@dp.callback_query(F.data.startswith("reorder:"))
async def cb_reorder(call: CallbackQuery):
    oid = int(call.data.split(":")[1])
    order = orders_db.get(oid)
    uid = call.from_user.id
    if not order or order.get("user_id") != uid:
        await call.answer("Заказ не найден"); return
    for name, qty in order["items"].items():
        carts[uid][name] = carts[uid].get(name, 0) + qty
    await call.answer(f"✅ Из заказа #{oid} добавлено в корзину!", show_alert=True)
    await render_cart(call.message, uid)


@dp.message(F.text == "❤️ Избранное")
async def msg_favorites(message: Message):
    uid = message.from_user.id
    favs = favorites.get(uid, set())
    if not favs:
        await message.answer("❤️ Избранное пусто.\n\nВ меню нажмите 🤍 на блюде."); return
    lines = ["<b>❤️ Избранное</b>\n"]
    btns = []
    for name in favs:
        item = find_item(name)
        if item:
            lines.append(f"{item[2]} {name} — {item[1]} сом")
            btns.append([InlineKeyboardButton(text=f"➕ {name}", callback_data=f"add:{name}")])
    btns.append([InlineKeyboardButton(text="🛒 Добавить всё", callback_data="fav_all")])
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


@dp.callback_query(F.data == "fav_all")
async def cb_fav_all(call: CallbackQuery):
    uid = call.from_user.id
    for name in favorites.get(uid, set()):
        carts[uid][name] = carts[uid].get(name, 0) + 1
    await call.answer("Всё избранное в корзине!")
    await render_cart(call.message, uid)


@dp.message(F.text == "🔎 Поиск")
async def msg_search(message: Message):
    awaiting_search.add(message.from_user.id)
    await message.answer(
        "🔎 <b>Поиск по меню</b>\n\n"
        "Напишите название или категорию:\n"
        "<code>пицца</code>, <code>суши</code>, <code>кофе</code>, <code>рамен</code>..."
    )


@dp.message(F.text == "🪑 Бронь")
async def msg_reservation(message: Message):
    awaiting_reservation[message.from_user.id] = {"step": "date"}
    await message.answer(
        "🪑 <b>Бронь столика</b>\n\nВыберите дату:",
        reply_markup=reservation_date_kb()
    )


@dp.callback_query(F.data.startswith("rdate:"))
async def cb_rdate(call: CallbackQuery):
    date = call.data.split(":", 1)[1]
    uid = call.from_user.id
    awaiting_reservation[uid] = {"step": "time", "date": date}
    try:
        await call.message.edit_text(
            f"🪑 Дата: <b>{date}</b>\n\nВыберите время:",
            reply_markup=reservation_time_kb()
        )
    except Exception:
        pass
    await call.answer()


@dp.callback_query(F.data.startswith("rtime:"))
async def cb_rtime(call: CallbackQuery):
    time = call.data.split(":", 1)[1]
    uid = call.from_user.id
    r = awaiting_reservation.get(uid, {})
    r["step"] = "guests"
    r["time"] = time
    awaiting_reservation[uid] = r
    try:
        await call.message.edit_text(
            f"🪑 Дата: <b>{r.get('date')}</b>\nВремя: <b>{time}</b>\n\nГостей?",
            reply_markup=reservation_guests_kb()
        )
    except Exception:
        pass
    await call.answer()


@dp.callback_query(F.data.startswith("rguests:"))
async def cb_rguests(call: CallbackQuery):
    guests = int(call.data.split(":")[1])
    uid = call.from_user.id
    r = awaiting_reservation.pop(uid, {})
    r["guests"] = guests
    r["user_id"] = uid
    r["username"] = call.from_user.username or call.from_user.first_name
    reservations.append(r)
    try:
        await call.message.edit_text(
            f"✅ <b>Бронь подтверждена!</b>\n\n"
            f"📅 {r.get('date')}\n"
            f"🕒 {r.get('time')}\n"
            f"👥 {guests} чел\n"
            f"📍 {CAFE_ADDRESS}\n\n"
            f"При опоздании 15+ мин бронь снимается.\nСвязь: {CAFE_PHONE}"
        )
    except Exception:
        pass
    await call.answer("Забронировано!")


@dp.message(F.text == "👤 Профиль")
async def msg_profile(message: Message):
    uid = message.from_user.id
    p = user_profile.get(uid, {})
    tier = vip_tier(uid)
    spent = user_total_spent[uid]
    orders_count = len(user_orders.get(uid, []))
    avg_check = spent / orders_count if orders_count else 0
    next_tier = None
    for t in VIP_TIERS:
        if spent < t[0]:
            next_tier = t; break
    nt_text = f"\n📈 До <b>{next_tier[1]}</b>: {next_tier[0] - spent} сом" if next_tier else ""
    branch = BRANCHES.get(user_branch.get(uid, "center"))[0]
    await message.answer(
        f"<b>👤 Профиль</b>\n\n"
        f"Имя: {p.get('name', '—')}\n"
        f"Филиал: {branch}\n"
        f"Статус: <b>{tier[1]}</b> (-{tier[2]}%)\n"
        f"Бонусов: <b>{bonus_points[uid]}</b>\n"
        f"Заказов: <b>{orders_count}</b>\n"
        f"Потрачено: <b>{spent} сом</b>\n"
        f"Средний чек: <b>{int(avg_check)} сом</b>\n"
        f"❤️ Избранных: <b>{len(favorites[uid])}</b>{nt_text}"
    )


@dp.message(F.text == "💬 Поддержка")
async def msg_support(message: Message):
    await message.answer(
        f"<b>💬 Поддержка</b>\n\n"
        f"Напишите: {SUPPORT_USERNAME}\n"
        f"Звонок: <b>{CAFE_PHONE}</b>\n\n"
        "Ответим в 15 минут ⏰"
    )


@dp.message(F.text == "🔥 Популярное")
async def msg_popular(message: Message):
    lines = ["<b>🔥 Топ блюда</b>\n"]
    btns = []
    for name in POPULAR:
        item = find_item(name)
        if item:
            lines.append(f"{item[2]} {name} — {item[1]} сом")
            btns.append([InlineKeyboardButton(text=f"➕ {name}", callback_data=f"add:{name}")])
    btns.append([InlineKeyboardButton(text="🛒 Корзина", callback_data="show_cart")])
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    ADMIN_IDS.add(message.from_user.id)
    await message.answer(
        "✅ <b>Админ</b>\n\n"
        "/stats /orders /revenue /reservations\n"
        "/broadcast Текст — рассылка"
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
        f"Заказов: <b>{total}</b>\n"
        f"Выручка: <b>{rev} сом</b>\n"
        f"Средний чек: <b>{int(avg)} сом</b>\n"
        f"Рейтинг: <b>{avg_r:.1f}⭐</b> ({len(ratings)})\n"
        f"Клиентов: <b>{len(user_profile)}</b>\n"
        f"Броней: <b>{len(reservations)}</b>\n"
        f"Ждут оплаты: <b>{len(pending_orders)}</b>"
    )


@dp.message(Command("orders"))
async def cmd_orders(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    if not orders_db:
        await message.answer("Заказов нет."); return
    last = sorted(orders_db.items(), reverse=True)[:10]
    lines = ["<b>📋 Последние заказы</b>\n"]
    btns = []
    for oid, o in last:
        ts = o["created_at"][:16].replace("T", " ")
        phone = o.get("phone", "—")
        lines.append(f"#{oid} — {o['total']} сом — @{o['username']} — {phone} — {ts}")
    for oid, _ in last[:5]:
        btns.append([
            InlineKeyboardButton(text=f"#{oid} 🍳", callback_data=f"astatus:{oid}:cooking"),
            InlineKeyboardButton(text=f"🚴", callback_data=f"astatus:{oid}:delivery"),
            InlineKeyboardButton(text=f"✅", callback_data=f"astatus:{oid}:done"),
        ])
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=btns) if btns else None)


@dp.callback_query(F.data.startswith("astatus:"))
async def cb_astatus(call: CallbackQuery):
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
        await bot.send_message(order["user_id"], f"📦 <b>Заказ #{oid}</b>\nСтатус: <b>{labels.get(st)}</b>")
    except Exception:
        pass
    await call.answer(f"✅ {labels.get(st)}")


@dp.message(Command("reservations"))
async def cmd_reservations(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    if not reservations:
        await message.answer("Броней нет."); return
    lines = ["<b>🪑 Брони</b>\n"]
    for r in reservations[-10:]:
        lines.append(f"{r.get('date')} {r.get('time')} — {r.get('guests')} чел — @{r.get('username')}")
    await message.answer("\n".join(lines))


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
        await message.answer("Использование: /broadcast Текст"); return
    text = args[1]
    count = 0
    for uid in user_profile:
        try:
            await bot.send_message(uid, f"📢 <b>{CAFE_NAME}</b>\n\n{text}")
            count += 1
        except Exception:
            pass
    await message.answer(f"✅ Отправлено {count}")


@dp.message()
async def handle_any(message: Message):
    uid = message.from_user.id
    text = message.text.strip()

    if uid in awaiting_phone:
        oid = awaiting_phone.pop(uid)
        if oid in pending_orders:
            pending_orders[oid]["phone"] = text
        await show_payment(message, oid)
        return

    if uid in awaiting_search:
        awaiting_search.discard(uid)
        q = text.lower()
        found = []
        for cat_key, cat in MENU.items():
            if q in cat["title"].lower() or q in cat_key:
                for it in cat["items"]:
                    found.append(it)
                continue
            for it in cat["items"]:
                if q in it[0].lower():
                    found.append(it)
        if not found:
            await message.answer(f"🔎 По '<b>{text}</b>' ничего не найдено."); return
        lines = [f"<b>🔎 Найдено '{text}':</b>\n"]
        btns = []
        for name, price, emoji in found[:15]:
            lines.append(f"{emoji} {name} — {price} сом")
            btns.append([InlineKeyboardButton(text=f"➕ {name}", callback_data=f"add:{name}")])
        btns.append([InlineKeyboardButton(text="🛒 Корзина", callback_data="show_cart")])
        await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
        return

    upper = text.upper()
    if upper in PROMO_CODES:
        pct = PROMO_CODES[upper]
        user_promos[uid] = pct
        await message.answer(f"✅ Промокод <b>{upper}</b> активирован! Скидка <b>{pct}%</b> 🛒")
        return

    await message.answer("🤔 Используйте кнопки ниже 👇", reply_markup=main_kb())


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
