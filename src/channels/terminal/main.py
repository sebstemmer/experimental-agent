import asyncio

from dotenv import load_dotenv

from channels.agent_setup import build_agent, build_mcp_client
from channels.handle_message import handle_message

load_dotenv()


async def main() -> None:
    client = build_mcp_client()

    async with client.session("postgres") as session:
        agent = await build_agent(session, allowed_tools=None)

        thread_id = "terminal"
        pending = 0

        while True:
            text = await asyncio.to_thread(input, "> ")
            reply, pending = await handle_message(agent, thread_id, text, pending)
            print(reply)


asyncio.run(main())
