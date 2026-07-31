from datetime import datetime
from zoneinfo import ZoneInfo

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware, dynamic_prompt
from langchain.agents.middleware.types import ModelRequest
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.checkpoint.memory import InMemorySaver

from utils.require_env import require_env

BASE_SYSTEM_PROMPT = (
    "You are a helpful assistant. "
    "Reply in plain text only. Do not use any Markdown formatting "
    "(no **bold**, no *italic*, no backticks, no headings or bullet markup) — "
    "the chat client shows it as literal characters."
)

def make_prompt_with_time(system_prompt: str):
    @dynamic_prompt
    def prompt_with_time(request: ModelRequest) -> str:
        now = datetime.now(ZoneInfo("Europe/Berlin"))
        return f"{system_prompt}\n\\Current date/time: {now.isoformat()}"

    return prompt_with_time


def describe_complete_todo(tool_call, state, runtime) -> str:
    return f"Complete todo {tool_call['args'].get('id')}?"


def build_mcp_client() -> MultiServerMCPClient:
    agent_folder = require_env("AGENT_FOLDER")
    postgres_mcp_python = require_env("POSTGRES_MCP_PYTHON")
    project_root = require_env("PROJECT_ROOT")

    return MultiServerMCPClient(
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
                "args": ["-m", "postgres_mcp.main"],
                "cwd": project_root,
            },
        }
    )


async def build_agent(postgres_session, system_prompt: str = BASE_SYSTEM_PROMPT):
    tools = await load_mcp_tools(postgres_session)
    return create_agent(
        model="openai:gpt-5.5",
        tools=tools,
        checkpointer=InMemorySaver(),
        middleware=[
            make_prompt_with_time(system_prompt),
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
