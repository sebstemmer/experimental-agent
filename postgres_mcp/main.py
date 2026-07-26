import todo.tools  # noqa: F401 -- import triggers @mcp.tool registration
from dotenv import load_dotenv
from mcp_app import mcp

load_dotenv()

if __name__ == "__main__":
    mcp.run()
