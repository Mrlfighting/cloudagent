import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from config.settings import create_llm
from tools.vector_tool import query_vector_db
from tools.graph_tool import query_knowledge_graph
from core.workflow.state import AgentState
from typing import Dict, Any

class ProductAgentNode:
    def __init__(self):
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        load_dotenv(dotenv_path)
        self.llm = create_llm(temperature=0.1)
        self.tools = [query_vector_db, query_knowledge_graph]

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        memory_context = state.get("memory_context", "")
        system_prompt = f"""You are a professional cloud service [Product Agent].
Your task is to answer user questions about cloud products (ECS, VPC, etc.).
You have two tools:
1. query_vector_db: Semantic search for concepts, steps, policies.
2. query_knowledge_graph: Query knowledge graph for architecture, entity relationships, config limits.

Requirements:
- Analyze the user's question and decide which tool(s) to use.
- For structured queries (network interfaces, bandwidth, instance relationships), prefer query_knowledge_graph.
- If knowledge graph times out or fails, fall back to query_vector_db.
- Never fabricate information. If tool returns no results, honestly tell the user.
- End each answer with data sources in format:
  Sources:
  - Vector: xxx.md

[Memory context]:
{memory_context if memory_context else "No background context."}
"""
        inner_agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=system_prompt
        )
        print("[ProductAgent] Processing product inquiry...")
        result = await inner_agent.ainvoke({"messages": state["messages"]})
        final_message = result["messages"][-1]
        return {"messages": [final_message]}
