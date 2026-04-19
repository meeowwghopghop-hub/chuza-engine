import os
import random
import time
import threading
from flask import Flask, render_template, request, jsonify
from telebot import TeleBot, types
import database

# --- CONFIGURATION ---
TOKEN = "8735091687:AAH9JRYZctl-E6L_Y28fSTedwAHnvH9N0Us"
bot = TeleBot(TOKEN)
app = Flask(__name__)

# --- SETTINGS (Inhe Update Karlo) ---
ADMIN_ID = 7978295530  # <--- Apni Telegram Numeric ID daal
CHANNEL_ID = -1003869160392  # <--- Apni Channel ID daal (-100 se shuru hone wali)

# Database Initialize
database.init_db()

# --- VIRTUAL ARENA ENGINE ---
v_match = {
    "t1": "Badmosh Bastards", "t2": "Suttebaz Sikandar", 
    "s1": 0, "w1": 0, "s2": 0, "w2": 0, 
    "ball": 0, "live": False, "start": time.time()
}

def start_virtual_cycle():
    global v_match
    teams = ["Badmosh Bastards", "Suttebaz Sikandar", "Charsi Challengers", "Ganjedi Gladiators", 
             "Lukkha Lions", "Velle Vikings", "Tharki Tigers", "Bewda Blasters", "Nasheri Nawabs", "Chapri Champions"]
    t1, t2 = random.sample(teams, 2)
    v_match.update({
        "t1": t1, "t2": t2, "s1": 0, "w1": 0, "s2": 0, "w2": 0, 
        "ball": 0, "live": True, "start": time.time()
    })

# --- TELEGRAM BOT HANDLERS ---

@bot.message_handler(commands=['start'])
def welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🏏 IPL 2026", "🏆 PSL 2026")
    markup.add("🎮 VIRTUAL ARENA (24/7)", "💰 Wallet")
    bot.reply_to(message, "🔥 **CHUZA090 ENGINE LIVE!**\n\nBhai, betting chalu hai. Paisa kamao aur maze karo!", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💰 Wallet")
def check_wallet(message):
    bal = database.get_balance(message.from_user.id)
    bot.send_message(message.chat.id, f"💳 **Your Balance:** ₹{bal}\n\nDeposit karne ke liye QR par payment bhejein aur screenshot yahan upload karein.")

@bot.message_handler(func=lambda m: m.text == "🎮 VIRTUAL ARENA (24/7)")
def arena(message):
    # Render URL update karna yahan
    web_app_url = "https://chuza-engine-1.onrender.com" 
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🏟️ ENTER ARENA", web_app=types.WebAppInfo(web_app_url)))
    bot.send_message(message.chat.id, f"🎮 **Virtual Match:** {v_match['t1']} vs {v_match['t2']}\nEvery 25 seconds new ball!", reply_markup=markup)

@bot.message_handler(commands=['post'])
def admin_post(message):
    if message.from_user.id == ADMIN_ID:
        msg_text = message.text.replace('/post ', '')
        bot.send_message(CHANNEL_ID, f"📢 **OFFICIAL UPDATE:**\n\n{msg_text}")
        bot.reply_to(message, "Channel par post kar diya! ✅")

@bot.message_handler(commands=['add'])
def admin_add_bal(message):
    if message.from_user.id == ADMIN_ID:
        try:
            parts = message.text.split()
            target_id, amount = int(parts[1]), float(parts[2])
            database.update_balance(target_id, amount)
            bot.send_message(target_id, f"✅ ₹{amount} added to your wallet!")
            bot.reply_to(message, "Balance Updated!")
        except Exception as e:
            bot.reply_to(message, "Format: /add [user_id] [amount]")

@bot.message_handler(content_types=['photo'])
def forward_payment(message):
    bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
    bot.reply_to(message, "Screenshot forwarded to Admin for verification. ⏳")

# --- FLASK ROUTES (WEB APP) ---

@app.route('/')
def home():
    return "<h1>Chuza090 Engine is Running!</h1>"

@app.route('/get_status')
def get_status():
    global v_match
    elapsed = int(time.time() - v_match['start'])
    v_match['ball'] = (elapsed // 25) + 1
    if v_match['ball'] > 24:
        start_virtual_cycle()
    return jsonify(v_match)

@app.route('/place_bet', methods=['POST'])
def virtual_bet():
    data = request.json
    uid, amt = data['user_id'], data['amount']
    target = v_match['ball'] + 3
    
    if target > 24:
        return jsonify({"status": "error", "msg": "Match ending, market closed!"})
    
    current_bal = database.get_balance(uid)
    if current_bal < amt:
        return jsonify({"status": "error", "msg": "Insufficient Balance!"})
    
    database.update_balance(uid, -amt)
    # Settlement logic will happen after 3 balls
    return jsonify({"status": "success", "msg": f"✅ Bet Fixed for Ball #{target}"})

# --- MULTI-THREADING STARTER ---

def run_bot():
    print("Core: Starting Bot Polling...")
    bot.remove_webhook()
    bot.infinity_polling(timeout=20, long_polling_timeout=10)

if __name__ == '__main__':
    start_virtual_cycle()
    
    # Start Bot in background
    t = threading.Thread(target=run_bot)
    t.daemon = True
    t.start()
    
    # Start Flask in foreground (Render needs this)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
