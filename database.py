import sqlite3

def init_db():
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    # User Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, upi_id TEXT)''')
    # IPL/PSL Bets (Manual Settlement)
    cursor.execute('''CREATE TABLE IF NOT EXISTS real_bets 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
                       amount REAL, match_name TEXT, team TEXT, is_settled INTEGER DEFAULT 0)''')
    # Virtual Arena Bets (Auto Settlement)
    cursor.execute('''CREATE TABLE IF NOT EXISTS virtual_bets 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
                       amount REAL, bet_type TEXT, target_ball INTEGER, is_settled INTEGER DEFAULT 0)''')
    # Winner Bets (Virtual)
    cursor.execute('''CREATE TABLE IF NOT EXISTS winner_bets 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
                       amount REAL, selected_team TEXT, is_settled INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 0

init_db()
