import os
import json
import asyncio
import sys
from copy import deepcopy
from pathlib import Path
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import ToolCallInterceptor, MCPToolCallRequest, MCPToolCallResult
from typing import Callable, Awaitable, Dict, Any
from config.settings import create_llm
from core.workflow.state import AgentState

class UserIdInjector(ToolCallInterceptor):
    async def __call__(
        self,
        request: MCPToolCallRequest,
        handler: Callable[[MCPToolCallRequest], Awaitable[MCPToolCallResult]],
    ) -> MCPToolCallResult:
        user_id = None
        if hasattr(request.runtime, 'config'):
            config = request.runtime.config
            user_id = config.get("configurable", {}).get("user_id")
        if user_id:
            new_args = dict(request.args)
            new_args["user_id"] = user_id
            new_request = request.override(args=new_args)
            return await handler(new_request)
        return await handler(request)

def normalize_mcp_config(config: dict) -> dict:
    """Resolve MCP stdio settings so they work from both CLI and FastAPI cwd."""
    normalized = deepcopy(config)
    agent_dir = Path(__file__).resolve().parents[1]
    project_root = agent_dir.parent

    for server in normalized.get("mcpServers", {}).values():
        if server.get("command") == "python":
            server["command"] = sys.executable

        cwd = server.get("cwd")
        if cwd:
            cwd_path = Path(cwd)
            if not cwd_path.is_absolute():
                project_candidate = project_root / cwd_path
                agent_candidate = agent_dir / cwd_path
                server["cwd"] = str(
                    project_candidate
                    if project_candidate.exists()
                    else agent_candidate
                )

    return normalized

class BillingAgentNode:
    def __init__(self):
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        load_dotenv(dotenv_path)
        self.llm = create_llm(temperature=0.1)
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'mcp_servers.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.servers_config = normalize_mcp_config(json.load(f))

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        config = {"configurable": {"user_id": state.get("user_id", "unknown")}}
        memory_context = state.get("memory_context", "")
        system_prompt = f"""You are a professional cloud service [Billing & Resource Agent].
You can query user orders, billing details, and cloud resource instances.

Requirements:
- For "my orders", "my billing", use query_user_orders tool.
- For "my instances", "my servers", use query_user_instances tool.
- The system will auto-inject user_id. Pass "auto" as placeholder.
- Never mention the actual user_id in responses.
- Never fabricate instance IDs, order status, or monitoring data.
- If tools fail, give a neutral message and suggest retrying later.

[Memory context]:
{memory_context if memory_context else "No background context."}
"""
        print("[BillingAgent] Processing billing/resource query...")

        client = MultiServerMCPClient(
            connections=self.servers_config.get("mcpServers", {}),
            tool_interceptors=[UserIdInjector()]
        )
        all_tools = await client.get_tools()
        allowed_tool_names = {"query_user_orders", "query_user_instances"}
        tools = [tool for tool in all_tools if tool.name in allowed_tool_names]

        inner_agent = create_react_agent(
            model=self.llm,
            tools=tools,
            prompt=system_prompt
        )
        result = await inner_agent.ainvoke(
            {"messages": state["messages"]},
            config=config
        )
        final_message = result["messages"][-1]
        return {"messages": [final_message]}
