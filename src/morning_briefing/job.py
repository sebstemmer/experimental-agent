import logging
import os
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from telegram.ext import ContextTypes, JobQueue

from channels.handle_message import handle_message

BERLIN = ZoneInfo("Europe/Berlin")
BRIEFING_TIME = time(7, 0, tzinfo=BERLIN)

logger = logging.getLogger(__name__)


def build_briefing_prompt() -> str:
    today = datetime.now(BERLIN).date()
    tomorrow = today + timedelta(days=1)
    week_end = today + timedelta(days=7)
    return (
        f"Send my morning briefing. Today is {today}. "
        "Use exactly this format and nothing else:\n\n"
        "Good morning Sebastian\n\n"
        "Today:\n"
        f"<todos with due date {today}, plus every todo without a due date>\n\n"
        "Next 7 days:\n"
        f"<todos with due date from {tomorrow} to {week_end}>\n\n"
        "Overdue:\n"
        f"<todos with due date before {today}>\n\n"
        "Copy each todo exactly as the tool returned it, unchanged - id, title, "
        "due date and recurrence. Do not shorten or reword them. "
        "Todos matching none of these are simply left out. "
        "Omit a section completely when it has no todos."
    )


def register(job_queue: JobQueue) -> None:
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not chat_id:
        logger.info("TELEGRAM_CHAT_ID is not set, no morning briefing scheduled")
        return

    async def send_morning_briefing(context: ContextTypes.DEFAULT_TYPE) -> None:
        agent = context.application.bot_data["agent"]
        reply, _ = await handle_message(agent, chat_id, build_briefing_prompt(), 0)
        await context.bot.send_message(chat_id=chat_id, text=reply)

    job_queue.run_daily(send_morning_briefing, time=BRIEFING_TIME)
