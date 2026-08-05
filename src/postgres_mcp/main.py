from dotenv import load_dotenv

import postgres_mcp.emails.tools
import postgres_mcp.todo.tools  # noqa: F401 -- import triggers @mcp.tool registration
from postgres_mcp.mcp_app import mcp

load_dotenv()

if __name__ == "__main__":
    mcp.run()
