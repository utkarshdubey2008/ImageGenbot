import telebot
import requests
from flask import Flask, request
from threading import Thread
from groq import Groq
import time

# Bot Configuration
API_TOKEN = '8107353617:AAEvH1iADJveysXU9QUobi6GQ9zz_rdJA4k'
GROQ_API_KEY = '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'
CHANNEL_ID = '@thealphabotz'
bot = telebot.TeleBot(API_TOKEN)

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

# Start and help command handlers
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    start_message = (
        "🤖 *Welcome to Alpha AI Assistant!* 🚀\n"
        "Here’s what I can do for you:\n"
        "🔹 *Image Generation*: Use `/gen <prompt>` to create stunning images.\n"
        "🔹 *Text-Based Queries*: Chat with me using AI models like:\n"
        "    - 🌟 *Mixtral*\n"
        "    - 💎 *Gemma*\n"
        "    - 🦙 *Llama*\n"
        "🔄 Switch models anytime with `/change`.\n\n"
        "⚠️ *Limits*:\n"
        "- 3 image generations every 3 hours.\n"
        "- 10 text queries every hour.\n\n"
        "🔗 Make sure to join The Alpha Botz Channel to start using the bot."
    )
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton('Join The Alpha Botz Channel', url='https://t.me/thealphabotz'))
    keyboard.add(telebot.types.InlineKeyboardButton('Change Model', callback_data='change_model'))
    bot.send_message(message.chat.id, start_message, parse_mode='Markdown', reply_markup=keyboard)

# Image generation command handler
@bot.message_handler(commands=['gen'])
def generate_image(message):
    if not is_subscribed(message.from_user.id):
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton('Join The Alpha Botz', url='https://t.me/thealphabotz'))
        bot.reply_to(message, "🚫 You must join The Alpha Botz to use this bot. ✅ Once you've joined, click 'Start' below.", parse_mode='Markdown', reply_markup=keyboard)
        return

    # Rate limit check
    user_id = message.from_user.id
    current_time = time.time()
    if user_id in image_rate_limit and len(image_rate_limit[user_id]) >= 3:
        if current_time - image_rate_limit[user_id][0] < 10800: # 3 hours in seconds
            bot.reply_to(message, "⚠️ You’ve reached the image generation limit (3 images/3 hours). Please try again later.")
            return
        else:
            image_rate_limit[user_id].pop(0)
    if user_id not in image_rate_limit:
        image_rate_limit[user_id] = []
    image_rate_limit[user_id].append(current_time)

    prompt = message.text[len('/gen '):]
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

    # Rate limit check
    user_id = message.from_user.id
    current_time = time.time()
    if user_id in query_rate_limit and len(query_rate_limit[user_id]) >= 10:
        if current_time - query_rate_limit[user_id][0] < 3600: # 1 hour in seconds
            bot.reply_to(message, "⚠️ You’ve exceeded the query limit (10 queries/hour). Please try again after some time.")
            return
        else:
            query_rate_limit[user_id].pop(0)
    if user_id not in query_rate_limit:
        query_rate_limit[user_id] = []
    query_rate_limit[user_id].append(current_time)

    prompt = message.text
    model = user_model.get(user_id, 'mixtral-8x7b-32768')
    if model == 'llama3-70b-8192':
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            max_completion_tokens=1024,
            top_p=1,
            stream=True,
            stop=None,
        )
    elif model == 'gemma2-9b-it':
        completion = client.chat.completions.create(
            model="gemma2-9b-it",
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            max_completion_tokens=1024,
            top_p=1,
            stream=True,
            stop=None,
        )
    else:
        completion = client.chat.completions.create(
            model="mixtral-8x7b-32768",
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

# Model change command handler
@bot.message_handler(commands=['change'])
def change_model(message):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton('🌟 Mixtral', callback_data='mixtral-8x7b-32768'))
    keyboard.add(telebot.types.InlineKeyboardButton('💎 Gemma', callback_data='gemma2-9b-it'))
    keyboard.add(telebot.types.InlineKeyboardButton('🦙 Llama', callback_data='llama3-70b-8192'))
    bot.send_message(message.chat.id, '🤖 Select your preferred model:', reply_markup=keyboard)

# Callback query handler for model selection
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    user_id = call.from_user.id
    user_model[user_id] = call.data
    bot.answer_callback_query(call.id, f'Model changed to: {call.data}')
    bot.send_message(call.message.chat.id, f'✅ Model changed to: {call.data}')

# Inline keyboard button handler for changing model
@bot.callback_query_handler(func=lambda call: call.data == 'change_model')
def inline_change_model(call):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton('🌟 Mixtral', callback_data='mixtral-8x7b-32768'))
    keyboard.add(telebot.types.InlineKeyboardButton('💎 Gemma', callback_data='gemma2-9b-it'))
    keyboard.add(telebot.types.InlineKeyboardButton('🦙 Llama', callback_data='llama3-70b-8192'))
    bot.send_message(call.message.chat.id, '🤖 Select your preferred model:', reply_markup=keyboard)

# Start the Flask app in a separate thread
flask_thread = Thread(target=run_flask_app)
flask_thread.start()

# Start the bot polling in the main thread
bot.polling()
