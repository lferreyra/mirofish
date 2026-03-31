"""
Research Service - calls OSINT MCP server to gather intelligence on a topic
Uses the MCP streamable HTTP protocol (initialize → tools/call → parse SSE)
"""
import httpx
import json
from ..utils.logger import get_logger

logger = get_logger('mirofish.research_service')


class ResearchService:
    def __init__(self, mcp_url: str = "http://localhost:8080/mcp"):
        self.mcp_url = mcp_url

    def _mcp_call(self, method: str, params: dict, request_id: int, session_id: str | None = None, timeout: float = 30.0) -> tuple[dict, str]:
        """
        Send a JSON-RPC request to the MCP server and parse the SSE response.
        Returns (result_dict, session_id).
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if session_id:
            headers["Mcp-Session-Id"] = session_id

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        with httpx.Client(timeout=timeout) as client:
            response = client.post(self.mcp_url, json=payload, headers=headers)
            response.raise_for_status()

            new_session_id = response.headers.get("mcp-session-id", session_id)

            # Parse SSE response - look for "data:" lines
            result = None
            for line in response.text.split("\n"):
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if "result" in data:
                        result = data["result"]
                    elif "error" in data:
                        raise Exception(data["error"].get("message", str(data["error"])))

            return result, new_session_id

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

            timeout = 30.0 if depth == "shallow" else 120.0 if depth == "deep" else 660.0

            # Step 1: Initialize MCP session
            init_result, session_id = self._mcp_call(
                method="initialize",
                params={
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "MiroFish", "version": "1.0"},
                },
                request_id=1,
                timeout=10.0,
            )
            logger.info(f"MCP session initialized: {session_id}")

            # Step 2: Send initialized notification (no response expected)
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Mcp-Session-Id": session_id,
            }
            with httpx.Client(timeout=5.0) as client:
                client.post(
                    self.mcp_url,
                    json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                    headers=headers,
                )

            # Step 3: Call research_and_synthesize tool
            tool_result, _ = self._mcp_call(
                method="tools/call",
                params={
                    "name": "research_and_synthesize",
                    "arguments": {
                        "topic": topic,
                        "depth": depth,
                        "output_format": output_format,
                    },
                },
                request_id=2,
                session_id=session_id,
                timeout=timeout,
            )

            # Extract report text from MCP tool result
            if isinstance(tool_result, dict) and "content" in tool_result:
                for item in tool_result["content"]:
                    if isinstance(item, dict) and item.get("type") == "text":
                        report_text = item["text"]
                        logger.info(f"Research completed. Report length: {len(report_text)}")
                        return {"success": True, "report": report_text, "topic": topic}

            if isinstance(tool_result, str):
                return {"success": True, "report": tool_result, "topic": topic}

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
