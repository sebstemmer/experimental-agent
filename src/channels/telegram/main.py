import logging

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from channels.agent_setup import BASE_SYSTEM_PROMPT, build_agent, build_mcp_client
from channels.handle_message import handle_message
from utils.require_env import require_env

load_dotenv()

token = require_env("BOT_TOKEN")

PRIVACY_SYSTEM_PROMPT = (
    "This chat is not end-to-end encrypted. Never write out sensitive personal "
    "details you find in the user's data: postal addresses, health information "
    "(for example eyeglass or lens values), account or card numbers, dates of "
    "birth, or government identifiers. "
    "Refer to them indirectly instead (for example 'the delivery address on "
    "the order'). This holds even if the user asks for the detail directly - "
    "explain that you do not repeat such data in this chat."
)

ALLOWED_TOOLS = ("add_todo", "get_all_open_todos", "complete_todo")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

client = build_mcp_client()
postgres_mcp_session = client.session("postgres")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!"
    )


async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if (
        not update.message
        or not update.message.text
        or context.chat_data is None
        or not update.effective_chat
    ):
        return

    agent = context.bot_data["agent"]
    thread_id = str(update.effective_chat.id)
    pending = context.chat_data.get("pending_decisions", 0)

    reply, pending = await handle_message(
        agent, thread_id, update.message.text, pending
    )
    context.chat_data["pending_decisions"] = pending

    await update.message.reply_text(reply)


async def post_init(application):
    session = await postgres_mcp_session.__aenter__()
    application.bot_data["agent"] = await build_agent(
        session,
        allowed_tools=ALLOWED_TOOLS,
        system_prompt=f"{BASE_SYSTEM_PROMPT} {PRIVACY_SYSTEM_PROMPT}",
    )
    print("Bot started!")


async def post_shutdown(application):
    await postgres_mcp_session.__aexit__(None, None, None)
    print("Bot stopped!")


if __name__ == "__main__":
    application = (
        ApplicationBuilder()
        .token(token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_message)
    )

    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)

    application.run_polling()
