import os
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from config.settings import create_llm
from core.workflow.state import AgentState
"""
接受用户信息，识别该使用哪个agent，不做任何业务，只做意图分类识别
"""
class OrchestratorAgent:
    def __init__(self):
        """
        保证任何情况下都能够被加载
        """
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        load_dotenv(dotenv_path)
        self.llm = create_llm(temperature=0.1)

    async def route(self, state: AgentState) -> Dict[str, Any]:
        messages = state.get("messages", [])
        if not messages:
            last_message = ""
        else:
            last_msg_obj = messages[-1]
            if isinstance(last_msg_obj, tuple):
                last_message = last_msg_obj[1]
            elif hasattr(last_msg_obj, "content"):
                last_message = last_msg_obj.content
            else:
                last_message = str(last_msg_obj)
        memory_context = state.get("memory_context", "")

        system_prompt = f"""You are an intelligent customer service orchestrator.
Your task is to decide which specialized agent should handle the user's question.

Available sub-agents:
1. "product_agent" : Cloud product introduction, specs, concepts, operation guides.
2. "billing_agent" : Query user's cloud resource instances, orders, billing details.
3. "promotion_agent" : Product sharing, affiliate promotion, event links, posters.
4. "recommendation_agent" : Cloud product selection and recommendation based on business needs.
5. "finops_agent_trigger" : Cost optimization, resource right-sizing, FinOps suggestions.

Routing rules:
- Product questions (What is VPC, specs) -> product_agent
- My orders/instances -> billing_agent
- Cost optimization ("bill is too expensive", "help me optimize") -> finops_agent_trigger
- Product recommendation/selection -> recommendation_agent
- Promotion/marketing -> promotion_agent

[Memory context]:
{memory_context}

Output ONLY the target name (product_agent, billing_agent, promotion_agent, recommendation_agent, finops_agent_trigger).
Default to product_agent if unsure.
"""

        response = await self.llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=last_message)
        ])

        decision = response.content.strip().lower()
        if "finops" in decision:
            next_node = "billing_agent"
            state["metadata"]["is_finops_workflow"] = True
            print("[Orchestrator] FinOps intent -> billing_agent")
        elif "billing" in decision:
            next_node = "billing_agent"
            state["metadata"]["is_finops_workflow"] = False
            print("[Orchestrator] Billing intent -> billing_agent")
        elif "promotion" in decision:
            next_node = "promotion_agent"
            print("[Orchestrator] Promotion intent -> promotion_agent")
        elif "recommendation" in decision:
            next_node = "recommendation_agent"
            print("[Orchestrator] Recommendation intent -> recommendation_agent")
        else:
            next_node = "product_agent"
            print("[Orchestrator] Default/product intent -> product_agent")

        return {"next_agent": next_node, "metadata": state.get("metadata", {})}
