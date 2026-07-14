import asyncio
import json
import os
import sys
import time

AGENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent")
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

from app_config.settings import settings as app_settings
from core.memory.memory_manager import MemoryManager
from core.workflow.graph_manager import AgentGraphManager
from infra.cache import semantic_cache
from service.agent_trace_service import append_trace_stage, finish_trace, start_trace
from service.demo_agent_service import build_demo_response
from service.session_service import append_message

graph = None
memory = None


async def init_agent_system():
    global graph, memory
    if app_settings.agent_demo_mode:
        print("[Init] AGENT_DEMO_MODE=true, skipping real Agent, memory and semantic cache initialization.")
        return

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


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _duration_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)


def _route_label(result: dict) -> str:
    route_agent = result.get("next_agent") or "unknown"
    metadata = result.get("metadata") or {}
    if metadata.get("is_finops_workflow"):
        return "billing_agent->finops_agent"
    return route_agent


async def stream_chat(query: str, user_id: str, session_id: str):
    started_at = time.perf_counter()
    trace_id = start_trace(user_id, session_id, query)
    route_agent = None

    def status_event(status: str, message: str) -> str:
        append_trace_stage(trace_id, status, message)
        return _sse({"type": "status", "status": status, "message": message})

    try:
        append_message(user_id, session_id, "user", query)

        if app_settings.agent_demo_mode:
            yield status_event("thinking", "正在理解问题...")
            await asyncio.sleep(0)
            demo_result = build_demo_response(query)
            route_agent = demo_result.route_agent
            yield status_event("agent_routing", f"已路由到 {route_agent}")
            await asyncio.sleep(0)
            yield status_event("tool_calling", f"正在调用 {demo_result.tool_name}")
            await asyncio.sleep(0)
            response_text = demo_result.answer
        else:
            yield status_event("thinking", "正在理解问题...")
            await asyncio.sleep(0)

            yield status_event("cache_lookup", "正在检查历史答案...")
            cache_hit = await semantic_cache.get_cache(query, user_id)
            if cache_hit:
                route_agent = "semantic_cache"
                response_text = cache_hit["answer"]
                append_trace_stage(trace_id, "cache_hit", f"命中语义缓存: {cache_hit.get('level', 'unknown')}")
                print(
                    f"[Cache] Hit: {cache_hit['level']} distance={cache_hit['distance']:.4f} matched='{cache_hit['matched_question']}'"
                )
            else:
                print("[Agent] Entering Agent workflow...")
                yield status_event("retrieving_context", "正在读取对话历史和用户偏好...")
                mem_context = await _extract_memory_context(user_id, session_id, query)
                state = {
                    "messages": [("user", query)],
                    "user_id": user_id,
                    "session_id": session_id,
                    "memory_context": mem_context,
                    "next_agent": "",
                    "metadata": {},
                }
                config = {"configurable": {"user_id": user_id}}
                yield status_event("agent_working", "正在思考并查询必要工具...")
                result = await graph.ainvoke(state, config=config)
                route_agent = _route_label(result)
                append_trace_stage(trace_id, "agent_routed", f"命中 {route_agent}")
                response_text = result["messages"][-1].content

        append_message(user_id, session_id, "assistant", response_text)

        if not app_settings.agent_demo_mode and memory and memory.short_term.available:
            turn = [
                {"role": "user", "content": query},
                {"role": "assistant", "content": response_text},
            ]
            await memory.save_conversation(user_id, session_id, turn)

        yield status_event("streaming", "正在生成回答...")
        chunk_size = 5
        for i in range(0, len(response_text), chunk_size):
            yield _sse({"type": "content", "content": response_text[i : i + chunk_size]})
            await asyncio.sleep(0.02)

        finish_trace(
            trace_id,
            status="success",
            route_agent=route_agent,
            duration_ms=_duration_ms(started_at),
        )
        yield _sse({"type": "done", "done": True})
    except Exception as exc:
        error_text = f"请求处理失败：{exc}"
        try:
            append_message(user_id, session_id, "assistant", error_text)
        except Exception:
            pass
        append_trace_stage(trace_id, "error", error_text)
        finish_trace(
            trace_id,
            status="error",
            route_agent=route_agent,
            duration_ms=_duration_ms(started_at),
            error_message=error_text,
        )
        yield _sse({"type": "error", "message": error_text})
