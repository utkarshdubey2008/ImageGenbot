import telebot
import requests
from flask import Flask, request
from threading import Thread
from groq import Groq
import time
import random
import string
import pymongo
from pymongo import MongoClient

# Bot Configuration
API_TOKEN = '8107353617:AAEvH1iADJveysXU9QUobi6GQ9zz_rdJA4k'
GROQ_API_KEY = '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'
CHANNEL_ID = '@thealphabotz'
ADMIN_ID = 7758708579  # Replace with the actual admin user ID
bot = telebot.TeleBot(API_TOKEN)

# MongoDB Configuration
MONGO_URI = 'mongodb+srv://ank41785:TjezIhHRkw3vJDBk@cluster0.nldfp.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
client = MongoClient(MONGO_URI)
db = client['bot_database']
users_collection = db['users']
codes_collection = db['codes']

# Rate limiting data structures
image_rate_limit = {}
query_rate_limit = {}
user_model = {}

# Groq client setup
client = Groq(api_key=GROQ_API_KEY)

# Headers for the image generation request
headers = {
    'authority': 'www.blackbox.ai',
    'accept': '*/*',
    'content-type': 'text/plain;charset=UTF-8',
    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36'
}

# Flask app for health checks
app = Flask(__name__)

@app.route('/')
def index():
    return 'Bot is running', 200

@app.route('/healthz')
def health_check():
    return 'OK', 200

def run_flask_app():
    app.run(host='0.0.0.0', port=8080)

# Helper function to check subscription
def is_subscribed(user_id):
    member = bot.get_chat_member(CHANNEL_ID, user_id)
    return member.status in ['member', 'administrator', 'creator']

# Helper function to check if a user is admin
def is_admin(user_id):
    return user_id == ADMIN_ID

# Helper function to generate random codes
def generate_random_code(length=8):
    letters_and_digits = string.ascii_uppercase + string.digits
    return ''.join(random.choice(letters_and_digits) for _ in range(length))

# Start and help command handlers
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    start_message = (
        "🤖 *Welcome to Alpha AI Assistant!* 🚀\n"
        "Here’s what I can do for you:\n"
        "🔹 *Image Generation*: Use `/gen <prompt>` to create stunning images.\n"
        "🔹 *Text-Based Queries*: Chat with me using AI models like:\n"
        "    - 💎 *Gemma*\n\n"
        "⚠️ *Limits*:\n"
        "- 3 image generations every hour (Free users).\n"
        "- 10 text queries every hour (Free users).\n"
        "- 5 image generations every hour (Premium users).\n"
        "- 25 text queries every hour (Premium users).\n\n"
        "🔗 Make sure to join [The Alpha Botz Channel](https://t.me/thealphabotz) to start using the bot."
    )
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton('Join The Alpha Botz Channel', url='https://t.me/thealphabotz'))
    keyboard.add(telebot.types.InlineKeyboardButton('Developer', url='https://t.me/adarsh2626'))
    bot.send_message(message.chat.id, start_message, parse_mode='Markdown', reply_markup=keyboard)

# Image generation command handler
@bot.message_handler(commands=['gen'])
def generate_image(message):
    if not is_subscribed(message.from_user.id):
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton('Join The Alpha Botz', url='https://t.me/thealphabotz'))
        bot.reply_to(message, "🚫 You must join The Alpha Botz to use this bot. ✅ Once you've joined, click 'Start' below.", parse_mode='Markdown', reply_markup=keyboard)
        return

    user_id = message.from_user.id
    prompt = message.text[len('/gen '):].strip()

    if not prompt:
        bot.reply_to(message, "⚠️ Please provide a prompt for image generation. Example: `/gen a beautiful sunset`")
        return

    # Retrieve user data
    user_data = users_collection.find_one({'user_id': user_id})
    if not user_data:
        user_data = {'user_id': user_id, 'is_premium': False, 'image_gen_count': 0, 'text_query_count': 0}
        users_collection.insert_one(user_data)

    # Check rate limits based on user type
    current_time = time.time()
    is_premium = user_data['is_premium']
    max_images_per_hour = 5 if is_premium else 3
    max_images_per_day = 25 if is_premium else 10

    # Check hourly image generation limit
    if user_data['image_gen_count'] >= max_images_per_hour:
        bot.reply_to(message, f"⚠️ You’ve reached the image generation limit ({max_images_per_hour} images/hour). Please try again later.")
        return

    # Check daily image generation limit
    if user_data['image_gen_count'] >= max_images_per_day:
        bot.reply_to(message, f"⚠️ You’ve reached the daily image generation limit ({max_images_per_day} images/day). Please try again tomorrow.")
        return

    # Increment image generation count
    users_collection.update_one({'user_id': user_id}, {'$inc': {'image_gen_count': 1}})

    # Send ⚡ emoji
    flash_message = bot.send_message(message.chat.id, "⚡")
    time.sleep(3.5)
    bot.delete_message(message.chat.id, flash_message.message_id)

    data = {'query': prompt, 'agentMode': True}
    response = requests.post('https://www.blackbox.ai/api/image-generator', headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        image_url = result.get('markdown', '').split('![](')[-1].strip(')')
        bot.send_photo(message.chat.id, image_url)
    else:
        bot.reply_to(message, 'Failed to fetch data.')

# Text query handler
@bot.message_handler(func=lambda message: True)
def handle_query(message):
    if not is_subscribed(message.from_user.id):
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton('Join The Alpha Botz', url='https://t.me/thealphabotz'))
        bot.reply_to(message, "🚫 You must join The Alpha Botz to use this bot. ✅ Once you've joined, click 'Start' below.", parse_mode='Markdown', reply_markup=keyboard)
        return

    user_id = message.from_user.id
    prompt = message.text

    # Retrieve user data
    user_data = users_collection.find_one({'user_id': user_id})
    if not user_data:
        user_data = {'user_id': user_id, 'is_premium': False, 'image_gen_count': 0, 'text_query_count': 0}
        users_collection.insert_one(user_data)

    # Check rate limits based on user type
    current_time = time.time()
    is_premium = user_data['is_premium']
    max_queries_per_hour = 25 if is_premium else 10

    # Check hourly text query limit
    if user_data['text_query_count'] >= max_queries_per_hour:
        bot.reply_to(message, f"⚠️ You’ve exceeded the query limit ({max_queries_per_hour} queries/hour). Please try again after some time.")
        return

    # Increment text query count
    users_collection.update_one({'user_id': user_id}, {'$inc': {'text_query_count': 1}})

    completion = client.chat.completions.create(
        model="gemma2-9b-it",
        messages=[{"role": "user", "content": prompt}],
        temperature=1,
        max_completion_tokens=1024,
        top_p=1,
        stream=True,
        stop=None,
    )

    response_text = ""
    for chunk in completion:
        response_text += chunk.choices[0].delta.content or ""
    bot.reply_to(message, response_text)

# Stats command handler for admins
@bot.message_handler(commands=['stats'])
def show_stats(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "🚫 You do not have permission to use this command.")
        return

    total_users = users_collection.count_documents({})
    total_image_gen_today = users_collection.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$image_gen_count"}}}
    ]).next().get('total', 0)
    total_text_queries_today = users_collection.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$text_query_count"}}}
    ]).next().get('total', 0)

    stats_message = (
        f"📊 *Bot Statistics:*\n"
        f"👥 Total Users: {total_users}\n"
        f"🖼️ Images Generated Today: {total_image_gen_today}\n"
        f"💬 Text Queries Today: {total_text_queries_today}"
    )
    bot.reply_to(message, stats_message, parse_mode='Markdown')

# Broadcast command handler for admins
@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "🚫 You do not have permission to use this command.")
        return

    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Please reply to a message with /broadcast to broadcast it.")
        return

    broadcast_content = message.reply_to_message
    for user in users_collection.find():
        try:
            if broadcast_content.text:
                bot.send_message(user['user_id'], broadcast_content.text, parse_mode='Markdown')
            elif broadcast_content.photo:
                bot.send_photo(user['user_id'], broadcast_content.photo[-1].file_id, caption=broadcast_content.caption, parse_mode='Markdown')
            elif broadcast_content.video:
                bot.send_video(user['user_id'], broadcast_content.video.file_id, caption=broadcast_content.caption, parse_mode='Markdown')
            elif broadcast_content.document:
                bot.send_document(user['user_id'], broadcast_content.document.file_id, caption=broadcast_content.caption, parse_mode='Markdown')
        except:
            continue

# Generate premium codes for admins
@bot.message_handler(commands=['generate_codes'])
def generate_premium_codes(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "🚫 You do not have permission to use this command.")
        return

    codes = [generate_random_code() for _ in range(5)]
    codes_collection.insert_many([{'code': code, 'is_redeemed': False} for code in codes])

    codes_message = "🔑 *Generated Premium Codes:*\n" + "\n".join(codes)
    bot.reply_to(message, codes_message, parse_mode='Markdown')

# Redeem premium codes
@bot.message_handler(commands=['redeem'])
def redeem_code(message):
    user_id = message.from_user.id
    command_parts = message.text.split()

    if len(command_parts) != 2:
        bot.reply_to(message, "⚠️ Usage: `/redeem <code>`\nExample: `/redeem ABC1234`", parse_mode='Markdown')
        return

    code = command_parts[1].strip().upper()
    code_data = codes_collection.find_one({'code': code, 'is_redeemed': False})

    if not code_data:
        bot.reply_to(message, "⚠️ Invalid or already redeemed code. Please try again.", parse_mode='Markdown')
        return

    # Mark the code as redeemed
    codes_collection.update_one({'code': code}, {'$set': {'is_redeemed': True}})

    # Update the user's data to mark them as premium
    users_collection.update_one({'user_id': user_id}, {'$set': {'is_premium': True}})

    bot.reply_to(message, "✅ Your premium membership has been activated!", parse_mode='Markdown')

# Start the Flask app in a separate thread
flask_thread = Thread(target=run_flask_app)
flask_thread.start()

# Start the bot polling in the main thread
bot.polling()
