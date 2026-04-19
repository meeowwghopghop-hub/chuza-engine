import sqlite3
import os
import pytz 
import random
import time
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask, jsonify, render_template, request
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIG ---
IST = pytz.timezone('Asia/Kolkata')
BOT_TOKEN = "8735091687:AAErETdqEJidXCpeqFLZ51DVqVZxb0fDbRg"
ADMIN_IDS = [7978295530]
CHANNEL_ID = -1003869160392
MIN_DEPOSIT = 100

# --- FLASK SERVER ---
web_app = Flask(__name__)

# Virtual Match Logic (Based on 3-hour intervals: 1:15, 4:15, 7:15...)
def get_next_match_info():
    now = datetime.now(IST)
    # Match slots: 1:15, 4:15, 7:15, 10:15, 13:15, 16:15, 19:15, 22:15
    slots = [1, 4, 7, 10, 13, 16, 19, 22]
    current_hour = now.hour
    
    # Find next slot
    next_slot = next((s for s in slots if s > current_hour or (s == current_hour and now.minute < 15)), slots[0])
    
    teams = ["Badmosh Bastards", "Suttebaz Sikandar", "Charsi Challengers", "Ganjedi Gladiators", "Lukkha Lions", "Velle Vikings"]
    t1, t2 = random.sample(teams, 2)
    
    return {"t1": t1, "t2": t2, "next_time": f"{next_slot}:15"}

@web_app.route('/')
def home():
    return render_template('index.html')

@web_app.route('/get_user_data')
def get_user_data():
    uid = request.args.get('user_id')
    if uid:
        conn = sqlite3.connect('ipl_wallet.db')
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (int(uid),))
        res = cursor.fetchone()
        conn.close()
        return jsonify({"balance": res[0] if res else 0})
    return jsonify({"balance": 0})

@web_app.route('/place_virtual_bet', methods=['POST'])
def virtual_bet_api():
    data = request.json
    uid, amt = int(data['user_id']), int(data['amount'])
    conn = sqlite3.connect('ipl_wallet.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (uid,))
    res = cursor.fetchone()
    if res and res[0] >= amt:
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amt, uid))
        conn.commit()
        new_bal = res[0] - amt
        conn.close()
        return jsonify({"status": "success", "new_balance": new_bal})
    conn.close()
    return jsonify({"status": "error", "message": "Low Balance!"})

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

# --- DATABASE LOGIC ---
def init_db():
    conn = sqlite3.connect('ipl_wallet.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT, balance INTEGER DEFAULT 0)')
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect('ipl_wallet.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 0

def update_balance(user_id, name, amount):
    conn = sqlite3.connect('ipl_wallet.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, name, balance) VALUES (?, ?, 0)", (user_id, name))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    keyboard = [
        [InlineKeyboardButton("💰 Deposit", callback_data='D'), InlineKeyboardButton("🏦 Withdraw", callback_data='W')],
        [InlineKeyboardButton("💳 Balance", callback_data='AB'), InlineKeyboardButton("🎲 Bet", callback_data='BET_SECTION')]
    ]
    await update.message.reply_text(f"🏆 *Chuza090 MULTI-LEAGUE*\nAdmin: @YourID", 
                                   reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == 'BET_SECTION':
        keyboard = [
            [InlineKeyboardButton("🏏 IPL/PSL Matches", callback_data='VIEW_LEAGUES')],
            [InlineKeyboardButton("🎮 VIRTUAL ARENA (24/7)", callback_data='VIEW_VIRTUAL')]
        ]
        await query.message.reply_text("Select Category:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'VIEW_VIRTUAL':
        info = get_next_match_info()
        # Passing user_id to Web App for balance sync
        web_app_url = f"https://{request.host_url.split('//')[1]}?user_id={user_id}" 
        keyboard = [[InlineKeyboardButton("🏟️ ENTER ARENA", web_app={"url": web_app_url})]]
        await query.message.reply_text(f"🎮 *VIRTUAL ARENA*\nNext Match: {info['t1']} vs {info['t2']}\nTime: {info['next_time']}", 
                                       reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif query.data == 'AB':
        await query.message.reply_text(f"💳 Balance: *₹{get_balance(user_id)}*", parse_mode='Markdown')
    # ... Rest of your D, W, M_ logic remains same ...

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Your existing SS and Admin +/- logic
    pass

def main():
    init_db()
    Thread(target=run_web).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()
