# Cloud Agent 演示用例

这些用例用于本地验收、简历展示和面试演示。推荐先设置 `AGENT_DEMO_MODE=true`，这样即使 DashScope、embedding、RAG 或外部 MCP 不可用，也能稳定展示完整产品链路。真实 Agent 联调时再切回 `AGENT_DEMO_MODE=false`。

## 演示前检查

1. 执行 migration：`python -m alembic upgrade head`。
2. 启动后端和前端。
3. 用 `user_1001 / Cloud@123456` 登录。
4. 打开浏览器开发者工具或前端“调用轨迹”抽屉，准备展示 SSE 状态和 Agent trace。

## 用例 1：订单查询

- 提问：`帮我查一下我最近的订单记录`
- Demo 预期路由：`order_agent`
- 真实模式预期：查询订单/账单类工具。
- 预期回答关键词：`订单`、`近 30 天`、`已完成`。
- 展示点：用户身份来自 JWT，前端不能伪造 `user_id`；回答会写入会话历史。

## 用例 2：账单查询

- 提问：`查询一下这个月的账单和费用构成`
- Demo 预期路由：`billing_agent`
- 预期回答关键词：`账单`、`ECS`、`RDS`、`消费`。
- 展示点：账单类问题由专门 Agent 处理，并在 trace 中记录路由和耗时。

## 用例 3：产品问答

- 提问：`云服务器ECS有哪些基本属性？`
- Demo 预期路由：`product_agent`
- 预期回答关键词：`地域`、`实例规格`、`安全组`、`计费方式`。
- 展示点：产品知识问答与业务数据查询拆分为不同 Agent。

## 用例 4：产品推荐

- 提问：`我是Java接口服务+MySQL，8核16G够吗？推荐具体实例型号。`
- Demo 预期路由：`promotion_agent`
- 预期回答关键词：`Java`、`MySQL`、`ECS`、`RDS`。
- 展示点：自然语言需求转为可执行的云资源选型建议。

## 用例 5：资源优化建议

- 提问：`获取近7天CPU/内存/带宽数据并做降本建议`
- Demo 预期路由：`finops_agent`
- 预期回答关键词：`CPU`、`降配`、`包年包月`、`带宽`。
- 展示点：FinOps 场景体现工程深度，不只是普通客服问答。

## 用例 6：调用轨迹展示

1. 完成任意一次聊天。
2. 点击右上角“调用轨迹”按钮。
3. 查看命中 Agent、执行状态、耗时、用户问题和阶段轨迹。

也可以直接查数据库：

```sql
SELECT trace_id, user_id, session_id, status, route_agent, duration_ms, error_message
FROM agent_call_traces
ORDER BY id DESC
LIMIT 5;
```

## 用例 7：用户隔离

1. 使用 `user_1001` 创建会话并提问。
2. 退出登录。
3. 使用 `user_1002` 登录。
4. 查看会话列表和调用轨迹。

预期结果：`user_1002` 看不到 `user_1001` 的历史会话、消息和 trace。

## 用例 8：Agent 路由评测

运行：

```powershell
D:\SoftwareInstallation\Anaconda\envs\cloud_agent\python.exe -m evals.run_agent_evals
```

预期输出：

```text
Agent route evals: 5/5 passed
```

展示点：项目不只“能跑”，还给 Agent 路由准备了可重复评测集，便于后续二次开发时防止能力退化。
