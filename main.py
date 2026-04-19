import os
import sqlite3
import threading
from flask import Flask, render_template, request, jsonify
import telebot
from telebot import types

# --- CONFIG ---
TOKEN = "8735091687:AAErETdqEJidXCpeqFLZ51DVqVZxb0fDbRg"
ADMIN_ID = 7978295530
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('ipl_wallet.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT, balance INTEGER DEFAULT 0)')
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect('ipl_wallet.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# --- BOT LOGIC ---

@bot.message_handler(commands=['start'])
def start(message):
    init_db()
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💰 Deposit", callback_data='D'))
    bot.send_message(message.chat.id, "🏆 **Chuza090 Bot**\nNiche deposit par click karo.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'D')
def deposit_init(call):
    msg = bot.send_message(call.message.chat.id, "💰 Kitna amount deposit karna hai?")
    bot.register_next_step_handler(msg, send_req_to_admin)

# 1. User ka amount Admin ko bhejna
def send_req_to_admin(message):
    amt = message.text
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Admin ko msg jayega jisme ID chupi hogi
    bot.send_message(ADMIN_ID, f"💵 **DEP REQ**\nUser: {user_name}\nID: `{user_id}`\nAmt: {amt}\n\nIspe reply karke **QR Photo** ya **UPI** bhejo.")
    bot.send_message(message.chat.id, "✅ Request bhej di hai. Admin abhi aapko QR bhejega, wait karo.")

# 2. Admin jab Reply kare (QR bhejne ke liye)
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.reply_to_message is not None)
def admin_reply_logic(message):
    try:
        # Reply wale msg se User ID nikalna
        orig_text = message.reply_to_message.text
        target_id = int(orig_text.split("ID: ")[1].split("\n")[0])

        # Agar admin +100 likhe toh balance update
        if message.text and (message.text.startswith('+') or message.text.startswith('-')):
            amt = int(message.text)
            update_balance(target_id, amt)
            bot.send_message(target_id, f"✅ Wallet Updated! New Balance add ho gaya hai.")
            bot.reply_to(message, "Balance Update Ho gaya!")
            return

        # Agar admin Photo ya UPI bhej raha hai toh user ko forward karna
        if message.content_type == 'photo':
            bot.send_photo(target_id, message.photo[-1].file_id, caption="Ye raha QR. Pay karke SS isi message par reply karein.")
        else:
            bot.send_message(target_id, f"Admin Message: {message.text}\n\nIspar reply karke SS bhejein.")
            
        bot.reply_to(message, "Message User ko bhej diya gaya hai. ✅")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

# 3. User jab QR wale message par SS reply kare
@bot.message_handler(content_types=['photo', 'text'])
def user_replies(message):
    # Agar ye normal message hai aur admin ko reply jaana chahiye
    if message.from_user.id != ADMIN_ID:
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        bot.send_message(ADMIN_ID, f"📩 **USER RESPONSE**\nID: `{message.from_user.id}`\nUpar wala message check karo.")

# --- FLASK ---
@app.route('/')
def index(): return "Bot is Running"

if __name__ == '__main__':
    init_db()
    threading.Thread(target=lambda: bot.infinity_polling()).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
