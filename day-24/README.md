# Day 24: A2A-ify Anything - 为任何 Agent 添加 A2A 能力

## 核心概念：Agent2Agent (A2A) 协议

### 问题：Agent 之间如何通信？

```
当前 AI Agent 生态的困境：

┌─────────────────────────────────────────────────────────────────┐
│                    各自为战的 Agent 孤岛                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐              │
│   │ LangChain│     │  ADK     │     │ AutoGen  │              │
│   │  Agent   │  ?  │  Agent   │  ?  │  Agent   │              │
│   └──────────┘     └──────────┘     └──────────┘              │
│        │                │                │                     │
│        ▼                ▼                ▼                     │
│   专有协议 A        专有协议 B        专有协议 C                  │
│                                                                 │
│   ❌ 无法互操作 | ❌ 无法发现 | ❌ 无法协作                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 解决方案：A2A 协议

[A2A (Agent2Agent)](https://a2a-protocol.org/) 是由 Google 于 2025 年 4 月在 Cloud Next 发布的开放协议，现已由 Linux Foundation 管理。

```
┌─────────────────────────────────────────────────────────────────┐
│                    A2A 统一通信协议                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐              │
│   │ LangChain│     │  ADK     │     │ AutoGen  │              │
│   │  Agent   │     │  Agent   │     │  Agent   │              │
│   └────┬─────┘     └────┬─────┘     └────┬─────┘              │
│        │                │                │                     │
│        ▼                ▼                ▼                     │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │              A2A Protocol (HTTP/JSON-RPC)               │  │
│   │  • Agent Card (能力发现)                                 │  │
│   │  • Task Management (任务管理)                            │  │
│   │  • Message Parts (消息交换)                              │  │
│   │  • Streaming (流式响应)                                  │  │
│   └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│   ✅ 互操作 | ✅ 能力发现 | ✅ 跨框架协作                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## A2A 协议核心概念

### 1. Agent Card（能力名片）

每个 A2A Agent 都通过 Agent Card 声明自己的能力：

```json
{
  "name": "expense-reimbursement-agent",
  "description": "处理员工报销申请的 Agent",
  "url": "https://expense-agent.example.com",
  "version": "1.0.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false
  },
  "skills": [
    {
      "id": "process-expense",
      "name": "处理报销",
      "description": "审核并处理员工报销申请",
      "inputSchema": {
        "type": "object",
        "properties": {
          "amount": { "type": "number" },
          "category": { "type": "string" },
          "receipt_url": { "type": "string" }
        }
      }
    }
  ]
}
```

Agent Card 通过 `/.well-known/agent.json` 端点公开。

### 2. 角色定义

| 角色 | 说明 | 职责 |
|------|------|------|
| **Client Agent** | 发起请求的 Agent | 发现远程 Agent，发送任务 |
| **Remote Agent** | 提供服务的 Agent | 处理任务，返回结果 |
| **User** | 最终用户 | 与 Client Agent 交互 |

```
┌──────────┐    A2A Protocol    ┌──────────┐
│  Client  │ ◀────────────────▶ │  Remote  │
│  Agent   │                    │  Agent   │
└────┬─────┘                    └──────────┘
     │
     │  自然语言
     ▼
┌──────────┐
│   User   │
└──────────┘
```

### 3. Task 生命周期

```
                    Task 状态流转

┌──────────┐     ┌──────────┐     ┌──────────┐
│ submitted│────▶│ working  │────▶│completed │
└──────────┘     └────┬─────┘     └──────────┘
                      │
                      │ 需要输入
                      ▼
                ┌──────────┐
                │input_    │ ◀── 等待用户/Agent 输入
                │required  │
                └──────────┘
                      │
                      │ 收到输入
                      ▼
                ┌──────────┐
                │ working  │
                └──────────┘
```

### 4. Message Parts（消息部分）

A2A 消息可以包含多种类型的内容：

```python
# 文本消息
TextPart(text="处理完成，已批准 $500 报销申请")

# 文件/图片
FilePart(
    file=FileContent(
        name="receipt.pdf",
        mimeType="application/pdf",
        bytes=base64_content
    )
)

# 结构化数据
DataPart(data={"status": "approved", "amount": 500})
```

---

## Agent Starter Pack：快速添加 A2A 能力

[Agent Starter Pack](https://github.com/GoogleCloudPlatform/agent-starter-pack) 是 Google Cloud 提供的工具，可以一键为任何 Agent 添加 A2A 能力。

### 快速开始

#### 方式一：从模板创建新 Agent

```bash
# 使用 uvx 直接运行（无需安装）
uvx agent-starter-pack create my-agent \
    -a adk@deep-search \
    --base-template adk_a2a_base

# 进入项目目录
cd my-agent

# 启动 Agent
uv run .
```

#### 方式二：增强现有 Agent

```bash
# 为现有 Agent 添加 A2A 能力
uvx agent-starter-pack enhance --base-template adk_a2a_base
```

### 可用模板

| 模板 | 说明 | 特性 |
|------|------|------|
| `adk_a2a_base` | ADK + A2A 基础模板 | A2A 协议支持 |
| `adk@deep-search` | 深度搜索 Agent | 网络搜索能力 |
| `adk@rag` | RAG Agent | 检索增强生成 |
| `adk@multi-agent` | 多 Agent 系统 | Agent 协作 |
| `adk@live` | 实时 Agent | 流式交互 |

---

## 实战：创建 A2A Agent

### 项目结构

```
my-a2a-agent/
├── pyproject.toml
├── agent/
│   ├── __init__.py
│   ├── agent.py           # Agent 定义
│   ├── a2a_server.py      # A2A 服务器
│   └── agent_card.py      # Agent Card 配置
└── tests/
```

### 核心代码

#### 1. 定义 Agent (agent.py)

```python
from google.adk import Agent, tool

@tool
def search_expenses(employee_id: str, date_range: str) -> list:
    """搜索员工的报销记录"""
    # 实际实现：查询数据库
    return [
        {"id": "EXP001", "amount": 500, "status": "pending"},
        {"id": "EXP002", "amount": 200, "status": "approved"},
    ]

@tool
def approve_expense(expense_id: str) -> dict:
    """批准报销申请"""
    return {"expense_id": expense_id, "status": "approved"}

expense_agent = Agent(
    name="expense-agent",
    model="gemini-2.0-flash",
    instruction="""你是一个报销处理 Agent。
    帮助用户查询和管理报销申请。""",
    tools=[search_expenses, approve_expense]
)
```

#### 2. 配置 Agent Card (agent_card.py)

```python
from a2a.types import AgentCard, AgentSkill

agent_card = AgentCard(
    name="expense-agent",
    description="处理员工报销申请的 AI Agent",
    url="http://localhost:8000",
    version="1.0.0",
    capabilities={
        "streaming": True,
        "pushNotifications": False
    },
    skills=[
        AgentSkill(
            id="search-expenses",
            name="搜索报销",
            description="搜索员工的报销记录",
            inputSchema={
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"},
                    "date_range": {"type": "string"}
                }
            }
        ),
        AgentSkill(
            id="approve-expense",
            name="批准报销",
            description="批准指定的报销申请",
            inputSchema={
                "type": "object",
                "properties": {
                    "expense_id": {"type": "string"}
                }
            }
        )
    ]
)
```

#### 3. A2A 服务器 (a2a_server.py)

```python
from a2a.server import A2AServer
from a2a.types import TaskRequest, TaskResponse, Message, TextPart
from agent import expense_agent
from agent_card import agent_card

class ExpenseA2AServer(A2AServer):

    def __init__(self):
        super().__init__(agent_card)

    async def handle_task(self, request: TaskRequest) -> TaskResponse:
        """处理 A2A 任务请求"""
        # 提取用户消息
        user_message = request.message.parts[0].text

        # 使用 ADK Agent 处理
        response = await expense_agent.run(user_message)

        # 构造 A2A 响应
        return TaskResponse(
            id=request.id,
            status="completed",
            messages=[
                Message(
                    role="agent",
                    parts=[TextPart(text=response)]
                )
            ]
        )

# 启动服务器
if __name__ == "__main__":
    server = ExpenseA2AServer()
    server.run(port=8000)
```

### 测试 A2A Agent

```bash
# 1. 查看 Agent Card
curl http://localhost:8000/.well-known/agent.json

# 2. 发送任务
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "role": "user",
      "parts": [{"text": "查询员工 EMP001 的报销记录"}]
    }
  }'
```

---

## A2A 多 Agent 协作

### 架构示例：采购审批系统

```
┌─────────────────────────────────────────────────────────────────┐
│                    采购审批多 Agent 系统                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  用户: "我需要购买一台 MacBook Pro 用于开发"                       │
│                         │                                       │
│                         ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Concierge Agent (协调者)                     │  │
│  │              • 理解用户意图                               │  │
│  │              • 选择合适的 Agent                           │  │
│  │              • 协调工作流程                               │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │                                     │
│           ┌───────────────┼───────────────┐                    │
│           │               │               │                    │
│           ▼               ▼               ▼                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│  │  Catalog    │ │  Budget     │ │  Approval   │              │
│  │  Agent      │ │  Agent      │ │  Agent      │              │
│  │             │ │             │ │             │              │
│  │ • 搜索产品   │ │ • 检查预算   │ │ • 流程审批   │              │
│  │ • 比较价格   │ │ • 验证权限   │ │ • 通知相关方 │              │
│  └─────────────┘ └─────────────┘ └─────────────┘              │
│         │               │               │                      │
│         └───────────────┼───────────────┘                      │
│                         │                                       │
│                         ▼                                       │
│                  A2A Protocol                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 实现代码

```python
from a2a.client import A2AClient
from a2a.types import TaskRequest, Message, TextPart

class ConciergeAgent:
    """协调者 Agent - 调用其他 A2A Agent"""

    def __init__(self):
        # 注册远程 Agent
        self.catalog_agent = A2AClient("http://catalog-agent:8000")
        self.budget_agent = A2AClient("http://budget-agent:8000")
        self.approval_agent = A2AClient("http://approval-agent:8000")

    async def process_purchase_request(self, request: str):
        """处理采购请求"""

        # Step 1: 在目录中搜索产品
        catalog_response = await self.catalog_agent.send_task(
            TaskRequest(
                message=Message(
                    role="user",
                    parts=[TextPart(text=f"搜索: {request}")]
                )
            )
        )

        product = catalog_response.messages[-1].parts[0].data

        # Step 2: 检查预算
        budget_response = await self.budget_agent.send_task(
            TaskRequest(
                message=Message(
                    role="user",
                    parts=[TextPart(text=f"检查预算: {product['price']}")]
                )
            )
        )

        if not budget_response.messages[-1].parts[0].data['approved']:
            return "预算不足，无法采购"

        # Step 3: 提交审批
        approval_response = await self.approval_agent.send_task(
            TaskRequest(
                message=Message(
                    role="user",
                    parts=[TextPart(text=f"审批采购: {product['name']}")]
                )
            )
        )

        return approval_response.messages[-1].parts[0].text
```

---

## A2A vs MCP 对比

| 特性 | A2A | MCP |
|------|-----|-----|
| **定位** | Agent 间通信 | Agent 访问工具/数据 |
| **通信方向** | Agent ↔ Agent | Agent → Tool Server |
| **能力发现** | Agent Card | Tool Definition |
| **任务模型** | 长时任务 + 状态 | 单次调用 |
| **流式支持** | ✅ SSE | ✅ SSE |
| **适用场景** | 分布式多 Agent | 工具集成 |

```
┌─────────────────────────────────────────────────────────────────┐
│                    A2A + MCP 完整架构                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐   A2A    ┌──────────┐   A2A    ┌──────────┐    │
│   │  Agent   │ ◀──────▶ │  Agent   │ ◀──────▶ │  Agent   │    │
│   │    A     │          │    B     │          │    C     │    │
│   └────┬─────┘          └────┬─────┘          └────┬─────┘    │
│        │                     │                     │           │
│        │ MCP                 │ MCP                 │ MCP       │
│        ▼                     ▼                     ▼           │
│   ┌─────────┐           ┌─────────┐           ┌─────────┐     │
│   │Database │           │  API    │           │  Files  │     │
│   │ Server  │           │ Server  │           │ Server  │     │
│   └─────────┘           └─────────┘           └─────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

A2A: Agent 之间的水平通信
MCP: Agent 到工具的垂直访问
```

---

## 快速参考

### 安装 Agent Starter Pack

```bash
# 方式一：使用 uvx（推荐，无需安装）
uvx agent-starter-pack --help

# 方式二：使用 pip 安装
pip install agent-starter-pack
```

### 创建项目命令

```bash
# 创建新 Agent
uvx agent-starter-pack create <project-name> \
    -a <template> \
    --base-template adk_a2a_base

# 可用模板
# adk@deep-search  - 深度搜索
# adk@rag          - RAG
# adk@multi-agent  - 多 Agent
# adk@live         - 实时
```

### A2A 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/.well-known/agent.json` | GET | Agent Card |
| `/tasks` | POST | 创建任务 |
| `/tasks/{id}` | GET | 查询任务状态 |
| `/tasks/{id}/cancel` | POST | 取消任务 |
| `/tasks/{id}/send` | POST | 发送消息 |

---

## 参考资源

- [A2A Protocol 官方文档](https://a2a-protocol.org/)
- [A2A GitHub 仓库](https://github.com/a2aproject/A2A)
- [Agent Starter Pack](https://github.com/GoogleCloudPlatform/agent-starter-pack)
- [Google ADK Samples](https://github.com/google/adk-samples)
- [A2A Codelab: Purchasing Concierge](https://codelabs.developers.google.com/intro-a2a-purchasing-concierge)
- [A2A Protocol 发布公告](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)

---

## 思考题

1. **A2A 和 MCP 应该如何配合使用？**
   - 提示：考虑水平通信 vs 垂直访问

2. **Agent Card 的设计原则是什么？**
   - 提示：考虑能力发现和版本控制

3. **在什么场景下应该选择 A2A 而不是直接 API 调用？**
   - 提示：考虑长时任务、状态管理、能力发现

4. **如何确保 A2A Agent 之间的安全通信？**
   - 提示：参考 A2A v0.3 的签名安全卡功能
