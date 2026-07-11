import os
import json
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from core.workflow.state import AgentState
from typing import Dict, Any
from langchain_mcp_adapters.client import MultiServerMCPClient
from agents.billing_agent import UserIdInjector
from config.settings import create_llm
from tools.vector_tool import query_vector_db

class RecommendationAgent:
    def __init__(self):
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
        load_dotenv(dotenv_path)
        self.llm = create_llm(temperature=0.3)
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'mcp_servers.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.servers_config = json.load(f)

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        memory_context = state.get("memory_context", "")
        config = {"configurable": {"user_id": state.get("user_id", "unknown")}}

        client = MultiServerMCPClient(
            connections=self.servers_config.get("mcpServers", {}),
            tool_interceptors=[UserIdInjector()]
        )
        all_tools = await client.get_tools()
        target_tools = ["get_promotable_products", "search_product_catalog", "get_promotion_materials"]
        mcp_tools = [t for t in all_tools if t.name in target_tools]
        tools = [query_vector_db] + mcp_tools

        system_prompt = f"""You are a senior cloud architect and [Recommendation Agent].
Your task is to recommend the best cloud products based on user requirements.

Workflow:
1. Analyze user requirements (business type, concurrency, budget, region).
2. Call get_promotable_products or search_product_catalog for available products.
3. Call query_vector_db to retrieve technical specs and use cases.
4. Recommend 1-3 products with professional reasoning.
5. Call get_promotion_materials for purchase links.

Requirements:
- Be professional and enthusiastic like an architect consultant.
- Include specific instance models or product names.
- Never recommend products not in the catalog.
- End with: Sources: Vector: xxx.md

[Memory context]:
{memory_context if memory_context else "No background context."}
"""
        inner_agent = create_react_agent(
            model=self.llm,
            tools=tools,
            prompt=system_prompt
        )
        print("[RecommendationAgent] Performing product recommendation...")
        result = await inner_agent.ainvoke(
            {"messages": state["messages"]},
            config=config
        )
        final_message = result["messages"][-1]
        return {"messages": [final_message]}
