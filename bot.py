import os
import asyncio
import logging
import json
from datetime import datetime, timedelta, date
from collections import defaultdict
import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode, ChatAction
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

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

POLLINATIONS_URL = "https://text.pollinations.ai/openai"
POLLINATIONS_MODEL = os.getenv("POLLINATIONS_MODEL", "openai")

BOT_NAME = "🧠 Умник AI"
SUPPORT_USERNAME = "@umnik_ai_support"
MBANK_NUMBER = "+996 502 052 906"
MBANK_HOLDER = "АЙДАР У."
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0") or "0")

FREE_DAILY_LIMIT = 10
PREMIUM_PRICE_MONTH = 500
PREMIUM_PRICE_YEAR = 4500

SUBJECTS = {
    "math": {
        "title": "🔢 Математика",
        "prompt": "Ты опытный учитель математики. Решай задачи пошагово на русском языке. Показывай каждое действие и объясняй формулы простыми словами. Если задача с уравнением — покажи решение по шагам.",
    },
    "geometry": {
        "title": "📐 Геометрия",
        "prompt": "Ты учитель геометрии. Помогай решать задачи по геометрии пошагово на русском. Объясняй теоремы и свойства фигур доступно. Если нужен чертёж — опиши его словами.",
    },
    "physics": {
        "title": "⚛️ Физика",
        "prompt": "Ты учитель физики. Решай задачи по физике пошагово на русском: напиши дано, формулу, подставь значения, реши. Объясняй физический смысл.",
    },
    "chemistry": {
        "title": "🧪 Химия",
        "prompt": "Ты учитель химии. Помогай с уравнениями реакций, расчётными задачами, понятиями. На русском, пошагово. Уравнивай реакции и показывай метод.",
    },
    "biology": {
        "title": "🧬 Биология",
        "prompt": "Ты учитель биологии. Объясняй биологические процессы, отвечай на вопросы по анатомии, генетике, экологии. На русском, понятно школьнику.",
    },
    "history": {
        "title": "📜 История",
        "prompt": "Ты учитель истории. Рассказывай о событиях, датах, исторических личностях. Объясняй причины и последствия событий. На русском, интересно.",
    },
    "geography": {
        "title": "🌍 География",
        "prompt": "Ты учитель географии. Помогай с физической, экономической географией, странами, столицами, природными зонами. На русском.",
    },
    "literature": {
        "title": "📚 Литература",
        "prompt": "Ты учитель литературы. Помогай разобрать произведения, темы, образы героев, художественные средства. Краткое содержание, анализ. На русском.",
    },
    "russian": {
        "title": "🇷🇺 Русский язык",
        "prompt": "Ты учитель русского языка. Помогай с орфографией, пунктуацией, грамматическим разбором, синтаксисом. Объясняй правила с примерами.",
    },
    "kyrgyz": {
        "title": "🇰🇬 Кыргыз тили",
        "prompt": "Сен кыргыз тилинин окутуучусусуң. Окуучуларга кыргыз тилинин эрежелери, грамматика, орфография боюнча жардам бер. Кыргызча жооп бер.",
    },
    "english": {
        "title": "🇬🇧 Английский",
        "prompt": "You are an English teacher helping Russian-speaking students. Explain grammar, translate, help with essays. Reply in Russian with English examples. Объясняй на русском с английскими примерами.",
    },
    "informatics": {
        "title": "💻 Информатика",
        "prompt": "Ты учитель информатики и программирования. Помогай с алгоритмами, Python, Pascal, базами данных, школьной информатикой. Показывай код с комментариями.",
    },
    "general": {
        "title": "💡 Общий вопрос",
        "prompt": "Ты умный школьный AI-помощник. Помогай с любыми учебными вопросами на русском языке. Если вопрос не учебный — мягко перенаправь к учёбе.",
    },
}

ACHIEVEMENTS = [
    (1, "🌱 Первый вопрос", "Задал первый вопрос"),
    (10, "📚 Любознательный", "10 вопросов"),
    (50, "🧠 Учёный", "50 вопросов"),
    (100, "🎓 Магистр", "100 вопросов"),
    (500, "🏆 Гений", "500 вопросов"),
]

STREAK_REWARDS = {3: 50, 7: 200, 14: 500, 30: 2000}

PROMO_CODES = {
    "WELCOME50": ("free_questions", 5),
    "STUDENT100": ("free_questions", 10),
    "PROMO20": ("discount_pct", 20),
    "FRIEND30": ("discount_pct", 30),
}

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

user_profile: dict[int, dict] = {}
user_subject: dict[int, str] = {}
user_history: dict[int, list[dict]] = defaultdict(list)
user_questions_today: dict[int, dict] = defaultdict(lambda: {"date": "", "count": 0})
user_total_questions: dict[int, int] = defaultdict(int)
user_streak: dict[int, dict] = defaultdict(lambda: {"days": 0, "last": ""})
user_premium: dict[int, str] = {}
user_bonus_questions: dict[int, int] = defaultdict(int)
user_promos_used: dict[int, set] = defaultdict(set)
user_achievements: dict[int, set] = defaultdict(set)
ADMIN_IDS: set[int] = set()
pending_premium: dict[int, dict] = {}
awaiting_screenshot: set[int] = set()
broadcasts_count = 0


def today_iso():
    return date.today().isoformat()


def is_premium(uid):
    until = user_premium.get(uid)
    if not until:
        return False
    return until >= today_iso()


def reset_daily(uid):
    today = today_iso()
    if user_questions_today[uid]["date"] != today:
        user_questions_today[uid] = {"date": today, "count": 0}


def can_ask(uid):
    if is_premium(uid):
        return True, ""
    reset_daily(uid)
    used = user_questions_today[uid]["count"]
    bonus = user_bonus_questions[uid]
    if used < FREE_DAILY_LIMIT or bonus > 0:
        return True, ""
    return False, f"Лимит исчерпан: {FREE_DAILY_LIMIT}/день"


def consume_question(uid):
    if is_premium(uid):
        return
    reset_daily(uid)
    if user_questions_today[uid]["count"] < FREE_DAILY_LIMIT:
        user_questions_today[uid]["count"] += 1
    elif user_bonus_questions[uid] > 0:
        user_bonus_questions[uid] -= 1


def update_streak(uid):
    today = today_iso()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    s = user_streak[uid]
    if s["last"] == today:
        return None
    if s["last"] == yesterday:
        s["days"] += 1
    else:
        s["days"] = 1
    s["last"] = today
    if s["days"] in STREAK_REWARDS:
        reward = STREAK_REWARDS[s["days"]]
        user_bonus_questions[uid] += reward // 50
        return (s["days"], reward // 50)
    return None


def check_achievements(uid):
    total = user_total_questions[uid]
    new_achievs = []
    for threshold, name, desc in ACHIEVEMENTS:
        if total >= threshold and threshold not in user_achievements[uid]:
            user_achievements[uid].add(threshold)
            new_achievs.append((name, desc))
    return new_achievs


def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Предметы"), KeyboardButton(text="💬 Спросить")],
            [KeyboardButton(text="📊 Прогресс"), KeyboardButton(text="🏆 Достижения")],
            [KeyboardButton(text="🔥 Стрик"), KeyboardButton(text="📜 История")],
            [KeyboardButton(text="💎 Премиум"), KeyboardButton(text="🎁 Промокод")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="❓ Помощь")],
            [KeyboardButton(text="💬 Поддержка")],
        ],
        resize_keyboard=True,
    )


def subjects_kb():
    btns = []
    keys = list(SUBJECTS.keys())
    for i in range(0, len(keys), 2):
        row = []
        for k in keys[i:i+2]:
            row.append(InlineKeyboardButton(text=SUBJECTS[k]["title"], callback_data=f"subj:{k}"))
        btns.append(row)
    return InlineKeyboardMarkup(inline_keyboard=btns)


def premium_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📅 Месяц — {PREMIUM_PRICE_MONTH} сом", callback_data="buy:month")],
        [InlineKeyboardButton(text=f"🎁 Год — {PREMIUM_PRICE_YEAR} сом (экономия 1500)", callback_data="buy:year")],
    ])


@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id
    name = message.from_user.first_name or "ученик"
    is_new = uid not in user_profile
    user_profile[uid] = {
        "name": name,
        "username": message.from_user.username,
        "joined": user_profile.get(uid, {}).get("joined", datetime.now().isoformat()),
    }
    if is_new:
        user_bonus_questions[uid] += 5

    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].startswith("ref_") and is_new:
        try:
            ref_id = int(args[1][4:])
            if ref_id != uid and ref_id in user_profile:
                user_bonus_questions[ref_id] += 5
                user_bonus_questions[uid] += 5
                await bot.send_message(ref_id, "🎁 По вашей ссылке зарегистрировался друг! +5 вопросов")
        except (ValueError, Exception):
            pass

    bonus_note = "\n🎁 <b>Подарок: +5 вопросов!</b>" if is_new else ""
    text = (
        f"{'Привет' if is_new else 'С возвращением'}, <b>{name}</b>! 👋\n\n"
        f"Я <b>{BOT_NAME}</b> — твой помощник с домашкой 📚\n\n"
        "<b>Что я умею:</b>\n"
        "🔢 Решаю задачи по математике\n"
        "⚛️ Объясняю физику и химию\n"
        "📜 Помогаю с историей и литературой\n"
        "🇬🇧 Учу английскому\n"
        "🇰🇬 Кыргыз тили боюнча жардам берем\n"
        "💻 Программирование, информатика\n\n"
        f"<b>Бесплатно:</b> {FREE_DAILY_LIMIT} вопросов в день{bonus_note}\n\n"
        "👇 Выбери предмет или жми <b>💬 Спросить</b>"
    )
    await message.answer(text, reply_markup=main_kb())


@dp.message(F.text == "📚 Предметы")
async def msg_subjects(message: Message):
    cur = user_subject.get(message.from_user.id)
    cur_text = ""
    if cur and cur in SUBJECTS:
        cur_text = f"\n\nТекущий: <b>{SUBJECTS[cur]['title']}</b>"
    await message.answer(
        f"<b>📚 Выбери предмет</b>{cur_text}\n\n"
        "После выбора пиши вопрос — отвечу как учитель этого предмета:",
        reply_markup=subjects_kb()
    )


@dp.callback_query(F.data.startswith("subj:"))
async def cb_subject(call: CallbackQuery):
    key = call.data.split(":")[1]
    if key not in SUBJECTS:
        await call.answer("Не найдено"); return
    user_subject[call.from_user.id] = key
    title = SUBJECTS[key]["title"]
    try:
        await call.message.edit_text(
            f"✅ Предмет: <b>{title}</b>\n\n"
            f"Теперь пиши свой вопрос — отвечу как учитель.\n\n"
            "<b>Пример:</b>\n"
            "<i>Реши уравнение: 2x + 5 = 13</i>\n"
            "<i>Объясни закон Ньютона</i>\n"
            "<i>Кто открыл Америку?</i>"
        )
    except Exception:
        pass
    await call.answer(f"Выбрано: {title}")


@dp.message(F.text == "💬 Спросить")
async def msg_ask(message: Message):
    uid = message.from_user.id
    cur = user_subject.get(uid)
    if not cur:
        await message.answer(
            "Сначала выбери предмет 👇",
            reply_markup=subjects_kb()
        )
        return
    title = SUBJECTS[cur]["title"]
    await message.answer(
        f"📝 Предмет: <b>{title}</b>\n\nНапиши свой вопрос — отвечу!"
    )


@dp.message(F.text == "📊 Прогресс")
async def msg_progress(message: Message):
    uid = message.from_user.id
    reset_daily(uid)
    used = user_questions_today[uid]["count"]
    bonus = user_bonus_questions[uid]
    total = user_total_questions[uid]
    premium = is_premium(uid)
    if premium:
        limit_text = "♾️ Безлимит (Премиум)"
        bar = "▓" * 10
    else:
        remaining = FREE_DAILY_LIMIT - used
        filled = min(used, FREE_DAILY_LIMIT)
        bar = "▓" * filled + "░" * (FREE_DAILY_LIMIT - filled)
        limit_text = f"{used}/{FREE_DAILY_LIMIT} вопросов\n{bar}\nОсталось: {remaining}"
        if bonus > 0:
            limit_text += f"\n🎁 Бонусных: +{bonus}"
    await message.answer(
        f"<b>📊 Твой прогресс</b>\n\n"
        f"<b>Сегодня:</b>\n{limit_text}\n\n"
        f"<b>Всего вопросов:</b> {total}\n"
        f"<b>Достижений:</b> {len(user_achievements[uid])}/{len(ACHIEVEMENTS)}\n"
        f"<b>Стрик:</b> 🔥 {user_streak[uid]['days']} дн"
    )


@dp.message(F.text == "🔥 Стрик")
async def msg_streak(message: Message):
    uid = message.from_user.id
    s = user_streak[uid]
    days = s["days"]
    last = s["last"]
    today = today_iso()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    if last not in (today, yesterday):
        days = 0
    next_milestone = None
    for milestone in sorted(STREAK_REWARDS.keys()):
        if days < milestone:
            next_milestone = milestone; break
    nm_text = ""
    if next_milestone:
        nm_text = f"\n📈 До <b>{next_milestone} дней</b>: ещё {next_milestone - days}\n💰 Награда: {STREAK_REWARDS[next_milestone] // 50} вопросов"
    rewards_text = "\n".join([f"• {d} дн → +{r // 50} вопросов" for d, r in STREAK_REWARDS.items()])
    await message.answer(
        f"<b>🔥 Учебный стрик</b>\n\n"
        f"Текущий стрик: <b>{days} дней подряд</b>{nm_text}\n\n"
        f"<b>Награды за стрик:</b>\n{rewards_text}\n\n"
        "Задавай хотя бы 1 вопрос в день — стрик растёт!"
    )


@dp.message(F.text == "🏆 Достижения")
async def msg_achievements(message: Message):
    uid = message.from_user.id
    total = user_total_questions[uid]
    earned = user_achievements[uid]
    lines = ["<b>🏆 Достижения</b>\n"]
    for threshold, name, desc in ACHIEVEMENTS:
        if threshold in earned:
            lines.append(f"✅ <b>{name}</b> — {desc}")
        else:
            progress = min(total, threshold)
            lines.append(f"🔒 <b>{name}</b> — {desc} ({progress}/{threshold})")
    await message.answer("\n".join(lines))


@dp.message(F.text == "📜 История")
async def msg_history(message: Message):
    uid = message.from_user.id
    hist = user_history.get(uid, [])
    if not hist:
        await message.answer("📜 История пуста.\nЗадай первый вопрос!"); return
    lines = ["<b>📜 Последние вопросы</b>\n"]
    for entry in hist[-5:][::-1]:
        q = entry["question"][:80]
        ts = entry.get("ts", "")[:16].replace("T", " ")
        subj = SUBJECTS.get(entry.get("subject", "general"), {}).get("title", "💡")
        lines.append(f"{subj} <i>{q}</i>\n<code>{ts}</code>\n")
    await message.answer("\n".join(lines))


@dp.message(F.text == "💎 Премиум")
async def msg_premium(message: Message):
    uid = message.from_user.id
    if is_premium(uid):
        until = user_premium[uid]
        await message.answer(
            f"<b>💎 У тебя активен Премиум</b>\n\n"
            f"Действует до: <b>{until}</b>\n\n"
            "Безлимитные вопросы, приоритетные ответы 🚀"
        )
        return
    await message.answer(
        f"<b>💎 Премиум подписка</b>\n\n"
        "<b>Преимущества:</b>\n"
        "♾️ Безлимит вопросов в день\n"
        "🚀 Приоритетные ответы\n"
        "📸 Фото задач (скоро)\n"
        "🎓 Доступ ко всем предметам\n"
        "🚫 Без рекламы\n\n"
        f"<b>Тарифы:</b>\n"
        f"📅 1 месяц — <b>{PREMIUM_PRICE_MONTH} сом</b>\n"
        f"🎁 1 год — <b>{PREMIUM_PRICE_YEAR} сом</b> (экономия 1500)\n",
        reply_markup=premium_kb()
    )


@dp.callback_query(F.data.startswith("buy:"))
async def cb_buy(call: CallbackQuery):
    period = call.data.split(":")[1]
    uid = call.from_user.id
    price = PREMIUM_PRICE_MONTH if period == "month" else PREMIUM_PRICE_YEAR
    days = 30 if period == "month" else 365
    pending_premium[uid] = {"period": period, "price": price, "days": days, "ts": datetime.now().isoformat()}
    try:
        await call.message.edit_text(
            f"<b>💳 Оплата {'месяца' if period == 'month' else 'года'} Премиум</b>\n\n"
            f"Сумма: <b>{price} сом</b>\n\n"
            f"<b>📲 МБанк перевод:</b>\n"
            f"Номер: <code>{MBANK_NUMBER}</code>\n"
            f"Получатель: {MBANK_HOLDER}\n"
            f"Сумма: <b>{price} сом</b>\n"
            f"Комментарий: <code>Премиум {uid}</code>\n\n"
            "После оплаты:\n"
            "1️⃣ Нажми <b>«Я оплатил»</b>\n"
            "2️⃣ Отправь <b>скрин чека</b> из МБанк\n"
            "3️⃣ Жди подтверждения от админа (5-15 мин)\n",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Я оплатил — отправить чек", callback_data=f"paid:{period}")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_buy")],
            ])
        )
    except Exception:
        pass
    await call.answer()


@dp.callback_query(F.data.startswith("paid:"))
async def cb_paid(call: CallbackQuery):
    uid = call.from_user.id
    p = pending_premium.get(uid)
    if not p:
        await call.answer("Заявка не найдена. Начни заново через 💎 Премиум", show_alert=True)
        return
    awaiting_screenshot.add(uid)
    try:
        await call.message.edit_text(
            f"📸 <b>Отправь скрин оплаты</b>\n\n"
            f"Сумма: {p['price']} сом\n"
            f"Получатель: {MBANK_HOLDER} ({MBANK_NUMBER})\n\n"
            "Просто пришли фото чека из МБанк сюда в чат.\n"
            "Админ проверит и активирует премиум за 5-15 минут ⏰\n\n"
            "<i>Если ошибка — напиши /cancel</i>"
        )
    except Exception:
        pass
    await call.answer("Жду скрин оплаты")


@dp.callback_query(F.data == "cancel_buy")
async def cb_cancel_buy(call: CallbackQuery):
    pending_premium.pop(call.from_user.id, None)
    awaiting_screenshot.discard(call.from_user.id)
    try:
        await call.message.edit_text("❌ Покупка отменена.\n\nПремиум всегда доступен — /start")
    except Exception:
        pass
    await call.answer()


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message):
    uid = message.from_user.id
    pending_premium.pop(uid, None)
    awaiting_screenshot.discard(uid)
    await message.answer("❌ Заявка отменена. /start")


@dp.message(F.photo)
async def handle_photo(message: Message):
    uid = message.from_user.id
    if uid not in awaiting_screenshot:
        await message.answer("📸 Спасибо за фото, но я работаю с текстом. Пиши вопросы! 📚")
        return
    p = pending_premium.get(uid)
    if not p:
        awaiting_screenshot.discard(uid)
        await message.answer("Заявка не найдена. /start")
        return

    file_id = message.photo[-1].file_id
    p["screenshot"] = file_id
    p["status"] = "awaiting_admin"
    awaiting_screenshot.discard(uid)

    await message.answer(
        "✅ <b>Чек получен!</b>\n\n"
        "Отправил админу на проверку.\n"
        "Премиум активируется в течение <b>5-15 минут</b> ⏰\n\n"
        "Ты получишь уведомление как только проверят."
    )

    user_info = message.from_user
    period_label = "месяц" if p["period"] == "month" else "год"
    caption = (
        f"💳 <b>Новая оплата Премиум</b>\n\n"
        f"Сумма: <b>{p['price']} сом</b>\n"
        f"Тариф: <b>{period_label}</b>\n"
        f"Юзер: <a href='tg://user?id={uid}'>{user_info.first_name}</a>"
        f"{' (@' + user_info.username + ')' if user_info.username else ''}\n"
        f"ID: <code>{uid}</code>\n"
        f"Время: {datetime.now().strftime('%H:%M %d.%m.%Y')}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve:{uid}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{uid}")],
    ])

    targets = set(ADMIN_IDS)
    if ADMIN_CHAT_ID:
        targets.add(ADMIN_CHAT_ID)
    sent_count = 0
    for admin_id in targets:
        try:
            await bot.send_photo(admin_id, photo=file_id, caption=caption, reply_markup=kb)
            sent_count += 1
        except Exception as e:
            logging.error(f"Failed to send to admin {admin_id}: {e}")
    if sent_count == 0:
        logging.warning(f"No admin received payment from {uid}")


@dp.callback_query(F.data.startswith("approve:"))
async def cb_approve_payment(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS and call.from_user.id != ADMIN_CHAT_ID:
        await call.answer("Только админ", show_alert=True)
        return
    uid = int(call.data.split(":")[1])
    p = pending_premium.pop(uid, None)
    if not p:
        await call.answer("Заявка не найдена / уже обработана", show_alert=True)
        return
    days = p["days"]
    cur_until = user_premium.get(uid)
    today = date.today()
    if cur_until and cur_until >= today.isoformat():
        base = date.fromisoformat(cur_until)
    else:
        base = today
    until = (base + timedelta(days=days)).isoformat()
    user_premium[uid] = until

    try:
        await call.message.edit_caption(
            caption=(call.message.caption or "") + f"\n\n✅ <b>ПОДТВЕРЖДЕНО админом @{call.from_user.username or call.from_user.id}</b>\nПремиум до: {until}"
        )
    except Exception:
        try:
            await call.message.reply(f"✅ Подтверждено. Премиум до {until}")
        except Exception:
            pass

    try:
        await bot.send_message(
            uid,
            f"🎉 <b>Премиум активирован!</b>\n\n"
            f"Срок: до <b>{until}</b>\n"
            f"Безлимит вопросов 🚀\n\n"
            f"Спасибо за оплату ❤️\n"
            f"Напиши /start или сразу задавай вопрос."
        )
    except Exception:
        pass
    await call.answer("Премиум активирован")


@dp.callback_query(F.data.startswith("reject:"))
async def cb_reject_payment(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS and call.from_user.id != ADMIN_CHAT_ID:
        await call.answer("Только админ", show_alert=True)
        return
    uid = int(call.data.split(":")[1])
    p = pending_premium.pop(uid, None)
    if not p:
        await call.answer("Уже обработано", show_alert=True)
        return
    try:
        await call.message.edit_caption(
            caption=(call.message.caption or "") + f"\n\n❌ <b>ОТКЛОНЕНО админом @{call.from_user.username or call.from_user.id}</b>"
        )
    except Exception:
        pass
    try:
        await bot.send_message(
            uid,
            f"⚠️ <b>Оплата не подтверждена</b>\n\n"
            f"Возможные причины:\n"
            f"• Сумма не сходится\n"
            f"• Скрин нечитаемый\n"
            f"• Платёж не пришёл\n\n"
            f"Свяжись с поддержкой: {SUPPORT_USERNAME}\n"
            f"Или попробуй заново через 💎 Премиум"
        )
    except Exception:
        pass
    await call.answer("Отклонено")


@dp.message(F.text == "🎁 Промокод")
async def msg_promo(message: Message):
    await message.answer(
        "<b>🎁 Введи промокод</b>\n\n"
        "Пример: <code>WELCOME50</code>\n\n"
        "Где взять промокод?\n"
        "• Подписка на наш канал\n"
        "• Друзья по реферальной ссылке\n"
        "• Розыгрыши\n\n"
        "Просто отправь код в чат."
    )


@dp.message(F.text == "👤 Профиль")
async def msg_profile(message: Message):
    uid = message.from_user.id
    p = user_profile.get(uid, {})
    me = await bot.get_me()
    ref = f"https://t.me/{me.username}?start=ref_{uid}"
    premium_text = ""
    if is_premium(uid):
        premium_text = f"💎 Премиум до {user_premium[uid]}"
    else:
        premium_text = "🆓 Бесплатный план"
    cur_subj = user_subject.get(uid)
    subj_text = SUBJECTS.get(cur_subj, {}).get("title", "не выбран") if cur_subj else "не выбран"
    await message.answer(
        f"<b>👤 Профиль</b>\n\n"
        f"Имя: {p.get('name', '—')}\n"
        f"Подписка: {premium_text}\n"
        f"Текущий предмет: {subj_text}\n"
        f"Всего вопросов: <b>{user_total_questions[uid]}</b>\n"
        f"Стрик: 🔥 <b>{user_streak[uid]['days']}</b> дней\n"
        f"Бонусных: <b>{user_bonus_questions[uid]}</b>\n"
        f"Достижений: <b>{len(user_achievements[uid])}/{len(ACHIEVEMENTS)}</b>\n\n"
        f"<b>📨 Реф. ссылка</b> (за друга +5 вопросов вам обоим):\n{ref}"
    )


@dp.message(F.text == "❓ Помощь")
async def msg_help(message: Message):
    await message.answer(
        "<b>❓ Как пользоваться</b>\n\n"
        "1️⃣ Жми <b>📚 Предметы</b> — выбери нужный\n"
        "2️⃣ Напиши вопрос текстом\n"
        "3️⃣ Получи решение от ИИ\n\n"
        f"<b>Бесплатно:</b> {FREE_DAILY_LIMIT} вопросов/день\n"
        f"<b>Премиум:</b> безлимит — {PREMIUM_PRICE_MONTH} сом/мес\n\n"
        "<b>Советы:</b>\n"
        "• Пиши вопрос полностью\n"
        "• Указывай условие задачи\n"
        "• Если не понял ответ — спроси уточнение\n\n"
        "Стрик растёт за вопросы каждый день — бонусы за 3, 7, 14, 30 дней!"
    )


@dp.message(F.text == "💬 Поддержка")
async def msg_support(message: Message):
    await message.answer(
        f"<b>💬 Поддержка</b>\n\n"
        f"Напиши команду:\n"
        f"<code>/report текст_твоей_проблемы</code>\n\n"
        f"Сообщение придёт админу — ответит в течение 15 минут ⏰"
    )


@dp.message(Command("report"))
async def cmd_report(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /report текст_проблемы"); return
    text = args[1]
    for admin in ADMIN_IDS:
        try:
            await bot.send_message(
                admin,
                f"🚨 <b>Жалоба от @{message.from_user.username or message.from_user.id}</b>\n\n{text}"
            )
        except Exception:
            pass
    await message.answer("✅ Жалоба отправлена админам. Спасибо!")


@dp.message(Command("myid"))
async def cmd_myid(message: Message):
    uid = message.from_user.id
    await message.answer(
        f"🆔 <b>Твой Telegram ID:</b>\n\n"
        f"<code>{uid}</code>\n\n"
        "Скопируй это число и добавь на Railway:\n"
        "<b>Variables</b> → <b>+ New Variable</b>\n"
        f"Name: <code>ADMIN_CHAT_ID</code>\n"
        f"Value: <code>{uid}</code>"
    )


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    uid = message.from_user.id
    if not ADMIN_IDS and not ADMIN_CHAT_ID:
        ADMIN_IDS.add(uid)
        await message.answer(
            f"✅ <b>Ты теперь админ!</b>\n\n"
            f"Твой ID: <code>{uid}</code>\n\n"
            f"<b>Чтобы оставаться админом после перезапуска</b> Railway:\n"
            f"Variables → <b>ADMIN_CHAT_ID</b> = <code>{uid}</code>\n\n"
            "<b>Команды админа:</b>\n"
            "/stats — статистика\n"
            "/users — последние юзеры\n"
            "/grant ID DAYS — премиум юзеру\n"
            "/broadcast Текст — рассылка всем\n"
            "/myid — узнать свой ID"
        )
        return
    if uid in ADMIN_IDS or uid == ADMIN_CHAT_ID:
        ADMIN_IDS.add(uid)
        await message.answer(
            "✅ <b>Админ-режим</b>\n\n"
            "/stats /users /grant /broadcast /myid"
        )
    else:
        await message.answer("❌ Админ уже назначен. Нет доступа.")


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    total_users = len(user_profile)
    premium_users = sum(1 for u in user_profile if is_premium(u))
    total_q = sum(user_total_questions.values())
    today = today_iso()
    today_q = sum(d["count"] for u, d in user_questions_today.items() if d["date"] == today)
    revenue = premium_users * PREMIUM_PRICE_MONTH
    await message.answer(
        f"<b>📊 Статистика</b>\n\n"
        f"Пользователей: <b>{total_users}</b>\n"
        f"Премиум: <b>{premium_users}</b>\n"
        f"Вопросов всего: <b>{total_q}</b>\n"
        f"Сегодня: <b>{today_q}</b>\n"
        f"Доход (минимум): <b>{revenue} сом</b>\n"
        f"Рассылок: <b>{broadcasts_count}</b>"
    )


@dp.message(Command("users"))
async def cmd_users(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    if not user_profile:
        await message.answer("Пусто"); return
    lines = ["<b>👥 Юзеры (последние 15)</b>\n"]
    for uid, p in list(user_profile.items())[-15:]:
        prem = "💎" if is_premium(uid) else ""
        lines.append(f"{prem} <code>{uid}</code> @{p.get('username') or '—'} — Q:{user_total_questions[uid]}")
    await message.answer("\n".join(lines))


@dp.message(Command("grant"))
async def cmd_grant(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Использование: /grant USER_ID DAYS"); return
    try:
        uid = int(args[1])
        days = int(args[2])
    except ValueError:
        await message.answer("Числа неверные"); return
    until = (date.today() + timedelta(days=days)).isoformat()
    user_premium[uid] = until
    await message.answer(f"✅ Премиум на {days} дней — до {until}")
    try:
        await bot.send_message(uid, f"🎁 Тебе подарили Премиум до {until}!")
    except Exception:
        pass


@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    global broadcasts_count
    if message.from_user.id not in ADMIN_IDS: return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /broadcast Текст"); return
    text = args[1]
    count = 0
    for uid in user_profile:
        try:
            await bot.send_message(uid, f"📢 <b>{BOT_NAME}</b>\n\n{text}")
            count += 1
        except Exception:
            pass
    broadcasts_count += 1
    await message.answer(f"✅ Отправлено {count}")


async def ask_pollinations(messages):
    payload = {
        "model": POLLINATIONS_MODEL,
        "messages": messages,
        "temperature": 0.4,
    }
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(POLLINATIONS_URL, json=payload)
            if r.status_code != 200:
                logging.error(f"Pollinations {r.status_code}: {r.text[:300]}")
                return None, f"Ошибка ИИ ({r.status_code})"
            try:
                data = r.json()
                return data["choices"][0]["message"]["content"], None
            except Exception:
                return r.text, None
    except httpx.TimeoutException:
        return None, "ИИ долго думает, попробуй ещё раз"
    except Exception as e:
        logging.error(f"Pollinations error: {e}")
        return None, "Ошибка соединения с ИИ"


async def ask_groq(messages):
    if not GROQ_API_KEY:
        return None, "no_key"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 1500,
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(GROQ_URL, json=payload, headers=headers)
            if r.status_code != 200:
                logging.error(f"Groq {r.status_code}: {r.text[:300]}")
                return None, f"groq_error_{r.status_code}"
            data = r.json()
            return data["choices"][0]["message"]["content"], None
    except httpx.TimeoutException:
        return None, "timeout"
    except Exception as e:
        logging.error(f"Groq error: {e}")
        return None, "connection_error"


async def ask_ai(messages):
    if GROQ_API_KEY:
        answer, err = await ask_groq(messages)
        if answer:
            return answer, None
        logging.info(f"Groq failed ({err}), falling back to Pollinations")
    return await ask_pollinations(messages)


@dp.message(F.text)
async def handle_question(message: Message):
    uid = message.from_user.id
    text = message.text.strip()

    if uid in awaiting_screenshot:
        await message.answer(
            "📸 Жду <b>скрин оплаты</b> (фото).\n\n"
            "Пришли картинку из приложения МБанк.\n"
            "Или нажми /cancel чтобы отменить."
        )
        return

    upper = text.upper()
    if upper in PROMO_CODES:
        if upper in user_promos_used[uid]:
            await message.answer("⚠️ Этот промокод уже использован.")
            return
        kind, val = PROMO_CODES[upper]
        if kind == "free_questions":
            user_bonus_questions[uid] += val
            user_promos_used[uid].add(upper)
            await message.answer(f"✅ Промокод <b>{upper}</b>!\n+{val} бонусных вопросов 🎁")
        else:
            user_promos_used[uid].add(upper)
            await message.answer(f"✅ Промокод <b>{upper}</b> активирован!\nСкидка {val}% на следующую покупку Премиум.")
        return

    if uid not in user_profile:
        user_profile[uid] = {
            "name": message.from_user.first_name or "ученик",
            "username": message.from_user.username,
            "joined": datetime.now().isoformat(),
        }

    cur = user_subject.get(uid)
    if not cur:
        await message.answer(
            "Сначала выбери предмет 👇 (или напиши что-то общее — выберу 'Общий вопрос')",
            reply_markup=subjects_kb()
        )
        user_subject[uid] = "general"
        cur = "general"

    ok, reason = can_ask(uid)
    if not ok:
        await message.answer(
            f"⚠️ <b>{reason}</b>\n\n"
            f"Бесплатно: {FREE_DAILY_LIMIT} вопросов/день.\n"
            "Получи безлимит с Премиум 💎",
            reply_markup=premium_kb()
        )
        return

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    subj = SUBJECTS[cur]
    history = user_history.get(uid, [])[-3:]
    messages = [{"role": "system", "content": subj["prompt"]}]
    for h in history:
        if h.get("subject") == cur:
            messages.append({"role": "user", "content": h["question"]})
            messages.append({"role": "assistant", "content": h["answer"]})
    messages.append({"role": "user", "content": text})

    answer, err = await ask_ai(messages)
    if err or not answer:
        await message.answer(f"😔 ИИ временно недоступен\n\nПопробуй ещё раз через минуту.")
        return

    consume_question(uid)
    user_total_questions[uid] += 1
    user_history[uid].append({
        "question": text,
        "answer": answer,
        "subject": cur,
        "ts": datetime.now().isoformat(),
    })
    if len(user_history[uid]) > 50:
        user_history[uid] = user_history[uid][-50:]

    streak_reward = update_streak(uid)
    new_achievs = check_achievements(uid)

    extras = []
    if streak_reward:
        extras.append(f"🔥 <b>Стрик {streak_reward[0]} дней!</b> +{streak_reward[1]} вопросов")
    for name, desc in new_achievs:
        extras.append(f"🏆 Достижение: <b>{name}</b>")

    used = user_questions_today[uid]["count"]
    bonus = user_bonus_questions[uid]
    if is_premium(uid):
        footer = "💎 Премиум — безлимит"
    else:
        rem = FREE_DAILY_LIMIT - used
        footer = f"📊 Осталось сегодня: {rem}/{FREE_DAILY_LIMIT}"
        if bonus:
            footer += f" + 🎁 {bonus} бонусных"

    full_answer = answer
    if extras:
        full_answer += "\n\n" + "\n".join(extras)
    full_answer += f"\n\n<i>{footer}</i>"

    if len(full_answer) > 4000:
        for i in range(0, len(full_answer), 4000):
            chunk = full_answer[i:i+4000]
            try:
                await message.answer(chunk)
            except Exception:
                await message.answer(chunk[:3500])
    else:
        try:
            await message.answer(full_answer)
        except Exception as e:
            logging.error(f"send error: {e}")
            await message.answer(answer[:3500])


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    me = await bot.get_me()
    logging.info(f"Bot started: @{me.username}")
    if ADMIN_CHAT_ID:
        ADMIN_IDS.add(ADMIN_CHAT_ID)
        logging.info(f"Admin registered: {ADMIN_CHAT_ID}")
    if not GROQ_API_KEY:
        logging.info("GROQ_API_KEY not set — using free Pollinations AI")
    else:
        logging.info("Using Groq AI (premium)")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
