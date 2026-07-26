from database import create_all_tables_on_start
from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan


@lifespan
async def app_lifespan(_server):
    await create_all_tables_on_start()
    yield {}


mcp = FastMCP("Demo 🚀", lifespan=app_lifespan)
