import telebot
import time
import json
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8842710767:AAFUmyxxdQIcWvOLL8qRmsBZgvcywqw18Qs"

bot = telebot.TeleBot(BOT_TOKEN)

def load_users():
    if os.path.exists("users.json"):
        with open("users.json", "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f)

def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("⛏️ Mine WOLF", callback_data="mine"))
    markup.row(InlineKeyboardButton("💰 Balance", callback_data="balance"),
               InlineKeyboardButton("🏆 Top Miners", callback_data="top"))
    markup.row(InlineKeyboardButton("👥 Invite Friends", callback_data="invite"))
    return markup

@bot.message_handler(commands=["start"])
def start(message):
    users = load_users()
    user_id = str(message.from_user.id)
    if user_id not in users:
        users[user_id] = {
            "balance": 0,
            "last_mine": 0,
            "username": message.from_user.first_name
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
        users[user_id] = {"balance": 0, "last_mine": 0, "username": call.from_user.first_name}
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
    bot.edit_message_text(f"""
💰 *Your Wolf Coin Balance*

👤 {call.from_user.first_name}
🐺 Balance: {users[user_id]['balance']} WOLF
    """, call.message.chat.id, call.message.message_id,
    parse_mode="Markdown", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "top")
def top(call):
    users = load_users()
    sorted_users = sorted(users.items(), key=lambda x: x[1]["balance"], reverse=True)[:10]
    text = "🏆 *Top Wolf Miners:*\n\n"
    for i, (uid, data) in enumerate(sorted_users, 1):
        text += f"{i}. {data['username']} — {data['balance']} WOLF\n"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
    parse_mode="Markdown", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "invite")
def invite(call):
    bot.edit_message_text(f"""
👥 *Invite Friends!*

🔗 Your invite link:
t.me/WolfCoinMineBot?start={call.from_user.id}

🎁 Share karo aur rewards pao!
    """, call.message.chat.id, call.message.message_id,
    parse_mode="Markdown", reply_markup=main_menu())

print("🐺 Wolf Coin Bot Starting...")
bot.infinity_polling()
