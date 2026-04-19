import random
import time
import threading
from flask import Flask, render_template, request, jsonify
from telebot import TeleBot, types
import database

app = Flask(__name__)
bot = TeleBot("8735091687:AAH9JRYZctl-E6L_Y28fSTedwAHnvH9N0Us") 
ADMIN_ID = 7978295530 # <--- Apni ID
CHANNEL_ID = -1003869160392 # <--- Apni Channel ID yahan daal (Without quotes agar number hai)

# --- VIRTUAL ARENA DATA ---
v_match = {"t1": "", "t2": "", "s1": 0, "w1": 0, "s2": 0, "w2": 0, "ball": 0, "live": False, "start": 0}

def start_virtual_cycle():
    global v_match
    teams = ["Badmosh Bastards", "Suttebaz Sikandar", "Charsi Challengers", "Ganjedi Gladiators", "Lukkha Lions", "Velle Vikings", "Tharki Tigers", "Bewda Blasters", "Nasheri Nawabs", "Chapri Champions"]
    t1, t2 = random.sample(teams, 2)
    v_match.update({"t1": t1, "t2": t2, "s1": 0, "w1": 0, "s2": 0, "w2": 0, "ball": 0, "live": True, "start": time.time()})

# --- BOT COMMANDS ---

@bot.message_handler(commands=['start'])
def welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🏏 IPL 2026", "🏆 PSL 2026")
    markup.add("🎮 VIRTUAL ARENA (24/7)", "💰 Wallet")
    bot.send_message(message.chat.id, "🔥 CHUZA090 Betting Bot is Active!", reply_markup=markup)

# Admin command to add balance: /add [user_id] [amount]
@bot.message_handler(commands=['add'])
def add_balance(message):
    if message.from_user.id == ADMIN_ID:
        try:
            parts = message.text.split()
            uid, amt = int(parts[1]), float(parts[2])
            database.update_balance(uid, amt)
            bot.send_message(uid, f"💰 ₹{amt} added to your wallet! Good luck.")
            bot.reply_to(message, "Done! Balance updated.")
        except:
            bot.reply_to(message, "Usage: /add 12345678 500")

# Channel Posting
@bot.message_handler(commands=['post'])
def post_channel(message):
    if message.from_user.id == ADMIN_ID:
        text = message.text.replace('/post ', '')
        bot.send_message(CHANNEL_ID, f"📢 **NEW UPDATE:**\n\n{text}")
        bot.reply_to(message, "Channel par post ho gaya! ✅")

@bot.message_handler(content_types=['photo'])
def handle_ss(message):
    bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
    bot.reply_to(message, "Screenshot forwarded. Admin is verifying... ⏳")

@bot.message_handler(func=lambda m: m.text == "🎮 VIRTUAL ARENA (24/7)")
def arena(message):
    web_app = types.WebAppInfo("https://your-app-name.onrender.com") # <--- APNA URL
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🏟️ PLAY NOW", web_app=web_app))
    bot.send_message(message.chat.id, f"🎮 Virtual Match: {v_match['t1']} vs {v_match['t2']}", reply_markup=markup)

# --- FLASK ---
@app.route('/')
def home(): return render_template('index.html')

@app.route('/get_status')
def status():
    global v_match
    elapsed = int(time.time() - v_match['start'])
    v_match['ball'] = (elapsed // 25) + 1
    if v_match['ball'] > 24: start_virtual_cycle()
    return jsonify(v_match)

@app.route('/place_bet', methods=['POST'])
def vbet():
    data = request.json
    uid, amt = data['user_id'], data['amount']
    target = v_match['ball'] + 3
    if target > 24: return jsonify({"status":"error", "msg":"Market Closed!"})
    if database.get_balance(uid) < amt: return jsonify({"status":"error", "msg":"Low Balance"})
    database.update_balance(uid, -amt)
    return jsonify({"status":"success", "msg":f"Bet set for Ball #{target}"})

def run_f(): app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    setup_virtual_match()
    
    import threading
    # Bot ko start karne ka function
    def start_bot():
        print("Starting Bot Polling...")
        bot.remove_webhook() # Purane fanse hue connections clear karega
        bot.infinity_polling(timeout=20, long_polling_timeout=10)

    # Threading setup
    thread = threading.Thread(target=start_bot)
    thread.daemon = True
    thread.start()

    # Render ka port handle karne ke liye
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
