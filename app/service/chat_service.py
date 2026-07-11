import asyncio
import json
import sys
import os

# Initialize Agent and Graph
AGENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent")
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

from core.workflow.graph_manager import AgentGraphManager
from core.memory.memory_manager import MemoryManager
from infra.cache import semantic_cache

# Global variables for graph and memory，懒加载全局单例
graph = None
memory = None

async def init_agent_system():
    global graph, memory
    if graph is None:
        print("[Init] Initializing Multi-Agent graph...")
        graph_manager = AgentGraphManager()
        graph = graph_manager.build_graph()

        print("[Init] Initializing Memory system...")
        from config import get_settings
        settings = get_settings()
        memory = MemoryManager(
            redis_url=settings.redis_url,
            redis_ttl=settings.redis_ttl,
            milvus_host=settings.milvus_host,
            milvus_port=settings.milvus_port,
            milvus_api_key=settings.milvus_api_key,
            embedding_api_key=settings.dashscope_api_key,
        )
        await memory.initialize()
        # Run semantic cache init in thread to avoid Milvus blocking
        try:
            loop = asyncio.get_running_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, semantic_cache.initialize_sync),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            print("[Init] Semantic cache init timed out, continuing without cache...")
        except Exception as e:
            print(f"[Init] Semantic cache init failed: {e}")
        print("[Init] Agent system initialized!")
#注入记忆到Agent，直接从提示词注入
async def _extract_memory_context(user_id: str, session_id: str, query: str) -> str:
    context_parts = []
    if memory and memory.short_term.available:
        history = await memory.short_term.get_messages(user_id, session_id)
        if history:
            recent_history = history[-10:] if len(history) > 10 else history
            context_parts.append("[Recent conversation history]:")
            for msg in recent_history:
                role = "User" if msg["role"] == "user" else "Assistant"
                context_parts.append(f"{role}: {msg['content']}")

    if memory and memory.long_term.available:
        prefs = await memory.long_term.retrieve_relevant(user_id, query)
        if prefs:
            context_parts.append("\n[User long-term preferences]:")
            for p in prefs:
                context_parts.append(f"- {p}")

    return "\n".join(context_parts)
"""
[Recent conversation history]:
User: 我上次问过阿里云ECS的配置
Assistant: 是的，ECS提供多种实例规格...
User: 那再帮我推荐一个便宜点的
Assistant: 考虑到预算，建议ecs.c7.large...

[User long-term preferences]:
- 城市: 杭州
- 偏好: 回答简洁
- 行业: 金融科技
"""
async def stream_chat(query: str, user_id: str, session_id: str):
    #语义缓存检查，
    cache_hit = await semantic_cache.get_cache(query, user_id)
    if cache_hit:
        response_text = cache_hit["answer"]
        print(
            f"[Cache] Hit: {cache_hit['level']} distance={cache_hit['distance']:.4f} matched='{cache_hit['matched_question']}'"
        )
    else:
        print("[Agent] Entering Agent workflow...")
        mem_context = await _extract_memory_context(user_id, session_id, query)
        state = {
            "messages": [("user", query)],
            "user_id": user_id,
            "session_id": session_id,
            "memory_context": mem_context,
            "next_agent": "",
            "metadata": {}
        }
        config = {"configurable": {"user_id": user_id}}
        result = await graph.ainvoke(state, config=config)
        response_text = result["messages"][-1].content

    # Save short-term memory
    if memory and memory.short_term.available:
        turn = [
            {"role": "user", "content": query},
            {"role": "assistant", "content": response_text},
        ]
        await memory.save_conversation(user_id, session_id, turn)

    # Stream response as SSE
    chunk_size = 5
    for i in range(0, len(response_text), chunk_size):
        chunk = response_text[i:i+chunk_size]
        yield f"data: {json.dumps({'content': chunk})}\n\n"
        await asyncio.sleep(0.02)

    yield f"data: {json.dumps({'done': True})}\n\n"
