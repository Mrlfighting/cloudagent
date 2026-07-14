import os
import json
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from typing import Dict, Any
from config.settings import create_llm

from core.workflow.state import AgentState
from agents.billing_agent import UserIdInjector, normalize_mcp_config

class PromotionAgentNode:
    def __init__(self):
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
        load_dotenv(dotenv_path)
        self.llm = create_llm(temperature=0.3)
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'mcp_servers.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.servers_config = normalize_mcp_config(json.load(f))

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        config = {"configurable": {"user_id": state.get("user_id", "unknown")}}
        client = MultiServerMCPClient(
            connections=self.servers_config.get("mcpServers", {}),
            tool_interceptors=[UserIdInjector()]
        )
        all_tools = await client.get_tools()
        target_tools = ["get_promotable_products", "search_product_catalog", "get_promotion_materials", "generate_ai_poster"]
        tools = [t for t in all_tools if t.name in target_tools]

        memory_context = state.get("memory_context", "")
        system_prompt = f"""You are an enthusiastic cloud service [Promotion Agent].
Your main task is to help users share or promote cloud products.

Workflow:
1. When user says "I want to promote", first call get_promotable_products.
2. After user selects a product, call search_product_catalog to get the product_id.
3. With a valid product_id, call get_promotion_materials for links.
4. Then call generate_ai_poster to create a promotional poster.

Note: System auto-injects user_id. Pass "auto" as placeholder.

[Memory context]:
{memory_context if memory_context else "No background context."}
"""
        inner_agent = create_react_agent(
            model=self.llm,
            tools=tools,
            prompt=system_prompt
        )
        print("[PromotionAgent] Generating promotion materials...")
        result = await inner_agent.ainvoke(
            {"messages": state["messages"]},
            config=config
        )
        final_message = result["messages"][-1]
        return {"messages": [final_message]}
