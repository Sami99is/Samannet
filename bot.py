import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
import os
import secrets
import time

# --- تنظیمات اصلی ---
BOT_TOKEN = "8936504596:AAGdlz2_-QetRjYLRW8b8ln3jN7lvsATNDk"
NODE_URL = "https://affix-production-fdfd.up.railway.app"
ADMIN_ID = 8443938939
ADMIN_WALLET = "AFIX_GMN_f89637364a"
AFIX_PRICE_TOMAN = 300000

bot = telebot.TeleBot(BOT_TOKEN)
USERS_DB = "bot_users.json"
CONFIG_DB = "bot_config.json"
TASKS_DB = "bot_tasks.json" # دیتابیس برای مرکز ماموریت‌ها و وضعیت انجام توسط کاربران

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
    # ساختار: {"tasks": [{"id": 1, "channel": "@ChanName", "reward": 0.5}], "completed": {"user_id": [1, 2]}}
    return load_json(TASKS_DB, {"tasks": [], "completed": {}})

def save_tasks(tasks):
    save_json(TASKS_DB, tasks)

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
        InlineKeyboardButton("💰 کیف پول من", callback_data="balance"),
        InlineKeyboardButton("🎯 مرکز ماموریت‌ها (پاداش)", callback_data="task_center"),
        InlineKeyboardButton("💸 انتقال ارز", callback_data="transfer_menu"),
        InlineKeyboardButton("🛒 بخش خرید و فروش", callback_data="market"),
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
    
    if user_id_str not in users:
        if user_id == ADMIN_ID:
            users[user_id_str] = ADMIN_WALLET
        else:
            users[user_id_str] = f"AFIX_usr_{secrets.token_hex(8)}"
        save_users(users)
    
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
    else:
        wallet_address = users.get(user_id_str)
        if not wallet_address:
            wallet_address = f"AFIX_usr_{secrets.token_hex(8)}"
            users[user_id_str] = wallet_address
            save_users(users)

    # --- کیف پول ---
    if call.data == "balance":
        try:
            res = requests.get(f"{NODE_URL}/api/balance?address={wallet_address}")
            if res.status_code == 200:
                data = res.json()
                text = (f"📍 **آدرس کیف پول شما:**\n`{data['address']}`\n\n"
                        f"💰 **موجودی کل:** {data['balance']:,.2f} AFIX\n"
                        f"💵 **ارزش تقریبی:** {data['value_in_toman']:,.0f} تومان\n"
                        f"⚡ کارمزد شبکه: 0.01 AFIX")
                bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
            else:
                bot.send_message(call.message.chat.id, "❌ خطا در دریافت اطلاعات موجودی.")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ خطای ارتباط با سرور: {e}")

    # --- مرکز ماموریت‌ها (Task Center) ---
    elif call.data == "task_center":
        task_data = load_tasks()
        tasks = task_data.get("tasks", [])
        
        if not tasks:
            bot.send_message(call.message.chat.id, "🎯 **مرکز ماموریت‌ها**\n\nدر حال حاضر ماموریت فعالی وجود ندارد. لطفاً بعداً سر بزنید!", parse_mode="Markdown")
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
            bot.answer_callback_query(call.id, "❌ ماموریت مورد نظر یافت نشد.", show_alert=True)
            return
            
        completed_list = task_data.setdefault("completed", {}).setdefault(user_id_str, [])
        if t_id in completed_list:
            bot.answer_callback_query(call.id, "⚠️ شما قبلاً پاداش این ماموریت را دریافت کرده‌اید!", show_alert=True)
            return
            
        # بررسی عضویت کاربر در کانال ماموریت
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
            
        # واریز پاداش به کاربر از طریق سرور (افزایش موجودی با انتقال از ادمین یا API مخصوص)
        # فرض بر این است که پاداش را به ولت کاربر اضافه می‌کنیم
        try:
            # ارسال درخواست به سرور برای اضافه کردن پاداش (یا ثبت تراکنش)
            payload = {"from_address": ADMIN_WALLET, "to_address": wallet_address, "amount": reward}
            res = requests.post(f"{NODE_URL}/api/transfer", json=payload)
            
            # ثبت در لیست انجام‌شده‌ها
            completed_list.append(t_id)
            save_tasks(task_data)
            
            bot.answer_callback_query(call.id, f"🎉 تبریک! {reward} واحد AFIX به حساب شما واریز شد.", show_alert=True)
            # رفرش کردن مرکز ماموریت‌ها
            handle_query(call)
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ خطا در واریز پاداش: {e}", show_alert=True)

    # --- ماین ۲۴ ساعته ---
    elif call.data == "mine":
        try:
            chal_res = requests.get(f"{NODE_URL}/api/mine/challenge").json()
            timestamp = chal_res['timestamp']
            
            payload = {"address": wallet_address, "nonce": 12345, "timestamp": timestamp}
            res = requests.post(f"{NODE_URL}/api/mine/submit", json=payload)
            data = res.json()
            
            if res.status_code == 200 and "status" in data and data["status"] == "success":
                bot.send_message(call.message.chat.id, f"✅ استخراج موفقیت‌آمیز بود!\n💰 موجودی جدید شما: {data['balance']:,.2f} AFIX")
            else:
                err_msg = data.get("error", "هنوز زمان استخراج ۲۴ ساعته‌ی شما فرا نرسیده است.")
                bot.send_message(call.message.chat.id, f"⚠️ {err_msg}")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ خطا در عملیات استخراج: {e}")

    # --- انتقال ارز ---
    elif call.data == "transfer_menu":
        text = (f"💸 **بخش انتقال ارز AFIX**\n\n"
                f"• کارمزد شبکه: **0.01 AFIX**\n"
                f"برای انتقال توکن‌های خود، مقدار و آدرس مقصد را ارسال کنید.")
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

    # --- بخش خرید و فروش ---
    elif call.data == "market":
        text = (f"🛒 **بخش خرید و فروش AFIX**\n\n"
                f" نرخ هر ۱ واحد AFIX: **{AFIX_PRICE_TOMAN:,} تومان**\n\n"
                f"🔹 می‌توانید درخواست فروش موجودی خود را ثبت کنید تا معادل ریالی آن به کارت شما واریز شود.")
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💵 ثبت درخواست فروش و تسویه", callback_data="sell_request"))
        markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_home"))
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

    elif call.data == "sell_request":
        bot.send_message(call.message.chat.id, "📝 لطفاً تعداد واحد AFIX برای فروش و شماره کارت بانکی خود را ارسال کنید.")

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
                f"• کارمزد انتقال: ۰.۰۱ AFIX")
        bot.send_message(call.message.chat.id, text)

    # --- پنل مدیریت انحصاری ادمین ---
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
                    f"💰 موجودی ولت ادمین شما: {admin_bal_res.get('balance', 0):,.2f} AFIX\n"
                    f"👥 تعداد کاربران: {len(users)} نفر\n"
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
        txt = "لیست ماموریت‌ها (برای حذف، آیدی عددی ماموریت را بفرستید):\n"
        for t in tasks:
            txt += f"🆔 شناسه: {t['id']} | کانال: {t['channel']} | پاداش: {t['reward']}\n"
        msg = bot.send_message(call.message.chat.id, txt)
        bot.register_next_step_handler(msg, remove_task_step)

    elif call.data == "admin_broadcast":
        if user_id != ADMIN_ID: return
        bot.send_message(call.message.chat.id, "✍️ متن پیام همگانی خود را بفرستید:")

    elif call.data == "back_home":
        bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_markup(user_id))

# توابع کمکی ادمین برای کانال‌ها و ماموریت‌ها
def save_new_channel(message):
    if message.from_user.id != ADMIN_ID: return
    ch = message.text.strip()
    config = load_config()
    if ch not in config["required_channels"]:
        config["required_channels"].append(ch)
        save_config(config)
        bot.reply_to(message, f"✅ کانال پایه {ch} اضافه شد.")
    else:
        bot.reply_to(message, "⚠️ از قبل وجود داشت.")

def remove_channel_step(message):
    if message.from_user.id != ADMIN_ID: return
    ch = message.text.strip()
    config = load_config()
    if ch in config["required_channels"]:
        config["required_channels"].remove(ch)
        save_config(config)
        bot.reply_to(message, f"✅ حذف شد.")
    else:
        bot.reply_to(message, "❌ پیدا نشد.")

def save_new_task_step(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        parts = message.text.strip().split()
        ch = parts[0]
        reward = float(parts[1])
        
        task_data = load_tasks()
        tasks = task_data.setdefault("tasks", [])
        new_id = int(time.time()) # ساخت شناسه یکتا بر اساس زمان
        
        tasks.append({"id": new_id, "channel": ch, "reward": reward})
        save_tasks(task_data)
        bot.reply_to(message, f"✅ ماموریت جدید با موفقیت به مرکز پاداش اضافه شد!\nکانال: {ch}\nپاداش: {reward} AFIX")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا در فرمت ارسال. لطفاً به صورت `يوزرنیم پاداش` بفرستید.\nمثال: `@AfixChannel 0.5`")

def remove_task_step(message):
    if message.from_user.id != ADMIN_ID: return
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
    except:
        bot.reply_to(message, "❌ لطفاً فقط شناسه عددی ماموریت را بفرستید.")

if __name__ == "__main__":
    print("🤖 Professional Bot is running with Task Center & Admin Panel...")
    bot.polling(none_stop=True)
      
