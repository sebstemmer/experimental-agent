import logging
import os
from functools import wraps

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
from morning_briefing.job import build_briefing_prompt
from morning_briefing.job import register as register_morning_briefing
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

TODO_TOOLS = (
    "add_todo",
    "get_all_open_todos",
    "complete_todo",
    "update_todo",
    "delete_todo",
)

SHOPPING_LIST_TOOLS = (
    "add_shopping_list_item",
    "get_all_open_shopping_list_items",
    "complete_shopping_list_items",
    "delete_shopping_list_item",
)

TOOLS_BY_CHAT_ID: dict[int, tuple[str, ...]] = {
    int(require_env("TELEGRAM_CHAT_ID")): TODO_TOOLS + SHOPPING_LIST_TOOLS
}
partner_telegram_chat_id = os.getenv("PARTNER_TELEGRAM_CHAT_ID")
if partner_telegram_chat_id:
    TOOLS_BY_CHAT_ID[int(partner_telegram_chat_id)] = SHOPPING_LIST_TOOLS

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

client = build_mcp_client()
postgres_mcp_session = client.session("postgres")


def restrict_to_allowed_chat(handler):
    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_chat or update.effective_chat.id not in TOOLS_BY_CHAT_ID:
            return

        await handler(update, context)

    return wrapper


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!"
    )


async def chatid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=str(update.effective_chat.id)
    )


@restrict_to_allowed_chat
async def briefing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat:
        return

    agent = context.bot_data["agents"][update.effective_chat.id]
    thread_id = str(update.effective_chat.id)

    reply, _ = await handle_message(agent, thread_id, build_briefing_prompt(), 0)

    await update.message.reply_text(reply)


@restrict_to_allowed_chat
async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if (
        not update.message
        or not update.message.text
        or context.chat_data is None
        or not update.effective_chat
    ):
        return

    agent = context.bot_data["agents"][update.effective_chat.id]
    thread_id = str(update.effective_chat.id)
    pending = context.chat_data.get("pending_decisions", 0)

    reply, pending = await handle_message(
        agent, thread_id, update.message.text, pending
    )
    context.chat_data["pending_decisions"] = pending

    await update.message.reply_text(reply)


async def post_init(application):
    session = await postgres_mcp_session.__aenter__()
    application.bot_data["agents"] = {
        chat_id: await build_agent(
            session,
            allowed_tools=tools,
            system_prompt=f"{BASE_SYSTEM_PROMPT} {PRIVACY_SYSTEM_PROMPT}",
        )
        for chat_id, tools in TOOLS_BY_CHAT_ID.items()
    }

    register_morning_briefing(application.job_queue)

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

    chatid_handler = CommandHandler("chatid", chatid)
    application.add_handler(chatid_handler)

    briefing_handler = CommandHandler("briefing", briefing)
    application.add_handler(briefing_handler)

    application.run_polling()
