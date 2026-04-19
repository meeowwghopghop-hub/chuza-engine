import os
import sqlite3
import random
import time
import threading
import pytz
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import telebot
from telebot import types

# --- CONFIG ---
TOKEN = "8735091687:AAErETdqEJidXCpeqFLZ51DVqVZxb0fDbRg"
ADMIN_ID = 7978295530
CHANNEL_ID = -1003869160392
IST = pytz.timezone('Asia/Kolkata')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('ipl_wallet.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT, balance INTEGER DEFAULT 0)')
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect('ipl_wallet.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 0

def update_balance(user_id, name, amount):
    conn = sqlite3.connect('ipl_wallet.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, name, balance) VALUES (?, ?, 0)", (user_id, name))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# --- VIRTUAL MATCH TIMING ---
def get_v_info():
    now = datetime.now(IST)
    slots = [1, 4, 7, 10, 13, 16, 19, 22] # Matches at 1:15, 4:15, etc.
    next_h = next((s for s in slots if s > now.hour or (s == now.hour and now.minute < 15)), slots[0])
    teams = ["Badmosh Bastards", "Suttebaz Sikandar", "Charsi Challengers", "Ganjedi Gladiators", "Lukkha Lions"]
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
    bot.send_message(message.chat.id, "🏆 *Chuza090 MULTI-LEAGUE BOOK*\nBhai, niche buttons use kar.", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    uid = call.from_user.id
    if call.data == 'BET_SECTION':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🏏 IPL/PSL Matches", callback_data='IPL_PSL'))
        markup.add(types.InlineKeyboardButton("🎮 VIRTUAL ARENA (24/7)", callback_data='V_ARENA'))
        bot.edit_message_text("Select Category:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif call.data == 'V_ARENA':
        info = get_v_info()
        # Render URL sync
        url = f"https://{request.host.split(':')[0]}?user_id={uid}" if request.host else f"https://chuza-engine-1.onrender.com?user_id={uid}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🏟️ ENTER ARENA", web_app=types.WebAppInfo(url)))
        bot.send_message(call.message.chat.id, f"🎮 *VIRTUAL MATCH*\n{info['t1']} vs {info['t2']}\n🕒 Time: {info['time']}", reply_markup=markup, parse_mode='Markdown')

    elif call.data == 'AB':
        bot.answer_callback_query(call.id, f"Current Balance: ₹{get_balance(uid)}", show_alert=True)
    
    elif call.data == 'D':
        msg = bot.send_message(call.message.chat.id, "Kitna deposit karna hai? (Min: 100)")
        bot.register_next_step_handler(msg, lambda m: bot.send_message(m.chat.id, "Ab Payment ka Screenshot bhejo!"))

# --- FLASK ROUTES (FOR BALANCE SYNC) ---
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
        update_balance(uid, "User", -amt)
        return jsonify({"status": "success", "new_balance": get_balance(uid)})
    return jsonify({"status": "error", "message": "Low Balance!"})

# --- RUNNER ---
def run_bot():
    bot.remove_webhook()
    bot.infinity_polling()

if __name__ == '__main__':
    init_db()
    threading.Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
