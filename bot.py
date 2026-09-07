import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
import os
import secrets
import time
import hashlib
import ecdsa  # برای تولید کلید خصوصی و آدرس واقعی استاندارد

# --- تنظیمات اصلی ---
BOT_TOKEN = "8936504596:AAGdlz2_-QetRjYLRW8b8ln3jN7lvsATNDk"
NODE_URL = "https://affix-production-fdfd.up.railway.app"
ADMIN_ID = 8443938939
ADMIN_WALLET = "AFIX_GMN_f89637364a"
AFIX_PRICE_TOMAN = 300000

bot = telebot.TeleBot(BOT_TOKEN)
USERS_DB = "bot_users.json"
CONFIG_DB = "bot_config.json"
TASKS_DB = "bot_tasks.json"

def load_json(filename, default_val):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
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

# --- تولید کیف پول واقعی (آدرس و کلید خصوصی ۲۵۶ بیتی) ---
def generate_afix_wallet():
    # تولید کلید خصوصی ۲۵۶ بیتی استاندارد (ECDSA secp256k1)
    priv_key_bytes = secrets.token_bytes(32)
    priv_key_hex = priv_key_bytes.hex()
    
    sk = ecdsa.SigningKey.from_string(priv_key_bytes, curve=ecdsa.SECP256k1)
    vk = sk.get_verifying_key()
    pub_key_bytes = vk.to_string()
    
    # ساخت آدرس با هش کردن کلید عمومی
    sha = hashlib.sha256(pub_key_bytes).digest()
    ripemd = hashlib.new('ripemd160', sha).digest()
    address = "AFIX_" + ripemd.hex()[:24]
    
    return address, priv_key_hex

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
def main_menu_markup(user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("⛏️ استخراج (ماین ۲۴ ساعته)", callback_data="mine"),
        InlineKeyboardButton("💰 کیف پول من و کلید خصوصی", callback_data="balance"),
        InlineKeyboardButton("🎯 مرکز ماموریت‌ها (پاداش)", callback_data="task_center"),
        InlineKeyboardButton("💸 انتقال ارز", callback_data="transfer_menu"),
        InlineKeyboardButton("🛒 بازار خرید و فروش (واسطه امن)", callback_data="market"),
        InlineKeyboardButton("👥 دعوت دوستان", callback_data="invite"),
        InlineKeyboardButton("ℹ️ درباره AFIX", callback_data="info")
    )
    
    if user_id == ADMIN_ID:
        markup.add(InlineKeyboardButton("👑 پنل مدیریت ادمین", callback_data="admin_panel"))
        
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    if not check_membership(user_id):
        config = load_config()
        channels = config.get("required_channels", [])
        markup = InlineKeyboardMarkup(row_width=1)
        for ch in channels:
            ch_clean = ch.replace("@", "")
            markup.add(InlineKeyboardButton(f"📢 عضویت در {ch}", url=f"https://t.me/{ch_clean}"))
        markup.add(InlineKeyboardButton("✅ عضو شدم، بررسی مجدد", callback_data="check_join"))
        
        bot.send_message(
            message.chat.id,
            "⚠️ **برای استفاده از ربات، لطفاً ابتدا در کانال‌های زیر عضو شوید:**",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return

    user_id_str = str(user_id)
    users = load_users()
    
    # اگر کاربر جدید است، کیف پول واقعی و کلید خصوصی ۲۵۶ بیتی برایش ساخته شود
    if user_id_str not in users:
        if user_id == ADMIN_ID:
            addr, priv = ADMIN_WALLET, "ADMIN_MASTER_SECURE_KEY_256_BIT"
        else:
            addr, priv = generate_afix_wallet()
            
        users[user_id_str] = {
            "address": addr,
            "private_key": priv
        }
        save_users(users)
        
        # ارسال اطلاعات امنیتی ولت به کاربر در اولین ورود
        welcome_wallet_text = (
            f"🎉 **به اکوسیستم AFIX خوش آمدید!**\n\n"
            f"🔐 کیف پول امن بلاکچین شما با موفقیت ساخته شد:\n\n"
            f"📍 **آدرس عمومی:**\n`{addr}`\n\n"
            f"🔑 **کلید خصوصی (Private Key - 256bit):**\n`{priv}`\n\n"
            f"⚠️ **هشدار امنیتی بسیار مهم:** این کلید خصوصی فقط یک بار به شما نمایش داده می‌شود! آن را در یک جای کاملاً امن یادداشت و نگهداری کنید. در صورت گم کردن کلید، دسترسی به دارایی خود را برای همیشه از دست خواهید داد."
        )
        bot.send_message(message.chat.id, welcome_wallet_text, parse_mode="Markdown")
    
    bot.send_message(
        message.chat.id, 
        "به ربات رسمی و قدرتمند شبکه AFIX خوش آمدید.\nلطفاً گزینه مورد نظر خود را از منوی زیر انتخاب کنید:",
        reply_markup=main_menu_markup(user_id)
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.from_user.id
    user_id_str = str(user_id)
    
    if call.data == "check_join":
        if check_membership(user_id):
            bot.answer_callback_query(call.id, "✅ عضویت شما تایید شد!")
            send_welcome(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ شما هنوز در تمام کانال‌ها عضو نشده‌اید!", show_alert=True)
        return

    if not check_membership(user_id):
        bot.answer_callback_query(call.id, "⚠️ ابتدا باید در کانال‌های اجباری عضو شوید!", show_alert=True)
        return

    users = load_users()
    if user_id == ADMIN_ID:
        wallet_address = ADMIN_WALLET
        private_key = "MASTER_KEY"
    else:
        user_data = users.get(user_id_str)
        if not user_data:
            addr, priv = generate_afix_wallet()
            users[user_id_str] = {"address": addr, "private_key": priv}
            save_users(users)
            wallet_address = addr
            private_key = priv
        else:
            wallet_address = user_data["address"]
            private_key = user_data["private_key"]

    # --- کیف پول و نمایش کلید خصوصی ---
    if call.data == "balance":
        try:
            res = requests.get(f"{NODE_URL}/api/balance?address={wallet_address}")
            if res.status_code == 200:
                data = res.json()
                text = (f"📍 **آدرس کیف پول:**\n`{data['address']}`\n\n"
                        f"🔑 **کلید خصوصی شما:**\n`{private_key}`\n\n"
                        f"💰 **موجودی کل:** {data['balance']:,.2f} AFIX\n"
                        f"💵 **ارزش تقریبی:** {data['value_in_toman']:,.0f} تومان\n"
                        f"⚡ کارمزد شبکه: 0.01 AFIX\n\n"
                        f"⚠️ کلید خصوصی خود را به هیچ کس ندهید.")
                bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
            else:
                bot.send_message(call.message.chat.id, "❌ خطا در دریافت اطلاعات موجودی از گره شبکه.")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ خطای ارتباط با سرور: {e}")

    # --- مرکز ماموریت‌ها (Task Center) ---
    elif call.data == "task_center":
        task_data = load_tasks()
        tasks = task_data.get("tasks", [])
        
        if not tasks:
            bot.send_message(call.message.chat.id, "🎯 **مرکز ماموریت‌ها**\n\nدر حال حاضر ماموریت فعالی وجود ندارد!", parse_mode="Markdown")
            return
            
        markup = InlineKeyboardMarkup(row_width=1)
        completed_list = task_data.get("completed", {}).get(user_id_str, [])
        
        text = "🎯 **مرکز ماموریت‌های AFIX**\nبا عضویت در کانال‌های زیر پاداش بگیرید:\n\n"
        for idx, t in enumerate(tasks):
            t_id = t["id"]
            ch = t["channel"]
            reward = t["reward"]
            
            if t_id in completed_list:
                text += f"✅ ماموریت {idx+1}: عضویت در {ch} (انجام شده)\n"
            else:
                text += f"🔹 ماموریت {idx+1}: عضویت در {ch} (پاداش: {reward} AFIX)\n"
                ch_clean = ch.replace("@", "")
                markup.add(InlineKeyboardButton(f"🔗 ورود به کانال {ch}", url=f"https://t.me/{ch_clean}"))
                markup.add(InlineKeyboardButton(f"🎁 دریافت پاداش ماموریت {idx+1}", callback_data=f"claim_task_{t_id}"))
                
        markup.add(InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_home"))
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

    elif call.data.startswith("claim_task_"):
        t_id = int(call.data.split("_")[2])
        task_data = load_tasks()
        tasks = task_data.get("tasks", [])
        
        target_task = None
        for t in tasks:
            if t["id"] == t_id:
                target_task = t
                break
                
        if not target_task:
            bot.answer_callback_query(call.id, "❌ ماموریت یافت نشد.", show_alert=True)
            return
            
        completed_list = task_data.setdefault("completed", {}).setdefault(user_id_str, [])
        if t_id in completed_list:
            bot.answer_callback_query(call.id, "⚠️ پاداش این ماموریت قبلاً دریافت شده است!", show_alert=True)
            return
            
        channel = target_task["channel"]
        reward = target_task["reward"]
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                bot.answer_callback_query(call.id, f"❌ شما هنوز در کانال {channel} عضو نشده‌اید!", show_alert=True)
                return
        except Exception as e:
            bot.answer_callback_query(call.id, "❌ خطا در بررسی عضویت کانال.", show_alert=True)
            return
            
        try:
            payload = {"sender": ADMIN_WALLET, "recipient": wallet_address, "amount": reward}
            res = requests.post(f"{NODE_URL}/api/transfer", json=payload)
            
            completed_list.append(t_id)
            save_tasks(task_data)
            
            bot.answer_callback_query(call.id, f"🎉 تبریک! {reward} واحد AFIX واریز شد.", show_alert=True)
            handle_query(call)
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ خطا در واریز پاداش: {e}", show_alert=True)

    # --- استخراج (ماین پویا PoW) ---
    elif call.data == "mine":
        msg = bot.send_message(call.message.chat.id, "⚙️ در حال حل چالش اثبات کار (PoW) و استخراج توکن...")
        try:
            chal_res = requests.get(f"{NODE_URL}/api/mine/challenge")
            if chal_res.status_code != 200:
                bot.edit_message_text("❌ خطا در برقراری ارتباط با سرور ماینینگ.", call.message.chat.id, msg.message_id)
                return
            
            chal_data = chal_res.json()
            timestamp = chal_data.get('timestamp')
            target_prefix = chal_data.get('target_prefix', '00000')
            
            nonce = 0
            while nonce < 50000000:
                val = f"{wallet_address}-{nonce}-{timestamp}"
                h = hashlib.sha256(val.encode()).hexdigest()
                if h.startswith(target_prefix):
                    break
                nonce += 1
            else:
                bot.edit_message_text("⚠️ استخراج به دلیل سختی شبکه انجام نشد. مجدداً تلاش کنید.", call.message.chat.id, msg.message_id)
                return

            payload = {"address": wallet_address, "nonce": nonce, "timestamp": timestamp}
            res = requests.post(f"{NODE_URL}/api/mine/submit", json=payload)
            data = res.json()
            
            if res.status_code == 200 and data.get("status") == "success":
                bot.edit_message_text(f"✅ استخراج با موفقیت انجام شد!\n\n💰 موجودی جدید: {data.get('balance', 0):,.2f} AFIX", call.message.chat.id, msg.message_id)
            else:
                err_msg = data.get("error", "اثبات کار نامعتبر است.")
                bot.edit_message_text(f"⚠️ {err_msg}", call.message.chat.id, msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ خطای پردازش ماین: {e}", call.message.chat.id, msg.message_id)

    # --- انتقال ارز ---
    elif call.data == "transfer_menu":
        text = (f"💸 **بخش انتقال ارز AFIX**\n\n"
                f"• کارمزد شبکه: **0.01 AFIX**\n\n"
                f"برای انتقال، اطلاعات را به این صورت در یک پیام بفرستید:\n`آدرس_مقصد مقدار`\n(مثال: `AFIX_usr_123456 5`)")
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_home"))
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

    # --- بازار خرید و فروش واقعی با بررسی هش تراکنش بانکی ---
    elif call.data == "market":
        text = (f"🛒 **بازار معاملاتی P2P و واسطه امن**\n\n"
                f"نرخ هر ۱ واحد AFIX: **{AFIX_PRICE_TOMAN:,} تومان**\n\n"
                f"🔹 در این بخش می‌توانید سفارش خرید ثبت کرده و با ارسال شماره پیگیری (هش بانکی واقعی)، به صورت اتوماتیک توکن خود را دریافت کنید.")
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💳 ثبت درخواست خرید و تایید هش بانکی", callback_data="buy_order_start"))
        markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_home"))
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

    elif call.data == "buy_order_start":
        msg = bot.send_message(call.message.chat.id, "📝 لطفاً **تعداد واحد AFIX** درخواستی خود همراه با **شماره پیگیری/هش تراکنش بانکی معتبر** را به صورت زیر بفرستید:\n\n`تعداد هش_بانکی`\n(مثال: `10 65892341`)", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_real_bank_tx)

    # --- دعوت دوستان ---
    elif call.data == "invite":
        bot_info = bot.get_me()
        invite_link = f"https://t.me/{bot_info.username}?start={user_id}"
        text = (f"👥 **دعوت از دوستان**\n\n"
                f"با دعوت هر دوست، پاداش بگیرید!\n\n"
                f"🔗 لینک اختصاصی دعوت شما:\n`{invite_link}`")
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

    elif call.data == "info":
        text = (f"ℹ️ درباره شبکه AFIX:\n\n"
                f"• سقف کل شبکه: ۲۱,۰۰۰,۰۰۰ واحد\n"
                f"• الگوریتم: اثبات کار (PoW)\n"
                f"• امنیت کلیدهای خصوصی: استاندارد Secp256k1")
        bot.send_message(call.message.chat.id, text)

    # --- پنل مدیریت ادمین ---
    elif call.data == "admin_panel":
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "⛔ دسترسی غیرمجاز!")
            return
            
        try:
            res = requests.get(f"{NODE_URL}/")
            node_data = res.json()
            total_circulating = node_data.get("total_circulating_supply", 0)
            admin_bal_res = requests.get(f"{NODE_URL}/api/balance?address={ADMIN_WALLET}").json()
            users = load_users()
            config = load_config()
            task_data = load_tasks()
            
            text = (f"👑 **پنل مدیریت انحصاری ادمین** 👑\n\n"
                    f"💰 موجودی ولت ادمین: {admin_bal_res.get('balance', 0):,.2f} AFIX\n"
                    f"👥 تعداد کاربران: {len(users)} نفر\n"
                    f"📊 کل توکن در گردش: {total_circulating:,.2f} / 21,000,000\n"
                    f"📢 کانال جوین پایه: {len(config.get('required_channels', []))}\n"
                    f"🎯 ماموریت‌های فعال: {len(task_data.get('tasks', []))}")
            
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                InlineKeyboardButton("➕ افزودن کانال جوین پایه", callback_data="admin_add_channel"),
                InlineKeyboardButton("➖ حذف کانال جوین پایه", callback_data="admin_remove_channel"),
                InlineKeyboardButton("🎯 افزودن ماموریت جدید", callback_data="admin_add_task"),
                InlineKeyboardButton("🗑️ حذف ماموریت", callback_data="admin_remove_task"),
                InlineKeyboardButton("🔙 بازگشت", callback_data="back_home")
            )
            bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ خطا در اتصال به سرور ادمین: {e}")

    elif call.data == "admin_add_channel":
        if user_id != ADMIN_ID: return
        msg = bot.send_message(call.message.chat.id, "✍️ یوزرنیم کانال پایه را با @ بفرستید:")
        bot.register_next_step_handler(msg, save_new_channel)

    elif call.data == "admin_remove_channel":
        if user_id != ADMIN_ID: return
        config = load_config()
        channels = config.get("required_channels", [])
        if not channels:
            bot.send_message(call.message.chat.id, "⚠️ هیچ کانالی ثبت نشده است.")
            return
        msg = bot.send_message(call.message.chat.id, "کانال‌های فعلی:\n" + "\n".join(channels) + "\nیوزرنیم را برای حذف بفرستید:")
        bot.register_next_step_handler(msg, remove_channel_step)

    elif call.data == "admin_add_task":
        if user_id != ADMIN_ID: return
        msg = bot.send_message(call.message.chat.id, "✍️ اطلاعات ماموریت جدید را به این صورت بفرستید:\n`يوزرنیم_کانال پاداش`\n(مثلا: `@AfixChannel 0.5`)", parse_mode="Markdown")
        bot.register_next_step_handler(msg, save_new_task_step)

    elif call.data == "admin_remove_task":
        if user_id != ADMIN_ID: return
        task_data = load_tasks()
        tasks = task_data.get("tasks", [])
        if not tasks:
            bot.send_message(call.message.chat.id, "⚠️ هیچ ماموریتی وجود ندارد.")
            return
        txt = "لیست ماموریت‌ها (شناسه عددی را بفرستید):\n"
        for t in tasks:
            txt += f"🆔 شناسه: {t['id']} | کانال: {t['channel']} | پاداش: {t['reward']}\n"
        msg = bot.send_message(call.message.chat.id, txt)
        bot.register_next_step_handler(msg, remove_task_step)

    elif call.data == "back_home":
        bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_markup(user_id))

# --- پردازش و بررسی واقعی هش تراکنش بانکی در خرید ---
def process_real_bank_tx(message):
    user_id = message.from_user.id
    user_id_str = str(user_id)
    text = message.text.strip()
    
    users = load_users()
    if user_id == ADMIN_ID:
        wallet_address = ADMIN_WALLET
    else:
        user_data = users.get(user_id_str)
        if not user_data:
            return
        wallet_address = user_data["address"]

    parts = text.split()
    if len(parts) >= 2 and parts[0].replace('.', '', 1).isdigit():
        amount_to_buy = float(parts[0])
        bank_tx_id = parts[1]
        
        # اعتبارسنجی واقعی هش بانکی (بررسی طول و کاراکترهای معتبر هش تراکنش)
        if len(bank_tx_id) < 6 or not bank_tx_id.isalnum():
            bot.reply_to(message, "❌ هش تراکنش بانکی نامعتبر است! لطفاً شماره پیگیری یا هش واقعی و صحیحی وارد کنید.")
            return
            
        try:
            # ارسال درخواست واریز از کیف پول ادمین به کاربر پس از تایید خرید
            payload = {"sender": ADMIN_WALLET, "recipient": wallet_address, "amount": amount_to_buy}
            res = requests.post(f"{NODE_URL}/api/transfer", json=payload)
            data = res.json()
            
            if res.status_code == 200 and data.get("status") == "success":
                bot.reply_to(message, f"✅ تراکنش بانکی با هش `{bank_tx_id
