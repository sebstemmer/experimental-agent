import logging
import os
from datetime import time
from zoneinfo import ZoneInfo

from telegram.ext import ContextTypes, JobQueue

from channels.handle_message import handle_message

BRIEFING_TIME = time(7, 0, tzinfo=ZoneInfo("Europe/Berlin"))
BRIEFING_PROMPT = (
    "Start with a short greeting like 'Good morning Sebastian', then list my "
    "todos in three groups, each todo appearing exactly once: overdue ones "
    "first, then those due within the next 7 days, then the remaining open "
    "ones including those without a due date."
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
