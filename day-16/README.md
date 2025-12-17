# Day 16: LangGraph + A2A + Human-in-the-Loop

## 概述

本项目展示了两个核心能力:

1. **LangGraph + A2A** - 使用 LangGraph 构建 Agent，通过 ADK 暴露 A2A 服务
2. **Human-in-the-Loop (HITL)** - 生产级人机协作实现，支持敏感操作审批

## 练习场景：企业 AI 助手审批系统

### 场景描述

企业级构建 AI 助手，该助手可以帮助员工执行各种操作。但出于安全考虑，某些敏感操作需要管理员审批后才能执行。

```
┌─────────────────────────────────────────────────────────────────┐
│                     企业 AI 助手审批系统                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  员工请求          AI 分析              管理员审批      执行      │
│  ─────────        ────────             ──────────     ────      │
│                                                                 │
│  "查询销售数据"  →  低风险  ────────────────────────→  直接执行  │
│                                                                 │
│  "修改客户信息"  →  中风险  → [等待审批] → 批准 ────→  执行修改  │
│                              │                                  │
│  "删除用户账号"  →  高风险  → [等待审批] → 拒绝 ────→  操作取消  │
│                              │                                  │
│  "批量发送邮件"  →  关键级  → [等待审批] → 超时 ────→  自动拒绝  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 真实场景示例

| 员工请求 | 风险评估 | 处理方式 |
|----------|----------|----------|
| "帮我查一下上个月的销售报表" | `low` | 直接执行，返回数据 |
| "把客户张三的手机号改成 138xxx" | `medium` | 需要审批，防止误操作 |
| "删除离职员工小王的所有数据" | `high` | 必须审批，不可逆操作 |
| "给所有 VIP 客户发送促销邮件" | `critical` | 必须审批，影响范围大 |

### 解决的核心问题

> **Agent 自主性 vs 安全性的平衡**

- 太自主 → 可能执行危险操作，造成损失
- 太保守 → 每个操作都要审批，效率低下
- **HITL 方案** → AI 自动评估风险，仅对高风险操作要求审批

## 核心知识点

### LangGraph 三大核心组件

```
┌─────────────────────────────────────────────────────────────┐
│    [START] ──► [Node A] ──► [Node B] ──► [END]             │
│                   │            ▲                            │
│                   └──► [Node C]┘  (条件边)                  │
└─────────────────────────────────────────────────────────────┘
```

| 组件 | 说明 |
|------|------|
| **State** | 共享内存对象，在所有节点间流转 |
| **Nodes** | 执行逻辑的函数，接收状态返回更新 |
| **Edges** | 节点间转换（静态边/条件边） |

### Human-in-the-Loop 架构

```
┌─────────┐    ┌──────────┐    ┌─────────────┐    ┌─────────┐
│ Analyze │ ─► │ Classify │ ─► │   Human     │ ─► │ Execute │
│ Request │    │   Risk   │    │   Review    │    │ Action  │
└─────────┘    └──────────┘    └─────────────┘    └─────────┘
                    │                 │
                    │ Low Risk        │ Rejected
                    └─────────────────┴─────────► [END]
```

**风险等级:**

| 等级 | 说明 | 是否审批 |
|------|------|----------|
| `low` | 只读查询，无副作用 | 否 |
| `medium` | 数据修改，可撤销 | 可配置 |
| `high` | 数据删除、外部 API 调用 | 是 |
| `critical` | 支付、批量操作、不可逆 | 是 + 二次确认 |

**核心特性:**

- **断点续跑** - 服务重启后可继续执行（需安装 SQLite 支持）
- **超时自动拒绝** - 防止任务无限等待（默认 5 分钟）
- **完整审计日志** - 追踪所有操作
- **状态持久化** - 任务元数据保存到 SQLite

## 项目结构

```
day-16/
├── README.md
├── requirements.txt
├── langgraph_agent/
│   ├── __init__.py
│   ├── agent.py           # LangGraph ReAct Agent + A2A
│   ├── hitl_agent.py      # Human-in-the-Loop Agent 核心
│   ├── checkpointer.py    # 状态持久化
│   └── server.py          # REST API 服务
├── client/
│   ├── test_client.py     # A2A 测试客户端
│   └── hitl_client.py     # HITL 交互客户端
└── data/                  # 运行时生成
    ├── checkpoints.db     # LangGraph 状态
    └── tasks.db           # 任务元数据
```

## 运行示例

### 1. 安装依赖

```bash
cd day-16
uv pip install -r requirements.txt

# 可选：安装 SQLite 持久化支持（生产环境推荐）
uv pip install langgraph-checkpoint-sqlite
```

### 2. 运行 HITL 服务

```bash
# Terminal 1 - 启动服务
uv run python -m langgraph_agent.server
```

输出:
```
============================================================
Day 16: Human-in-the-Loop Agent Server
============================================================

API 端点:
  Base URL: http://localhost:8016
  API Docs: http://localhost:8016/docs

主要功能:
  POST /tasks           - 创建新任务
  GET  /tasks           - 获取任务列表
  GET  /tasks/pending   - 获取待审批任务
  POST /tasks/{id}/approve - 批准任务
  POST /tasks/{id}/reject  - 拒绝任务

审批超时: 300 秒
============================================================
```

```bash
# Terminal 2 - 运行交互式客户端
uv run python -m client.hitl_client
```

### 3. 完整演示流程

```bash
# 1. 启动服务
uv run python -m langgraph_agent.server

# 2. 在另一个终端运行客户端，选择 "6. 运行所有演示"
uv run python -m client.hitl_client

# 演示包括:
# - 低风险任务（查询天气）→ 自动执行
# - 高风险任务（删除数据）→ 等待审批 → 拒绝
# - 中风险任务（发送邮件）→ 等待审批 → 批准
```

### 4. 使用 curl 测试

```bash
# 场景 1: 低风险查询 - 直接返回结果
curl -X POST http://localhost:8016/tasks \
  -H "Content-Type: application/json" \
  -d '{"message": "查询今天北京的天气"}'

# 场景 2: 高风险操作 - 需要审批
curl -X POST http://localhost:8016/tasks \
  -H "Content-Type: application/json" \
  -d '{"message": "删除用户 test@example.com 的所有数据"}'

# 查看待审批任务
curl http://localhost:8016/tasks/pending

# 批准任务（替换 {task_id}）
curl -X POST http://localhost:8016/tasks/{task_id}/approve \
  -H "Content-Type: application/json" \
  -d '{"approved": true, "comment": "已确认用户已离职", "approver": "admin"}'

# 或者拒绝
curl -X POST http://localhost:8016/tasks/{task_id}/reject \
  -H "Content-Type: application/json" \
  -d '{"approved": false, "comment": "需要先备份数据", "approver": "admin"}'
```

### 5. 运行原有的 A2A 服务

```bash
# Terminal 1 - 启动 A2A 服务
uv run python -m langgraph_agent.agent

# Terminal 2 - 运行测试
uv run python -m client.test_client
```

## 代码核心

### 1. HITL Graph 构建

```python
from langgraph.graph import StateGraph, END

class HITLState(TypedDict):
    task_id: str
    messages: Annotated[list, add]
    risk_level: str
    requires_approval: bool
    approval_status: str  # pending, approved, rejected
    final_answer: str

def create_hitl_graph(checkpointer):
    graph = StateGraph(HITLState)

    # 添加节点
    graph.add_node("analyze", analyze_request_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("execute", execute_action_node)
    graph.add_node("respond", generate_response_node)

    # 条件路由：根据风险等级决定是否需要审批
    graph.add_conditional_edges(
        "analyze",
        route_after_analysis,
        {"human_review": "human_review", "execute": "execute"}
    )

    # 关键：在审批节点前中断，等待外部输入
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],
    )
```

### 2. 状态持久化

```python
from langgraph.checkpoint.memory import MemorySaver
# 或使用 SQLite（需要安装 langgraph-checkpoint-sqlite）
# from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = MemorySaver()

# 图执行时使用 thread_id 区分不同会话
config = {"configurable": {"thread_id": "unique-thread-id"}}
result = graph.invoke(initial_state, config)
```

### 3. 审批后恢复执行

```python
def resume_after_approval(task_id, thread_id, approved):
    graph = create_hitl_graph(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}

    # 注入审批结果到图状态
    graph.update_state(config, {
        "approval_status": "approved" if approved else "rejected"
    })

    # 从中断点继续执行
    result = graph.invoke(None, config)
    return result
```

## 关键学习点

1. **interrupt_before** - LangGraph 的中断机制，让图在指定节点前暂停
2. **Checkpointer** - 状态持久化，支持断点续跑
3. **update_state** - 外部更新图状态，注入审批结果
4. **风险评估** - LLM 自动评估操作风险等级
5. **超时机制** - 后台任务定期检查，超时自动拒绝

## API 文档

启动服务后访问: http://localhost:8016/docs

| 端点 | 方法 | 说明 |
|------|------|------|
| `/tasks` | POST | 创建新任务 |
| `/tasks` | GET | 获取任务列表 |
| `/tasks/pending` | GET | 获取待审批任务 |
| `/tasks/{id}` | GET | 获取任务详情 |
| `/tasks/{id}/approve` | POST | 批准任务 |
| `/tasks/{id}/reject` | POST | 拒绝任务 |
| `/health` | GET | 健康检查 |

## 配置项

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `GOOGLE_API_KEY` | - | Google AI API Key |
| `APPROVAL_TIMEOUT_SECONDS` | 300 | 审批超时时间（秒） |
| `HITL_SERVER_URL` | http://localhost:8016 | 服务地址 |

## 扩展练习

1. **添加更多风险类型** - 扩展 `analyze_request_node` 支持更细粒度的风险判断
2. **接入真实工具** - 将 `execute_action_node` 中的模拟执行替换为真实 API 调用
3. **添加审批层级** - 高风险需要一级审批，关键级需要二级审批
4. **集成通知系统** - 待审批时发送 Slack/邮件通知给管理员

## 扩展阅读

- [LangGraph Human-in-the-Loop](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)
- [LangGraph Checkpointing](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [A2A Protocol](https://a2a-protocol.org/)
