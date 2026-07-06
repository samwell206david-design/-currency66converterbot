import logging
import os
import re
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# --- Configuration ---
# Get tokens from environment variables for security[citation:3][citation:5]
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
EXCHANGE_API_KEY = os.environ.get("EXCHANGE_API_KEY")

# Using a free API, you can get your key at https://fixer.io/ or exchangerate-api.com
# Free tier often uses EUR as base
BASE_URL = f"http://api.exchangerate.host/live?access_key={EXCHANGE_API_KEY}"

# Enable logging to see what's happening
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Helper Functions ---
async def get_exchange_rate(from_currency: str, to_currency: str) -> float | None:
    """Fetches the exchange rate between two currencies."""
    try:
        # The free 'exchangerate.host' API uses EUR as base[citation:5]
        response = requests.get(BASE_URL)
        data = response.json()
        
        if not data.get("success"):
            logger.error(f"API Error: {data.get('error', {}).get('info', 'Unknown error')}")
            return None

        # The API returns rates like 'USDINR' for USD to INR
        # We need to construct the key based on the base currency (EUR)
        rates = data.get("quotes", {})
        
        # Find the rate from base (EUR) to the target currencies
        # Since API gives rates from EUR, we need to compute cross rates
        # Check if source currency is EUR directly
        if from_currency.upper() == "EUR":
            rate_key = f"EUR{to_currency.upper()}"
            if rate_key in rates:
                return rates[rate_key]
        
        # Check if target currency is EUR directly
        elif to_currency.upper() == "EUR":
            rate_key = f"EUR{from_currency.upper()}"
            if rate_key in rates and rates[rate_key] != 0:
                return 1 / rates[rate_key]
        
        # For other currencies, compute cross rate: (EUR -> to) / (EUR -> from)
        from_key = f"EUR{from_currency.upper()}"
        to_key = f"EUR{to_currency.upper()}"
        
        if from_key in rates and to_key in rates and rates[from_key] != 0:
            return rates[to_key] / rates[from_key]
        
        logger.warning(f"Could not find rate for {from_currency} to {to_currency}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching exchange rate: {e}")
        return None

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when /start is issued."""
    user = update.effective_user
    welcome_text = (
        f"👋 Hello {user.first_name}!\n"
        "I am a currency converter bot. I can help you convert between various currencies.\n\n"
        "**Commands:**\n"
        "/convert - Convert between currencies\n"
        "/list - Show supported currencies\n"
        "/help - Show this help message\n\n"
        "**Example:**\n"
        "Send: `100 usd to eur` or `/convert 100 USD EUR`\n"
        "I will reply with the converted amount!"
    )
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a help message."""
    help_text = (
        "**How to use me:**\n"
        "1. **Direct conversion:** Send a message like '100 usd to eur'\n"
        "2. **Using command:** Type `/convert 100 USD EUR`\n"
        "3. **View all currencies:** Type `/list`\n\n"
        "I support major world currencies like USD, EUR, GBP, INR, JPY, and more."
    )
    await update.message.reply_text(help_text)

async def list_currencies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows a list of supported currencies."""
    # This is a sample list; the actual list is fetched from API in a full implementation
    sample_currencies = [
        "USD (US Dollar)", "EUR (Euro)", "GBP (British Pound)",
        "INR (Indian Rupee)", "JPY (Japanese Yen)", "AUD (Australian Dollar)",
        "CAD (Canadian Dollar)", "CHF (Swiss Franc)", "CNY (Chinese Yuan)",
        "RUB (Russian Ruble)", "BRL (Brazilian Real)", "ZAR (South African Rand)"
    ]
    currency_text = "**Supported Currencies:**\n" + "\n".join(sample_currencies)
    await update.message.reply_text(currency_text)

async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /convert command."""
    # This is a simplified version; it expects input like: /convert 100 USD EUR
    try:
        # Get the arguments after the command
        args = context.args
        if len(args) != 3:
            await update.message.reply_text(
                "❌ Please provide the amount and currencies in the format:\n`/convert <amount> <from_currency> <to_currency>`\n\nExample: `/convert 100 USD EUR`"
            )
            return

        amount = float(args[0])
        from_currency = args[1].upper()
        to_currency = args[2].upper()

        rate = await get_exchange_rate(from_currency, to_currency)
        if rate is None:
            await update.message.reply_text(
                f"❌ Sorry, I could not convert from {from_currency} to {to_currency}. Please check the currency codes and try again."
            )
            return

        converted_amount = amount * rate
        reply = (
            f"💱 **Conversion Result:**\n"
            f"• {amount:.2f} {from_currency} = {converted_amount:.2f} {to_currency}\n"
            f"• Exchange Rate: 1 {from_currency} = {rate:.4f} {to_currency}"
        )
        await update.message.reply_text(reply)

    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number.")
    except Exception as e:
        logger.error(f"Error in convert command: {e}")
        await update.message.reply_text("❌ An unexpected error occurred. Please try again later.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles direct messages like '100 USD to EUR'."""
    text = update.message.text
    # Regex to match patterns like "100 USD to EUR"
    match = re.search(r"(\d+\.?\d*)\s*([A-Za-z]{3})\s*(?:to|in)\s*([A-Za-z]{3})", text, re.IGNORECASE)
    
    if match:
        amount = float(match.group(1))
        from_currency = match.group(2).upper()
        to_currency = match.group(3).upper()
        
        rate = await get_exchange_rate(from_currency, to_currency)
        if rate is None:
            await update.message.reply_text(
                f"❌ Sorry, I could not convert from {from_currency} to {to_currency}."
            )
            return

        converted_amount = amount * rate
        reply = (
            f"💱 **Quick Conversion:**\n"
            f"• {amount:.2f} {from_currency} = {converted_amount:.2f} {to_currency}\n"
            f"• Rate: 1 {from_currency} = {rate:.4f} {to_currency}"
        )
        await update.message.reply_text(reply)
    else:
        # If no pattern matches, send a helpful hint
        await update.message.reply_text(
            "🤔 I didn't understand that. Try sending something like:\n"
            "`100 USD to EUR` or use the /convert command."
        )

# --- Main Function ---
def main() -> None:
    """Starts the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("No TELEGRAM_TOKEN set. Please set the environment variable.")
        return
    
    if not EXCHANGE_API_KEY:
        logger.warning("No EXCHANGE_API_KEY set. The bot will not work. Get one from exchangerate.host or fixer.io")

    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_currencies))
    application.add_handler(CommandHandler("convert", convert_command))

    # Register a handler for any text message (for direct conversion)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot with long polling (no webhook needed)[citation:3][citation:12]
    logger.info("Starting bot with long polling...")
    application.run_polling()

if __name__ == "__main__":
    main()
