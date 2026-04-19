import os
import sqlite3
import random
import threading
import pytz
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import telebot
from telebot import types

# --- CONFIG ---
TOKEN = "8735091687:AAErETdqEJidXCpeqFLZ51DVqVZxb0fDbRg"
ADMIN_ID = 7978295530
IST = pytz.timezone('Asia/Kolkata')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('ipl_wallet.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)')
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect('ipl_wallet.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 0

def update_balance(user_id, amount):
    conn = sqlite3.connect('ipl_wallet.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# --- VIRTUAL MATCH INFO ---
def get_v_info():
    now = datetime.now(IST)
    slots = [1, 4, 7, 10, 13, 16, 19, 22] 
    next_h = next((s for s in slots if s > now.hour or (s == now.hour and now.minute < 15)), slots[0])
    teams = ["Lions", "Tigers", "Kings", "Warriors", "Titans"]
    t1, t2 = random.sample(teams, 2)
    return {"t1": t1, "t2": t2, "time": f"{next_h}:15"}

# --- BOT HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    init_db()
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("💰 Deposit", callback_data='D'),
               types.InlineKeyboardButton("🏦 Withdraw", callback_data='W'),
               types.InlineKeyboardButton("💳 Balance", callback_data='AB'),
               types.InlineKeyboardButton("🎲 Bet Section", callback_data='BET_SECTION'))
    bot.send_message(message.chat.id, "🏆 **Chuza090 MULTI-LEAGUE BOOK**\n\nChoose an option:", reply_markup=markup, parse_mode='Markdown')

# --- YAHAN FIX KIYA HAI (ALL CALLBACKS) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.from_user.id
    
    if call.data == 'BET_SECTION':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🏏 IPL/PSL Matches", callback_data='IPL_PSL'))
        markup.add(types.InlineKeyboardButton("🎮 VIRTUAL ARENA (24/7)", callback_data='V_ARENA'))
        bot.edit_message_text("🎯 **Select League:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

    elif call.data == 'V_ARENA':
        info = get_v_info()
        url = f"https://chuza-engine-1.onrender.com?user_id={uid}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🏟️ ENTER ARENA", web_app=types.WebAppInfo(url)))
        bot.send_message(call.message.chat.id, f"🎮 **VIRTUAL MATCH**\n{info['t1']} vs {info['t2']}\n🕒 Next: {info['time']}", reply_markup=markup, parse_mode='Markdown')

    elif call.data == 'IPL_PSL':
        bot.send_message(call.message.chat.id, "🏏 **IPL/PSL TODAY**\n\nNo matches live right now. Next match at 7:30 PM.")

    elif call.data == 'AB':
        bal = get_balance(uid)
        bot.answer_callback_query(call.id, f"💰 Balance: ₹{bal}", show_alert=True)

    elif call.data == 'D':
        msg = bot.send_message(call.message.chat.id, "💰 Kitna amount deposit karna hai?")
        bot.register_next_step_handler(msg, send_to_admin)

    elif call.data == 'W':
        msg = bot.send_message(call.message.chat.id, "🏦 Kitna amount withdraw karna hai? (Min: 100)")
        bot.register_next_step_handler(msg, process_withdraw)

# --- DEPOSIT/WITHDRAW LOGIC ---
def send_to_admin(message):
    if not message.text.isdigit(): return bot.send_message(message.chat.id, "❌ Sirf number likho.")
    bot.send_message(ADMIN_ID, f"💵 **DEP REQ**\nUser: {message.from_user.first_name}\nID: `{message.from_user.id}`\nAmt: {message.text}\n\nIspe reply karke **QR** bhejo.")
    bot.send_message(message.chat.id, "✅ Request sent! Admin QR bhej raha hai, wait karo.")

def process_withdraw(message):
    try:
        amt = int(message.text)
        if amt < 100: return bot.send_message(message.chat.id, "❌ Min withdrawal ₹100.")
        if amt > get_balance(message.from_user.id): return bot.send_message(message.chat.id, "❌ Balance kam hai.")
        msg = bot.send_message(message.chat.id, "Ab apni **UPI ID** bhejein:")
        bot.register_next_step_handler(msg, lambda m: finalize_w(m, amt))
    except: bot.send_message(message.chat.id, "❌ Invalid amount.")

def finalize_w(message, amt):
    bot.send_message(ADMIN_ID, f"🏦 **WITHDRAWAL REQUEST**\nID: `{message.from_user.id}`\nAmt: ₹{amt}\nUPI: `{message.text}`")
    bot.send_message(message.chat.id, "✅ Request Admin ko bhej di gayi hai.")

# --- ADMIN REPLY & SS HANDLING ---
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.reply_to_message is not None, content_types=['text', 'photo'])
def admin_reply(message):
    try:
        orig = message.reply_to_message.text
        target_id = int(orig.split("ID: ")[1].split("\n")[0])
        if message.text and (message.text.startswith('+') or message.text.startswith('-')):
            update_balance(target_id, int(message.text))
            bot.send_message(target_id, f"✅ Wallet Update: ₹{get_balance(target_id)}")
            bot.reply_to(message, "Done!")
        elif message.content_type == 'photo':
            bot.send_photo(target_id, message.photo[-1].file_id, caption="QR mil gaya. Pay karke SS reply karo.")
        else: bot.send_message(target_id, f"Admin: {message.text}")
    except: bot.reply_to(message, "Error processing reply.")

@bot.message_handler(content_types=['photo', 'text'])
def forward_to_admin(message):
    if message.from_user.id != ADMIN_ID:
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        bot.send_message(ADMIN_ID, f"📩 **MSG FROM ID: `{message.from_user.id}`**")

# --- FLASK ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/get_user_data')
def get_user_data():
    uid = request.args.get('user_id')
    return jsonify({"balance": get_balance(int(uid)) if uid else 0})

@app.route('/place_virtual_bet', methods=['POST'])
def v_bet():
    data = request.json
    uid, amt = int(data['user_id']), int(data['amount'])
    if get_balance(uid) >= amt:
        update_balance(uid, -amt)
        return jsonify({"status": "success", "new_balance": get_balance(uid)})
    return jsonify({"status": "error", "message": "Low Balance!"})

if __name__ == '__main__':
    init_db()
    threading.Thread(target=lambda: bot.infinity_polling(timeout=20)).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
