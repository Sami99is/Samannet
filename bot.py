import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
import os
import secrets
import time
import hashlib

# --- تنظیمات اصلی (بدون تغییر - برای عدم قطع اتصال با سرور) ---
BOT_TOKEN = "8936504596:AAGdlz2_-QetRjYLRW8b8ln3jN7lvsATNDk"
NODE_URL = "https://affix-production-fdfd.up.railway.app"
ADMIN_ID = 8443938939
ADMIN_WALLET = "AFIX_GMN_f89637364a"
AFIX_PRICE_TOMAN = 300000

bot = telebot.TeleBot(BOT_TOKEN)
USERS_DB = "bot_users.json"
CONFIG_DB = "bot_config.json"
TASKS_DB = "bot_tasks.json"

# --- توابع فایل ---
def load_json(filename, default_val):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return default_val
    return default_val

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_users():
    return load_json(USERS_DB, {})

def save_users(users):
    save_json(USERS_DB, users)

def load_config():
    return load_json(CONFIG_DB, {"required_channels": []})

def save_config(config):
    save_json(CONFIG_DB, config)

def load_tasks():
    return load_json(TASKS_DB, {"tasks": [], "completed": {}})

def save_tasks(tasks):
    save_json(TASKS_DB, tasks)

# --- مدیریت کاربر / کیف پول / زبان ---
# ساختار جدید هر کاربر: {"wallet": "...", "lang": "fa" | "en"}
def ensure_user(user_id, users):
    """اگر کاربر وجود نداشت، کیف پول برایش می‌سازد (بدون تعیین زبان). users را in-place تغییر می‌دهد."""
    user_id_str = str(user_id)
    if user_id_str not in users:
        if user_id == ADMIN_ID:
            users[user_id_str] = {"wallet": ADMIN_WALLET}
        else:
            users[user_id_str] = {"wallet": f"AFIX_usr_{secrets.token_hex(8)}"}
    return users[user_id_str]

def get_wallet(user_id, users):
    entry = users.get(str(user_id))
    if not entry:
        entry = ensure_user(user_id, users)
        save_users(users)
    return entry.get("wallet")

def get_lang(user_id, users):
    entry = users.get(str(user_id))
    if entry and entry.get("lang") in ("fa", "en"):
        return entry.get("lang")
    return "fa"  # پیش‌فرض تا انتخاب شود

def has_lang(user_id, users):
    entry = users.get(str(user_id))
    return bool(entry and entry.get("lang") in ("fa", "en"))

def set_lang(user_id, users, lang):
    entry = ensure_user(user_id, users)
    entry["lang"] = lang
    save_users(users)

# --- متن‌های دو زبانه (بخش‌های اصلی که کاربر عادی می‌بیند) ---
T = {
    "choose_lang": {
        "fa": "🌐 لطفاً زبان خود را انتخاب کنید:",
        "en": "🌐 Please choose your language:",
    },
    "welcome": {
        "fa": "به ربات رسمی و قدرتمند شبکه AFIX خوش آمدید.\nلطفاً گزینه مورد نظر خود را از منوی زیر انتخاب کنید:",
        "en": "Welcome to the official AFIX network bot.\nPlease choose an option from the menu below:",
    },
    "join_required": {
        "fa": "⚠️ برای استفاده از ربات، لطفاً ابتدا در کانال‌های زیر عضو شوید:",
        "en": "⚠️ To use this bot, please join the channels below first:",
    },
    "join_button": {"fa": "📢 عضویت در {ch}", "en": "📢 Join {ch}"},
    "join_check_button": {"fa": "✅ عضو شدم، بررسی مجدد", "en": "✅ I joined, check again"},
    "join_confirmed": {"fa": "✅ عضویت شما تایید شد!", "en": "✅ Membership confirmed!"},
    "join_failed": {"fa": "❌ شما هنوز در تمام کانال‌ها عضو نشده‌اید!", "en": "❌ You haven't joined all required channels yet!"},
    "join_required_alert": {"fa": "⚠️ ابتدا باید در کانال‌های اجباری عضو شوید!", "en": "⚠️ You must join the required channels first!"},
    "menu_mine": {"fa": "⛏️ استخراج (ماین ۲۴ ساعته)", "en": "⛏️ Mine (24h Mining)"},
    "menu_balance": {"fa": "💰 کیف پول من", "en": "💰 My Wallet"},
    "menu_tasks": {"fa": "🎯 مرکز ماموریت‌ها (پاداش)", "en": "🎯 Task Center (Rewards)"},
    "menu_transfer": {"fa": "💸 انتقال ارز", "en": "💸 Transfer"},
    "menu_market": {"fa": "🛒 بخش خرید و فروش", "en": "🛒 Buy / Sell"},
    "menu_invite": {"fa": "👥 دعوت دوستان", "en": "👥 Invite Friends"},
    "menu_info": {"fa": "ℹ️ درباره AFIX", "en": "ℹ️ About AFIX"},
    "menu_admin": {"fa": "👑 پنل مدیریت ادمین", "en": "👑 Admin Panel"},
    "menu_back": {"fa": "🔙 بازگشت به منوی اصلی", "en": "🔙 Back to Main Menu"},
    "balance_error": {"fa": "❌ خطا در دریافت اطلاعات موجودی.", "en": "❌ Error fetching balance info."},
    "server_error": {"fa": "❌ خطای ارتباط با سرور: {e}", "en": "❌ Server connection error: {e}"},
    "no_tasks": {"fa": "🎯 مرکز ماموریت‌ها\n\nدر حال حاضر ماموریت فعالی وجود ندارد. لطفاً بعداً سر بزنید!",
                 "en": "🎯 Task Center\n\nThere are no active tasks right now. Please check back later!"},
    "tasks_title": {"fa": "🎯 مرکز ماموریت‌های AFIX\nبا عضویت در کانال‌های زیر پاداش بگیرید:\n\n",
                     "en": "🎯 AFIX Task Center\nJoin the channels below to earn rewards:\n\n"},
    "task_done_line": {"fa": "✅ ماموریت {n}: عضویت در {ch} (انجام شده)\n", "en": "✅ Task {n}: Join {ch} (Done)\n"},
    "task_open_line": {"fa": "🔹 ماموریت {n}: عضویت در {ch} (پاداش: {reward} AFIX)\n", "en": "🔹 Task {n}: Join {ch} (Reward: {reward} AFIX)\n"},
    "task_join_button": {"fa": "🔗 ورود به کانال {ch}", "en": "🔗 Open channel {ch}"},
    "task_claim_button": {"fa": "🎁 دریافت پاداش ماموریت {n}", "en": "🎁 Claim reward for task {n}"},
    "task_not_found": {"fa": "❌ ماموریت مورد نظر یافت نشد.", "en": "❌ Task not found."},
    "task_already_claimed": {"fa": "⚠️ شما قبلاً پاداش این ماموریت را دریافت کرده‌اید!", "en": "⚠️ You already claimed this task's reward!"},
    "task_not_member": {"fa": "❌ شما هنوز در کانال {ch} عضو نشده‌اید!", "en": "❌ You haven't joined {ch} yet!"},
    "task_check_error": {"fa": "❌ خطا در بررسی عضویت کانال.", "en": "❌ Error checking channel membership."},
    "task_claim_success": {"fa": "🎉 تبریک! {reward} واحد AFIX به حساب شما واریز شد.", "en": "🎉 Congrats! {reward} AFIX credited to your account."},
    "task_claim_error": {"fa": "❌ خطا در واریز پاداش: {e}", "en": "❌ Error crediting reward: {e}"},
    "mine_success": {"fa": "✅ استخراج موفقیت‌آمیز بود!\n💰 موجودی جدید شما: {bal:,.2f} AFIX",
                      "en": "✅ Mining successful!\n💰 New balance: {bal:,.2f} AFIX"},
    "mine_default_fail": {"fa": "هنوز زمان استخراج ۲۴ ساعته‌ی شما فرا نرسیده است.", "en": "Your 24h mining cooldown hasn't ended yet."},
    "mine_too_hard": {"fa": "⚠️ استخراج ناموفق بود (نیاز به تلاش مجدد). لطفاً دوباره امتحان کنید.",
                       "en": "⚠️ Mining attempt failed (needs retry). Please try again."},
    "mine_error": {"fa": "❌ خطا در عملیات استخراج: {e}", "en": "❌ Mining error: {e}"},
    "transfer_ask_address": {"fa": "💸 بخش انتقال ارز AFIX\n\n• کارمزد شبکه: 0.01 AFIX\n\n📥 لطفاً آدرس کیف پول مقصد را ارسال کنید:",
                              "en": "💸 AFIX Transfer\n\n• Network fee: 0.01 AFIX\n\n📥 Please send the destination wallet address:"},
    "transfer_ask_amount": {"fa": "📤 حالا مقدار AFIX که می‌خواهید ارسال کنید را وارد کنید:",
                             "en": "📤 Now enter the amount of AFIX you want to send:"},
    "transfer_invalid_address": {"fa": "❌ آدرس نامعتبر است. عملیات لغو شد. دوباره از منو امتحان کنید.",
                                  "en": "❌ Invalid address. Operation cancelled. Please try again from the menu."},
    "transfer_invalid_amount": {"fa": "❌ مقدار وارد شده نامعتبر است. عملیات لغو شد.",
                                 "en": "❌ Invalid amount. Operation cancelled."},
    "transfer_processing": {"fa": "⏳ در حال پردازش انتقال...", "en": "⏳ Processing transfer..."},
    "transfer_success": {"fa": "✅ انتقال {amount} AFIX به آدرس زیر با موفقیت انجام شد:\n`{addr}`",
                          "en": "✅ Successfully transferred {amount} AFIX to:\n`{addr}`"},
    "transfer_error": {"fa": "❌ خطا در انتقال: {e}", "en": "❌ Transfer error: {e}"},
    "market_text": {"fa": "🛒 بخش خرید و فروش AFIX\n\nنرخ هر ۱ واحد AFIX: {price:,} تومان\n\n🔹 می‌توانید درخواست فروش موجودی خود را ثبت کنید تا معادل ریالی آن به کارت شما واریز شود.",
                     "en": "🛒 AFIX Buy/Sell\n\nRate per 1 AFIX: {price:,} Toman\n\n🔹 You can submit a sell request to cash out to your bank card."},
    "market_sell_button": {"fa": "💵 ثبت درخواست فروش و تسویه", "en": "💵 Submit Sell Request"},
    "market_back_button": {"fa": "🔙 بازگشت", "en": "🔙 Back"},
    "sell_ask_amount": {"fa": "📝 لطفاً تعداد واحد AFIX برای فروش را ارسال کنید:", "en": "📝 Please enter the amount of AFIX to sell:"},
    "sell_ask_card": {"fa": "💳 حالا شماره کارت بانکی خود را ارسال کنید:", "en": "💳 Now send your bank card number:"},
    "sell_invalid_amount": {"fa": "❌ مقدار نامعتبر است. عملیات لغو شد.", "en": "❌ Invalid amount. Operation cancelled."},
    "sell_success_user": {"fa": "✅ درخواست فروش شما ثبت شد و به ادمین ارسال گردید. به‌زودی بررسی می‌شود.",
                           "en": "✅ Your sell request has been submitted to the admin and will be reviewed shortly."},
    "sell_admin_notify": {"fa": "🔔 درخواست فروش جدید:\n👤 کاربر: {uid}\n💰 مقدار: {amount} AFIX\n💳 شماره کارت: {card}",
                           "en": "🔔 New sell request:\n👤 User: {uid}\n💰 Amount: {amount} AFIX\n💳 Card: {card}"},
    "invite_text": {"fa": "👥 دعوت از دوستان\n\nبا دعوت هر دوست، پاداش بگیرید!\n\n🔗 لینک اختصاصی دعوت شما:\n`{link}`",
                     "en": "👥 Invite Friends\n\nInvite friends and earn rewards!\n\n🔗 Your unique invite link:\n`{link}`"},
    "info_text": {"fa": "ℹ️ درباره شبکه AFIX:\n\n• سقف کل شبکه: ۲۱,۰۰۰,۰۰۰ واحد\n• کارمزد انتقال: ۰.۰۱ AFIX",
                  "en": "ℹ️ About AFIX Network:\n\n• Total supply cap: 21,000,000 units\n• Transfer fee: 0.01 AFIX"},
    "admin_denied": {"fa": "⛔ دسترسی غیرمجاز!", "en": "⛔ Access denied!"},
    "admin_conn_error": {"fa": "❌ خطا در اتصال به سرور ادمین: {e}", "en": "❌ Error connecting to admin server: {e}"},
    "broadcast_ask": {"fa": "✍️ متن پیام همگانی خود را بفرستید:", "en": "✍️ Send the broadcast message text:"},
    "broadcast_done": {"fa": "✅ پیام همگانی ارسال شد.\n📨 موفق: {ok} | ناموفق: {fail}",
                        "en": "✅ Broadcast sent.\n📨 Success: {ok} | Failed: {fail}"},
}

def tr(key, lang, **kwargs):
    text = T.get(key, {}).get(lang, T.get(key, {}).get("fa", key))
    if kwargs:
        return text.format(**kwargs)
    return text

# --- بررسی عضویت اجباری پایه ---
def check_membership(user_id):
    if user_id == ADMIN_ID:
        return True
    config = load_config()
    channels = config.get("required_channels", [])
    if not channels:
        return True
    for channel in channels:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            print(f"Error checking channel {channel}: {e}")
            continue
    return True

# --- منوی شیشه‌ای اصلی ---
def main_menu_markup(user_id, lang):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(tr("menu_mine", lang), callback_data="mine"),
        InlineKeyboardButton(tr("menu_balance", lang), callback_data="balance"),
        InlineKeyboardButton(tr("menu_tasks", lang), callback_data="task_center"),
        InlineKeyboardButton(tr("menu_transfer", lang), callback_data="transfer_menu"),
        InlineKeyboardButton(tr("menu_market", lang), callback_data="market"),
        InlineKeyboardButton(tr("menu_invite", lang), callback_data="invite"),
        InlineKeyboardButton(tr("menu_info", lang), callback_data="info")
    )
    if user_id == ADMIN_ID:
        markup.add(InlineKeyboardButton(tr("menu_admin", lang), callback_data="admin_panel"))
    return markup

def show_join_required(chat_id, lang):
    config = load_config()
    channels = config.get("required_channels", [])
    markup = InlineKeyboardMarkup(row_width=1)
    for ch in channels:
        ch_clean = ch.replace("@", "")
        markup.add(InlineKeyboardButton(tr("join_button", lang, ch=ch), url=f"https://t.me/{ch_clean}"))
    markup.add(InlineKeyboardButton(tr("join_check_button", lang), callback_data="check_join"))
    bot.send_message(chat_id, tr("join_required", lang), reply_markup=markup, parse_mode="Markdown")

def show_main_menu(chat_id, user_id, lang):
    bot.send_message(chat_id, tr("welcome", lang), reply_markup=main_menu_markup(user_id, lang))

def ask_language(chat_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🇮🇷 فارسی", callback_data="set_lang_fa"),
        InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en"),
    )
    bot.send_message(chat_id, "🌐 فارسی یا English؟ / Persian or English?", reply_markup=markup)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_id_str = str(user_id)
    users = load_users()
    ensure_user(user_id, users)
    save_users(users)

    if not has_lang(user_id, users):
        ask_language(message.chat.id)
        return

    lang = get_lang(user_id, users)

    if not check_membership(user_id):
        show_join_required(message.chat.id, lang)
        return

    show_main_menu(message.chat.id, user_id, lang)

def show_task_center(chat_id, user_id_str, lang):
    task_data = load_tasks()
    tasks = task_data.get("tasks", [])
    if not tasks:
        bot.send_message(chat_id, tr("no_tasks", lang))
        return
    markup = InlineKeyboardMarkup(row_width=1)
    completed_list = task_data.get("completed", {}).get(user_id_str, [])
    text = tr("tasks_title", lang)
    for idx, t in enumerate(tasks):
        t_id = t["id"]
        ch = t["channel"]
        reward = t["reward"]
        if t_id in completed_list:
            text += tr("task_done_line", lang, n=idx + 1, ch=ch)
        else:
            text += tr("task_open_line", lang, n=idx + 1, ch=ch, reward=reward)
            ch_clean = ch.replace("@", "")
            markup.add(InlineKeyboardButton(tr("task_join_button", lang, ch=ch), url=f"https://t.me/{ch_clean}"))
            markup.add(InlineKeyboardButton(tr("task_claim_button", lang, n=idx + 1), callback_data=f"claim_task_{t_id}"))
    markup.add(InlineKeyboardButton(tr("menu_back", lang), callback_data="back_home"))
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.from_user.id
    user_id_str = str(user_id)
    users = load_users()

    # --- انتخاب زبان (باید قبل از هر چیز دیگری هندل شود) ---
    if call.data in ("set_lang_fa", "set_lang_en"):
        lang = "fa" if call.data == "set_lang_fa" else "en"
        ensure_user(user_id, users)
        set_lang(user_id, users, lang)
        bot.answer_callback_query(call.id, "✅")
        if not check_membership(user_id):
            show_join_required(call.message.chat.id, lang)
        else:
            show_main_menu(call.message.chat.id, user_id, lang)
        return

    ensure_user(user_id, users)
    save_users(users)
    lang = get_lang(user_id, users)

    if call.data == "check_join":
        if check_membership(user_id):
            bot.answer_callback_query(call.id, tr("join_confirmed", lang))
            show_main_menu(call.message.chat.id, user_id, lang)
        else:
            bot.answer_callback_query(call.id, tr("join_failed", lang), show_alert=True)
        return

    if not check_membership(user_id):
        bot.answer_callback_query(call.id, tr("join_required_alert", lang), show_alert=True)
        return

    wallet_address = get_wallet(user_id, users)

    # --- کیف پول ---
    if call.data == "balance":
        try:
            res = requests.get(f"{NODE_URL}/api/balance?address={wallet_address}")
            if res.status_code == 200:
                data = res.json()
                text = (f"📍 **آدرس کیف پول شما:**\n`{data['address']}`\n\n"
                        f"💰 **موجودی کل:** {data['balance']:,.2f} AFIX\n"
                        f"💵 **ارزش تقریبی:** {data['value_in_toman']:,.0f} تومان\n"
                        f"⚡ کارمزد شبکه: 0.01 AFIX") if lang == "fa" else (
                        f"📍 **Your wallet address:**\n`{data['address']}`\n\n"
                        f"💰 **Total balance:** {data['balance']:,.2f} AFIX\n"
                        f"💵 **Approx. value:** {data['value_in_toman']:,.0f} Toman\n"
                        f"⚡ Network fee: 0.01 AFIX")
                bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
            else:
                bot.send_message(call.message.chat.id, tr("balance_error", lang))
        except Exception as e:
            bot.send_message(call.message.chat.id, tr("server_error", lang, e=e))

    # --- مرکز ماموریت‌ها ---
    elif call.data == "task_center":
        show_task_center(call.message.chat.id, user_id_str, lang)

    elif call.data.startswith("claim_task_"):
        t_id = int(call.data.split("_")[2])
        task_data = load_tasks()
        tasks = task_data.get("tasks", [])
        target_task = next((t for t in tasks if t["id"] == t_id), None)

        if not target_task:
            bot.answer_callback_query(call.id, tr("task_not_found", lang), show_alert=True)
            return

        completed_list = task_data.setdefault("completed", {}).setdefault(user_id_str, [])
        if t_id in completed_list:
            bot.answer_callback_query(call.id, tr("task_already_claimed", lang), show_alert=True)
            return

        channel = target_task["channel"]
        reward = target_task["reward"]
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                bot.answer_callback_query(call.id, tr("task_not_member", lang, ch=channel), show_alert=True)
                return
        except Exception:
            bot.answer_callback_query(call.id, tr("task_check_error", lang), show_alert=True)
            return

        try:
            payload = {"from_address": ADMIN_WALLET, "to_address": wallet_address, "amount": reward}
            requests.post(f"{NODE_URL}/api/transfer", json=payload)
            completed_list.append(t_id)
            save_tasks(task_data)
            bot.answer_callback_query(call.id, tr("task_claim_success", lang, reward=reward), show_alert=True)
            # رفرش صحیح مرکز ماموریت‌ها (باگ قبلی: هندل دوباره claim_task_ به‌جای نمایش منو)
            show_task_center(call.message.chat.id, user_id_str, lang)
        except Exception as e:
            bot.answer_callback_query(call.id, tr("task_claim_error", lang, e=e), show_alert=True)

    # --- ماین ۲۴ ساعته ---
    elif call.data == "mine":
        try:
            chal_res = requests.get(f"{NODE_URL}/api/mine/challenge").json()
            timestamp = chal_res['timestamp']
            # فرض: سرور نیاز به یک proof-of-work ساده دارد (sha256 با تعداد صفر ابتدایی = difficulty).
            # اگر منطق سرور فرق می‌کند، این بخش را باید مطابق کد Node.js تنظیم کرد.
            difficulty = int(chal_res.get('difficulty', 4))
            prefix = "0" * difficulty
            found_nonce = None
            for i in range(300000):
                candidate = hashlib.sha256(f"{wallet_address}{timestamp}{i}".encode()).hexdigest()
                if candidate.startswith(prefix):
                    found_nonce = i
                    break

            if found_nonce is None:
                bot.send_message(call.message.chat.id, tr("mine_too_hard", lang))
                return

            payload = {"address": wallet_address, "nonce": found_nonce, "timestamp": timestamp}
            res = requests.post(f"{NODE_URL}/api/mine/submit", json=payload)
            data = res.json()

            if res.status_code == 200 and data.get("status") == "success":
                bot.send_message(call.message.chat.id, tr("mine_success", lang, bal=data['balance']))
            else:
                err_msg = data.get("error", tr("mine_default_fail", lang))
                bot.send_message(call.message.chat.id, f"⚠️ {err_msg}")
        except Exception as e:
            bot.send_message(call.message.chat.id, tr("mine_error", lang, e=e))

    # --- انتقال ارز (اصلاح شده: حالا واقعاً ورودی کاربر را می‌گیرد) ---
    elif call.data == "transfer_menu":
        msg = bot.send_message(call.message.chat.id, tr("transfer_ask_address", lang))
        bot.register_next_step_handler(msg, process_transfer_address, lang)

    # --- بخش خرید و فروش ---
    elif call.data == "market":
        text = tr("market_text", lang, price=AFIX_PRICE_TOMAN)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(tr("market_sell_button", lang), callback_data="sell_request"))
        markup.add(InlineKeyboardButton(tr("market_back_button", lang), callback_data="back_home"))
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

    elif call.data == "sell_request":
        msg = bot.send_message(call.message.chat.id, tr("sell_ask_amount", lang))
        bot.register_next_step_handler(msg, process_sell_amount, lang)

    # --- دعوت دوستان ---
    elif call.data == "invite":
        bot_info = bot.get_me()
        invite_link = f"https://t.me/{bot_info.username}?start={user_id}"
        bot.send_message(call.message.chat.id, tr("invite_text", lang, link=invite_link), parse_mode="Markdown")

    elif call.data == "info":
        bot.send_message(call.message.chat.id, tr("info_text", lang))

    # --- پنل مدیریت انحصاری ادمین (فقط فارسی - فقط ادمین می‌بیند) ---
    elif call.data == "admin_panel":
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, tr("admin_denied", lang))
            return
        try:
            res = requests.get(f"{NODE_URL}/")
            node_data = res.json()
            total_circulating = node_data.get("total_circulating_supply", 0)
            admin_bal_res = requests.get(f"{NODE_URL}/api/balance?address={ADMIN_WALLET}").json()
            all_users = load_users()
            config = load_config()
            task_data = load_tasks()

            text = (f"👑 **پنل مدیریت انحصاری ادمین** 👑\n\n"
                    f"💰 موجودی ولت ادمین شما: {admin_bal_res.get('balance', 0):,.2f} AFIX\n"
                    f"👥 تعداد کاربران: {len(all_users)} نفر\n"
                    f"📊 کل توکن در گردش: {total_circulating:,.2f} / 21,000,000\n"
                    f"📢 کانال جوین پایه: {len(config.get('required_channels', []))}\n"
                    f"🎯 ماموریت‌های فعال مرکز پاداش: {len(task_data.get('tasks', []))}")

            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                InlineKeyboardButton("➕ افزودن کانال جوین پایه", callback_data="admin_add_channel"),
                InlineKeyboardButton("➖ حذف کانال جوین پایه", callback_data="admin_remove_channel"),
                InlineKeyboardButton("🎯 افزودن ماموریت جدید به مرکز پاداش", callback_data="admin_add_task"),
                InlineKeyboardButton("🗑️ حذف ماموریت از مرکز پاداش", callback_data="admin_remove_task"),
                InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast"),
                InlineKeyboardButton("🔙 بازگشت", callback_data="back_home")
            )
            bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)
        except Exception as e:
            bot.send_message(call.message.chat.id, tr("admin_conn_error", lang, e=e))

    elif call.data == "admin_add_channel":
        if user_id != ADMIN_ID:
            return
        msg = bot.send_message(call.message.chat.id, "✍️ یوزرنیم کانال پایه را با @ بفرستید:")
        bot.register_next_step_handler(msg, save_new_channel)

    elif call.data == "admin_remove_channel":
        if user_id != ADMIN_ID:
            return
        config = load_config()
        channels = config.get("required_channels", [])
        if not channels:
            bot.send_message(call.message.chat.id, "⚠️ هیچ کانالی ثبت نشده است.")
            return
        msg = bot.send_message(call.message.chat.id, "کانال‌های فعلی:\n" + "\n".join(channels) + "\nیوزرنیم را برای حذف بفرستید:")
        bot.register_next_step_handler(msg, remove_channel_step)

    elif call.data == "admin_add_task":
        if user_id != ADMIN_ID:
            return
        msg = bot.send_message(call.message.chat.id, "✍️ اطلاعات ماموریت جدید را به این صورت بفرستید:\n`يوزرنیم_کانال پاداش`\n(مثلا: `@AfixChannel 0.5`)", parse_mode="Markdown")
        bot.register_next_step_handler(msg, save_new_task_step)

    elif call.data == "admin_remove_task":
        if user_id != ADMIN_ID:
            return
        task_data = load_tasks()
        tasks = task_data.get("tasks", [])
        if not tasks:
            bot.send_message(call.message.chat.id, "⚠️ هیچ ماموریتی وجود ندارد.")
            return
        txt = "لیست ماموریت‌ها (برای حذف، آیدی عددی ماموریت را بفرستید):\n"
        for t in tasks:
            txt += f"🆔 شناسه: {t['id']} | کانال: {t['channel']} | پاداش: {t['reward']}\n"
        msg = bot.send_message(call.message.chat.id, txt)
        bot.register_next_step_handler(msg, remove_task_step)

    elif call.data == "admin_broadcast":
        if user_id != ADMIN_ID:
            return
        msg = bot.send_message(call.message.chat.id, tr("broadcast_ask", lang))
        bot.register_next_step_handler(msg, process_broadcast_step)

    elif call.data == "back_home":
        show_main_menu(call.message.chat.id, user_id, lang)


# ==================== مراحل انتقال ارز ====================
def process_transfer_address(message, lang):
    if message.from_user.id != message.from_user.id:
        return
    address = message.text.strip()
    if not address.startswith("AFIX_") or " " in address:
        bot.reply_to(message, tr("transfer_invalid_address", lang))
        return
    msg = bot.send_message(message.chat.id, tr("transfer_ask_amount", lang))
    bot.register_next_step_handler(msg, process_transfer_amount, lang, address)

def process_transfer_amount(message, lang, address):
    user_id = message.from_user.id
    users = load_users()
    wallet_address = get_wallet(user_id, users)
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError()
    except ValueError:
        bot.reply_to(message, tr("transfer_invalid_amount", lang))
        return

    bot.send_message(message.chat.id, tr("transfer_processing", lang))
    try:
        payload = {"from_address": wallet_address, "to_address": address, "amount": amount}
        res = requests.post(f"{NODE_URL}/api/transfer", json=payload)
        if res.status_code == 200:
            bot.send_message(message.chat.id, tr("transfer_success", lang, amount=amount, addr=address), parse_mode="Markdown")
        else:
            err = res.json().get("error", res.text) if res.headers.get("content-type", "").startswith("application/json") else res.text
            bot.send_message(message.chat.id, tr("transfer_error", lang, e=err))
    except Exception as e:
        bot.send_message(message.chat.id, tr("transfer_error", lang, e=e))


# ==================== مراحل فروش ====================
def process_sell_amount(message, lang):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError()
    except ValueError:
        bot.reply_to(message, tr("sell_invalid_amount", lang))
        return
    msg = bot.send_message(message.chat.id, tr("sell_ask_card", lang))
    bot.register_next_step_handler(msg, process_sell_card, lang, amount)

def process_sell_card(message, lang, amount):
    card = message.text.strip()
    user_id = message.from_user.id
    bot.send_message(message.chat.id, tr("sell_success_user", lang))
    try:
        bot.send_message(ADMIN_ID, tr("sell_admin_notify", "fa", uid=user_id, amount=amount, card=card))
    except Exception as e:
        print(f"Could not notify admin of sell request: {e}")


# ==================== توابع کمکی ادمین (کانال‌ها / ماموریت‌ها / broadcast) ====================
def save_new_channel(message):
    if message.from_user.id != ADMIN_ID:
        return
    ch = message.text.strip()
    config = load_config()
    if ch not in config["required_channels"]:
        config["required_channels"].append(ch)
        save_config(config)
        bot.reply_to(message, f"✅ کانال پایه {ch} اضافه شد.")
    else:
        bot.reply_to(message, "⚠️ از قبل وجود داشت.")

def remove_channel_step(message):
    if message.from_user.id != ADMIN_ID:
        return
    ch = message.text.strip()
    config = load_config()
    if ch in config["required_channels"]:
        config["required_channels"].remove(ch)
        save_config(config)
        bot.reply_to(message, "✅ حذف شد.")
    else:
        bot.reply_to(message, "❌ پیدا نشد.")

def save_new_task_step(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.strip().split()
        ch = parts[0]
        reward = float(parts[1])
        task_data = load_tasks()
        tasks = task_data.setdefault("tasks", [])
        new_id = int(time.time())
        tasks.append({"id": new_id, "channel": ch, "reward": reward})
        save_tasks(task_data)
        bot.reply_to(message, f"✅ ماموریت جدید با موفقیت به مرکز پاداش اضافه شد!\nکانال: {ch}\nپاداش: {reward} AFIX")
    except Exception:
        bot.reply_to(message, "❌ خطا در فرمت ارسال. لطفاً به صورت `يوزرنیم پاداش` بفرستید.\nمثال: `@AfixChannel 0.5`")

def remove_task_step(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        t_id = int(message.text.strip())
        task_data = load_tasks()
        tasks = task_data.get("tasks", [])
        updated_tasks = [t for t in tasks if t["id"] != t_id]
        if len(updated_tasks) < len(tasks):
            task_data["tasks"] = updated_tasks
            save_tasks(task_data)
            bot.reply_to(message, f"✅ ماموریت با شناسه {t_id} حذف شد.")
        else:
            bot.reply_to(message, "❌ چنین شناسه‌ای پیدا نشد.")
    except Exception:
        bot.reply_to(message, "❌ لطفاً فقط شناسه عددی ماموریت را بفرستید.")

def process_broadcast_step(message):
    if message.from_user.id != ADMIN_ID:
        return
    text_to_send = message.text
    all_users = load_users()
    ok, fail = 0, 0
    for uid_str in all_users.keys():
        try:
            bot.send_message(int(uid_str), text_to_send)
            ok += 1
            time.sleep(0.05)  # جلوگیری از rate-limit تلگرام
        except Exception:
            fail += 1
    bot.reply_to(message, tr("broadcast_done", "fa", ok=ok, fail=fail))


if __name__ == "__main__":
    print("🤖 Professional Bot is running with Task Center, Admin Panel & Language Selection...")
    bot.polling(none_stop=True)
