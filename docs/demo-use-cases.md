# Cloud Agent 演示用例

这些用例用于本地验收和简历/面试演示。建议先执行 `python -m alembic upgrade head`，确认 mock 数据已经写入 MySQL。

## 用例 1：订单查询

- 登录用户：`user_1001`
- 提问：`帮我查一下我最近的订单记录`
- 预期路由：`billing_agent`
- 预期数据：返回 `ORD-1001-001`、`ORD-1001-002`、`ORD-1001-003` 等订单。
- 展示点：Agent 使用当前登录用户，不允许前端传入伪造 user_id。

## 用例 2：实例查询

- 登录用户：`user_1001`
- 提问：`查询我名下的所有运行中的实例`
- 预期路由：`billing_agent`
- 预期数据：返回 `i-bp1_user1001_ecs`、`rm-bp1_user1001_rds`。
- 展示点：MCP 工具查询 MySQL 结构化数据，回答不是模型凭空生成。

## 用例 3：产品问答

- 登录用户：`user_1001`
- 提问：`云服务器ECS有哪些基本属性？`
- 预期路由：`product_agent`
- 预期能力：结合产品知识说明实例规格、地域、可用区、计费模式、网络和存储等概念。
- 展示点：产品知识问答与业务数据查询由不同 Agent 处理。

## 用例 4：产品推荐

- 登录用户：`user_1001`
- 提问：`我是Java接口服务+MySQL，8核16G够吗？推荐具体实例型号。`
- 预期路由：`recommendation_agent`
- 预期能力：结合业务描述推荐 ECS/RDS 等规格，并说明适用原因。
- 展示点：用户输入是自然语言需求，Agent 输出可执行的选型建议。

## 用例 5：资源优化建议

- 登录用户：`user_1001`
- 提问：`获取近7天CPU/内存/带宽数据并做降本建议`
- 预期路由：`billing_agent -> finops_agent`
- 预期数据：`i-bp1_user1001_ecs` 近 7 天 CPU 和内存平均利用率较低。
- 预期建议：可降配、改按量、释放闲置资源或调整实例规格。
- 展示点：跨 Agent 状态交接，先查资源和监控，再做 FinOps 分析。

## 用例 6：推广活动

- 登录用户：`user_1001`
- 提问：`我想推广云服务器ECS，有海报吗？`
- 预期路由：`promotion_agent`
- 预期能力：返回推广链接、佣金信息，若图片模型可用则生成海报。
- 展示点：外部模型/工具异常时应返回可理解失败原因，而不是前端空白。

## 用例 7：用户隔离

1. 使用 `user_1001` 创建会话并提问订单查询。
2. 退出登录。
3. 使用 `user_1002` 登录。
4. 查看会话列表。

预期结果：`user_1002` 看不到 `user_1001` 的任何历史会话。

## 用例 8：Agent 调用轨迹

执行任意聊天后查询：

```sql
SELECT trace_id, user_id, session_id, status, route_agent, duration_ms, error_message
FROM agent_call_traces
ORDER BY id DESC
LIMIT 5;
```

预期结果：可以看到本次调用的状态、命中的 Agent 或缓存、耗时和错误信息。若请求失败，`status = 'error'` 且 `error_message` 有可读原因。