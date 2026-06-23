import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import random
import time
import threading
import hashlib
import datetime
import sqlite3
import re
import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

# ==================== تنظیمات اولیه ====================
BOT_TOKEN = '8647710024:AAFjd7WDcVpF0Rpk1iuP-iw1K2MPRiNYjPQ'
bot = telebot.TeleBot(BOT_TOKEN)
BOT_USERNAME = 'lotto_ir_bot'
MAIN_ADMIN_ID = '7281938958'

# ==================== دیتابیس ====================
DB_PATH = "./lotto_bot.db"

def get_db():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    else:
        return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    if DATABASE_URL:
        # ===== PostgreSQL (برای Supabase) =====
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                wallet BIGINT DEFAULT 0,
                total_earnings BIGINT DEFAULT 0,
                xp BIGINT DEFAULT 0,
                level INTEGER DEFAULT 1,
                games INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS invites (
                user_id TEXT PRIMARY KEY,
                code TEXT UNIQUE,
                invited_count INTEGER DEFAULT 0,
                rewarded INTEGER DEFAULT 0
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS invited_users (
                inviter_id TEXT,
                invited_id TEXT,
                PRIMARY KEY (inviter_id, invited_id)
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id TEXT PRIMARY KEY,
                nickname TEXT,
                can_add_admin INTEGER DEFAULT 0,
                can_remove_admin INTEGER DEFAULT 0,
                can_set_access INTEGER DEFAULT 0,
                can_reset_bot INTEGER DEFAULT 0,
                can_gift_cash INTEGER DEFAULT 0,
                can_deposit_user INTEGER DEFAULT 0,
                can_view_requests INTEGER DEFAULT 1,
                can_change_shift INTEGER DEFAULT 1
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS shift_stats (
                id SERIAL PRIMARY KEY,
                admin_id TEXT,
                nickname TEXT,
                start_time REAL,
                deposits BIGINT DEFAULT 0,
                withdrawals BIGINT DEFAULT 0,
                profits BIGINT DEFAULT 0
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS pending_deposits (
                request_id TEXT PRIMARY KEY,
                user_id TEXT,
                user_name TEXT,
                amount INTEGER,
                message_id INTEGER,
                photo_id TEXT
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS pending_withdrawals (
                request_id TEXT PRIMARY KEY,
                user_id TEXT,
                user_name TEXT,
                amount INTEGER,
                card_number TEXT,
                full_name TEXT
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS admin_earnings (
                id SERIAL PRIMARY KEY,
                date TEXT,
                amount INTEGER,
                withdrawn INTEGER DEFAULT 0
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                user_id TEXT,
                user_name TEXT,
                message TEXT,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS active_games (
                game_id TEXT PRIMARY KEY,
                data TEXT
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS level_rewards (
                level INTEGER PRIMARY KEY,
                title TEXT,
                xp_needed INTEGER,
                reward INTEGER
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS welcome_bonus (
                user_id TEXT PRIMARY KEY,
                received INTEGER DEFAULT 0,
                join_order INTEGER
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS bonus_stats (
                key TEXT PRIMARY KEY,
                value INTEGER DEFAULT 0
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # ===== اطلاعات اولیه =====
        c.execute("INSERT INTO bonus_stats (key, value) VALUES ('total_bonus_given', 0) ON CONFLICT (key) DO NOTHING")
        
        levels = [
            (1, "🌱 تازه‌کار", 0, 0),
            (2, "🌟 ستاره نوظهور", 100, 5000),
            (3, "⚡ جنگجوی بازار", 250, 10000),
            (4, "🎯 تیرانداز دقیق", 500, 20000),
            (5, "🏅 برنزی", 800, 35000),
            (6, "🥈 نقره‌ای", 1200, 50000),
            (7, "🥇 طلایی", 1700, 75000),
            (8, "💎 پلاتینیوم", 2300, 100000),
            (9, "👑 سلطان بازار", 3000, 150000),
            (10, "🌈 افسانه‌ای", 4000, 200000)
        ]
        for lvl in levels:
            c.execute('INSERT INTO level_rewards (level, title, xp_needed, reward) VALUES (%s,%s,%s,%s) ON CONFLICT (level) DO NOTHING', lvl)
        
        c.execute("INSERT INTO bot_settings (key, value) VALUES ('bot_enabled', 'true') ON CONFLICT (key) DO NOTHING")
        c.execute("INSERT INTO bot_settings (key, value) VALUES ('bot_win_rate', '30') ON CONFLICT (key) DO NOTHING")
        c.execute("INSERT INTO bot_settings (key, value) VALUES ('bot_timeout', '30') ON CONFLICT (key) DO NOTHING")
        c.execute("INSERT INTO bot_settings (key, value) VALUES ('max_bots', '5') ON CONFLICT (key) DO NOTHING")
        
        c.execute('''
            INSERT INTO admins (user_id, nickname, can_add_admin, can_remove_admin, can_set_access, can_reset_bot, can_gift_cash, can_deposit_user)
            VALUES (%s, %s, 1, 1, 1, 1, 1, 1) ON CONFLICT (user_id) DO NOTHING
        ''', (MAIN_ADMIN_ID, '🧙‍♂️ مدیر ارشد 🧙‍♂️'))
        
        c.execute("INSERT INTO settings (key, value) VALUES ('current_card', '6219861075600832') ON CONFLICT (key) DO NOTHING")
        
        c.execute("SELECT COUNT(*) FROM shift_stats")
        if c.fetchone()[0] == 0:
            c.execute('INSERT INTO shift_stats (admin_id, nickname, start_time, deposits, withdrawals, profits) VALUES (%s, %s, %s, 0, 0, 0)', 
                      (MAIN_ADMIN_ID, '🧙‍♂️ مدیر ارشد 🧙‍♂️', time.time()))
    
    else:
        # ===== SQLite (برای تست محلی) =====
        c.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, name TEXT, wallet INTEGER DEFAULT 0, total_earnings INTEGER DEFAULT 0, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1, games INTEGER DEFAULT 0, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS invites (user_id TEXT PRIMARY KEY, code TEXT UNIQUE, invited_count INTEGER DEFAULT 0, rewarded INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS invited_users (inviter_id TEXT, invited_id TEXT, PRIMARY KEY (inviter_id, invited_id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS admins (user_id TEXT PRIMARY KEY, nickname TEXT, can_add_admin INTEGER DEFAULT 0, can_remove_admin INTEGER DEFAULT 0, can_set_access INTEGER DEFAULT 0, can_reset_bot INTEGER DEFAULT 0, can_gift_cash INTEGER DEFAULT 0, can_deposit_user INTEGER DEFAULT 0, can_view_requests INTEGER DEFAULT 1, can_change_shift INTEGER DEFAULT 1)''')
        c.execute('''CREATE TABLE IF NOT EXISTS shift_stats (id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id TEXT, nickname TEXT, start_time REAL, deposits INTEGER DEFAULT 0, withdrawals INTEGER DEFAULT 0, profits INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS pending_deposits (request_id TEXT PRIMARY KEY, user_id TEXT, user_name TEXT, amount INTEGER, message_id INTEGER, photo_id TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS pending_withdrawals (request_id TEXT PRIMARY KEY, user_id TEXT, user_name TEXT, amount INTEGER, card_number TEXT, full_name TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS admin_earnings (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, amount INTEGER, withdrawn INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS tickets (ticket_id TEXT PRIMARY KEY, user_id TEXT, user_name TEXT, message TEXT, status TEXT DEFAULT 'open', created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS active_games (game_id TEXT PRIMARY KEY, data TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS level_rewards (level INTEGER PRIMARY KEY, title TEXT, xp_needed INTEGER, reward INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS welcome_bonus (user_id TEXT PRIMARY KEY, received INTEGER DEFAULT 0, join_order INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS bonus_stats (key TEXT PRIMARY KEY, value INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT)''')
        
        c.execute('INSERT OR IGNORE INTO bonus_stats (key, value) VALUES (?, ?)', ('total_bonus_given', 0))
        
        levels = [(1, "🌱 تازه‌کار", 0, 0), (2, "🌟 ستاره نوظهور", 100, 5000), (3, "⚡ جنگجوی بازار", 250, 10000), (4, "🎯 تیرانداز دقیق", 500, 20000), (5, "🏅 برنزی", 800, 35000), (6, "🥈 نقره‌ای", 1200, 50000), (7, "🥇 طلایی", 1700, 75000), (8, "💎 پلاتینیوم", 2300, 100000), (9, "👑 سلطان بازار", 3000, 150000), (10, "🌈 افسانه‌ای", 4000, 200000)]
        c.executemany('INSERT OR IGNORE INTO level_rewards VALUES (?,?,?,?)', levels)
        
        c.execute('INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?, ?)', ('bot_enabled', 'true'))
        c.execute('INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?, ?)', ('bot_win_rate', '30'))
        c.execute('INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?, ?)', ('bot_timeout', '30'))
        c.execute('INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?, ?)', ('max_bots', '5'))
        
        c.execute('INSERT OR IGNORE INTO admins (user_id, nickname, can_add_admin, can_remove_admin, can_set_access, can_reset_bot, can_gift_cash, can_deposit_user) VALUES (?, ?, 1, 1, 1, 1, 1, 1)', (MAIN_ADMIN_ID, '🧙‍♂️ مدیر ارشد 🧙‍♂️'))
        c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('current_card', '6219861075600832'))
        
        c.execute('SELECT COUNT(*) FROM shift_stats')
        if c.fetchone()[0] == 0:
            c.execute('INSERT INTO shift_stats (admin_id, nickname, start_time, deposits, withdrawals, profits) VALUES (?, ?, ?, 0, 0, 0)', 
                      (MAIN_ADMIN_ID, '🧙‍♂️ مدیر ارشد 🧙‍♂️', time.time()))
    
    conn.commit()
    conn.close()
    print("✅ دیتابیس راه‌اندازی شد!")

init_db()

# ==================== توابع دیتابیس ====================
def get_user_data(user_id):
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('SELECT * FROM users WHERE user_id = %s', (str(user_id),))
    else:
        c.execute('SELECT * FROM users WHERE user_id = ?', (str(user_id),))
    r = c.fetchone()
    conn.close()
    if r:
        return {
            "user_id": r[0], 
            "name": r[1], 
            "wallet": r[2], 
            "total_earnings": r[3], 
            "xp": r[4], 
            "level": r[5], 
            "games": r[6], 
            "wins": r[7], 
            "losses": r[8]
        }
    return None

def create_user(user_id, name):
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('INSERT INTO users (user_id, name) VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING', (str(user_id), name))
    else:
        c.execute('INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)', (str(user_id), name))
    conn.commit()
    conn.close()

def update_wallet(user_id, amount):
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('UPDATE users SET wallet = wallet + %s WHERE user_id = %s', (amount, str(user_id)))
    else:
        c.execute('UPDATE users SET wallet = wallet + ? WHERE user_id = ?', (amount, str(user_id)))
    conn.commit()
    conn.close()

def get_wallet(user_id):
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('SELECT wallet FROM users WHERE user_id = %s', (str(user_id),))
    else:
        c.execute('SELECT wallet FROM users WHERE user_id = ?', (str(user_id),))
    r = c.fetchone()
    conn.close()
    return r[0] if r else 0

def update_stats(user_id, games=0, wins=0, losses=0):
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('UPDATE users SET games = games + %s, wins = wins + %s, losses = losses + %s WHERE user_id = %s', 
                  (games, wins, losses, str(user_id)))
    else:
        c.execute('UPDATE users SET games = games + ?, wins = wins + ?, losses = losses + ? WHERE user_id = ?', 
                  (games, wins, losses, str(user_id)))
    conn.commit()
    conn.close()

def update_earnings(user_id, amount):
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('UPDATE users SET total_earnings = total_earnings + %s WHERE user_id = %s', (amount, str(user_id)))
    else:
        c.execute('UPDATE users SET total_earnings = total_earnings + ? WHERE user_id = ?', (amount, str(user_id)))
    conn.commit()
    conn.close()

def add_xp(user_id, amount):
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('SELECT xp, level FROM users WHERE user_id = %s', (str(user_id),))
    else:
        c.execute('SELECT xp, level FROM users WHERE user_id = ?', (str(user_id),))
    r = c.fetchone()
    if r:
        old_xp, old_level = r[0], r[1]
        new_xp = old_xp + amount
        if DATABASE_URL:
            c.execute('SELECT level, title, reward FROM level_rewards WHERE xp_needed <= %s ORDER BY level DESC LIMIT 1', (new_xp,))
        else:
            c.execute('SELECT level, title, reward FROM level_rewards WHERE xp_needed <= ? ORDER BY level DESC LIMIT 1', (new_xp,))
        lvl_data = c.fetchone()
        if lvl_data:
            new_level, level_title, reward = lvl_data
            if DATABASE_URL:
                c.execute('UPDATE users SET xp = %s, level = %s WHERE user_id = %s', (new_xp, new_level, str(user_id)))
            else:
                c.execute('UPDATE users SET xp = ?, level = ? WHERE user_id = ?', (new_xp, new_level, str(user_id)))
            conn.commit()
            if new_level > old_level:
                update_wallet(user_id, reward)
                conn.close()
                return True, new_level, level_title, reward
        else:
            if DATABASE_URL:
                c.execute('UPDATE users SET xp = %s WHERE user_id = %s', (new_xp, str(user_id)))
            else:
                c.execute('UPDATE users SET xp = ? WHERE user_id = ?', (new_xp, str(user_id)))
            conn.commit()
    conn.close()
    return False, None, None, None

def get_leaderboard():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT user_id, total_earnings FROM users ORDER BY total_earnings DESC LIMIT 10')
    r = c.fetchall()
    conn.close()
    return r

# ==================== هدیه ورود (۱۰۰ نفر اول) ====================
WELCOME_BONUS_AMOUNT = 30000
MAX_BONUS_USERS = 70

def get_total_bonus_given():
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('SELECT value FROM bonus_stats WHERE key = %s', ('total_bonus_given',))
    else:
        c.execute('SELECT value FROM bonus_stats WHERE key = "total_bonus_given"')
    r = c.fetchone()
    conn.close()
    return r[0] if r else 0

def increase_bonus_count():
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('UPDATE bonus_stats SET value = value + 1 WHERE key = %s', ('total_bonus_given',))
    else:
        c.execute('UPDATE bonus_stats SET value = value + 1 WHERE key = "total_bonus_given"')
    conn.commit()
    conn.close()

def has_received_welcome_bonus(user_id):
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('SELECT received FROM welcome_bonus WHERE user_id = %s', (str(user_id),))
    else:
        c.execute('SELECT received FROM welcome_bonus WHERE user_id = ?', (str(user_id),))
    r = c.fetchone()
    conn.close()
    return r and r[0] == 1

def set_welcome_bonus_received(user_id):
    total_given = get_total_bonus_given()
    join_order = total_given + 1
    
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('INSERT INTO welcome_bonus (user_id, received, join_order) VALUES (%s, 1, %s) ON CONFLICT (user_id) DO UPDATE SET received = 1, join_order = %s', 
                  (str(user_id), join_order, join_order))
    else:
        c.execute('INSERT OR REPLACE INTO welcome_bonus (user_id, received, join_order) VALUES (?, 1, ?)', (str(user_id), join_order))
    conn.commit()
    conn.close()
    increase_bonus_count()

def get_remaining_bonus_slots():
    total_given = get_total_bonus_given()
    remaining = MAX_BONUS_USERS - total_given
    return remaining if remaining > 0 else 0

def give_welcome_bonus(user_id):
    if has_received_welcome_bonus(user_id):
        return False, None
    
    remaining = get_remaining_bonus_slots()
    if remaining <= 0:
        return False, None
    
    update_wallet(user_id, WELCOME_BONUS_AMOUNT)
    set_welcome_bonus_received(user_id)
    return True, remaining - 1

def get_level_title(level):
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('SELECT title FROM level_rewards WHERE level = %s', (level,))
    else:
        c.execute('SELECT title FROM level_rewards WHERE level = ?', (level,))
    r = c.fetchone()
    conn.close()
    return r[0] if r else f"سطح {level}"

def get_invite_code(user_id):
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('SELECT code FROM invites WHERE user_id = %s', (str(user_id),))
    else:
        c.execute('SELECT code FROM invites WHERE user_id = ?', (str(user_id),))
    r = c.fetchone()
    conn.close()
    return r[0] if r else None

def create_invite(user_id):
    code = hashlib.md5(str(user_id).encode()).hexdigest()[:10]
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('INSERT INTO invites (user_id, code) VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING', (str(user_id), code))
    else:
        c.execute('INSERT OR IGNORE INTO invites (user_id, code) VALUES (?, ?)', (str(user_id), code))
    conn.commit()
    conn.close()
    return code

def get_invited_count(user_id):
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('SELECT invited_count FROM invites WHERE user_id = %s', (str(user_id),))
    else:
        c.execute('SELECT invited_count FROM invites WHERE user_id = ?', (str(user_id),))
    r = c.fetchone()
    conn.close()
    return r[0] if r else 0

def add_invited(user_id):
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('UPDATE invites SET invited_count = invited_count + 1 WHERE user_id = %s', (str(user_id),))
    else:
        c.execute('UPDATE invites SET invited_count = invited_count + 1 WHERE user_id = ?', (str(user_id),))
    conn.commit()
    conn.close()

def is_rewarded(user_id):
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('SELECT rewarded FROM invites WHERE user_id = %s', (str(user_id),))
    else:
        c.execute('SELECT rewarded FROM invites WHERE user_id = ?', (str(user_id),))
    r = c.fetchone()
    conn.close()
    return r[0] == 1 if r else False

def set_rewarded(user_id):
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('UPDATE invites SET rewarded = 1 WHERE user_id = %s', (str(user_id),))
    else:
        c.execute('UPDATE invites SET rewarded = 1 WHERE user_id = ?', (str(user_id),))
    conn.commit()
    conn.close()

def get_invite_by_code(code):
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('SELECT user_id FROM invites WHERE code = %s', (code,))
    else:
        c.execute('SELECT user_id FROM invites WHERE code = ?', (code,))
    r = c.fetchone()
    conn.close()
    return r[0] if r else None

def is_admin(user_id, access_key=None):
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('SELECT * FROM admins WHERE user_id = %s', (str(user_id),))
    else:
        c.execute('SELECT * FROM admins WHERE user_id = ?', (str(user_id),))
    r = c.fetchone()
    conn.close()
    if not r:
        return False
    if access_key:
        col_map = {
            "add_admin": 3, 
            "remove_admin": 4, 
            "set_access": 5, 
            "reset_bot": 6, 
            "gift_cash": 7, 
            "deposit_user": 8, 
            "view_requests": 9, 
            "change_shift": 10
        }
        index = col_map.get(access_key, 9)
        if len(r) > index:
            if access_key == "change_shift":
                return True
            return r[index] == 1
        return False
    return True

def get_admins():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT user_id FROM admins')
    r = c.fetchall()
    conn.close()
    return [row[0] for row in r]

def get_current_card():
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('SELECT value FROM settings WHERE key = %s', ('current_card',))
    else:
        c.execute('SELECT value FROM settings WHERE key = "current_card"')
    r = c.fetchone()
    conn.close()
    return r[0] if r else "6219861075600832"

def update_shift_stats(deposits=0, withdrawals=0, profits=0):
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('''
            UPDATE shift_stats 
            SET deposits = deposits + %s, withdrawals = withdrawals + %s, profits = profits + %s 
            WHERE id = (SELECT id FROM shift_stats ORDER BY id DESC LIMIT 1)
        ''', (deposits, withdrawals, profits))
    else:
        c.execute('''
            UPDATE shift_stats 
            SET deposits = deposits + ?, withdrawals = withdrawals + ?, profits = profits + ? 
            WHERE id = (SELECT id FROM shift_stats ORDER BY id DESC LIMIT 1)
        ''', (deposits, withdrawals, profits))
    conn.commit()
    conn.close()

def get_shift_stats():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT deposits, withdrawals, profits FROM shift_stats ORDER BY id DESC LIMIT 1')
    r = c.fetchone()
    conn.close()
    return r if r else (0, 0, 0)

def get_current_shift():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT admin_id, nickname, start_time, deposits, withdrawals, profits FROM shift_stats ORDER BY id DESC LIMIT 1')
    r = c.fetchone()
    conn.close()
    if r:
        return {
            "admin_id": r[0],
            "nickname": r[1],
            "start_time": r[2],
            "deposits": r[3],
            "withdrawals": r[4],
            "profits": r[5]
        }
    return None

# ==================== توابع ربات‌های ساختگی ====================
def is_bot_enabled():
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('SELECT value FROM bot_settings WHERE key = %s', ('bot_enabled',))
    else:
        c.execute('SELECT value FROM bot_settings WHERE key = "bot_enabled"')
    r = c.fetchone()
    conn.close()
    return r and r[0] == 'true'

def get_bot_setting(key):
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('SELECT value FROM bot_settings WHERE key = %s', (key,))
    else:
        c.execute('SELECT value FROM bot_settings WHERE key = ?', (key,))
    r = c.fetchone()
    conn.close()
    return r[0] if r else None

def get_bot_timeout():
    timeout = get_bot_setting('bot_timeout')
    return int(timeout) if timeout else 30

def get_max_bots():
    max_bots = get_bot_setting('max_bots')
    return int(max_bots) if max_bots else 5

BOT_NAMES = [
    "امیر", "علی", "سارا", "محمد", "زهرا", 
    "نیما", "الناز", "رضا", "فاطمه", "کیان",
    "مریم", "حسین", "نگار", "محسن", "مهسا",
    "امید", "نازنین", "سعید", "مائده", "آرش",
    "یاسمن", "رامین", "بهاره", "شهرام", "هانیه",
    "پدرام", "شیما", "کاوه", "نگین", "فرهاد",
    "ریحانه", "سیاوش", "گلناز", "بهنام", "شادی",
    "آرمان", "ترانه", "کیانوش", "رویا", "آریا"
]

def fill_room_with_bots_silent(room_id, user_id, is_rps=False):
    timeout = get_bot_timeout()
    max_bots = get_max_bots()
    time.sleep(timeout)
    
    if is_rps:
        if room_id not in rps_waiting:
            return
        
        user_found = False
        for player in rps_waiting[room_id]:
            if player["id"] == user_id:
                user_found = True
                break
        
        if not user_found:
            return
        
        if len(rps_waiting[room_id]) < 2:
            used_names = [p["name"] for p in rps_waiting[room_id] if not p.get("is_bot", False)]
            available_names = [n for n in BOT_NAMES if n not in used_names]
            if not available_names:
                available_names = BOT_NAMES
            
            bot_name = random.choice(available_names)
            bot_id = f"rps_bot_{room_id}_{int(time.time())}"
            
            rps_waiting[room_id].append({
                "id": bot_id,
                "name": bot_name,
                "message_id": None,
                "is_bot": True
            })
            
            threading.Thread(target=start_rps_game, args=(room_id,)).start()
    else:
        if room_id not in waiting_players:
            return
        
        user_found = False
        for player in waiting_players[room_id]:
            if player["id"] == user_id:
                user_found = True
                break
        
        if not user_found:
            return
        
        current_count = len(waiting_players[room_id])
        needed_bots = 6 - current_count
        if needed_bots > max_bots:
            needed_bots = max_bots
        
        if needed_bots <= 0:
            threading.Thread(target=start_game, args=(room_id,)).start()
            return
        
        used_names = [p["name"] for p in waiting_players[room_id] if not p.get("is_bot", False)]
        available_names = [n for n in BOT_NAMES if n not in used_names]
        
        if len(available_names) < needed_bots:
            available_names = BOT_NAMES.copy()
            random.shuffle(available_names)
        
        for i in range(needed_bots):
            bot_name = available_names[i % len(available_names)]
            bot_id = f"bot_{room_id}_{int(time.time())}_{i}"
            
            waiting_players[room_id].append({
                "id": bot_id,
                "name": bot_name,
                "message_id": None,
                "is_bot": True
            })
        
        threading.Thread(target=start_game, args=(room_id,)).start()

# ==================== پیام‌های فانتزی ====================
def msg_fancy(content):
    return f"""🎰 𝙇𝙊𝙏𝙏𝙊 𝙆𝙄𝙉𝙂 🎰
🤴 سلطان لوتو 🤴
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{content}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔹 پشتیبانی ۲۴ ساعته 🔹 بازی شرافتمندانه 🔹 برد مسئولانه 🔹"""

def msg_simple(content):
    return f"✨ {content} ✨"

# ==================== اتاق‌های لوتو ====================
ROOMS = {
    "room1": {"name": "🍃 مقدماتی", "amount": 20000, "prize": 40000, "second_card_cost": 10000, "xp": 10, "emoji": "🍃"},
    "room2": {"name": "🥉 برنزی", "amount": 50000, "prize": 100000, "second_card_cost": 25000, "xp": 20, "emoji": "🥉"},
    "room3": {"name": "🥈 نقره‌ای", "amount": 100000, "prize": 200000, "second_card_cost": 50000, "xp": 35, "emoji": "🥈"},
    "room4": {"name": "🥇 طلایی", "amount": 200000, "prize": 400000, "second_card_cost": 100000, "xp": 50, "emoji": "🥇"},
    "room5": {"name": "💎 پلاتینیوم", "amount": 500000, "prize": 1000000, "second_card_cost": 250000, "xp": 80, "emoji": "💎"},
    "room6": {"name": "👑 الماس", "amount": 750000, "prize": 1500000, "second_card_cost": 375000, "xp": 120, "emoji": "👑"},
    "room7": {"name": "⚡ افسانه‌ای", "amount": 1000000, "prize": 2000000, "second_card_cost": 500000, "xp": 200, "emoji": "⚡"},
}

RPS_ROOMS = {
    "rps1": {"name": "🌱 خاکی", "amount": 5000, "xp": 5, "emoji": "🌱"},
    "rps2": {"name": "🌿 برگی", "amount": 10000, "xp": 8, "emoji": "🌿"},
    "rps3": {"name": "🔥 آتشین", "amount": 20000, "xp": 12, "emoji": "🔥"},
    "rps4": {"name": "💨 بادی", "amount": 35000, "xp": 18, "emoji": "💨"},
    "rps5": {"name": "⚡ صاعقه", "amount": 50000, "xp": 25, "emoji": "⚡"},
}
RPS_ADMIN_PERCENT = 15

# ==================== کیبوردها ====================
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("🎮 جستجوی حریف 🎲"),
        KeyboardButton("✊ سنگ کاغذ قیچی ✋")
    )
    keyboard.add(
        KeyboardButton("📊 آمار من 📈"),
        KeyboardButton("👥 دعوت از دوستان 🎁")
    )
    keyboard.add(
        KeyboardButton("💼 کیف پول 💰")
    )
    keyboard.add(
        KeyboardButton("⭐ سطح من 🌟"),
        KeyboardButton("ℹ️ درباره ما 📖")
    )
    keyboard.add(
        KeyboardButton("🆘 پشتیبانی 🎫"),
        KeyboardButton("👥 مشاهده صف انتظار 📊")
    )
    keyboard.add(
        KeyboardButton("📖 راهنما و قوانین 📖")
    )
    return keyboard

def get_wallet_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(KeyboardButton("💸 واریز 📤"), KeyboardButton("💳 برداشت 📥"))
    keyboard.add(KeyboardButton("↩️ بازگشت 🏠"))
    return keyboard

def get_admin_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📊 آمار ربات 📈"), 
        KeyboardButton("🔄 ریست ربات 🔄")
    )
    keyboard.add(
        KeyboardButton("📋 درخواست‌ها 📋"), 
        KeyboardButton("🎁 هدیه پول 🎁")
    )
    keyboard.add(
        KeyboardButton("💸 واریز به کاربر 💸"), 
        KeyboardButton("⚙️ تنظیمات ادمین ⚙️")
    )
    keyboard.add(
        KeyboardButton("🔄 تغییر شیفت 🔄"), 
        KeyboardButton("💰 مدیریت سود 💰")
    )
    keyboard.add(
        KeyboardButton("🎫 تیکت‌ها 🎫"),
        KeyboardButton("📢 پیام همگانی 📢")
    )
    return keyboard

def get_admin_settings_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(KeyboardButton("➕ افزودن ادمین 👤"), KeyboardButton("➖ حذف ادمین 👤"))
    keyboard.add(KeyboardButton("🔑 دسترسی ادمین 🔐"), KeyboardButton("↩️ بازگشت 🔙"))
    return keyboard

def get_room_selection_keyboard(user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    for rid, room in ROOMS.items():
        markup.add(InlineKeyboardButton(f"{room['emoji']} {room['name']} {room['amount']:,} تومان", callback_data=f"room_{rid}_{user_id}"))
    return markup

def get_rps_room_selection_keyboard(user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    for rid, room in RPS_ROOMS.items():
        markup.add(InlineKeyboardButton(f"{room['emoji']} {room['name']} {room['amount']:,} تومان", callback_data=f"rpsroom_{rid}_{user_id}"))
    return markup

def get_rps_choice_keyboard(game_id, user_id):
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("✊ سنگ", callback_data=f"rps_choice_{game_id}_{user_id}_سنگ"),
        InlineKeyboardButton("✋ کاغذ", callback_data=f"rps_choice_{game_id}_{user_id}_کاغذ"),
        InlineKeyboardButton("✌️ قیچی", callback_data=f"rps_choice_{game_id}_{user_id}_قیچی")
    )
    return markup

# ==================== تولید کارت لوتو ====================
def generate_lotto_card():
    card = [[None] * 8 for _ in range(3)]
    ranges = [(1, 9), (10, 19), (20, 29), (30, 39), (40, 49), (50, 59), (60, 69), (70, 80)]
    all_existing = []
    for row in range(3):
        filled_columns = random.sample(range(8), 5)
        for col in range(8):
            if col in filled_columns:
                start, end = ranges[col]
                number = random.randint(start, end)
                while number in all_existing:
                    number = random.randint(start, end)
                card[row][col] = number
                all_existing.append(number)
    return card

def get_lotto_card_markup(game_id, user_id, cards, marked_numbers, second_card_purchased=False):
    markup = InlineKeyboardMarkup(row_width=8)
    
    for card_index, card in enumerate(cards):
        markup.add(InlineKeyboardButton(f"🎴 کارت {card_index + 1}", callback_data="dummy"))
        
        for row in card:
            buttons = []
            for num in row:
                if num is None:
                    buttons.append(InlineKeyboardButton("⬜", callback_data=f"lotto_{game_id}_{user_id}_empty_{card_index}"))
                else:
                    if num in marked_numbers[card_index]:
                        buttons.append(InlineKeyboardButton(f"✅{num:02d}", callback_data=f"lotto_{game_id}_{user_id}_{num}_{card_index}"))
                    else:
                        buttons.append(InlineKeyboardButton(f"{num:02d}", callback_data=f"lotto_{game_id}_{user_id}_{num}_{card_index}"))
            markup.add(*buttons)
        
        markup.add(InlineKeyboardButton("⚪⚪⚪⚪⚪⚪⚪⚪", callback_data="dummy"))
    
    markup.add(InlineKeyboardButton("💬 چت با حریف 💬", callback_data=f"start_chat_{game_id}"))
    if not second_card_purchased:
        markup.add(InlineKeyboardButton("🎴 خرید کارت دوم 🎴", callback_data=f"buy_second_card_{game_id}_{user_id}"))
    
    return markup

# ==================== متغیرهای موقت ====================
waiting_players = {}
lotto_games = {}
active_chats = {}
pending_wallet_requests = {}
pending_withdrawal_requests = {}
support_chats = {}
rps_waiting = {}
rps_games = {}
pending_broadcasts = {}

# ==================== هندلر استارت ====================
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = str(message.from_user.id)
    user_name = message.from_user.first_name or "کاربر"
    
    create_user(user_id, user_name)
    
    if not get_invite_code(user_id):
        create_invite(user_id)
    
    # ========== بخش هدیه ورود (۱۰۰ نفر اول) ==========
    welcome_text = ""
    bonus_given, remaining = give_welcome_bonus(user_id)
    
    if bonus_given:
        welcome_text = f"\n\n🎁 **هدیه ویژه ورود:** {WELCOME_BONUS_AMOUNT:,} تومان به کیف پولت اضافه شد! 🎉\n\n📊 **جای مونده:** {remaining} نفر از ۱۰۰ نفر"
    else:
        if has_received_welcome_bonus(user_id):
            pass
        else:
            welcome_text = "\n\n😔 **متاسفیم!** هدیه ۱۰۰ نفر اول به پایان رسیده."
    # ==========================================
    
    args = message.text.split()
    if len(args) > 1:
        invite_code = args[1]
        inviter_id = get_invite_by_code(invite_code)
        
        if inviter_id and inviter_id != user_id:
            conn = get_db()
            c = conn.cursor()
            if DATABASE_URL:
                c.execute('SELECT * FROM invited_users WHERE inviter_id = %s AND invited_id = %s', (inviter_id, user_id))
            else:
                c.execute('SELECT * FROM invited_users WHERE inviter_id = ? AND invited_id = ?', (inviter_id, user_id))
            existing = c.fetchone()
            conn.close()
            
            if not existing:
                conn = get_db()
                c = conn.cursor()
                if DATABASE_URL:
                    c.execute('INSERT INTO invited_users (inviter_id, invited_id) VALUES (%s, %s)', (inviter_id, user_id))
                else:
                    c.execute('INSERT INTO invited_users (inviter_id, invited_id) VALUES (?, ?)', (inviter_id, user_id))
                conn.commit()
                conn.close()
                
                add_invited(inviter_id)
                invited_count = get_invited_count(inviter_id)
                
                bot.send_message(user_id, msg_fancy(f"🎉 خوش اومدی! با لینک دعوت وارد شدی!{welcome_text}"), parse_mode="HTML")
                bot.send_message(inviter_id, msg_fancy(f"👥 یه نفر با لینک دعوتت وارد شد! تعداد: {invited_count}/20 🌟"), parse_mode="HTML")
                
                if invited_count >= 20 and not is_rewarded(inviter_id):
                    update_wallet(inviter_id, 50000)
                    set_rewarded(inviter_id)
                    bot.send_message(inviter_id, msg_fancy("🎁 تبریک! ۵۰,۰۰۰ تومان جایزه دعوت به کیف پولت اضافه شد! 🎁"), parse_mode="HTML")
                
                bot.send_message(
                    user_id, 
                    msg_fancy(f"✨ به سلطان لوتو خوش اومدی! ✨\n💰 رویاهایت رو به واقعیت تبدیل کن! 💰{welcome_text}"), 
                    parse_mode="HTML", 
                    reply_markup=get_main_keyboard()
                )
                return
    
    bot.send_message(
        user_id, 
        msg_fancy(f"✨ به سلطان لوتو خوش اومدی! ✨\n💰 رویاهایت رو به واقعیت تبدیل کن! 💰{welcome_text}"), 
        parse_mode="HTML", 
        reply_markup=get_main_keyboard()
    )

# ==================== جستجوی حریف (لوتو) ====================
@bot.message_handler(func=lambda message: message.text == "🎮 جستجوی حریف 🎲")
def find_opponent_handler(message):
    user_id = str(message.from_user.id)
    wallet = get_wallet(user_id)
    
    if wallet < 20000:
        bot.send_message(user_id, msg_fancy("💰 موجودی کیف پولت کافی نیست! لطفاً شارژ کن 💰"), parse_mode="HTML")
        return
    
    text = """🎲 **اتاق‌های بازی لوتو** 🎲

🍃 مقدماتی → ۲۰,۰۰۰ تومان
🥉 برنزی → ۵۰,۰۰۰ تومان
🥈 نقره‌ای → ۱۰۰,۰۰۰ تومان
🥇 طلایی → ۲۰۰,۰۰۰ تومان
💎 پلاتینیوم → ۵۰۰,۰۰۰ تومان
👑 الماس → ۷۵۰,۰۰۰ تومان
⚡ افسانه‌ای → ۱,۰۰۰,۰۰۰ تومان

👇 یکی رو انتخاب کن:"""
    
    bot.send_message(
        user_id, 
        msg_fancy(text), 
        parse_mode="HTML", 
        reply_markup=get_room_selection_keyboard(user_id)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("room_"))
def handle_room_selection(call):
    user_id = str(call.from_user.id)
    parts = call.data.split("_")
    room_id = parts[1]
    selected_user_id = parts[2]
    
    if selected_user_id != user_id:
        bot.answer_callback_query(call.id, "🚫 این برای تو نیست!")
        return
    
    if room_id not in ROOMS:
        bot.answer_callback_query(call.id, "🚫 اتاق نامعتبر!")
        return
    
    room = ROOMS[room_id]
    wallet = get_wallet(user_id)
    
    if wallet < room["amount"]:
        bot.answer_callback_query(call.id, "💰 موجودی کافی نیست!")
        return
    
    update_wallet(user_id, -room["amount"])
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    if room_id not in waiting_players:
        waiting_players[room_id] = []
    
    msg_sent = bot.send_message(
        user_id, 
        msg_simple(f"⏳ در حال جستجوی حریف در {room['name']}... 🔍"), 
        parse_mode="HTML"
    )
    
    player_data = {
        "id": user_id, 
        "name": call.from_user.first_name, 
        "message_id": msg_sent.message_id
    }
    waiting_players[room_id].append(player_data)
    
    threading.Thread(target=fill_room_with_bots_silent, args=(room_id, user_id, False)).start()
    threading.Thread(target=start_game, args=(room_id,)).start()
    bot.answer_callback_query(call.id, f"✅ وارد {room['name']} شدی!")

def start_game(room_id):
    time.sleep(3)
    if room_id not in waiting_players:
        return
    
    players = waiting_players[room_id]
    
    if len(players) >= 2:
        players_to_play = players[:6]
        waiting_players[room_id] = players[6:]
        
        room = ROOMS[room_id]
        game_id = str(int(time.time() * 1000))
        
        game_data = {
            "room_id": room_id,
            "room_name": room['name'],
            "amount": room['amount'],
            "prize": room['prize'],
            "second_card_cost": room['second_card_cost'],
            "xp_reward": room['xp'],
            "players": {},
            "numbers": [],
            "game_over": False,
            "has_bot": False,
            "bot_count": 0,
            "real_players": []
        }
        
        for player in players_to_play:
            is_bot = player.get("is_bot", False)
            game_data["players"][player["id"]] = {
                "name": player["name"],
                "cards": [generate_lotto_card()],
                "marked_numbers": [[]],
                "second_card_purchased": False,
                "message_id": player["message_id"],
                "is_bot": is_bot
            }
            if is_bot:
                game_data["has_bot"] = True
                game_data["bot_count"] += 1
            else:
                game_data["real_players"].append(player["id"])
        
        lotto_games[game_id] = game_data
        
        for player_id, player_data in game_data["players"].items():
            if not player_data["is_bot"]:
                markup = get_lotto_card_markup(game_id, player_id, player_data["cards"], player_data["marked_numbers"], False)
                try:
                    bot.edit_message_text(
                        msg_simple(f"🎰 بازی در {room['name']} شروع شد! 🎰\n\n✨ روی اعداد کلیک کن تا علامت بزنی! ✨"),
                        player_id, 
                        player_data["message_id"], 
                        parse_mode="HTML", 
                        reply_markup=markup
                    )
                except:
                    pass
        
        threading.Thread(target=run_game, args=(game_id,)).start()

def run_game(game_id):
    if game_id not in lotto_games:
        return
    
    game = lotto_games[game_id]
    all_numbers = set(range(1, 81))
    drawn_numbers = set()
    bot_win_rate = int(get_bot_setting('bot_win_rate') or '30')
    
    while not game["game_over"] and len(drawn_numbers) < 80:
        remaining = all_numbers - drawn_numbers
        if not remaining:
            break
        
        current_number = random.choice(list(remaining))
        drawn_numbers.add(current_number)
        game["numbers"].append(current_number)
        
        numbers_str = " ➡️ ".join(map(str, game["numbers"][-10:]))
        
        for player_id, player_data in game["players"].items():
            if not player_data["is_bot"]:
                markup = get_lotto_card_markup(game_id, player_id, player_data["cards"], player_data["marked_numbers"], player_data["second_card_purchased"])
                try:
                    bot.edit_message_text(
                        msg_simple(f"🎲 اعداد اعلام‌شده:\n{numbers_str}\n\n🔄 عدد جدید: {current_number}\n\n✅ روی عددهای داخل کارت کلیک کن!"),
                        player_id, 
                        player_data["message_id"], 
                        parse_mode="HTML", 
                        reply_markup=markup
                    )
                except:
                    pass
        
        for player_id, player_data in game["players"].items():
            if player_data["is_bot"]:
                for card_idx, card in enumerate(player_data["cards"]):
                    for row in card:
                        for num in row:
                            if num and num in drawn_numbers and num not in player_data["marked_numbers"][card_idx]:
                                if random.randint(1, 100) <= bot_win_rate:
                                    player_data["marked_numbers"][card_idx].append(num)
        
        for player_id, player_data in game["players"].items():
            for card_idx, marked in enumerate(player_data["marked_numbers"]):
                card = player_data["cards"][card_idx]
                for row in card:
                    filled_nums = [num for num in row if num is not None]
                    if filled_nums and all(num in marked for num in filled_nums):
                        game["game_over"] = True
                        winner_id = player_id
                        break
                if game["game_over"]:
                    break
        
        if game["game_over"]:
            room = ROOMS[game["room_id"]]
            
            winner_data = game["players"][winner_id]
            winner_name = winner_data["name"]
            is_bot_winner = winner_data.get("is_bot", False)
            
            real_players = [pid for pid, pdata in game["players"].items() if not pdata.get("is_bot", False)]
            
            total_players = len(game["players"])
            total_pot = total_players * room["amount"]
            
            admin_cut = int(total_pot * 0.3)
            winner_prize = total_pot - admin_cut
            
            if admin_cut > 0:
                conn = get_db()
                c = conn.cursor()
                if DATABASE_URL:
                    c.execute('INSERT INTO admin_earnings (date, amount) VALUES (%s, %s)', 
                             (datetime.datetime.now().date().isoformat(), admin_cut))
                else:
                    c.execute('INSERT INTO admin_earnings (date, amount) VALUES (?, ?)', 
                             (datetime.datetime.now().date().isoformat(), admin_cut))
                conn.commit()
                conn.close()
                update_shift_stats(profits=admin_cut)
            
            if is_bot_winner:
                for pid in real_players:
                    try:
                        bot.send_message(
                            pid, 
                            msg_fancy(f"😞 بازی تموم شد! برنده: {winner_name}\n💰 جایزه کل: {total_pot:,} تومان\n🍀 دفعه بعد شانس توئه!"), 
                            parse_mode="HTML"
                        )
                    except:
                        pass
            
            else:
                update_wallet(winner_id, winner_prize)
                update_earnings(winner_id, winner_prize)
                update_stats(winner_id, games=1, wins=1)
                
                for pid in real_players:
                    if pid != winner_id:
                        update_stats(pid, games=1, losses=1)
                
                leveled, new_level, level_title, reward = add_xp(winner_id, room["xp"])
                
                winner_msg = f"🏆 **تبریک! برنده شدی!** 🏆\n\n👑 {winner_name} 👑\n\n💰 **جایزه:** {winner_prize:,} تومان\n✨ **XP کسب شده:** {room['xp']}"
                
                if leveled:
                    winner_msg += f"\n\n🌟 به سطح **{level_title}** رسیدی! {reward:,} تومان پاداش 🌟"
                
                winner_msg += "\n\n🎉 تبریک می‌گم! 🎉"
                
                try:
                    bot.send_message(winner_id, msg_fancy(winner_msg), parse_mode="HTML")
                except:
                    pass
                
                for pid in real_players:
                    if pid != winner_id:
                        try:
                            bot.send_message(
                                pid, 
                                msg_fancy(f"😞 بازی تموم شد! برنده: {winner_name}\n💰 جایزه: {winner_prize:,} تومان\n🍀 دفعه بعد شانس توئه!"), 
                                parse_mode="HTML"
                            )
                        except:
                            pass
            
            del lotto_games[game_id]
            break
        
        time.sleep(5)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lotto_"))
def handle_lotto_mark(call):
    parts = call.data.split("_")
    game_id = parts[1]
    user_id = parts[2]
    num_str = parts[3]
    card_index = int(parts[4])
    
    if num_str == "empty":
        bot.answer_callback_query(call.id, "⬜ این خانه خالی است!")
        return
    
    if user_id != str(call.from_user.id):
        bot.answer_callback_query(call.id, "🚫 این کارت برای شما نیست!")
        return
    
    if game_id not in lotto_games:
        bot.answer_callback_query(call.id, "🎮 بازی یافت نشد!")
        return
    
    num = int(num_str)
    game = lotto_games[game_id]
    
    if num not in game["numbers"]:
        bot.answer_callback_query(call.id, f"⏳ عدد {num} هنوز اعلام نشده!")
        return
    
    player_data = game["players"][user_id]
    if num in player_data["marked_numbers"][card_index]:
        bot.answer_callback_query(call.id, f"✅ عدد {num} قبلاً علامت زده شده!")
        return
    
    player_data["marked_numbers"][card_index].append(num)
    markup = get_lotto_card_markup(game_id, user_id, player_data["cards"], player_data["marked_numbers"], player_data["second_card_purchased"])
    
    try:
        bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=markup)
    except:
        pass
    
    bot.answer_callback_query(call.id, f"✅ عدد {num} علامت زده شد!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_second_card_"))
def buy_second_card_handler(call):
    parts = call.data.split("_")
    game_id = parts[3]
    user_id = parts[4]
    
    if user_id != str(call.from_user.id):
        bot.answer_callback_query(call.id, "🚫 این دکمه برای شما نیست!")
        return
    
    if game_id not in lotto_games:
        bot.answer_callback_query(call.id, "🎮 بازی یافت نشد!")
        return
    
    game = lotto_games[game_id]
    player_data = game["players"][user_id]
    
    if player_data["second_card_purchased"]:
        bot.answer_callback_query(call.id, "🎴 قبلاً کارت دوم رو خریدی!")
        return
    
    wallet = get_wallet(user_id)
    if wallet < game["second_card_cost"]:
        bot.answer_callback_query(call.id, "💰 موجودی کافی نیست!")
        return
    
    update_wallet(user_id, -game["second_card_cost"])
    player_data["cards"].append(generate_lotto_card())
    player_data["marked_numbers"].append([])
    player_data["second_card_purchased"] = True
    
    markup = get_lotto_card_markup(game_id, user_id, player_data["cards"], player_data["marked_numbers"], True)
    
    try:
        bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=markup)
    except:
        pass
    
    bot.answer_callback_query(call.id, "🎴 کارت دوم خریداری شد! شانس تو دو برابر شد! 🎴")

@bot.callback_query_handler(func=lambda call: call.data.startswith("start_chat_"))
def start_chat_handler(call):
    game_id = call.data.split("_")[2]
    user_id = str(call.from_user.id)
    
    if game_id not in lotto_games:
        bot.answer_callback_query(call.id, "🎮 بازی یافت نشد!")
        return
    
    if game_id not in active_chats:
        active_chats[game_id] = True
    
    bot.send_message(
        user_id, 
        msg_simple("💬 چت فعال شد! پیام‌های تو به حریف ارسال میشه 💬"), 
        parse_mode="HTML", 
        reply_markup=get_main_keyboard()
    )
    bot.answer_callback_query(call.id, "💬 چت شروع شد!")

# ==================== سنگ کاغذ قیچی ====================
@bot.message_handler(func=lambda message: message.text == "✊ سنگ کاغذ قیچی ✋")
def rps_main_handler(message):
    user_id = str(message.from_user.id)
    wallet = get_wallet(user_id)
    
    if wallet < 5000:
        bot.send_message(user_id, msg_fancy("💰 موجودی کیف پولت کافی نیست! حداقل ۵,۰۰۰ تومان نیازه 💰"), parse_mode="HTML")
        return
    
    text = """✊ **اتاق‌های سنگ کاغذ قیچی** ✋

🌱 خاکی → ۵,۰۰۰ تومان
🌿 برگی → ۱۰,۰۰۰ تومان
🔥 آتشین → ۲۰,۰۰۰ تومان
💨 بادی → ۳۵,۰۰۰ تومان
⚡ صاعقه → ۵۰,۰۰۰ تومان

👇 یکی رو انتخاب کن:"""
    
    bot.send_message(
        user_id, 
        msg_fancy(text), 
        parse_mode="HTML", 
        reply_markup=get_rps_room_selection_keyboard(user_id)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("rpsroom_"))
def handle_rps_room_selection(call):
    user_id = str(call.from_user.id)
    parts = call.data.split("_")
    room_id = parts[1]
    selected_user_id = parts[2]
    
    if selected_user_id != user_id:
        bot.answer_callback_query(call.id, "🚫 این برای تو نیست!")
        return
    
    if room_id not in RPS_ROOMS:
        bot.answer_callback_query(call.id, "🚫 اتاق نامعتبر!")
        return
    
    room = RPS_ROOMS[room_id]
    wallet = get_wallet(user_id)
    
    if wallet < room["amount"]:
        bot.answer_callback_query(call.id, "💰 موجودی کافی نیست!")
        return
    
    update_wallet(user_id, -room["amount"])
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    if room_id not in rps_waiting:
        rps_waiting[room_id] = []
    
    msg_sent = bot.send_message(
        user_id, 
        msg_simple(f"⏳ در حال جستجوی حریف در {room['name']}... 🔍"), 
        parse_mode="HTML"
    )
    
    player_data = {
        "id": user_id, 
        "name": call.from_user.first_name, 
        "message_id": msg_sent.message_id
    }
    rps_waiting[room_id].append(player_data)
    
    threading.Thread(target=fill_room_with_bots_silent, args=(room_id, user_id, True)).start()
    threading.Thread(target=start_rps_game, args=(room_id,)).start()
    bot.answer_callback_query(call.id, f"✅ وارد {room['name']} شدی!")

def start_rps_game(room_id):
    time.sleep(3)
    if room_id not in rps_waiting:
        return
    
    if len(rps_waiting[room_id]) < 2:
        return
    
    players = rps_waiting[room_id][:2]
    rps_waiting[room_id] = rps_waiting[room_id][2:]
    
    room = RPS_ROOMS[room_id]
    game_id = str(int(time.time() * 1000))
    
    game_data = {
        "room_id": room_id,
        "room_name": room['name'],
        "amount": room['amount'],
        "xp_reward": room['xp'],
        "players": {},
        "choices": {},
        "game_over": False,
        "has_bot": False
    }
    
    for player in players:
        is_bot = player.get("is_bot", False)
        game_data["players"][player["id"]] = {
            "name": player["name"],
            "message_id": player["message_id"],
            "is_bot": is_bot
        }
        if is_bot:
            game_data["has_bot"] = True
    
    rps_games[game_id] = game_data
    
    for player_id, player_data in game_data["players"].items():
        if not player_data["is_bot"]:
            markup = get_rps_choice_keyboard(game_id, player_id)
            try:
                bot.edit_message_text(
                    msg_simple(f"✊ انتخاب خود را بکن! {room['name']} - {room['amount']:,} تومان\n\nسنگ ✊ | کاغذ ✋ | قیچی ✌️"),
                    player_id, 
                    player_data["message_id"], 
                    parse_mode="HTML", 
                    reply_markup=markup
                )
            except:
                pass
    
    threading.Thread(target=run_rps_game, args=(game_id,)).start()

def run_rps_game(game_id):
    if game_id not in rps_games:
        return
    
    game = rps_games[game_id]
    timeout = 20
    start_time = time.time()
    
    for pid, pdata in game["players"].items():
        if pdata.get("is_bot", False):
            choice = random.choice(["سنگ", "کاغذ", "قیچی"])
            game["choices"][pid] = choice
    
    while len(game["choices"]) < len(game["players"]) and time.time() - start_time < timeout:
        time.sleep(1)
    
    if len(game["choices"]) >= len(game["players"]):
        players = list(game["players"].keys())
        p1 = players[0]
        p2 = players[1]
        choice1 = game["choices"][p1]
        choice2 = game["choices"][p2]
        
        rules = {
            "سنگ": "قیچی",
            "کاغذ": "سنگ",
            "قیچی": "کاغذ"
        }
        
        winner_id = None
        is_bot_winner = False
        
        if choice1 == choice2:
            result_text = "🤝 مساوی! هر دو برگشت داده میشه."
            for pid in game["players"]:
                if not game["players"][pid].get("is_bot", False):
                    update_wallet(pid, game["amount"])
            del rps_games[game_id]
            return
        
        elif rules[choice1] == choice2:
            winner_id = p1
            is_bot_winner = game["players"][p1].get("is_bot", False)
            result_text = f"🏆 برنده: {game['players'][p1]['name']}!"
        else:
            winner_id = p2
            is_bot_winner = game["players"][p2].get("is_bot", False)
            result_text = f"🏆 برنده: {game['players'][p2]['name']}!"
        
        real_players = [pid for pid, pdata in game["players"].items() if not pdata.get("is_bot", False)]
        
        total_players = len(game["players"])
        total_pot = total_players * game["amount"]
        
        admin_cut = int(total_pot * 0.1)
        winner_prize = total_pot - admin_cut
        
        if admin_cut > 0:
            conn = get_db()
            c = conn.cursor()
            if DATABASE_URL:
                c.execute('INSERT INTO admin_earnings (date, amount) VALUES (%s, %s)', 
                         (datetime.datetime.now().date().isoformat(), admin_cut))
            else:
                c.execute('INSERT INTO admin_earnings (date, amount) VALUES (?, ?)', 
                         (datetime.datetime.now().date().isoformat(), admin_cut))
            conn.commit()
            conn.close()
            update_shift_stats(profits=admin_cut)
        
        if is_bot_winner and winner_id:
            for pid in real_players:
                try:
                    bot.send_message(
                        pid,
                        msg_fancy(f"😞 بازی تموم شد! برنده: {game['players'][winner_id]['name']}\n💰 جایزه کل: {total_pot:,} تومان\n🍀 دفعه بعد شانس توئه!"),
                        parse_mode="HTML"
                    )
                except:
                    pass
        
        elif winner_id and not is_bot_winner:
            update_wallet(winner_id, winner_prize)
            update_earnings(winner_id, winner_prize)
            update_stats(winner_id, games=1, wins=1)
            
            for pid in real_players:
                if pid != winner_id:
                    update_stats(pid, games=1, losses=1)
            
            add_xp(winner_id, game["xp_reward"])
        
        for pid in game["players"]:
            if not game["players"][pid].get("is_bot", False):
                emojis = {"سنگ": "✊", "کاغذ": "✋", "قیچی": "✌️"}
                result_msg = f"""✊ **نتیجه سنگ کاغذ قیچی** ✋

🏷️ **اتاق:** {game['room_name']}
💰 **مبلغ:** {game['amount']:,} تومان

👤 {game['players'][p1]['name']}: {emojis.get(choice1, choice1)}
👤 {game['players'][p2]['name']}: {emojis.get(choice2, choice2)}

{result_text}"""
                
                if winner_id == pid and not is_bot_winner:
                    result_msg += f"\n\n🎉 تبریک! {winner_prize:,} تومان بردی! 🎉"
                elif is_bot_winner:
                    result_msg += "\n\n😞 دفعه بعد شانس توئه! 🍀"
                elif winner_id:
                    result_msg += "\n\n😞 دفعه بعد شانس توئه! 🍀"
                
                try:
                    bot.send_message(pid, msg_fancy(result_msg), parse_mode="HTML")
                except:
                    pass
        
        del rps_games[game_id]
    
    else:
        for pid in game["players"]:
            if not game["players"][pid].get("is_bot", False):
                update_wallet(pid, game["amount"])
                try:
                    bot.send_message(
                        pid,
                        msg_fancy(f"⏰ زمان انتخاب به پایان رسید! مبلغ {game['amount']:,} تومان به کیف پولت برگشت."),
                        parse_mode="HTML"
                    )
                except:
                    pass
        del rps_games[game_id]

@bot.callback_query_handler(func=lambda call: call.data.startswith("rps_choice_"))
def handle_rps_choice(call):
    parts = call.data.split("_")
    game_id = parts[2]
    user_id = parts[3]
    choice = parts[4]
    
    if user_id != str(call.from_user.id):
        bot.answer_callback_query(call.id, "🚫 این دکمه برای شما نیست!")
        return
    
    if game_id not in rps_games:
        bot.answer_callback_query(call.id, "🎮 بازی یافت نشد!")
        return
    
    game = rps_games[game_id]
    
    if user_id in game["choices"]:
        bot.answer_callback_query(call.id, "✅ قبلاً انتخاب کردی!")
        return
    
    game["choices"][user_id] = choice
    
    bot.answer_callback_query(call.id, f"✅ انتخاب شد: {choice}")
    
    try:
        bot.edit_message_text(
            msg_simple(f"✅ انتخاب شما ثبت شد: {choice}\n\n⏳ منتظر حریف..."), 
            user_id, 
            game["players"][user_id]["message_id"], 
            parse_mode="HTML"
        )
    except:
        pass

# ==================== مشاهده صف انتظار ====================
@bot.message_handler(func=lambda message: message.text == "👥 مشاهده صف انتظار 📊")
def view_queue_handler(message):
    user_id = str(message.from_user.id)
    
    text = """📊 **صف انتظار بازی‌ها** 📊
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎲 **لوتو:**
"""
    
    if waiting_players:
        for room_id, players in waiting_players.items():
            if room_id in ROOMS:
                room = ROOMS[room_id]
                real_players = [p for p in players if not p.get("is_bot", False)]
                count = len(real_players)
                text += f"  {room['emoji']} {room['name']}: {count} نفر\n"
    else:
        text += "  📭 هیچ‌کس در صف نیست\n"
    
    text += "\n✊ **سنگ کاغذ قیچی:**\n"
    
    if rps_waiting:
        for room_id, players in rps_waiting.items():
            if room_id in RPS_ROOMS:
                room = RPS_ROOMS[room_id]
                real_players = [p for p in players if not p.get("is_bot", False)]
                count = len(real_players)
                text += f"  {room['emoji']} {room['name']}: {count} نفر\n"
    else:
        text += "  📭 هیچ‌کس در صف نیست\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += "💡 برای ورود به صف، روی دکمه‌های بازی کلیک کن!"
    
    bot.send_message(user_id, msg_fancy(text), parse_mode="HTML")

# ==================== آمار کاربر ====================
@bot.message_handler(func=lambda message: message.text == "📊 آمار من 📈")
def user_stats_handler(message):
    user_id = str(message.from_user.id)
    user = get_user_data(user_id)
    
    if user:
        win_rate = (user['wins'] / user['games'] * 100) if user['games'] > 0 else 0
        level_title = get_level_title(user['level'])
        text = f"""📊 **آمار تو** 📊

🎮 **کل بازی‌ها:** {user['games']}
🏆 **برد:** {user['wins']}    💀 **باخت:** {user['losses']}
📈 **نرخ برد:** {win_rate:.1f}%

🌟 **سطح:** {level_title}
💰 **مجموع برد:** {user['total_earnings']:,} تومان
💵 **موجودی کیف پول:** {user['wallet']:,} تومان"""
        bot.send_message(user_id, msg_fancy(text), parse_mode="HTML")

# ==================== سطح کاربر ====================
@bot.message_handler(func=lambda message: message.text == "⭐ سطح من 🌟")
def level_handler(message):
    user_id = str(message.from_user.id)
    user = get_user_data(user_id)
    
    if user:
        level_title = get_level_title(user['level'])
        conn = get_db()
        c = conn.cursor()
        if DATABASE_URL:
            c.execute('SELECT xp_needed FROM level_rewards WHERE level = %s', (user['level'] + 1,))
        else:
            c.execute('SELECT xp_needed FROM level_rewards WHERE level = ?', (user['level'] + 1,))
        next_lvl = c.fetchone()
        conn.close()
        
        next_xp = next_lvl[0] if next_lvl else user['xp']
        needed = next_xp - user['xp']
        
        text = f"""⭐ **سطح تو** ⭐

🌟 **{level_title}** 🌟

📊 **XP فعلی:** {user['xp']}
🎯 **XP تا سطح بعدی:** {needed}

💡 با هر برد، XP دریافت کن و سطحت رو بالا ببر!
🎁 هر سطح پاداش نقدی داره!"""
        bot.send_message(user_id, msg_fancy(text), parse_mode="HTML")

# ==================== تالار مشاهیر ====================
@bot.message_handler(func=lambda message: message.text == "🏆 تالار مشاهیر 🏅")
def leaderboard_handler(message):
    leaders = get_leaderboard()
    
    if not leaders:
        bot.send_message(message.from_user.id, msg_fancy("📭 هنوز هیچ بردی ثبت نشده!"), parse_mode="HTML")
        return
    
    text = "🏆 **تالار مشاهیر** 🏆\n\n"
    medals = ["👑", "🥈", "🥉", "🏅", "🏅", "🏅", "🏅", "🏅", "🏅", "🏅"]
    for i, (uid, earning) in enumerate(leaders[:10], 1):
        try:
            user = bot.get_chat(uid)
            name = user.first_name or "کاربر"
        except:
            name = "ناشناس"
        text += f"{medals[i-1]} {i}. {name[:15]} → {earning:,} تومان\n"
    
    bot.send_message(message.from_user.id, msg_fancy(text), parse_mode="HTML")

# ==================== کیف پول ====================
@bot.message_handler(func=lambda message: message.text == "💼 کیف پول 💰")
def wallet_handler(message):
    user_id = str(message.from_user.id)
    wallet = get_wallet(user_id)
    
    text = f"""💼 **کیف پول تو** 💼

💵 {wallet:,} تومان"""
    bot.send_message(
        user_id, 
        msg_fancy(text), 
        parse_mode="HTML", 
        reply_markup=get_wallet_keyboard()
    )

# ==================== واریز ====================
@bot.message_handler(func=lambda message: message.text == "💸 واریز 📤")
def deposit_handler(message):
    user_id = str(message.from_user.id)
    bot.send_message(
        user_id, 
        msg_fancy("💰 مبلغ واریزی رو به تومان وارد کن:"), 
        parse_mode="HTML"
    )
    bot.register_next_step_handler(message, lambda m: handle_deposit_amount(m, user_id))

def handle_deposit_amount(message, user_id):
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError
        
        request_id = str(int(time.time() * 1000))
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📸 ارسال فیش", callback_data=f"send_receipt_{request_id}_{user_id}"))
        
        current_card = get_current_card()
        
        bot.send_message(
            user_id, 
            msg_fancy(f"""
💳 **شماره کارت:** `{current_card}`

💰 **مبلغ:** {amount:,} تومان

📸 لطفاً فیش واریزی رو بفرست.
"""), 
            parse_mode="HTML", 
            reply_markup=markup
        )
        
        pending_wallet_requests[request_id] = {
            "user_id": user_id,
            "user_name": message.from_user.first_name,
            "amount": amount,
            "type": "wallet"
        }
    except:
        bot.send_message(user_id, msg_fancy("⚠️ مبلغ نامعتبر!"), parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("send_receipt_"))
def send_receipt(call):
    parts = call.data.split("_")
    request_id = parts[2]
    user_id = parts[3]
    
    if user_id != str(call.from_user.id):
        bot.answer_callback_query(call.id, "🚫 این درخواست برای تو نیست!")
        return
    
    bot.edit_message_text(
        msg_fancy("📸 لطفاً عکس فیش رو بفرست:"), 
        call.from_user.id, 
        call.message.message_id, 
        parse_mode="HTML"
    )
    bot.register_next_step_handler(call.message, lambda m: handle_receipt_photo(m, request_id, user_id))

def handle_receipt_photo(message, request_id, user_id):
    if not message.photo:
        bot.send_message(
            user_id, 
            msg_fancy("⚠️ لطفاً یه عکس معتبر بفرست!"), 
            parse_mode="HTML"
        )
        bot.register_next_step_handler(message, lambda m: handle_receipt_photo(m, request_id, user_id))
        return
    
    pending_wallet_requests[request_id]["message_id"] = message.message_id
    
    bot.send_message(
        user_id, 
        msg_fancy("✅ فیش دریافت شد! در انتظار تأیید ادمین..."), 
        parse_mode="HTML", 
        reply_markup=get_main_keyboard()
    )
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ تأیید", callback_data=f"approve_wallet_{request_id}"),
        InlineKeyboardButton("❌ رد", callback_data=f"reject_wallet_{request_id}")
    )
    
    for admin_id in get_admins():
        try:
            bot.send_photo(
                admin_id, 
                message.photo[-1].file_id,
                caption=f"📦 درخواست واریز\n👤 {message.from_user.first_name}\n💰 {pending_wallet_requests[request_id]['amount']:,} تومان",
                reply_markup=markup
            )
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_wallet_"))
def approve_wallet(call):
    request_id = call.data.split("_")[2]
    
    if request_id not in pending_wallet_requests:
        bot.answer_callback_query(call.id, "🚫 درخواست وجود ندارد!")
        return
    
    req = pending_wallet_requests[request_id]
    update_wallet(req['user_id'], req['amount'])
    update_shift_stats(deposits=req['amount'])
    
    bot.send_message(
        req['user_id'], 
        msg_fancy(f"✅ واریز {req['amount']:,} تومان تأیید شد! 💰"), 
        parse_mode="HTML"
    )
    bot.edit_message_text("✅ تأیید شد", call.from_user.id, call.message.message_id)
    bot.answer_callback_query(call.id, "✅ واریز تأیید شد!")
    
    del pending_wallet_requests[request_id]

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_wallet_"))
def reject_wallet(call):
    request_id = call.data.split("_")[2]
    
    if request_id not in pending_wallet_requests:
        bot.answer_callback_query(call.id, "🚫 درخواست وجود ندارد!")
        return
    
    req = pending_wallet_requests[request_id]
    bot.send_message(
        req['user_id'], 
        msg_fancy("❌ درخواست واریز رد شد!"), 
        parse_mode="HTML"
    )
    bot.edit_message_text("❌ رد شد", call.from_user.id, call.message.message_id)
    bot.answer_callback_query(call.id, "❌ رد شد")
    
    del pending_wallet_requests[request_id]

# ==================== برداشت ====================
@bot.message_handler(func=lambda message: message.text == "💳 برداشت 📥")
def withdraw_handler(message):
    user_id = str(message.from_user.id)
    wallet = get_wallet(user_id)
    
    if wallet < 100000:
        bot.send_message(
            user_id, 
            msg_fancy("⚠️ حداقل مبلغ برداشت ۱۰۰,۰۰۰ تومان است!"), 
            parse_mode="HTML"
        )
        return
    
    bot.send_message(
        user_id, 
        msg_fancy(f"💰 موجودی: {wallet:,} تومان\n\n💸 مبلغ برداشت رو وارد کن:"), 
        parse_mode="HTML"
    )
    bot.register_next_step_handler(message, lambda m: handle_withdraw_amount(m, user_id))

def handle_withdraw_amount(message, user_id):
    try:
        amount = int(message.text.strip())
        wallet = get_wallet(user_id)
        
        if amount < 100000:
            raise ValueError("حداقل ۱۰۰,۰۰۰ تومان")
        if amount > wallet:
            raise ValueError("بیشتر از موجودی")
        
        update_wallet(user_id, -amount)
        bot.send_message(
            user_id, 
            msg_fancy("🏦 شماره کارت ۱۶ رقمی رو وارد کن:"), 
            parse_mode="HTML"
        )
        bot.register_next_step_handler(message, lambda m: handle_withdraw_card(m, user_id, amount))
    except:
        bot.send_message(user_id, msg_fancy("⚠️ مبلغ نامعتبر!"), parse_mode="HTML")

def handle_withdraw_card(message, user_id, amount):
    card = message.text.strip()
    if not card.isdigit() or len(card) != 16:
        bot.send_message(
            user_id, 
            msg_fancy("⚠️ شماره کارت باید ۱۶ رقم باشد!"), 
            parse_mode="HTML"
        )
        return
    
    bot.send_message(
        user_id, 
        msg_fancy("👤 نام و نام خانوادگی رو وارد کن:"), 
        parse_mode="HTML"
    )
    bot.register_next_step_handler(message, lambda m: handle_withdraw_name(m, user_id, amount, card))

def handle_withdraw_name(message, user_id, amount, card):
    name = message.text.strip()
    request_id = str(int(time.time() * 1000))
    
    pending_withdrawal_requests[request_id] = {
        "user_id": user_id,
        "user_name": message.from_user.first_name,
        "amount": amount,
        "card_number": card,
        "full_name": name
    }
    
    bot.send_message(
        user_id, 
        msg_fancy(f"✅ درخواست برداشت {amount:,} تومان ثبت شد! در انتظار تأیید ادمین..."), 
        parse_mode="HTML", 
        reply_markup=get_main_keyboard()
    )
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ تأیید", callback_data=f"approve_withdraw_{request_id}"),
        InlineKeyboardButton("❌ رد", callback_data=f"reject_withdraw_{request_id}")
    )
    
    for admin_id in get_admins():
        try:
            bot.send_message(
                admin_id, 
                msg_fancy(f"📦 درخواست برداشت\n👤 {message.from_user.first_name}\n💰 {amount:,} تومان\n🏦 {card}\n👤 {name}"), 
                parse_mode="HTML", 
                reply_markup=markup
            )
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_withdraw_"))
def approve_withdraw(call):
    request_id = call.data.split("_")[2]
    
    if request_id not in pending_withdrawal_requests:
        bot.answer_callback_query(call.id, "🚫 درخواست وجود ندارد!")
        return
    
    req = pending_withdrawal_requests[request_id]
    update_shift_stats(withdrawals=req['amount'])
    
    bot.send_message(
        req['user_id'], 
        msg_fancy(f"✅ برداشت {req['amount']:,} تومان تأیید شد! به زودی واریز میشه."), 
        parse_mode="HTML"
    )
    bot.edit_message_text("✅ تأیید شد", call.from_user.id, call.message.message_id)
    bot.answer_callback_query(call.id, "✅ برداشت تأیید شد!")
    
    del pending_withdrawal_requests[request_id]

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_withdraw_"))
def reject_withdraw(call):
    request_id = call.data.split("_")[2]
    
    if request_id not in pending_withdrawal_requests:
        bot.answer_callback_query(call.id, "🚫 درخواست وجود ندارد!")
        return
    
    req = pending_withdrawal_requests[request_id]
    update_wallet(req['user_id'], req['amount'])
    
    bot.send_message(
        req['user_id'], 
        msg_fancy("❌ درخواست برداشت رد شد! مبلغ به کیف پولت برگشت."), 
        parse_mode="HTML"
    )
    bot.edit_message_text("❌ رد شد", call.from_user.id, call.message.message_id)
    bot.answer_callback_query(call.id, "❌ رد شد")
    
    del pending_withdrawal_requests[request_id]

# ==================== دعوت از دوستان ====================
@bot.message_handler(func=lambda message: message.text == "👥 دعوت از دوستان 🎁")
def invite_friends_handler(message):
    user_id = str(message.from_user.id)
    
    code = get_invite_code(user_id)
    if not code:
        code = create_invite(user_id)
    
    invited_count = get_invited_count(user_id)
    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    
    text = f"""👥 **دعوت از دوستان** 👥

🔗 **لینک اختصاصی تو:**
`{link}`

👥 **تعداد دعوت‌شده‌ها:** {invited_count}/20
🎁 **جایزه ۲۰ نفر:** ۵۰,۰۰۰ تومان

💡 هر دوستت با لینک تو وارد بشه، ۱ نفر به حسابتو اضافه میشه
و به ۲۰ نفر که برسی، جایزه می‌گیری!"""
    bot.send_message(
        user_id, 
        msg_fancy(text), 
        parse_mode="HTML", 
        disable_web_page_preview=True
    )

# ==================== درباره ما ====================
@bot.message_handler(func=lambda message: message.text == "ℹ️ درباره ما 📖")
def about_handler(message):
    text = """ℹ️ **درباره ما** ℹ️

🎰 **ربات لوتو سلطان** - تجربه‌ای متفاوت از بازی! 🎰

✨ با ما هیجان رو تجربه کن و شانس خودتو امتحان کن! ✨

🛡️ بازی شرافتمندانه، برد مسئولانه 🛡️

📞 پشتیبانی: از طریق دکمه پشتیبانی با ما در ارتباط باش"""
    bot.send_message(message.from_user.id, msg_fancy(text), parse_mode="HTML")

@bot.message_handler(func=lambda message: message.text == "📖 راهنما و قوانین 📖")
def help_button_handler(message):
    help_text = """🎰 راهنمای کامل بازی‌های سلطان لوتو 🎰
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎲 **بازی لوتو (بیینگو)**
─────────────────
✅ وارد اتاق مورد نظر میشی
✅ برات یه کارت ۳×۸ با ۱۵ عدد تصادفی ساخته میشه
✅ هر بار یه عدد بین ۱ تا ۸۰ اعلام میشه
✅ باید اعدادی که اعلام شدن رو روی کارتت علامت بزنی
✅ هر کس زودتر یه سطر کامل رو علامت بزنه، برنده‌ست! 🏆

💡 **نکات طلایی:**
• می‌تونی کارت دوم بخری (شانست رو دو برابر کن!)
• هر چی اتاق بالاتر باشه، جایزه بزرگ‌تره
• با هر برد، XP می‌گیری و سطحت بالا می‌ره

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✊ **سنگ-کاغذ-قیچی**
─────────────────
✅ وارد اتاق مورد نظر میشی
✅ با حریف (واقعی یا ربات) روبرو میشی
✅ یکی از سه گزینه رو انتخاب میکنی:
   ✊ سنگ > ✌️ قیچی
   ✌️ قیچی > ✋ کاغذ
   ✋ کاغذ > ✊ سنگ
✅ برنده کل مبلغ رو می‌بره! (کمی هم سود برای ادمین)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 **کیف پول و تراکنش‌ها**
─────────────────
💸 **واریز:** فیش واریزی رو بفرست، ادمین تأیید میکنه
💳 **برداشت:** حداقل ۱۰۰,۰۰۰ تومان، تا ۲۴ ساعت واریز میشه
🎁 **دعوت دوستان:** با ۲۰ دعوت، ۵۰,۰۰۰ تومان جایزه

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⭐ **سیستم سطوح و امتیازات**
─────────────────
🌱 تازه‌کار → ۰ XP
🌟 ستاره نوظهور → ۱۰۰ XP
⚡ جنگجوی بازار → ۲۵۰ XP
🎯 تیرانداز دقیق → ۵۰۰ XP
🏅 برنزی → ۸۰۰ XP
🥈 نقره‌ای → ۱۲۰۰ XP
🥇 طلایی → ۱۷۰۰ XP
💎 پلاتینیوم → ۲۳۰۰ XP
👑 سلطان بازار → ۳۰۰۰ XP
🌈 افسانه‌ای → ۴۰۰۰ XP

🎁 هر سطح پاداش نقدی داره!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🛡️ **قوانین مهم**
─────────────────
✅ بازی شرافتمندانه و منصفانه
✅ ربات‌ها فقط برای پر کردن اتاق هستن
✅ بردها به صورت خودکار به کیف پول اضافه میشن
✅ پشتیبانی ۲۴ ساعته برای رفع مشکلات
❌ کلاهبرداری و تقلب = بن دائمی

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📞 **پشتیبانی:** از دکمه 🆘 پشتیبانی 🎫 استفاده کن

🎯 **شانس مال کسیه که تلاش کنه! همین حالا شروع کن!** 🎯"""
    
    bot.send_message(
        message.from_user.id, 
        msg_fancy(help_text), 
        parse_mode="HTML"
    )

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda message: message.text == "🆘 پشتیبانی 🎫")
def support_handler(message):
    user_id = str(message.from_user.id)
    bot.send_message(
        user_id, 
        msg_fancy("📝 مشکل یا پیام خودت رو بنویس. یک کد تیکت دریافت می‌کنی:"), 
        parse_mode="HTML"
    )
    bot.register_next_step_handler(message, lambda m: create_ticket(m, user_id))

def create_ticket(message, user_id):
    ticket_id = hashlib.md5(f"{user_id}{time.time()}".encode()).hexdigest()[:8].upper()
    
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('INSERT INTO tickets (ticket_id, user_id, user_name, message) VALUES (%s, %s, %s, %s)',
                  (ticket_id, user_id, message.from_user.first_name, message.text))
    else:
        c.execute('INSERT INTO tickets (ticket_id, user_id, user_name, message) VALUES (?, ?, ?, ?)',
                  (ticket_id, user_id, message.from_user.first_name, message.text))
    conn.commit()
    conn.close()
    
    bot.send_message(
        user_id, 
        msg_fancy(f"✅ تیکت شما با کد `{ticket_id}` ثبت شد! به زودی پاسخ داده میشه."), 
        parse_mode="HTML"
    )
    
    for admin_id in get_admins():
        try:
            bot.send_message(
                admin_id, 
                msg_fancy(f"🎫 تیکت جدید\n🆔 کد: {ticket_id}\n👤 کاربر: {message.from_user.first_name}\n📝 پیام: {message.text[:200]}"), 
                parse_mode="HTML"
            )
        except:
            pass

# ==================== پاسخ به تیکت ====================
@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_ticket_"))
def reply_ticket(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "🚫 دسترسی غیرمجاز!")
        return
    
    ticket_id = call.data.split("_")[2]
    support_chats[str(call.from_user.id)] = {"ticket_id": ticket_id, "action": "reply"}
    
    bot.send_message(
        call.from_user.id, 
        msg_fancy(f"📝 پاسخ خود را برای تیکت {ticket_id} بنویسید:"),
        parse_mode="HTML"
    )
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: str(message.from_user.id) in support_chats and support_chats[str(message.from_user.id)]["action"] == "reply")
def handle_ticket_reply(message):
    admin_id = str(message.from_user.id)
    ticket_id = support_chats[admin_id]["ticket_id"]
    
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('SELECT user_id FROM tickets WHERE ticket_id = %s', (ticket_id,))
    else:
        c.execute('SELECT user_id FROM tickets WHERE ticket_id = ?', (ticket_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        user_id = result[0]
        reply_text = f"""📩 **پاسخ ادمین به تیکت {ticket_id}**

{message.text}

📌 برای پاسخ، روی دکمه زیر کلیک کنید."""
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📨 پاسخ به ادمین", callback_data=f"reply_to_admin_{ticket_id}"))
        
        bot.send_message(user_id, msg_fancy(reply_text), parse_mode="HTML", reply_markup=markup)
        bot.send_message(admin_id, msg_fancy(f"✅ پاسخ شما به تیکت {ticket_id} ارسال شد."), parse_mode="HTML")
        
        conn = get_db()
        c = conn.cursor()
        if DATABASE_URL:
            c.execute('UPDATE tickets SET status = %s WHERE ticket_id = %s', ('closed', ticket_id))
        else:
            c.execute('UPDATE tickets SET status = "closed" WHERE ticket_id = ?', (ticket_id,))
        conn.commit()
        conn.close()
    
    del support_chats[admin_id]

@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_to_admin_"))
def reply_to_admin(call):
    ticket_id = call.data.split("_")[3]
    user_id = str(call.from_user.id)
    
    support_chats[user_id] = {"ticket_id": ticket_id, "action": "user_reply"}
    bot.send_message(user_id, msg_fancy("📝 پاسخ خود را بنویسید:"), parse_mode="HTML")
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: str(message.from_user.id) in support_chats and support_chats[str(message.from_user.id)]["action"] == "user_reply")
def handle_user_ticket_reply(message):
    user_id = str(message.from_user.id)
    ticket_id = support_chats[user_id]["ticket_id"]
    
    for admin_id in get_admins():
        try:
            bot.send_message(
                admin_id, 
                msg_fancy(f"📩 پاسخ کاربر به تیکت {ticket_id}:\n\n{message.text}"), 
                parse_mode="HTML"
            )
        except:
            pass
    
    bot.send_message(user_id, msg_fancy("✅ پاسخ شما به ادمین ارسال شد."), parse_mode="HTML")
    del support_chats[user_id]

# ==================== پنل ادمین ====================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.from_user.id, msg_fancy("🚫 دسترسی غیرمجاز!"), parse_mode="HTML")
        return
    
    bot.send_message(
        message.from_user.id, 
        msg_fancy("🎛️ **پنل مدیریت سلطان لوتو** 🎛️"), 
        parse_mode="HTML", 
        reply_markup=get_admin_keyboard()
    )

# ==================== آمار ربات ====================
@bot.message_handler(func=lambda message: message.text == "📊 آمار ربات 📈")
def admin_stats(message):
    if not is_admin(message.from_user.id):
        return
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM users')
    users_count = c.fetchone()[0]
    
    c.execute('SELECT SUM(wallet) FROM users')
    total_wallet = c.fetchone()[0] or 0
    
    c.execute('SELECT SUM(amount) FROM admin_earnings WHERE withdrawn = 0')
    pending_profit = c.fetchone()[0] or 0
    
    c.execute('SELECT SUM(amount) FROM admin_earnings')
    total_profit = c.fetchone()[0] or 0
    
    deposits, withdrawals, profits = get_shift_stats()
    
    conn.close()
    
    text = f"""📊 **آمار ربات** 📊

👥 کل کاربران: {users_count}
💰 مجموع کیف پول‌ها: {total_wallet:,} تومان

💎 سود معوقه: {pending_profit:,} تومان
💰 سود کل: {total_profit:,} تومان

📊 آمار شیفت فعلی:
   💸 واریزها: {deposits:,} تومان
   💳 برداشتها: {withdrawals:,} تومان
   💰 سود شیفت: {profits:,} تومان"""
    bot.send_message(message.from_user.id, msg_fancy(text), parse_mode="HTML")

# ==================== مدیریت سود ====================
@bot.message_handler(func=lambda message: message.text == "💰 مدیریت سود 💰")
def profit_management(message):
    if not is_admin(message.from_user.id):
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT SUM(amount) FROM admin_earnings WHERE withdrawn = 0')
    pending = c.fetchone()[0] or 0
    c.execute('SELECT SUM(amount) FROM admin_earnings')
    total = c.fetchone()[0] or 0
    conn.close()
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💸 برداشت سود", callback_data="withdraw_profit"))
    
    text = f"""💰 **مدیریت سود** 💰

💎 سود معوقه: {pending:,} تومان
💰 سود کل تا الان: {total:,} تومان

📌 سود ۳۰% از هر بازی لوتو و ۱۵% از سنگ کاغذ قیچی به اینجا اضافه میشه
📌 برای برداشت، دکمه زیر رو بزن"""
    bot.send_message(
        message.from_user.id, 
        msg_fancy(text), 
        parse_mode="HTML", 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "withdraw_profit")
def withdraw_profit(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "🚫 دسترسی غیرمجاز!")
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT SUM(amount) FROM admin_earnings WHERE withdrawn = 0')
    pending = c.fetchone()[0] or 0
    
    if pending == 0:
        bot.answer_callback_query(call.id, "💰 سودی برای برداشت وجود ندارد!")
        return
    
    c.execute('UPDATE admin_earnings SET withdrawn = 1 WHERE withdrawn = 0')
    conn.commit()
    conn.close()
    
    bot.edit_message_text(
        msg_fancy(f"✅ مبلغ {pending:,} تومان از سود با موفقیت برداشت شد! 💰"), 
        call.from_user.id, 
        call.message.message_id, 
        parse_mode="HTML"
    )
    bot.answer_callback_query(call.id, f"✅ {pending:,} تومان برداشت شد!")

# ==================== تیکت‌ها ====================
@bot.message_handler(func=lambda message: message.text == "🎫 تیکت‌ها 🎫")
def admin_tickets(message):
    if not is_admin(message.from_user.id):
        return
    
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('SELECT ticket_id, user_name, message, status FROM tickets WHERE status = %s ORDER BY created_at DESC', ('open',))
    else:
        c.execute('SELECT ticket_id, user_name, message, status FROM tickets WHERE status = "open" ORDER BY created_at DESC')
    tickets = c.fetchall()
    conn.close()
    
    if not tickets:
        bot.send_message(message.from_user.id, msg_fancy("📭 هیچ تیکت باز وجود ندارد!"), parse_mode="HTML")
        return
    
    for ticket in tickets:
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("📨 پاسخ", callback_data=f"reply_ticket_{ticket[0]}"),
            InlineKeyboardButton("✅ بستن", callback_data=f"close_ticket_{ticket[0]}")
        )
        text = f"""🎫 **تیکت #{ticket[0]}**
👤 کاربر: {ticket[1]}
📝 پیام: {ticket[2][:100]}
📌 وضعیت: {'🟢 باز' if ticket[3] == 'open' else '🔴 بسته'}"""
        bot.send_message(message.from_user.id, msg_fancy(text), parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("close_ticket_"))
def close_ticket(call):
    ticket_id = call.data.split("_")[2]
    
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('UPDATE tickets SET status = %s WHERE ticket_id = %s', ('closed', ticket_id))
    else:
        c.execute('UPDATE tickets SET status = "closed" WHERE ticket_id = ?', (ticket_id,))
    conn.commit()
    conn.close()
    
    bot.edit_message_text(
        msg_fancy(f"✅ تیکت #{ticket_id} بسته شد!"), 
        call.from_user.id, 
        call.message.message_id, 
        parse_mode="HTML"
    )
    bot.answer_callback_query(call.id, "تیکت بسته شد!")

# ==================== درخواست‌ها ====================
@bot.message_handler(func=lambda message: message.text == "📋 درخواست‌ها 📋")
def view_requests(message):
    if not is_admin(message.from_user.id, "view_requests"):
        bot.send_message(message.from_user.id, msg_fancy("🚫 دسترسی نداری!"), parse_mode="HTML")
        return
    
    if not pending_wallet_requests and not pending_withdrawal_requests:
        bot.send_message(message.from_user.id, msg_fancy("📭 هیچ درخواستی وجود ندارد!"), parse_mode="HTML")
        return
    
    for req_id, req in pending_wallet_requests.items():
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ تأیید", callback_data=f"approve_wallet_{req_id}"),
            InlineKeyboardButton("❌ رد", callback_data=f"reject_wallet_{req_id}")
        )
        bot.send_message(
            message.from_user.id, 
            msg_fancy(f"📦 واریز از {req['user_name']}\n💰 {req['amount']:,} تومان"), 
            parse_mode="HTML", 
            reply_markup=markup
        )
    
    for req_id, req in pending_withdrawal_requests.items():
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ تأیید", callback_data=f"approve_withdraw_{req_id}"),
            InlineKeyboardButton("❌ رد", callback_data=f"reject_withdraw_{req_id}")
        )
        bot.send_message(
            message.from_user.id, 
            msg_fancy(f"📦 برداشت از {req['user_name']}\n💰 {req['amount']:,} تومان\n🏦 {req['card_number']}"), 
            parse_mode="HTML", 
            reply_markup=markup
        )

# ==================== هدیه پول ====================
@bot.message_handler(func=lambda message: message.text == "🎁 هدیه پول 🎁")
def gift_cash(message):
    if not is_admin(message.from_user.id, "gift_cash"):
        bot.send_message(message.from_user.id, msg_fancy("🚫 دسترسی نداری!"), parse_mode="HTML")
        return
    
    bot.send_message(message.from_user.id, msg_fancy("🆔 آیدی کاربر رو وارد کن:"), parse_mode="HTML")
    bot.register_next_step_handler(message, lambda m: get_gift_user(m))

def get_gift_user(message):
    try:
        target_id = str(int(message.text.strip()))
        bot.send_message(message.from_user.id, msg_fancy("💰 مبلغ (تومان) رو وارد کن:"), parse_mode="HTML")
        bot.register_next_step_handler(message, lambda m: send_gift(m, target_id))
    except:
        bot.send_message(message.from_user.id, msg_fancy("⚠️ آیدی نامعتبر!"), parse_mode="HTML")

def send_gift(message, target_id):
    try:
        amount = int(message.text.strip())
        update_wallet(target_id, amount)
        bot.send_message(
            message.from_user.id, 
            msg_fancy(f"✅ {amount:,} تومان به {target_id} هدیه شد! 🎁"), 
            parse_mode="HTML"
        )
        bot.send_message(
            target_id, 
            msg_fancy(f"🎁 {amount:,} تومان از طرف ادمین به کیف پولت اضافه شد! 🎉"), 
            parse_mode="HTML"
        )
    except:
        bot.send_message(message.from_user.id, msg_fancy("⚠️ مبلغ نامعتبر!"), parse_mode="HTML")

# ==================== واریز به کاربر ====================
@bot.message_handler(func=lambda message: message.text == "💸 واریز به کاربر 💸")
def deposit_to_user(message):
    if not is_admin(message.from_user.id, "deposit_user"):
        bot.send_message(message.from_user.id, msg_fancy("🚫 دسترسی نداری!"), parse_mode="HTML")
        return
    
    bot.send_message(message.from_user.id, msg_fancy("🆔 آیدی کاربر رو وارد کن:"), parse_mode="HTML")
    bot.register_next_step_handler(message, lambda m: get_deposit_user(m))

def get_deposit_user(message):
    try:
        target_id = str(int(message.text.strip()))
        bot.send_message(message.from_user.id, msg_fancy("💰 مبلغ (تومان) رو وارد کن:"), parse_mode="HTML")
        bot.register_next_step_handler(message, lambda m: send_deposit(m, target_id))
    except:
        bot.send_message(message.from_user.id, msg_fancy("⚠️ آیدی نامعتبر!"), parse_mode="HTML")

def send_deposit(message, target_id):
    try:
        amount = int(message.text.strip())
        update_wallet(target_id, amount)
        update_shift_stats(deposits=amount)
        
        bot.send_message(
            message.from_user.id, 
            msg_fancy(f"✅ {amount:,} تومان به {target_id} واریز شد! 💸"), 
            parse_mode="HTML"
        )
        bot.send_message(
            target_id, 
            msg_fancy(f"💸 {amount:,} تومان به کیف پولت واریز شد! 🎉"), 
            parse_mode="HTML"
        )
    except:
        bot.send_message(message.from_user.id, msg_fancy("⚠️ مبلغ نامعتبر!"), parse_mode="HTML")

# ==================== تنظیمات ادمین ====================
@bot.message_handler(func=lambda message: message.text == "⚙️ تنظیمات ادمین ⚙️")
def admin_settings(message):
    if not is_admin(message.from_user.id, "add_admin"):
        bot.send_message(message.from_user.id, msg_fancy("🚫 فقط ادمین اصلی!"), parse_mode="HTML")
        return
    
    bot.send_message(
        message.from_user.id, 
        msg_fancy("⚙️ **تنظیمات ادمین** ⚙️"), 
        parse_mode="HTML", 
        reply_markup=get_admin_settings_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == "➕ افزودن ادمین 👤")
def add_admin(message):
    if not is_admin(message.from_user.id, "add_admin"):
        return
    
    bot.send_message(message.from_user.id, msg_fancy("🆔 آیدی عددی ادمین جدید رو وارد کن:"), parse_mode="HTML")
    bot.register_next_step_handler(message, lambda m: add_admin_id(m))

def add_admin_id(message):
    try:
        new_id = str(int(message.text.strip()))
        
        conn = get_db()
        c = conn.cursor()
        if DATABASE_URL:
            c.execute('SELECT * FROM admins WHERE user_id = %s', (new_id,))
        else:
            c.execute('SELECT * FROM admins WHERE user_id = ?', (new_id,))
        if c.fetchone():
            bot.send_message(message.from_user.id, msg_fancy("🚫 این آیدی قبلاً ادمینه!"), parse_mode="HTML")
            conn.close()
            return
        
        bot.send_message(message.from_user.id, msg_fancy("📛 لقب ادمین رو وارد کن:"), parse_mode="HTML")
        bot.register_next_step_handler(message, lambda m: add_admin_nickname(m, new_id))
        conn.close()
    except:
        bot.send_message(message.from_user.id, msg_fancy("⚠️ آیدی نامعتبر!"), parse_mode="HTML")

def add_admin_nickname(message, new_id):
    nickname = message.text.strip()
    
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('INSERT INTO admins (user_id, nickname, can_view_requests, can_change_shift) VALUES (%s, %s, 1, 1)',
                  (new_id, nickname))
    else:
        c.execute('INSERT INTO admins (user_id, nickname, can_view_requests, can_change_shift) VALUES (?, ?, 1, 1)',
                  (new_id, nickname))
    conn.commit()
    conn.close()
    
    bot.send_message(
        message.from_user.id, 
        msg_fancy(f"✅ ادمین {nickname} با آیدی {new_id} اضافه شد! 👤"), 
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda message: message.text == "➖ حذف ادمین 👤")
def remove_admin(message):
    if not is_admin(message.from_user.id, "remove_admin"):
        return
    
    bot.send_message(message.from_user.id, msg_fancy("🆔 آیدی ادمین برای حذف رو وارد کن:"), parse_mode="HTML")
    bot.register_next_step_handler(message, lambda m: remove_admin_id(m))

def remove_admin_id(message):
    try:
        remove_id = str(int(message.text.strip()))
        
        if remove_id == MAIN_ADMIN_ID:
            bot.send_message(message.from_user.id, msg_fancy("🚫 نمی‌تونی ادمین اصلی رو حذف کنی!"), parse_mode="HTML")
            return
        
        conn = get_db()
        c = conn.cursor()
        if DATABASE_URL:
            c.execute('DELETE FROM admins WHERE user_id = %s', (remove_id,))
        else:
            c.execute('DELETE FROM admins WHERE user_id = ?', (remove_id,))
        conn.commit()
        conn.close()
        
        bot.send_message(message.from_user.id, msg_fancy(f"✅ ادمین {remove_id} حذف شد!"), parse_mode="HTML")
    except:
        bot.send_message(message.from_user.id, msg_fancy("⚠️ آیدی نامعتبر!"), parse_mode="HTML")

@bot.message_handler(func=lambda message: message.text == "🔑 دسترسی ادمین 🔐")
def set_access(message):
    if not is_admin(message.from_user.id, "set_access"):
        return
    
    bot.send_message(message.from_user.id, msg_fancy("🆔 آیدی ادمین رو وارد کن:"), parse_mode="HTML")
    bot.register_next_step_handler(message, lambda m: set_access_admin(m))

def set_access_admin(message):
    try:
        admin_id = str(int(message.text.strip()))
        
        conn = get_db()
        c = conn.cursor()
        if DATABASE_URL:
            c.execute('SELECT * FROM admins WHERE user_id = %s', (admin_id,))
        else:
            c.execute('SELECT * FROM admins WHERE user_id = ?', (admin_id,))
        if not c.fetchone():
            bot.send_message(message.from_user.id, msg_fancy("🚫 ادمین یافت نشد!"), parse_mode="HTML")
            conn.close()
            return
        conn.close()
        
        text = """🔑 **کلیدهای دسترسی:**
- add_admin (افزودن ادمین)
- remove_admin (حذف ادمین)
- set_access (تنظیم دسترسی)
- reset_bot (ریست ربات)
- gift_cash (هدیه پول)
- deposit_user (واریز به کاربر)
- view_requests (مشاهده درخواست‌ها)
- change_shift (تغییر شیفت)

کلید مورد نظر رو وارد کن:"""
        bot.send_message(message.from_user.id, msg_fancy(text), parse_mode="HTML")
        bot.register_next_step_handler(message, lambda m: set_access_key(m, admin_id))
    except:
        bot.send_message(message.from_user.id, msg_fancy("⚠️ آیدی نامعتبر!"), parse_mode="HTML")

def set_access_key(message, admin_id):
    key = message.text.strip()
    valid_keys = ['add_admin', 'remove_admin', 'set_access', 'reset_bot', 'gift_cash', 'deposit_user', 'view_requests', 'change_shift']
    
    if key not in valid_keys:
        bot.send_message(message.from_user.id, msg_fancy("🚫 کلید نامعتبر!"), parse_mode="HTML")
        return
    
    bot.send_message(message.from_user.id, msg_fancy("✅ فعال (1) یا غیرفعال (0):"), parse_mode="HTML")
    bot.register_next_step_handler(message, lambda m: set_access_value(m, admin_id, key))

def set_access_value(message, admin_id, key):
    value = message.text.strip()
    if value not in ['0', '1']:
        bot.send_message(message.from_user.id, msg_fancy("🚫 فقط 0 یا 1!"), parse_mode="HTML")
        return
    
    col_map = {
        "add_admin": "can_add_admin", 
        "remove_admin": "can_remove_admin", 
        "set_access": "can_set_access",
        "reset_bot": "can_reset_bot", 
        "gift_cash": "can_gift_cash", 
        "deposit_user": "can_deposit_user",
        "view_requests": "can_view_requests", 
        "change_shift": "can_change_shift"
    }
    
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute(f'UPDATE admins SET {col_map[key]} = %s WHERE user_id = %s', (int(value), admin_id))
    else:
        c.execute(f'UPDATE admins SET {col_map[key]} = ? WHERE user_id = ?', (int(value), admin_id))
    conn.commit()
    conn.close()
    
    status = "فعال ✅" if value == '1' else "غیرفعال ❌"
    bot.send_message(
        message.from_user.id, 
        msg_fancy(f"✅ دسترسی {key} برای ادمین {admin_id} {status} شد!"), 
        parse_mode="HTML"
    )

# ==================== تغییر شیفت ====================
@bot.message_handler(func=lambda message: message.text == "🔄 تغییر شیفت 🔄")
def change_shift(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.from_user.id, msg_fancy("🚫 فقط ادمین‌ها دسترسی دارن!"), parse_mode="HTML")
        return
    
    current = get_current_shift()
    if current:
        start_time = datetime.datetime.fromtimestamp(current['start_time']).strftime('%Y/%m/%d %H:%M')
        shift_text = f"""📊 **شیفت فعلی:**

👤 ادمین: {current['nickname']}
🕐 شروع: {start_time}
💸 واریزها: {current['deposits']:,} تومان
💳 برداشتها: {current['withdrawals']:,} تومان
💰 سود شیفت: {current['profits']:,} تومان
━━━━━━━━━━━━━━━━━━━
"""
        bot.send_message(message.from_user.id, msg_fancy(shift_text), parse_mode="HTML")
    else:
        bot.send_message(message.from_user.id, msg_fancy("📭 هنوز شیفتی ثبت نشده!"), parse_mode="HTML")
    
    bot.send_message(message.from_user.id, msg_fancy("🏦 **شماره کارت جدید** رو وارد کن (۱۶ رقم):"), parse_mode="HTML")
    bot.register_next_step_handler(message, lambda m: update_shift_card(m))

def update_shift_card(message):
    card = message.text.strip()
    card = re.sub(r'[\s\-_]+', '', card)
    
    if not card.isdigit() or len(card) != 16:
        bot.send_message(message.from_user.id, msg_fancy("⚠️ شماره کارت باید ۱۶ رقم باشد!"), parse_mode="HTML")
        bot.register_next_step_handler(message, lambda m: update_shift_card(m))
        return
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        if DATABASE_URL:
            c.execute('UPDATE settings SET value = %s WHERE key = %s', (card, 'current_card'))
        else:
            c.execute('UPDATE settings SET value = ? WHERE key = "current_card"', (card,))
        
        admin_nick = "ادمین"
        if DATABASE_URL:
            c.execute('SELECT nickname FROM admins WHERE user_id = %s', (str(message.from_user.id),))
        else:
            c.execute('SELECT nickname FROM admins WHERE user_id = ?', (str(message.from_user.id),))
        r = c.fetchone()
        if r:
            admin_nick = r[0]
        
        if DATABASE_URL:
            c.execute('''INSERT INTO shift_stats 
                        (admin_id, nickname, start_time, deposits, withdrawals, profits) 
                        VALUES (%s, %s, %s, 0, 0, 0)''', 
                      (str(message.from_user.id), admin_nick, time.time()))
        else:
            c.execute('''INSERT INTO shift_stats 
                        (admin_id, nickname, start_time, deposits, withdrawals, profits) 
                        VALUES (?, ?, ?, 0, 0, 0)''', 
                      (str(message.from_user.id), admin_nick, time.time()))
        
        conn.commit()
        
        bot.send_message(
            message.from_user.id, 
            msg_fancy(f"✅ **شیفت با موفقیت تحویل گرفته شد!**\n\n🏦 **کارت جدید:** `{card}`\n📛 **لقب ادمین:** {admin_nick}\n\n🕐 **زمان شروع:** {datetime.datetime.now().strftime('%Y/%m/%d %H:%M')}"), 
            parse_mode="HTML"
        )
        
    except Exception as e:
        conn.rollback()
        bot.send_message(message.from_user.id, msg_fancy(f"⚠️ خطا در ثبت شیفت: {str(e)}"), parse_mode="HTML")
    
    finally:
        conn.close()

# ==================== ریست ربات ====================
@bot.message_handler(func=lambda message: message.text == "🔄 ریست ربات 🔄")
def reset_bot(message):
    if not is_admin(message.from_user.id, "reset_bot"):
        bot.send_message(message.from_user.id, msg_fancy("🚫 دسترسی نداری!"), parse_mode="HTML")
        return
    
    conn = get_db()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute('DELETE FROM users WHERE user_id != %s', (MAIN_ADMIN_ID,))
    else:
        c.execute('DELETE FROM users WHERE user_id != ?', (MAIN_ADMIN_ID,))
    c.execute('DELETE FROM invites')
    c.execute('DELETE FROM invited_users')
    c.execute('DELETE FROM pending_deposits')
    c.execute('DELETE FROM pending_withdrawals')
    c.execute('DELETE FROM tickets')
    c.execute('DELETE FROM admin_earnings')
    c.execute('DELETE FROM active_games')
    conn.commit()
    conn.close()
    
    global waiting_players, lotto_games, pending_wallet_requests, pending_withdrawal_requests, rps_waiting, rps_games
    waiting_players = {}
    lotto_games = {}
    pending_wallet_requests = {}
    pending_withdrawal_requests = {}
    rps_waiting = {}
    rps_games = {}
    
    bot.send_message(
        message.from_user.id, 
        msg_fancy("🎉 ربات با موفقیت ریست شد! همه داده‌ها پاک شدن."), 
        parse_mode="HTML"
    )

# ==================== بازگشت ====================
@bot.message_handler(func=lambda message: message.text == "↩️ بازگشت 🏠" or message.text == "↩️ بازگشت به منوی اصلی 🏠")
def back_to_main(message):
    bot.send_message(
        message.from_user.id, 
        msg_fancy("🔙 بازگشت به منوی اصلی"), 
        parse_mode="HTML", 
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == "↩️ بازگشت 🔙" or message.text == "↩️ بازگشت به پنل ادمین 🔙")
def back_to_admin(message):
    bot.send_message(
        message.from_user.id, 
        msg_fancy("🔙 بازگشت به پنل ادمین"), 
        parse_mode="HTML", 
        reply_markup=get_admin_keyboard()
    )

# ==================== پیام همگانی ====================
@bot.message_handler(func=lambda message: message.text == "📢 پیام همگانی 📢")
def broadcast_handler(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.from_user.id, msg_fancy("🚫 دسترسی غیرمجاز!"), parse_mode="HTML")
        return
    
    bot.send_message(
        message.from_user.id, 
        msg_fancy("📝 **پیام خود را بنویسید:**\n\n⚠️ این پیام برای **همه کاربران** ارسال میشه!"), 
        parse_mode="HTML"
    )
    bot.register_next_step_handler(message, send_broadcast)

def send_broadcast(message):
    admin_id = str(message.from_user.id)
    broadcast_text = message.text
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    users = c.fetchall()
    conn.close()
    
    if not users:
        bot.send_message(admin_id, msg_fancy("📭 هیچ کاربری در دیتابیس وجود ندارد!"), parse_mode="HTML")
        return
    
    pending_broadcasts[admin_id] = broadcast_text
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ بله، ارسال کن", callback_data=f"confirm_broadcast_{admin_id}"),
        InlineKeyboardButton("❌ لغو", callback_data="cancel_broadcast")
    )
    
    preview_text = f"""📢 **پیش‌نمایش پیام همگانی:**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{broadcast_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👥 **تعداد گیرندگان:** {len(users)} نفر

⚠️ آیا مطمئنی؟"""
    
    bot.send_message(
        admin_id, 
        msg_fancy(preview_text), 
        parse_mode="HTML", 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_broadcast_"))
def confirm_broadcast(call):
    admin_id = call.data.split("_")[2]
    
    if str(call.from_user.id) != admin_id:
        bot.answer_callback_query(call.id, "🚫 این دکمه برای شما نیست!")
        return
    
    broadcast_text = pending_broadcasts.get(admin_id, "پیام همگانی")
    
    bot.edit_message_text(
        msg_fancy("⏳ **در حال ارسال پیام همگانی...**\n\nلطفاً صبر کنید..."), 
        call.from_user.id, 
        call.message.message_id, 
        parse_mode="HTML"
    )
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    users = c.fetchall()
    conn.close()
    
    success_count = 0
    fail_count = 0
    
    for user in users:
        user_id = user[0]
        try:
            bot.send_message(user_id, msg_fancy(f"📢 **پیام همگانی از ادمین:**\n\n{broadcast_text}"), parse_mode="HTML")
            success_count += 1
        except:
            fail_count += 1
        time.sleep(0.05)
    
    if admin_id in pending_broadcasts:
        del pending_broadcasts[admin_id]
    
    result_text = f"""📊 **گزارش ارسال پیام همگانی:**

✅ **موفق:** {success_count} نفر
❌ **ناموفق:** {fail_count} نفر
👥 **کل کاربران:** {len(users)} نفر

📝 **متن پیام:**
{broadcast_text[:100]}{'...' if len(broadcast_text) > 100 else ''}"""
    
    bot.edit_message_text(
        msg_fancy(result_text), 
        call.from_user.id, 
        call.message.message_id, 
        parse_mode="HTML"
    )
    
    bot.answer_callback_query(call.id, "✅ پیام همگانی ارسال شد!")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_broadcast")
def cancel_broadcast(call):
    admin_id = str(call.from_user.id)
    if admin_id in pending_broadcasts:
        del pending_broadcasts[admin_id]
    
    bot.edit_message_text(
        msg_fancy("❌ **ارسال پیام همگانی لغو شد!**"), 
        call.from_user.id, 
        call.message.message_id, 
        parse_mode="HTML"
    )
    bot.answer_callback_query(call.id, "❌ لغو شد!")

# ==================== اجرا ====================
if __name__ == "__main__":
    print("""
    🎰 𝙇𝙊𝙏𝙏𝙊 𝙆𝙄𝙉𝙂 - سلطان لوتو 🎰
    
    ✅ ۷ اتاق لوتو فانتزی
    ✅ ۵ اتاق سنگ کاغذ قیچی
    ✅ سطوح فانتزی (تازه‌کار تا افسانه‌ای)
    ✅ تالار مشاهیر
    ✅ مدیریت سود (۳۰% لوتو - ۱۵% سنگ کاغذ قیچی)
    ✅ سیستم تیکت با پاسخ
    ✅ مشاهده صف انتظار
    ✅ تغییر شیفت
    ✅ ربات‌های ساختگی با اسم‌های معمولی (بی‌صدا)
    ✅ اگه ربات برنده شد، پول کاربرا به سود ادمین
    ✅ اگه کاربر برنده شد، پول کاربرا به برنده + سود ادمین
    """)
    print("🤖 ربات در حال اجراست...")
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"⚠️ خطا: {e}")
            time.sleep(5)
