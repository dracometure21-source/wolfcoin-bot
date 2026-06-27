import telebot
import time
import json
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import urllib.parse

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8842710767:AAFUmyxxdQIcWvOLL8qRmsBZgvcywqw18Qs')

bot = telebot.TeleBot(BOT_TOKEN)

USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("⛏️ Mine WOLF", callback_data="mine"))
    markup.row(
        InlineKeyboardButton("💰 Balance", callback_data="balance"),
        InlineKeyboardButton("🏆 Top Miners", callback_data="top")
    )
    markup.row(InlineKeyboardButton("👥 Invite Friends", callback_data="invite"))
    return markup

@bot.message_handler(commands=["start"])
def start(message):
    users = load_users()
    user_id = str(message.from_user.id)
    
    # Referral check
    parts = message.text.split()
    if len(parts) > 1:
        ref_id = parts[1]
        if ref_id != user_id and ref_id in users and user_id not in users:
            users[ref_id]["balance"] += 50
            users[ref_id]["referrals"] = users[ref_id].get("referrals", 0) + 1
            save_users(users)
    
    if user_id not in users:
        users[user_id] = {
            "balance": 0,
            "last_mine": 0,
            "username": message.from_user.first_name,
            "mine_count": 0,
            "referrals": 0
        }
        save_users(users)
    
    bot.send_message(message.chat.id, f"""
🐺 *Welcome to Wolf Coin Mining Bot!*

👋 Hello {message.from_user.first_name}!
💰 Balance: {users[user_id]['balance']} WOLF

Choose an option below:
    """, parse_mode="Markdown", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "mine")
def mine(call):
    users = load_users()
    user_id = str(call.from_user.id)
    if user_id not in users:
        users[user_id] = {"balance": 0, "last_mine": 0, "username": call.from_user.first_name, "mine_count": 0, "referrals": 0}
    
    current_time = time.time()
    last_mine = users[user_id]["last_mine"]
    cooldown = 3600
    
    if current_time - last_mine < cooldown:
        remaining = int(cooldown - (current_time - last_mine))
        minutes = remaining // 60
        seconds = remaining % 60
        bot.answer_callback_query(call.id, f"⏰ Wait {minutes}m {seconds}s!")
        return
    
    reward = 10
    users[user_id]["balance"] += reward
    users[user_id]["last_mine"] = current_time
    users[user_id]["mine_count"] = users[user_id].get("mine_count", 0) + 1
    save_users(users)
    
    bot.edit_message_text(f"""
⛏️ *Mining Successful!*

🐺 You mined {reward} WOLF!
💰 Total Balance: {users[user_id]['balance']} WOLF
⏰ Mine again in 1 hour!
    """, call.message.chat.id, call.message.message_id,
    parse_mode="Markdown", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "balance")
def balance(call):
    users = load_users()
    user_id = str(call.from_user.id)
    if user_id not in users:
        bot.answer_callback_query(call.id, "❌ First use /start!")
        return
    u = users[user_id]
    bot.edit_message_text(f"""
💰 *Your Wolf Coin Balance*

👤 {call.from_user.first_name}
🐺 Balance: {u['balance']} WOLF
⛏️ Times Mined: {u.get('mine_count', 0)}
👥 Referrals: {u.get('referrals', 0)}
    """, call.message.chat.id, call.message.message_id,
    parse_mode="Markdown", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "top")
def top(call):
    users = load_users()
    sorted_users = sorted(users.items(), key=lambda x: x[1]["balance"], reverse=True)[:10]
    text = "🏆 *Top Wolf Miners:*\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, data) in enumerate(sorted_users, 1):
        medal = medals[i-1] if i <= 3 else str(i)
        text += f"{medal} {data['username']} — {data['balance']} WOLF\n"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
    parse_mode="Markdown", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "invite")
def invite(call):
    users = load_users()
    user_id = str(call.from_user.id)
    refs = users.get(user_id, {}).get('referrals', 0)
    bot.edit_message_text(f"""
👥 *Invite Friends!*

🔗 Your invite link:
`t.me/WolfCoinMineBot?start={call.from_user.id}`

👥 Your referrals: {refs}
🎁 Each referral = 50 WOLF bonus!
    """, call.message.chat.id, call.message.message_id,
    parse_mode="Markdown", reply_markup=main_menu())

# API Server for Mini App
class ApiHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        path = self.path
        users = load_users()
        
        if path.startswith('/api/user/'):
            user_id = path.split('/')[-1]
            if user_id in users:
                self.wfile.write(json.dumps(users[user_id]).encode())
            else:
                self.wfile.write(json.dumps({"balance": 0, "mine_count": 0, "referrals": 0}).encode())
        
        elif path == '/api/top':
            sorted_users = sorted(users.items(), key=lambda x: x[1]["balance"], reverse=True)[:10]
            top_list = [{"username": v["username"], "balance": v["balance"]} for k, v in sorted_users]
            self.wfile.write(json.dumps(top_list).encode())
        
        else:
            self.wfile.write(json.dumps({"status": "ok"}).encode())
    
    def log_message(self, format, *args):
        pass

def run_api():
    server = HTTPServer(('0.0.0.0', 8080), ApiHandler)
    server.serve_forever()

# Start API in background
api_thread = threading.Thread(target=run_api)
api_thread.daemon = True
api_thread.start()

print("🐺 Wolf Coin Bot Starting...")
bot.infinity_polling()
