import telebot
import time
import json
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import urllib.request

BOT_TOKEN = os.environ.get('BOT_TOKEN')
SUPABASE_URL = "https://tlxxenwpzawblplolati.supabase.co"
SUPABASE_KEY = "sb_publishable_Sk-ZZvk2Yv1lbxkQXIUSNw_prss_Rx0"

bot = telebot.TeleBot(BOT_TOKEN)

def supabase_request(method, endpoint, data=None):
    url = SUPABASE_URL + "/rest/v1/" + endpoint
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": "Bearer " + SUPABASE_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Supabase error: {e}")
        return []

def get_user(user_id):
    result = supabase_request("GET", f"users?user_id=eq.{user_id}")
    if result and len(result) > 0:
        return result[0]
    return None

def create_user(user_id, username):
    data = {
        "user_id": str(user_id),
        "username": username,
        "balance": 0,
        "last_mine": 0,
        "mine_count": 0,
        "referrals": 0
    }
    result = supabase_request("POST", "users", data)
    if result and len(result) > 0:
        return result[0]
    return data

def update_user(user_id, data):
    supabase_request("PATCH", f"users?user_id=eq.{user_id}", data)

def get_top_users():
    return supabase_request("GET", "users?order=balance.desc&limit=10")

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
    user_id = str(message.from_user.id)
    username = message.from_user.first_name
    user = get_user(user_id)
    if not user:
        parts = message.text.split()
        if len(parts) > 1:
            ref_id = parts[1]
            if ref_id != user_id:
                ref_user = get_user(ref_id)
                if ref_user:
                    update_user(ref_id, {
                        "balance": ref_user["balance"] + 50,
                        "referrals": ref_user["referrals"] + 1
                    })
        user = create_user(user_id, username)
    bot.send_message(message.chat.id, f"""
🐺 *Welcome to Wolf Coin Mining Bot!*

👋 Hello {username}!
💰 Balance: {user['balance']} WOLF

Choose an option below:
    """, parse_mode="Markdown", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "mine")
def mine(call):
    user_id = str(call.from_user.id)
    user = get_user(user_id)
    if not user:
        user = create_user(user_id, call.from_user.first_name)
    current_time = int(time.time())
    last_mine = user["last_mine"]
    cooldown = 3600
    if current_time - last_mine < cooldown:
        remaining = int(cooldown - (current_time - last_mine))
        minutes = remaining // 60
        seconds = remaining % 60
        bot.answer_callback_query(call.id, f"⏰ Wait {minutes}m {seconds}s!")
        return
    reward = 10
    update_user(user_id, {
        "balance": user["balance"] + reward,
        "last_mine": current_time,
        "mine_count": user["mine_count"] + 1
    })
    bot.edit_message_text(f"""
⛏️ *Mining Successful!*

🐺 You mined {reward} WOLF!
💰 Total Balance: {user['balance'] + reward} WOLF
⏰ Mine again in 1 hour!
    """, call.message.chat.id, call.message.message_id,
    parse_mode="Markdown", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "balance")
def balance(call):
    user_id = str(call.from_user.id)
    user = get_user(user_id)
    if not user:
        bot.answer_callback_query(call.id, "❌ First use /start!")
        return
    bot.edit_message_text(f"""
💰 *Your Wolf Coin Balance*

👤 {call.from_user.first_name}
🐺 Balance: {user['balance']} WOLF
⛏️ Times Mined: {user['mine_count']}
👥 Referrals: {user['referrals']}
    """, call.message.chat.id, call.message.message_id,
    parse_mode="Markdown", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "top")
def top(call):
    users = get_top_users()
    text = "🏆 *Top Wolf Miners:*\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(users):
        medal = medals[i] if i < 3 else str(i+1)
        text += f"{medal} {u['username']} — {u['balance']} WOLF\n"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
    parse_mode="Markdown", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "invite")
def invite(call):
    user_id = str(call.from_user.id)
    user = get_user(user_id)
    refs = user['referrals'] if user else 0
    bot.edit_message_text(f"""
👥 *Invite Friends!*

🔗 Your invite link:
`t.me/WolfCoinMineBot?start={call.from_user.id}`

👥 Your referrals: {refs}
🎁 Each referral = 50 WOLF bonus!
    """, call.message.chat.id, call.message.message_id,
    parse_mode="Markdown", reply_markup=main_menu())

class ApiHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        path = self.path
        if path.startswith('/api/user/'):
            user_id = path.split('/')[-1]
            user = get_user(user_id)
            if user:
                self.wfile.write(json.dumps(user).encode())
            else:
                self.wfile.write(json.dumps({"balance": 0, "mine_count": 0, "referrals": 0}).encode())
        elif path == '/api/top':
            users = get_top_users()
            self.wfile.write(json.dumps(users).encode())
        else:
            self.wfile.write(json.dumps({"status": "ok"}).encode())
    def log_message(self, format, *args):
        pass

def run_api():
    server = HTTPServer(('0.0.0.0', 8080), ApiHandler)
    server.serve_forever()

api_thread = threading.Thread(target=run_api)
api_thread.daemon = True
api_thread.start()

print("🐺 Wolf Coin Bot Starting with Supabase!")
bot.infinity_polling()
