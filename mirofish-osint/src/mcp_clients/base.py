import json
from mcp import StdioServerParameters, stdio_client, ClientSession


class InternalMCPClient:
    def __init__(self, command: str, args: list[str] | None = None, env: dict[str, str] | None = None):
        self.server_params = StdioServerParameters(
            command=command,
            args=args or [],
            env=env,
        )

    async def call_tool(self, tool_name: str, arguments: dict) -> any:
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                if result.content and len(result.content) > 0:
                    text = result.content[0].text
                    try:
                        return json.loads(text)
                    except (json.JSONDecodeError, AttributeError):
                        return text
                return None
