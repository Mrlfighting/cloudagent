import os
import json
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from typing import Dict, Any
from config.settings import create_llm

from core.workflow.state import AgentState
from agents.billing_agent import UserIdInjector
"""
共同构成两阶段流水线
"""
class FinOpsAgentNode:
    def __init__(self):
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
        load_dotenv(dotenv_path)
        self.llm = create_llm(temperature=0.1)
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'mcp_servers.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.servers_config = json.load(f)

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        config = {"configurable": {"user_id": state.get("user_id", "unknown")}}

        client = MultiServerMCPClient(
            connections=self.servers_config.get("mcpServers", {}),
            tool_interceptors=[UserIdInjector()]
        )
        all_tools = await client.get_tools()
        target_tools = ["query_user_instances", "analyze_instance_usage"]
        tools = [t for t in all_tools if t.name in target_tools]
#agent中共享对话历史很重要
        system_prompt = f"""You are a professional cloud [FinOps Cost Optimization Expert].
You received context from the previous BillingAgent.

Your tasks:
1. Review conversation history for target instance IDs.
2. If no instance_id, call query_user_instances first.
3. Call analyze_instance_usage for monitoring data (CPU, memory).
4. Analyze if resources are idle (RESOURCES_IDLE).
5. Give cost-saving suggestions:
   - If CPU is very low, suggest downgrade.
   - Estimate monthly savings.
   - Be professional and genuinely helpful.

Note: System auto-injects user_id. Pass "auto" as placeholder.
Never fabricate instance IDs, monitoring data, or cost savings.
"""
        inner_agent = create_react_agent(
            model=self.llm,
            tools=tools,
            prompt=system_prompt
        )
        print("[FinOpsAgent] Analyzing instance metrics for cost optimization...")
        result = await inner_agent.ainvoke(
            {"messages": state["messages"]},
            config=config
        )
        final_message = result["messages"][-1]
        return {"messages": [final_message], "next_agent": ""}
