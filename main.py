import os
from dotenv import load_dotenv

from web3 import Web3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

from __db__.db import connect_db, get_chat, set_chat, update_chat
from __web3__.web3 import validateAddress

import logging

logging.basicConfig(format="%(asctime)s -%(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MAINNET_API_URL= os.getenv("MAINNET_API_URL")

START, END = range(2)
db = None

web3 = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.username)

    try:
        if update.message.chat.type != "private":
            chat_id = update.effective_chat.id
            user_id = update.effective_user.id

            chat_member = await context.bot.get_chat_member(chat_id, user_id)
            user_status = chat_member.status
            print(f"CHAT MEMBER: {user_status}")

            if user_status not in ["administrator", "creator"]:
                reply_msg = "<b>🚨 You do not have Non-Anonymous Admin Rights to use.</b>"
                await update.message.reply_html(text=reply_msg)

                return ConversationHandler.END

            chat_id = update.message.chat_id

            query = {"chat_id": chat_id}
            existing_token = get_chat(db=db, query=query)

            if existing_token:
                reply_msg = "<b>🚨 A token address is already set for this group.</b>"
                await update.message.reply_html(text=reply_msg)

                return ConversationHandler.END

            keyboard = [
                [InlineKeyboardButton("Click to get started 🚀", callback_data="start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            reply_msg = f"<b>Hello ${user.username} 👋, Welcome to the 0xBuyBot 🤖.</b>\n\n<i>It provides blockchain powered trending insights on any token of your choice on BSC & ETH 🚀.</i>\n\n<b>To get started:</b>\n\n<i>✅ Start by sending your the token address ie: 0x23exb......</i>\n<i>✅ You must have Non-Anonymous Admin Rights in your token's group chat.</i>"

            await update.message.reply_html(text=reply_msg, reply_markup=reply_markup)

            return START
        else:
            reply_msg = "<b>🚨 This command is only used in group chats.</b>"
            await update.message.reply_html(text=reply_msg)

            return ConversationHandler.END
    except Exception as e:
        logging.error(f"An error has occurred: {e}")

        reply_msg = "<b>🚨 An error occured while using the bot.</b>"
        await update.message.reply_html(text=reply_msg)

        return ConversationHandler.END

async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    try:
        keyboard = [
            [InlineKeyboardButton("Binance Smart Chain", callback_data="bsc-chain")],
            [InlineKeyboardButton("Ethereum", callback_data="eth-chain")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = "<b>🔰 Please select the blockchain of choice.....</b>"
        await query.message.reply_html(text=reply_msg, reply_markup=reply_markup)

        return START
    except Exception as e:
        logging.error(f"An error has occurred: {e}")

        reply_msg = "<b>🚨 An error occured while using the bot.</b>"
        await query.message.reply_html(text=reply_msg)

        return ConversationHandler.END
    
async def chain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    try:
        context.user_data["chain"] = query.data

        reply_msg = "<b>🔰 Enter your token address ie: 0x1234....</b>"
        await query.message.reply_html(text=reply_msg)

        return START
    except Exception as e:
        logging.error(f"An error has occurred: {e}")

        reply_msg = "<b>🚨 An error occured while using the bot.</b>"
        await query.message.reply_html(text=reply_msg)

        return ConversationHandler.END
    
async def token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("User %s sent a token address.", user.username)

    try:
        is_valid = validateAddress(update.message.text)
        print(is_valid)

        if is_valid:
            context.user_data["token"] = update.message.text

            reply_msg = "<b>🔰 Enter your token group chat emoji....</b>"
            await update.message.reply_html(text=reply_msg)

            return START
        else:
            reply_msg = "<b>🚨 Token Address is not valid.</b>"
            await update.message.reply_html(text=reply_msg)

            return ConversationHandler.END

    except Exception as e:
        logging.error(f"An error has occurred: {e}")

        reply_msg = "<b>🚨 An error occured while using the bot.</b>"
        await update.message.reply_html(text=reply_msg)

        return ConversationHandler.END
    
async def set_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("User %s sent an emoji.", user.username)

    try:
        chat_id = update.message.chat_id
        chain = context.user_data["chain"]
        token = context.user_data["token"]

        value = {"chat_id": chat_id, "chain": chain, "token": token, "emoji": update.message.text, "buys": []}
        chat = set_chat(db=db, value=value)
        print(chat)

        keyboard = [
            [InlineKeyboardButton("End Conversation", callback_data="end")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_msg = f"<b>Congratulations {user.username} 🎉, You have successfully added the 0xBuyBot to your token group chat. Get ready for super-powered trending insights 🚀.</b>"

        await update.message.reply_html(text=reply_msg, reply_markup=reply_markup)

        return START

    except Exception as e:
        logging.error(f"An error has occurred: {e}")

        reply_msg = "<b>🚨 An error occured while using the bot.</b>"
        await update.message.reply_html(text=reply_msg)

        return ConversationHandler.END
    
async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await query.message.reply_html("See you soon.")

    return ConversationHandler.END

async def emoji(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logger.info("User %s has entered the /emoji command.", user.username)

    try:
        reply_msg = "<b>🔰 Enter a new token group chat emoji....</b>"
        await update.message.reply_html(text=reply_msg)

    except Exception as e:
        logging.error(f"An error has occurred: {e}")

        reply_msg = "<b>🚨 An error occured while using the bot.</b>"
        await update.message.reply_html(text=reply_msg)

async def change_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("User %s sent an emoji.", user.username)

    try:
        chat_id = update.message.chat_id

        query = {"chat_id": chat_id}
        value = {"emoji": update.message.text}
        chat = update_chat(db=db, query=query, value=value)
        print(chat)

        reply_msg = f"<b>Congratulations {user.username} 🎉, You have successfully changed the emoji of your token group chat.</b>"

        await update.message.reply_html(text=reply_msg)

    except Exception as e:
        logging.error(f"An error has occurred: {e}")

        reply_msg = "<b>🚨 An error occured while using the bot.</b>"
        await update.message.reply_html(text=reply_msg)

def main() -> None:
    global db
    db = connect_db(uri=MONGO_URI)

    global web3
    web3 = Web3(Web3.HTTPProvider(endpoint_uri=MAINNET_API_URL))

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START: [
                CallbackQueryHandler(_start, pattern="^start$"),
                CallbackQueryHandler(chain, pattern="chain$"),
                MessageHandler(filters.Regex("^0x"), token),
                MessageHandler(filters.Regex("[^a-zA-Z0-9]"), set_emoji)
            ]
        },
        fallbacks=[CallbackQueryHandler(end, pattern="^end$")]
    )
    emoji_handler = CommandHandler("emoji", emoji)
    change_emoji_handler = MessageHandler(filters.Regex("[^a-zA-Z0-9]"), change_emoji)

    app.add_handler(conv_handler)
    app.add_handler(emoji_handler)
    app.add_handler(change_emoji_handler)

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()