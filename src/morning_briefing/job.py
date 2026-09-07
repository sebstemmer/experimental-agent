import logging
import os
from datetime import time
from zoneinfo import ZoneInfo

from telegram.ext import ContextTypes, JobQueue

from channels.handle_message import handle_message

BRIEFING_TIME = time(7, 0, tzinfo=ZoneInfo("Europe/Berlin"))
BRIEFING_PROMPT = (
    "Send my morning briefing. Use exactly this format and nothing else:\n\n"
    "Good morning Sebastian\n\n"
    "Today:\n"
    "<todos due today, plus every todo without a due date>\n\n"
    "Next 7 days:\n"
    "<todos due in the next 7 days, except those already under Today>\n\n"
    "Overdue:\n"
    "<todos whose due date is in the past>\n\n"
    "Start every todo with the id the tool returned, so I can refer to it. "
    "Todos matching none of these are simply left out. "
    "Omit a section completely when it has no todos."
)

logger = logging.getLogger(__name__)


def register(job_queue: JobQueue) -> None:
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not chat_id:
        logger.info("TELEGRAM_CHAT_ID is not set, no morning briefing scheduled")
        return

    async def send_morning_briefing(context: ContextTypes.DEFAULT_TYPE) -> None:
        agent = context.application.bot_data["agent"]
        reply, _ = await handle_message(agent, chat_id, BRIEFING_PROMPT, 0)
        await context.bot.send_message(chat_id=chat_id, text=reply)

    job_queue.run_daily(send_morning_briefing, time=BRIEFING_TIME)
