import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware, dynamic_prompt
from langchain.agents.middleware.types import ModelRequest
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


token = require_env("BOT_TOKEN")
agent_folder = require_env("AGENT_FOLDER")
postgres_mcp_python = require_env("POSTGRES_MCP_PYTHON")
postgres_mcp_script = require_env("POSTGRES_MCP_SCRIPT")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!"
    )


APPROVALS = {"yes", "y", "ok"}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if (
        not update.message
        or not update.message.text
        or context.chat_data is None
        or not update.effective_chat
    ):
        return

    agent = context.bot_data["agent"]
    config = {"configurable": {"thread_id": str(update.effective_chat.id)}}
    text = update.message.text

    pending = context.chat_data.get("pending_decisions", 0)
    if pending:
        if text.strip().lower() in APPROVALS:
            decisions = [{"type": "approve"} for _ in range(pending)]
        else:
            decisions = [
                {"type": "reject", "message": f"User declined: {text}"}
                for _ in range(pending)
            ]
        result = await agent.ainvoke(
            Command(resume={"decisions": decisions}), config=config
        )
    else:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": text}]}, config=config
        )

    if interrupts := result.get("__interrupt__"):
        action_requests = interrupts[0].value["action_requests"]
        context.chat_data["pending_decisions"] = len(action_requests)
        question = "\n".join(action["description"] for action in action_requests)
        await update.message.reply_text(f"{question}\n\n(yes/no)")
        return

    context.chat_data["pending_decisions"] = 0
    await update.message.reply_text(result["messages"][-1].content)


client = MultiServerMCPClient(
    {
        "filesystem": {
            "transport": "stdio",
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                agent_folder,
            ],
        },
        "postgres": {
            "transport": "stdio",
            "command": postgres_mcp_python,
            "args": [postgres_mcp_script],
        },
    }
)

postgres_mcp_session = client.session("postgres")

BASE_SYSTEM_PROMPT = "You are a helpful assistant."


@dynamic_prompt
def prompt_with_time(request: ModelRequest) -> str:
    now = datetime.now(ZoneInfo("Europe/Berlin"))
    return f"{BASE_SYSTEM_PROMPT}\n\\Current date/time: {now.isoformat()}"


def describe_complete_todo(tool_call, state, runtime) -> str:
    return f"Complete todo {tool_call['args'].get('id')}?"


async def post_init(application):
    session = await postgres_mcp_session.__aenter__()
    tools = await load_mcp_tools(session)
    application.bot_data["agent"] = create_agent(
        model="openai:gpt-5.5",
        tools=[get_weather] + tools,
        checkpointer=InMemorySaver(),
        middleware=[
            prompt_with_time,
            HumanInTheLoopMiddleware(
                interrupt_on={
                    "complete_todo": {
                        "allowed_decisions": ["approve", "reject"],
                        "description": describe_complete_todo,
                    }
                }
            ),
        ],
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
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)

    application.run_polling()
