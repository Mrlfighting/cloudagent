<h1 align="center">Cloud Agent</h1>

<p align="center">
  <strong>面向云产品咨询、业务查询与 FinOps 分析的多智能体客服系统</strong>
</p>

<p align="center">
  基于 LangGraph 编排专业 Agent，结合 MCP 工具、RAG、分层记忆、SSE 流式交互与调用链追踪，<br />
  提供从用户登录、会话持久化到 Agent 执行与质量评测的完整应用链路。
</p>

<p align="center">
  <a href="#四系统架构">系统架构</a> ·
  <a href="#六本地部署">本地部署</a> ·
  <a href="#七测试与评测">测试与评测</a> ·
  <a href="#十演示用例">演示用例</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Vue-3.5+-42b883?logo=vuedotjs&logoColor=white" alt="Vue 3" />
  <img src="https://img.shields.io/badge/LangGraph-1.1+-1c3c3c" alt="LangGraph" />
  <img src="https://img.shields.io/badge/MySQL-8.0-4479a1?logo=mysql&logoColor=white" alt="MySQL 8" />
  <img src="https://img.shields.io/badge/Redis-7-dc382d?logo=redis&logoColor=white" alt="Redis 7" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ed?logo=docker&logoColor=white" alt="Docker Compose" />
</p>

---

## 一、项目介绍

**Cloud Agent** 是一个面向云平台服务场景的全栈 Multi-Agent 项目。系统将产品知识问答、订单与资源查询、产品推荐、推广材料查询和 FinOps 资源优化拆分为独立 Agent，由 Orchestrator 根据用户意图进行调度，并通过 LangGraph 管理执行状态与跨 Agent 协作。

项目不仅关注“让模型回答问题”，还补齐了一个可运行应用需要的外围能力：多用户认证、会话历史、消息持久化、用户数据隔离、流式响应、短期与长期记忆、调用轨迹、数据库迁移、自动化测试、Agent 评测集和 Docker Compose 本地部署。

### 为什么做这个项目？

云平台客服请求通常同时包含知识问答、用户数据查询、产品选型和成本治理等不同任务。将所有能力塞进单个 Prompt 会使工具权限、上下文范围和执行链路难以维护。Cloud Agent 使用“Orchestrator + 专业 Agent + 工具层”的方式拆分职责，让每类 Agent 只访问完成任务所需的工具和上下文，并通过 Trace 记录执行过程，便于调试和扩展。

### 核心能力

1. **多智能体编排**：Orchestrator 调度 Product、Billing、Promotion、Recommendation、FinOps 五类专业 Agent。
2. **跨 Agent 状态交接**：FinOps 请求先由 Billing Agent 获取用户资源，再将状态交给 FinOps Agent 生成优化建议。
3. **工具与知识检索**：通过 MCP 调用订单、实例、监控指标和产品目录工具，通过 Milvus 与 Neo4j 完成向量检索和知识图谱检索。
4. **分层记忆**：MySQL 保存完整会话，Redis 保存带 TTL 的近期上下文，Milvus 保存可语义召回的长期用户偏好。
5. **多用户与会话隔离**：JWT access token、refresh token 轮换、登出撤销、会话归属校验和软删除。
6. **流式交互与可观测性**：SSE 返回阶段状态和回答片段，Trace 记录路由结果、阶段、耗时和失败原因。
7. **双运行模式**：真实模式接入 DashScope、RAG 和 MCP；Demo 模式完全离线，保证本地演示稳定可复现。
8. **工程化交付**：Alembic、pytest、Playwright、确定性 Agent eval、Docker Compose 和 utf8mb4 数据库规范。

## 二、技术亮点

### 1. LangGraph 多 Agent 协作

- 使用 `StateGraph` 管理 Agent 状态，以 Orchestrator 作为统一入口。
- Product、Billing、Promotion、Recommendation 和 FinOps Agent 分别维护自己的 Prompt 与工具集合。
- Billing Agent 执行后根据 `is_finops_workflow` 决定直接结束，或将上下文交给 FinOps Agent，形成可解释的 State Handoff。
- 专业 Agent 内部使用 ReAct 模式自主选择工具，业务编排与工具实现相互解耦。

### 2. MCP、Vector RAG 与 Graph RAG

- MCP Server 封装产品目录、推广材料、订单、实例和资源指标等结构化工具。
- Billing 与 FinOps 工具调用通过拦截器注入当前登录用户 ID，避免模型参数绕过用户隔离。
- Product Agent 组合 Milvus 向量检索与 Neo4j 知识图谱检索，兼顾语义相关性和实体关系。
- Recommendation Agent 将产品目录工具与向量知识库结合，输出有依据的产品选型建议。

### 3. 三层上下文与记忆

| 层级 | 存储 | 作用 | 生命周期 |
| --- | --- | --- | --- |
| 会话事实 | MySQL | 保存会话、用户消息和 Agent 回答，支持刷新后恢复 | 长期持久化 |
| 短期上下文 | Redis | 保存近期对话，按 `user_id + session_id` 隔离 | 默认 TTL 30 分钟 |
| 长期偏好 | Milvus | 保存用户偏好并按当前问题进行语义召回 | 长期持久化 |

真实 Agent 模式会向执行状态注入最近 10 条短期消息与相关长期偏好；Redis、Milvus 或语义缓存不可用时，相关模块会降级，不影响基础 API 启动。

### 4. 认证、会话与数据隔离

- bcrypt 保存密码哈希，JWT access token 用于 API 鉴权。
- refresh token 仅保存 SHA-256 哈希，刷新时轮换，登出后立即撤销。
- 会话、消息和 Trace 均按当前登录用户校验归属，跨用户访问返回 404。
- 会话删除采用 `deleted_at` 软删除，保留数据审计与后续恢复空间。

### 5. SSE 流式状态与 Agent Trace

聊天接口统一输出四类 JSON 事件：

| 事件 | 作用 |
| --- | --- |
| `status` | 展示正在思考、检查缓存、读取上下文、路由 Agent、调用工具等阶段 |
| `content` | 增量输出回答内容 |
| `done` | 标记本次请求正常结束 |
| `error` | 返回可理解的错误信息，不向前端暴露堆栈 |

每次请求同时写入 `agent_call_traces`，记录 `trace_id`、用户、会话、问题、阶段列表、命中 Agent、总耗时和失败原因。前端调用轨迹抽屉可以按当前用户和会话查看这些信息。

### 6. 可复现的 Demo 与质量评测

`AGENT_DEMO_MODE=true` 时，系统不会调用 DashScope、Embedding、RAG 或外部 MCP，而是使用确定性规则覆盖订单、账单、产品问答、产品推荐和资源优化五类场景。Demo 模式仍会完整执行鉴权、会话持久化、SSE 和 Trace 链路，因此适合离线开发、自动化测试和项目演示。

### 工程指标

| 指标 | 当前实现 |
| --- | ---: |
| 专业 Agent | 5 个 + 1 个 Orchestrator |
| 业务 API | 11 个 |
| MySQL 业务表 | 8 张 |
| Alembic migration | 2 个版本 |
| pytest 主测试 | 9 项 |
| Playwright E2E | 3 条场景 |
| 确定性 Agent eval | 5 类意图 |
| Docker Compose 服务 | 8 个 |

> 上述数字来自当前仓库代码与测试集，不代表生产环境性能指标。项目尚未发布标准化并发量、吞吐量或响应时延数据，因此不提供未经复现实验的性能结论。

## 三、功能模块

| 模块 | 主要能力 | 依赖 |
| --- | --- | --- |
| 用户认证 | 登录、token 刷新、登出撤销、当前用户信息 | FastAPI、JWT、MySQL |
| 会话管理 | 新建、切换、恢复消息、软删除、用户隔离 | MySQL |
| 智能聊天 | Agent 路由、上下文注入、流式输出、异常处理 | LangGraph、SSE |
| 产品问答 | 云产品概念、规格与使用建议 | Milvus、Neo4j、DashScope |
| 订单与资源查询 | 查询当前用户订单、实例和账单相关信息 | MCP、MySQL |
| 产品推荐 | 按业务类型、预算和规格需求给出选型建议 | MCP、Vector RAG |
| 推广服务 | 可推广产品、产品目录和推广材料查询 | MCP |
| FinOps | 获取资源利用率并给出降配、计费和带宽优化建议 | MCP、MySQL |
| 调用轨迹 | 路由 Agent、阶段、耗时、错误信息展示 | MySQL、Vue |
| 离线演示 | 五类确定性场景，不依赖模型与外部网络 | Demo Router |

## 四、系统架构

### 1. 分层架构

~~~mermaid
flowchart TB
    subgraph Client["访问与展示层"]
        direction LR
        Browser([桌面端 / 移动端浏览器])
        Web["Vue 3 + TypeScript<br/>Element Plus · 响应式布局"]
        Nginx["Nginx<br/>静态资源 · API 反向代理"]
    end

    subgraph API["应用服务层 · FastAPI"]
        direction LR
        Auth["认证服务<br/>JWT · Refresh Token"]
        Session["会话服务<br/>历史恢复 · 软删除"]
        Chat["聊天服务<br/>SSE · 异常降级"]
        Trace["Trace 服务<br/>阶段 · 路由 · 耗时"]
    end

    subgraph Runtime["Agent 运行层 · LangGraph"]
        direction TB
        Demo["Demo Router<br/>确定性离线路由"]
        Cache["Semantic Cache<br/>相似问题复用"]
        Orchestrator["Orchestrator<br/>意图识别与任务调度"]
        Agents["专业 Agent<br/>Product · Billing · Promotion<br/>Recommendation · FinOps"]
    end

    subgraph Tools["工具与知识层"]
        direction LR
        MCP["MCP Server<br/>订单 · 实例 · 指标 · 产品目录"]
        Vector["Vector RAG<br/>产品文档语义检索"]
        Graph["Graph RAG<br/>产品实体关系检索"]
        Model["DashScope<br/>对话模型 · Embedding"]
    end

    subgraph Data["数据与基础设施"]
        direction LR
        MySQL[("MySQL 8<br/>用户 · 会话 · 业务数据 · Trace")]
        Redis[("Redis 7<br/>短期上下文 · TTL")]
        Milvus[("Milvus<br/>向量知识 · 长期偏好")]
        Neo4j[("Neo4j<br/>知识图谱")]
    end

    Browser --> Web --> Nginx
    Nginx -->|REST / SSE| Auth & Session & Chat & Trace
    Auth & Session & Trace --> MySQL
    Chat -->|演示模式| Demo
    Chat -->|真实模式| Cache
    Cache -->|未命中| Orchestrator --> Agents
    Cache -->|命中| Chat
    Agents --> MCP & Vector & Graph & Model
    MCP --> MySQL
    Chat --> Redis & Milvus
    Vector --> Milvus
    Graph --> Neo4j
    Demo --> Chat
    Agents --> Chat
    Chat --> MySQL

    classDef client fill:#eefaff,stroke:#55b8d0,color:#202735,stroke-width:1.5px;
    classDef service fill:#fff4f8,stroke:#e879a4,color:#202735,stroke-width:1.5px;
    classDef agent fill:#fff8e8,stroke:#d9a441,color:#202735,stroke-width:1.5px;
    classDef tool fill:#f0fbf7,stroke:#54ae91,color:#202735,stroke-width:1.5px;
    classDef data fill:#f5f1ff,stroke:#8b7bd4,color:#202735,stroke-width:1.5px;
    class Browser,Web,Nginx client;
    class Auth,Session,Chat,Trace service;
    class Demo,Cache,Orchestrator,Agents agent;
    class MCP,Vector,Graph,Model tool;
    class MySQL,Redis,Milvus,Neo4j data;
    style Client fill:#f8fdff,stroke:#b9e4ef
    style API fill:#fff9fb,stroke:#f1c4d4
    style Runtime fill:#fffcf4,stroke:#ecd59d
    style Tools fill:#f8fdfb,stroke:#bde2d5
    style Data fill:#fbf9ff,stroke:#d3cbef
~~~

### 2. 单次聊天请求链路

~~~mermaid
flowchart TD
    Start([用户发送问题]) --> Auth[校验 Access Token 与会话归属]
    Auth --> SaveUser[保存 User 消息并创建 Trace]
    SaveUser --> Status[发送 SSE status: thinking]
    Status --> Mode{AGENT_DEMO_MODE?}

    Mode -->|true| Rule[确定性规则路由]
    Rule --> MockTool[生成本地工具结果]

    Mode -->|false| Cache{语义缓存命中?}
    Cache -->|是| Answer[复用缓存回答]
    Cache -->|否| Context[读取 Redis 近期消息<br/>召回 Milvus 用户偏好]
    Context --> Router[Orchestrator 意图识别]
    Router --> Product[Product Agent]
    Router --> Billing[Billing Agent]
    Router --> Promotion[Promotion Agent]
    Router --> Recommend[Recommendation Agent]
    Billing -->|FinOps 请求| FinOps[FinOps Agent]

    Product & Billing & Promotion & Recommend & FinOps --> Tools[MCP / Vector RAG / Graph RAG]
    Tools --> Answer
    MockTool --> Answer
    Answer --> SaveAssistant[保存 Assistant 消息<br/>完成 Trace 与耗时统计]
    SaveAssistant --> Stream[发送 SSE content 分片]
    Stream --> Done[发送 SSE done]
    Auth -.异常.-> Error[发送 SSE error<br/>Trace 记录失败原因]
    Router -.异常.-> Error
    Tools -.异常.-> Error
~~~

## 五、Agent 设计

| Agent | 责任 | 可用能力 |
| --- | --- | --- |
| Orchestrator | 识别意图并选择下一个 Agent，不直接处理业务 | DashScope LLM、LangGraph 条件边 |
| Product Agent | 产品概念、规格、使用方式和故障知识问答 | Vector RAG、Graph RAG |
| Billing Agent | 查询当前用户订单、实例与账单上下文 | MCP 订单与实例工具 |
| Promotion Agent | 查询可推广产品、目录和推广材料 | MCP 产品与推广工具 |
| Recommendation Agent | 根据业务需求进行产品与规格选型 | Vector RAG、MCP 产品目录 |
| FinOps Agent | 分析资源利用率并生成降本建议 | MCP 实例与监控指标工具 |

真实模式下，Orchestrator 对 FinOps 意图先路由至 Billing Agent 获取资源上下文，再通过 LangGraph 条件边交给 FinOps Agent；普通账单请求在 Billing Agent 完成后直接结束。

## 六、本地部署

项目只提供本地部署方案。推荐先使用 Demo 模式完成全链路验证，再切换到真实 Agent 模式联调模型、RAG 与 MCP。

### 1. 前置条件

| 工具 | 建议版本 | 用途 |
| --- | --- | --- |
| Git | 最新稳定版 | 克隆与版本管理 |
| Docker Desktop / Docker Engine | 24+ | 运行全部服务 |
| Docker Compose | v2 | 本地服务编排 |
| Python | 3.10+ | 源码方式运行后端 |
| Node.js | 20.19+ 或 22.12+ | 源码方式运行前端 |

### 2. 克隆项目

~~~bash
git clone https://github.com/Mrlfighting/cloudagent.git
cd cloudagent
~~~

### 3. 配置环境变量

从示例文件创建本地配置：

~~~bash
cp agent/.env.example agent/.env
~~~

至少需要检查以下配置：

~~~dotenv
# 演示模式：不访问模型、Embedding、RAG 或外部 MCP
AGENT_DEMO_MODE=true

# 请替换为随机长字符串，不要提交到 Git
JWT_SECRET_KEY=replace_with_a_random_secret_at_least_32_chars

# Demo 模式可保留占位值；真实模式必须配置有效 Key
DASHSCOPE_API_KEY=your_dashscope_api_key

MYSQL_PASSWORD=root123
NEO4J_PASSWORD=password123
~~~

> `agent/.env` 已被 `.gitignore` 排除。不要把真实 API Key、JWT 密钥或数据库密码提交到仓库。

### 4. Docker Compose 一键启动

~~~bash
docker compose up -d --build
docker compose ps
~~~

API 容器启动时会自动执行 `alembic upgrade head`，创建表、写入演示账号和 Mock 业务数据。

本地访问地址：

| 服务 | 地址 |
| --- | --- |
| Web 应用 | <http://localhost:5173> |
| FastAPI | <http://localhost:5000> |
| Swagger | <http://localhost:5000/docs> |
| ReDoc | <http://localhost:5000/redoc> |
| Neo4j Browser | <http://localhost:7474> |
| MinIO Console | <http://localhost:9001> |

查看服务日志：

~~~bash
docker compose logs -f api
docker compose logs -f web
~~~

停止本地服务：

~~~bash
docker compose down
~~~

### 5. 源码方式启动

源码运行适合二次开发。MySQL、Redis、Neo4j 和 Milvus 仍可由 Docker Compose 提供：

~~~bash
docker compose up -d mysql redis neo4j etcd minio milvus
~~~

创建 Python 环境并安装依赖：

~~~bash
conda create -n cloud_agent python=3.10 -y
conda activate cloud_agent
python -m pip install -r agent/requirements.txt
~~~

执行数据库迁移：

~~~bash
python -m alembic upgrade head
~~~

启动后端：

~~~bash
cd app
python -m uvicorn app_main:app --host 0.0.0.0 --port 5000 --reload
~~~

在另一个终端启动前端：

~~~bash
cd front/cloud_agent
cp .env.example .env.local
npm ci
npm run dev -- --host 0.0.0.0 --port 5173
~~~

### 6. 切换真实 Agent 模式

修改 `agent/.env`：

~~~dotenv
AGENT_DEMO_MODE=false
DASHSCOPE_API_KEY=replace_with_a_valid_key
~~~

真实模式还需要确保 Redis、Milvus、Neo4j、MySQL 与 MCP Server 可访问。修改配置后重启 API 服务。

## 七、测试与评测

### 1. 后端接口测试

测试覆盖登录与 token 轮换、未认证访问、会话生命周期、软删除、跨用户隔离、SSE、消息持久化、Demo 模式和 Trace API。

~~~bash
python -m pytest tests -q
~~~

### 2. Agent 路由评测

评测集位于 `evals/agent_routes.json`，使用确定性 Demo 路由验证五类核心意图，不依赖 API Key 或外部网络。

~~~bash
python -m evals.run_agent_evals
~~~

预期结果：

~~~text
Agent route evals: 5/5 passed
~~~

### 3. 前端构建与 E2E

~~~bash
cd front/cloud_agent
npm run build
npx playwright install chromium
npm run test:e2e
~~~

E2E 覆盖桌面端登录与会话生命周期、Trace 抽屉、移动端会话抽屉与横向溢出检查，以及不同用户的会话隔离。

## 八、API 与数据模型

### API 概览

| 方法 | 路径 | 认证 | 说明 |
| --- | --- | :---: | --- |
| POST | `/api/auth/login` | 否 | 登录并返回 access/refresh token |
| POST | `/api/auth/refresh` | 否 | 轮换 refresh token |
| POST | `/api/auth/logout` | 是 | 撤销 refresh token |
| GET | `/api/auth/me` | 是 | 获取当前用户 |
| GET | `/api/sessions` | 是 | 获取当前用户会话列表 |
| POST | `/api/sessions` | 是 | 创建会话 |
| GET | `/api/sessions/{session_id}/messages` | 是 | 获取会话消息 |
| DELETE | `/api/sessions/{session_id}` | 是 | 软删除会话 |
| GET | `/api/sessions/{session_id}/traces` | 是 | 获取指定会话的调用轨迹 |
| GET | `/api/traces/recent` | 是 | 获取当前用户最近调用轨迹 |
| POST | `/api/chat` | 是 | 发起 SSE 流式聊天 |

### MySQL 表

| 表 | 用途 |
| --- | --- |
| `users` | 用户、显示名称、密码哈希和禁用状态 |
| `refresh_tokens` | refresh token 哈希、过期时间和撤销状态 |
| `chat_sessions` | 会话标题、归属、更新时间和软删除标记 |
| `chat_messages` | 用户与 Agent 消息 |
| `cloud_orders` | Mock 云产品订单与账单数据 |
| `cloud_instances` | Mock 云资源实例 |
| `instance_metrics_daily` | 实例日级 CPU、内存和带宽指标 |
| `agent_call_traces` | Agent 路由、阶段、耗时和失败原因 |

所有表使用 `utf8mb4` 与 `utf8mb4_unicode_ci`，避免中文会话标题和消息出现乱码。

## 九、项目结构

~~~text
cloudagent/
├── app/
│   ├── app_main.py                 # FastAPI 入口与生命周期
│   ├── router/                     # Auth、Chat、Session、Trace API
│   ├── service/                    # 认证、会话、聊天、Demo、Trace 服务
│   ├── schemas/                    # 请求与响应模型
│   └── infra/                      # MySQL 与语义缓存基础设施
├── agent/
│   ├── agents/                     # Orchestrator 与五类专业 Agent
│   ├── core/workflow/              # LangGraph 状态与图编排
│   ├── core/memory/                # Redis 短期记忆与 Milvus 长期记忆
│   ├── core/mcp/                   # MCP 客户端管理
│   ├── core/graph/                 # Neo4j 知识图谱构建与访问
│   ├── mcp_servers/                # 云平台 MCP 工具服务
│   ├── tools/                      # Vector RAG 与 Graph RAG 工具
│   ├── database/                   # 兼容初始化 SQL
│   └── config/                     # 模型与 MCP 配置
├── front/cloud_agent/
│   ├── src/                        # Vue 聊天应用
│   ├── e2e/                        # Playwright 端到端测试
│   ├── Dockerfile
│   └── nginx.conf
├── migrations/                     # Alembic 版本化迁移
├── tests/                          # pytest 接口与集成测试
├── evals/                          # Agent 路由评测集与 Runner
├── mock_data/                      # 产品、账单和故障知识文档
├── docs/                           # 演示用例文档
├── Dockerfile.api                  # 后端镜像
├── docker-compose.yml              # 本地完整运行环境
└── README.md
~~~

## 十、演示用例

初始化数据包含两个用户，用于演示登录、会话持久化和跨用户隔离：

| 用户名 | 密码 | 用途 |
| --- | --- | --- |
| `user_1001` | `Cloud@123456` | 主要演示账号 |
| `user_1002` | `Cloud@123456` | 用户隔离验证账号 |

推荐在 `AGENT_DEMO_MODE=true` 下依次提问：

| 场景 | 示例问题 | 预期路由 |
| --- | --- | --- |
| 订单查询 | 帮我查一下我最近的订单记录 | `order_agent` |
| 账单查询 | 查询一下这个月的账单和费用构成 | `billing_agent` |
| 产品问答 | 云服务器 ECS 有哪些基本属性？ | `product_agent` |
| 产品推荐 | 我是 Java 接口服务加 MySQL，8 核 16G 够吗？ | `promotion_agent` |
| 资源优化 | 获取近 7 天 CPU、内存、带宽数据并做降本建议 | `finops_agent` |

完整验收步骤与预期关键词见 [演示用例文档](docs/demo-use-cases.md)。

## 十一、当前边界

- 项目面向本地学习、二次开发与演示，不提供线上部署地址。
- 当前不开放用户注册，通过 migration 初始化两个测试账号。
- Demo 模式返回确定性 Mock 数据，用于验证产品链路，不代表真实云厂商账单。
- 真实模式依赖 DashScope 与本地中间件状态；网络、SSL、账号额度或外部服务异常可能影响回答。
- Trace 当前记录请求级 Agent 阶段，不包含每个 LangGraph 内部 token 和所有 MCP 协议报文。
- 项目尚未进行生产级压测、高可用部署、细粒度限流和完整安全审计。

## 十二、常见问题

### 后端提示无法导入 `app_main`

`app_main.py` 位于 `app/` 目录。使用源码启动时先进入该目录：

~~~bash
cd app
python -m uvicorn app_main:app --host 0.0.0.0 --port 5000 --reload
~~~

### `/api/chat` 返回 Connection error

真实模式会访问 DashScope、Embedding、RAG 和 MCP。先将 `AGENT_DEMO_MODE` 设为 `true` 验证本地业务链路；真实联调时再检查 API Key、网络代理、SSL 和账号额度。

### 提示 `agent_call_traces` 表不存在

执行最新 migration：

~~~bash
python -m alembic upgrade head
~~~

### 中文显示为 `????`

确认数据库和业务表使用 `utf8mb4`：

~~~sql
SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME
FROM information_schema.SCHEMATA
WHERE SCHEMA_NAME = 'cloud_platform';
~~~

Docker Compose 已配置 `utf8mb4` 和 `utf8mb4_unicode_ci`。如果旧数据写入时已经损坏，需要重新初始化数据后再创建会话。
