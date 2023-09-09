import telebot
from telebot import types
import ccxt
import threading
import time
import schedule

# Insert your actual API token obtained from @BotFather on Telegram
API_TOKEN = 'YOUR_API_TOKEN'

# Create a bot instance
bot = telebot.TeleBot(API_TOKEN)

# Initialize the CCXT exchange object for fetching cryptocurrency prices
exchange = ccxt.binance()  # You can replace 'binance' with the exchange of your choice

# Dictionary to store user balances
user_balances = {}

# Dictionary to store user goals
user_goals = {}

# File path for the database
DATABASE_FILE = 'database.txt'
GOALS_FILE = 'goals.txt'

# Load user balances from the database file
def load_balances():
    try:
        with open(DATABASE_FILE, 'r') as file:
            lines = file.readlines()
            for line in lines:
                user_id, currency, amount = line.strip().split(',')
                user_id = str(user_id)
                amount = float(amount)
                if user_id not in user_balances:
                    user_balances[user_id] = {}
                user_balances[user_id][currency] = amount
    except FileNotFoundError:
        pass

# Save user balances to the database file
def save_balances():
    with open(DATABASE_FILE, 'w') as file:
        for user_id, balances in user_balances.items():
            for currency, amount in balances.items():
                file.write(f'{user_id},{currency},{amount}\n')

# Load user goals from the goals file
def load_goals():
    try:
        with open(GOALS_FILE, 'r') as file:
            lines = file.readlines()
            for line in lines:
                user_id, goal_usd = line.strip().split(',')
                user_id = str(user_id)
                goal_usd = float(goal_usd)
                user_goals[user_id] = goal_usd
    except FileNotFoundError:
        pass

# Save user goals to the goals file
def save_goals():
    with open(GOALS_FILE, 'w') as file:
        for user_id, goal_usd in user_goals.items():
            file.write(f'{user_id},{goal_usd}\n')

# Load user balances and goals when the bot starts
load_balances()
load_goals()

# Function to fetch cryptocurrency prices in USD
def get_crypto_price(symbol):
    try:
        ticker = exchange.fetch_ticker(symbol)
        price_usd = ticker['last']
        return price_usd
    except Exception as e:
        return None

# Function to get the exchange rate for a currency pair (e.g., BTC/USD)
def get_exchange_rate(base_currency, target_currency):
    try:
        ticker = exchange.fetch_ticker(f'{base_currency}/{target_currency}')
        return ticker['last']
    except Exception as e:
        print(f'Error fetching exchange rate: {e}')
        return None

# Handler for the /start command
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    if user_id not in user_balances:
        user_balances[user_id] = {}  # Create an empty balance dictionary for new users

    welcome_message = 'Welcome to the FinanceBot!\n\nHere is a step-by-step guide on how to use this bot:\n\n'
    welcome_message += '1. Use the /set_balance command to set your balance in a specific currency. '
    welcome_message += 'For example: /set_balance USD 100.0\n\n'
    welcome_message += '2. Use the /get_balance command to get your balance in a specific currency. '
    welcome_message += 'For example: /get_balance USD\n\n'
    welcome_message += '3. Use the /balance command to get your balances in all currencies.\n\n'
    welcome_message += '4. Use the /crypto_price command to get the price of a cryptocurrency in USD. '
    welcome_message += 'For example: /crypto_price BTC\n\n'
    welcome_message += '5. Use the /set_goal command to set a savings goal in USD. '
    welcome_message += 'For example: /set_goal 500.0\n\n'
    welcome_message += '6. Use the /goals command to view your savings goal progress.\n\n'
    welcome_message += '7. Use the /help command to display the available commands.\n\n'
    welcome_message += 'Enjoy using FinanceBot!'

    bot.reply_to(message, welcome_message)

# Handler for the /set_balance command
@bot.message_handler(commands=['set_balance'])
def set_balance(message):
    try:
        # Split the user's message into arguments
        args = message.text.split()[1:]
        if len(args) != 2:
            raise ValueError()

        currency, amount = args
        amount = float(amount)
        user_id = str(message.from_user.id)

        # Check if the user exists in the balance dictionary
        if user_id not in user_balances:
            user_balances[user_id] = {}

        # Save the user's balance in the specified currency
        user_balances[user_id][currency] = amount

        # Save user balances to the database file
        save_balances()

        bot.reply_to(message, f'Balance set: {amount} {currency}')
    except (ValueError, IndexError):
        bot.reply_to(message, 'Use the command in the format: /set_balance CURRENCY AMOUNT')

# Handler for the /get_balance command
@bot.message_handler(commands=['get_balance'])
def get_balance(message):
    try:
        # Split the user's message into arguments
        args = message.text.split()[1:]
        if len(args) != 1:
            raise ValueError()

        currency = args[0]
        user_id = str(message.from_user.id)

        # Check if the user exists in the balance dictionary
        if user_id not in user_balances:
            bot.reply_to(message, 'User not found.')
            return

        # Get the user's balance in the specified currency
        if currency in user_balances[user_id]:
            balance = user_balances[user_id][currency]

            # Calculate the equivalent in USD
            exchange_rate = get_exchange_rate(currency, 'USDT')
            if exchange_rate is not None:
                balance_usd = balance * exchange_rate
                bot.reply_to(message, f'Your balance in {currency}: {balance} ({balance_usd:.2f} USD)')
            else:
                bot.reply_to(message, f'Unable to fetch the exchange rate for {currency}')
        else:
            bot.reply_to(message, f'You have no balance in {currency}')
    except (ValueError, IndexError):
        bot.reply_to(message, 'Use the command in the format: /get_balance CURRENCY')

# Handler for the /balance command
@bot.message_handler(commands=['balance'])
def balance(message):
    user_id = str(message.from_user.id)
    if user_id not in user_balances:
        bot.reply_to(message, 'User not found.')
        return

    response = 'Your balances:\n'
    total_balance_usd = 0  # For calculating the total balance in USD

    for currency, amount in user_balances[user_id].items():
        exchange_rate = get_exchange_rate(currency, 'USDT')
        if exchange_rate is not None:
            balance_usd = amount * exchange_rate
            response += f'{currency}: {amount} ({balance_usd:.2f} USD)\n'
            total_balance_usd += balance_usd
        else:
            response += f'{currency}: {amount} (Exchange rate not available)\n'

    response += f'Total Balance in USD: {total_balance_usd:.2f} USD'
    bot.reply_to(message, response)

# Handler for the /crypto_price command
@bot.message_handler(commands=['crypto_price'])
def crypto_price(message):
    try:
        # Split the user's message into arguments
        args = message.text.split()[1:]
        if len(args) != 1:
            raise ValueError()

        crypto_symbol = args[0].upper()
        price_usd = get_crypto_price(f'{crypto_symbol}/USDT')

        if price_usd is not None:
            bot.reply_to(message, f'Price of {crypto_symbol}: {price_usd:.2f} USD')
        else:
            bot.reply_to(message, f'Unable to fetch the price for {crypto_symbol}')
    except (ValueError, IndexError):
        bot.reply_to(message, 'Use the command in the format: /crypto_price CRYPTO_SYMBOL')

# Handler for the /set_goal command
@bot.message_handler(commands=['set_goal'])
def set_goal(message):
    try:
        # Split the user's message into arguments
        args = message.text.split()[1:]
        if len(args) != 1:
            raise ValueError()

        goal_usd = float(args[0])
        user_id = str(message.from_user.id)

        # Save the user's goal in USD
        user_goals[user_id] = goal_usd
        save_goals()

        bot.reply_to(message, f'Goal set: {goal_usd:.2f} USD')
    except (ValueError, IndexError):
        bot.reply_to(message, 'Use the command in the format: /set_goal GOAL_AMOUNT')

# Handler for the /goals command
@bot.message_handler(commands=['goals'])
def goals(message):
    user_id = str(message.from_user.id)
    if user_id not in user_goals:
        bot.reply_to(message, 'You have not set any goals yet. Use /set_goal to set a savings goal.')
        return

    goal_usd = user_goals[user_id]
    total_balance_usd = calculate_total_balance_usd(user_id)

    progress_percent = (total_balance_usd / goal_usd) * 100

    response = f'Your savings goal:\n'
    response += f'Goal: {goal_usd:.2f} USD\n'
    response += f'Collected: {total_balance_usd:.2f} USD\n'
    response += f'Progress: {progress_percent:.2f}%'

    bot.reply_to(message, response)

    # Check if the goal is completed
    if total_balance_usd >= goal_usd:
        bot.send_message(message.chat.id, 'Congratulations! You have reached your savings goal.')

# Handler for the /help command with buttons
@bot.message_handler(commands=['help'])
def help(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item = types.KeyboardButton("/set_balance")
    markup.add(item)
    item = types.KeyboardButton("/get_balance")
    markup.add(item)
    item = types.KeyboardButton("/balance")
    markup.add(item)
    item = types.KeyboardButton("/crypto_price")
    markup.add(item)
    item = types.KeyboardButton("/set_goal")
    markup.add(item)
    item = types.KeyboardButton("/goals")
    markup.add(item)

    help_text = 'Welcome to the FinanceBot!\n\nHere are the available commands:'
    bot.send_message(message.chat.id, help_text, reply_markup=markup)

# Handler for unknown commands
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, 'I don\'t know that command. Use /help to see the available commands.')

# Set the list of commands for the bot
bot.set_my_commands([
    types.BotCommand("set_balance", "Set your balance in a specific currency."),
    types.BotCommand("get_balance", "Get your balance in a specific currency."),
    types.BotCommand("balance", "Get your balances in all currencies."),
    types.BotCommand("crypto_price", "Get the price of a cryptocurrency in USD."),
    types.BotCommand("set_goal", "Set a savings goal in USD."),
    types.BotCommand("goals", "View your savings goal progress."),
    types.BotCommand("help", "Display this help message."),
])

# Function to calculate total balance in USD for a user
def calculate_total_balance_usd(user_id):
    total_balance_usd = 0
    for currency, amount in user_balances[user_id].items():
        exchange_rate = get_exchange_rate(currency, 'USDT')
        if exchange_rate is not None:
            balance_usd = amount * exchange_rate
            total_balance_usd += balance_usd
    return total_balance_usd

# Check for completed goals when the bot starts
def check_completed_goals():
    for user_id, goal_usd in user_goals.items():
        total_balance_usd = calculate_total_balance_usd(user_id)
        if total_balance_usd >= goal_usd:
            bot.send_message(user_id, 'Congratulations! You have reached your savings goal.')

user_completed_goals = {}

# Function to check and send notifications for completed goals every second
def check_and_send_goal_notifications_every_second():
    while True:
        for user_id, goal_usd in user_goals.items():
            total_balance_usd = calculate_total_balance_usd(user_id)
            
            # Check if the user has not received a completion message for this goal yet
            if user_id not in user_completed_goals:
                user_completed_goals[user_id] = {}  # Initialize if not exists
                
            if total_balance_usd >= goal_usd and not user_completed_goals[user_id].get(goal_usd):
                bot.send_message(user_id, 'Congratulations! You have reached your savings goal.')
                user_completed_goals[user_id][goal_usd] = True  # Mark the goal as completed
                
        time.sleep(1)  # Sleep for 1 second between checks

# Start the function to check goals every second in a separate thread
if __name__ == '__main__':
    check_completed_goals()  # Check for completed goals on startup
    threading.Thread(target=check_and_send_goal_notifications_every_second).start()  # Start the periodic checks

    bot.polling()
