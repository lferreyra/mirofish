"""
Research Service - calls OSINT MCP server to gather intelligence on a topic
"""
import httpx
import json
from ..utils.logger import get_logger

logger = get_logger('mirofish.research_service')


class ResearchService:
    def __init__(self, mcp_url: str = "http://localhost:8080/mcp"):
        self.mcp_url = mcp_url

    def research(self, topic: str, depth: str = "shallow", output_format: str = "mirofish") -> dict:
        """
        Call the OSINT MCP server's research_and_synthesize tool.

        Args:
            topic: Research subject
            depth: "shallow" | "deep" | "research"
            output_format: "mirofish" | "general"

        Returns:
            {"success": True, "report": "...", "topic": "..."} or
            {"success": False, "error": "..."}
        """
        try:
            logger.info(f"Starting OSINT research: topic='{topic}', depth='{depth}'")

            # Call MCP server via HTTP using the MCP protocol
            # The FastMCP server accepts JSON-RPC over HTTP
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "research_and_synthesize",
                    "arguments": {
                        "topic": topic,
                        "depth": depth,
                        "output_format": output_format,
                    }
                }
            }

            timeout = 30.0 if depth == "shallow" else 120.0 if depth == "deep" else 660.0

            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    self.mcp_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                result = response.json()

            # Extract the report text from MCP response
            if "result" in result:
                content = result["result"]
                # MCP tool results come as content array
                if isinstance(content, dict) and "content" in content:
                    for item in content["content"]:
                        if item.get("type") == "text":
                            report_text = item["text"]
                            logger.info(f"Research completed. Report length: {len(report_text)}")
                            return {"success": True, "report": report_text, "topic": topic}
                # If result is already a string
                if isinstance(content, str):
                    return {"success": True, "report": content, "topic": topic}

            if "error" in result:
                error_msg = result["error"].get("message", str(result["error"]))
                logger.error(f"MCP error: {error_msg}")
                return {"success": False, "error": error_msg}

            return {"success": False, "error": "Unexpected MCP response format"}

        except httpx.ConnectError:
            logger.error("Cannot connect to OSINT MCP server")
            return {"success": False, "error": "Cannot connect to OSINT MCP server at " + self.mcp_url}
        except httpx.TimeoutException:
            logger.error("Research timed out")
            return {"success": False, "error": "Research timed out. Try a shallower depth."}
        except Exception as e:
            logger.error(f"Research failed: {str(e)}")
            return {"success": False, "error": str(e)}
