import sqlite3

def init_db():
    conn = sqlite3.connect('ipl_wallet.db')
    cursor = conn.cursor()
    # User Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                     (user_id INTEGER PRIMARY KEY, name TEXT, balance INTEGER DEFAULT 0)''')
    
    # Virtual Bets Table (Target_ball_idx se settlement track hoga)
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
    # Agar user naya hai toh insert karega, nahi toh update
    cursor.execute("INSERT OR IGNORE INTO users (user_id, name, balance) VALUES (?, 'User', 0)", (user_id,))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()