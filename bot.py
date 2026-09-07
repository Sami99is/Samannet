import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# توکن ربات شما
TOKEN = "8936504596:AAGdlz2_-QetRjYLRW8b8ln3jN7lvsATNDk"
bot = telebot.TeleBot(TOKEN)

# لینک مینی‌اپ شما روی کلودفلر
WEB_APP_URL = "https://fuzzy-octo-barnacle.rnsryn659.workers.dev"
CHANNEL_URL = "https://t.me/AfixWallet"
ADMIN_ID = 8443938939

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = InlineKeyboardMarkup(row_width=1)
    
    btn_webapp = InlineKeyboardButton("🚀 ورود به مینی‌اپ AFIX", web_app=WebAppInfo(url=WEB_APP_URL))
    btn_channel = InlineKeyboardButton("📢 ورود به کانال رسمی", url=CHANNEL_URL)
    
    markup.add(btn_webapp, btn_channel)
    
    welcome_text = (
        f"سلام {message.from_user.first_name} عزیز! 🌟\n\n"
        "به ربات رسمی شبکه AFIX خوش آمدید.\n"
        "از طریق دکمه زیر می‌توانید وارد مینی‌اپ شده و استخراج توکن را شروع کنید:"
    )
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

if __name__ == '__main__':
    print("Bot is running...")
    bot.infinity_polling()
    
