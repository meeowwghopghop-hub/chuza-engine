import sqlite3
import os
import pytz
import time
import random
import json
from datetime import datetime
from threading import Thread
from flask import Flask, render_template
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
IST = pytz.timezone('Asia/Kolkata')
BOT_TOKEN = "8735091687:AAHn5Grvzg0Lf2R799xwPtRRnzgA8O8WE4w"
ADMIN_IDS = [7978295530, 6987036375]
CHANNEL_ID = -1003869160392
MIN_DEPOSIT = 100
MIN_VIRTUAL_BET = 25

# --- FLASK SERVER ---
app = Flask(__name__)

@app.route('/')
def home(): return "Chuza090 Multi-League Bot is Live!"

@app.route('/virtual')
def virtual_arena():
    return render_template('index.html') # Ye wahi HTML file hai jo maine di thi

# --- DATABASE LOGIC ---
def init_db():
    conn = sqlite3.connect('ipl_wallet.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT, balance INTEGER DEFAULT 0)')
    cursor.execute('''CREATE TABLE IF NOT EXISTS virtual_bets (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user_id INTEGER, 
        bet_amount INTEGER, 
        prediction TEXT, 
        target_ball_idx INTEGER, 
        status TEXT DEFAULT 'pending'
    )''')
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect('ipl_wallet.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 0

def update_balance(user_id, amount):
    conn = sqlite3.connect('ipl_wallet.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, name, balance) VALUES (?, 'User', 0)", (user_id,))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# --- VIRTUAL SETTLEMENT ENGINE ---
# Ye background mein chalta rahega
current_match_ball = 0
last_result = "STARTING"

def auto_settle_engine():
    global current_match_ball, last_result
    results_pool = ['runs_0', 'runs_1', 'runs_2', 'runs_4', 'runs_6', 'W-BOWLED']
    
    while True:
        time.sleep(25) # 25 second ka cycle
        current_match_ball += 1
        last_result = random.choice(results_pool)
        
        conn = sqlite3.connect('ipl_wallet.db')
        cursor = conn.cursor()
        
        # Settle Bets
        cursor.execute("SELECT id, user_id, bet_amount, prediction FROM virtual_bets WHERE target_ball_idx = ? AND status = 'pending'", (current_match_ball,))
        bets = cursor.fetchall()
        
        for bid, uid, amt, pred in bets:
            if pred == last_result:
                # Odds Logic (4 pe 4x, 6 pe 6x, baaki pe 2x)
                multiplier = 6 if '6' in pred else (4 if '4' in pred else 2)
                win_amt = amt * multiplier
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (win_amt, uid))
                cursor.execute("UPDATE virtual_bets SET status = 'WON' WHERE id = ?", (bid,))
            else:
                cursor.execute("UPDATE virtual_bets SET status = 'LOST' WHERE id = ?", (bid,))
        
        conn.commit()
        conn.close()

# --- BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    # Yahan Render ka URL daalna hai deploy karne ke baad
    web_url = "https://your-app-name.onrender.com/virtual" 
    
    keyboard = [
        [InlineKeyboardButton("🎰 VIRTUAL ARENA (NEW)", web_app=WebAppInfo(url=web_url))],
        [InlineKeyboardButton("💰 Deposit", callback_data='D'), InlineKeyboardButton("🏦 Withdraw", callback_data='W')],
        [InlineKeyboardButton("💳 Balance", callback_data='AB'), InlineKeyboardButton("🎲 Bet Official", callback_data='BET_SECTION')]
    ]
    await update.message.reply_text(f"🏆 *Chuza090 MULTI-LEAGUE BOOK*\nMin Deposit: ₹{MIN_DEPOSIT}\nVirtual Min Bet: ₹{MIN_VIRTUAL_BET}", 
                                   reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# --- WEBAPP DATA RECEIVER ---
async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = json.loads(update.effective_message.web_app_data.data)
    user_id = update.effective_user.id
    
    if data.get("action") == "place_virtual_bet":
        amt = data['amount']
        pred = data['type']
        bal = get_balance(user_id)
        
        if bal >= amt:
            update_balance(user_id, -amt)
            conn = sqlite3.connect('ipl_wallet.db')
            cursor = conn.cursor()
            # Bet hamesha next se next ball par lagegi (Safety)
            target = current_match_ball + 2 
            cursor.execute("INSERT INTO virtual_bets (user_id, bet_amount, prediction, target_ball_idx) VALUES (?,?,?,?)",
                           (user_id, amt, pred, target))
            conn.commit()
            conn.close()
            await update.effective_user.send_message(f"✅ Bet Placed: {pred} for Ball #{target}")

# --- WEB SERVER THREAD ---
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    init_db()
    Thread(target=run_flask).start()
    Thread(target=auto_settle_engine).start()
    
    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    # Yahan apne purane button_click aur handle_message handlers add kar lena
    bot_app.run_polling()