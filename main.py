import logging
import os
import re
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# --- Configuration ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
EXCHANGE_API_KEY = os.environ.get("EXCHANGE_API_KEY", "")

# Using exchangerate.host API (free, no key required for basic usage)
BASE_URL = "https://api.exchangerate.host/latest"

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Helper Functions ---
def get_exchange_rate(from_currency: str, to_currency: str):
    """Fetches the exchange rate between two currencies."""
    try:
        # Get rates with EUR as base (default for exchangerate.host)
        response = requests.get(BASE_URL)
        data = response.json()
        
        if not data.get("success", True):
            logger.error(f"API Error: {data}")
            return None

        rates = data.get("rates", {})
        
        # If from_currency is EUR
        if from_currency.upper() == "EUR":
            if to_currency.upper() in rates:
                return rates[to_currency.upper()]
        
        # If to_currency is EUR
        elif to_currency.upper() == "EUR":
            if from_currency.upper() in rates:
                return 1 / rates[from_currency.upper()]
        
        # Cross rate calculation
        if from_currency.upper() in rates and to_currency.upper() in rates:
            return rates[to_currency.upper()] / rates[from_currency.upper()]
        
        logger.warning(f"Could not find rate for {from_currency} to {to_currency}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching exchange rate: {e}")
        return None

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message when /start is issued."""
    user = update.effective_user
    welcome_text = (
        f"👋 Hello {user.first_name}!\n"
        "I am a Currency Converter Bot.\n\n"
        "**How to use me:**\n"
        "• Send: `100 USD to EUR`\n"
        "• Or use: `/convert 100 USD EUR`\n"
        "• Type `/list` to see supported currencies\n"
        "• Type `/help` for more info"
    )
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a help message."""
    help_text = (
        "📖 **Available Commands:**\n\n"
        "/start - Welcome message\n"
        "/help - Show this help\n"
        "/list - Show supported currencies\n"
        "/convert - Convert currencies\n\n"
        "**Examples:**\n"
        "`100 USD to EUR`\n"
        "`/convert 50 GBP INR`\n"
        "`1000 JPY in USD`"
    )
    await update.message.reply_text(help_text)

async def list_currencies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows a list of popular currencies."""
    currencies = (
        "🌍 **Popular Currencies:**\n\n"
        "🇺🇸 USD - US Dollar\n"
        "🇪🇺 EUR - Euro\n"
        "🇬🇧 GBP - British Pound\n"
        "🇮🇳 INR - Indian Rupee\n"
        "🇯🇵 JPY - Japanese Yen\n"
        "🇨🇦 CAD - Canadian Dollar\n"
        "🇦🇺 AUD - Australian Dollar\n"
        "🇨🇭 CHF - Swiss Franc\n"
        "🇨🇳 CNY - Chinese Yuan\n"
        "🇧🇷 BRL - Brazilian Real\n"
        "🇿🇦 ZAR - South African Rand\n"
        "🇷🇺 RUB - Russian Ruble"
    )
    await update.message.reply_text(currencies)

async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /convert command."""
    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text(
                "❌ Please use: `/convert <amount> <from> <to>`\n"
                "Example: `/convert 100 USD EUR`"
            )
            return

        amount = float(args[0])
        from_currency = args[1].upper()
        to_currency = args[2].upper()

        rate = get_exchange_rate(from_currency, to_currency)
        if rate is None:
            await update.message.reply_text(
                f"❌ Cannot convert {from_currency} to {to_currency}.\n"
                "Check currency codes and try again."
            )
            return

        converted_amount = amount * rate
        reply = (
            f"💱 **Conversion:**\n"
            f"• {amount:.2f} {from_currency} = {converted_amount:.2f} {to_currency}\n"
            f"• Rate: 1 {from_currency} = {rate:.4f} {to_currency}"
        )
        await update.message.reply_text(reply)

    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a number.")
    except Exception as e:
        logger.error(f"Error in convert: {e}")
        await update.message.reply_text("❌ Something went wrong. Try again later.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles direct messages like '100 USD to EUR'."""
    text = update.message.text
    
    # Pattern: "100 USD to EUR" or "100 USD in EUR"
    pattern = r"(\d+\.?\d*)\s*([A-Za-z]{3})\s+(?:to|in)\s+([A-Za-z]{3})"
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        amount = float(match.group(1))
        from_currency = match.group(2).upper()
        to_currency = match.group(3).upper()
        
        rate = get_exchange_rate(from_currency, to_currency)
        if rate is None:
            await update.message.reply_text(
                f"❌ Cannot convert {from_currency} to {to_currency}."
            )
            return

        converted_amount = amount * rate
        reply = (
            f"💱 **Quick Convert:**\n"
            f"• {amount:.2f} {from_currency} = {converted_amount:.2f} {to_currency}\n"
            f"• Rate: 1 {from_currency} = {rate:.4f} {to_currency}"
        )
        await update.message.reply_text(reply)
    else:
        await update.message.reply_text(
            "🤔 I didn't understand.\n\n"
            "Try:\n"
            "• `100 USD to EUR`\n"
            "• `/convert 100 USD EUR`\n"
            "• Type `/help` for more options"
        )

# --- Main Function ---
def main():
    """Start the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN not set!")
        logger.error("Please set the environment variable in Railway.")
        return

    logger.info("🚀 Starting Currency Converter Bot...")
    
    # Create application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_currencies))
    application.add_handler(CommandHandler("convert", convert_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start polling
    logger.info("✅ Bot is running and polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
