# Day 14: 使用 A2A 协议连接 Agents

## 概述

今天我们学习 **Agent2Agent (A2A)** 协议 - 一个开放标准，允许不同的 AI Agents 之间进行通信和协作，无论它们使用什么框架或语言。

## A2A 协议核心概念

### 什么是 A2A？

A2A (Agent-to-Agent) 是 Google 推出的开放协议，解决了一个关键问题：**如何让不同团队、不同框架构建的 Agents 互相协作？**

```
┌─────────────────┐         A2A 协议          ┌─────────────────┐
│   Host Agent    │  ◄──────────────────────► │  Remote Agent   │
│   (客户端)       │     JSON-RPC over HTTP    │   (服务端)       │
│   ADK/LangChain │                           │   ADK/其他框架   │
└─────────────────┘                           └─────────────────┘
```

### A2A 的核心组件

1. **Agent Card** - Agent 的"名片"
   - 描述 Agent 的能力、技能
   - 提供 RPC URL 端点
   - 类似于 API 文档
   - 可通过 `/.well-known/agent-card.json` 访问

2. **Task** - 任务单元
   - 客户端向服务端发送的工作请求
   - 包含 message (消息) 和 context (上下文)
   - 有状态流转：submitted → working → completed/failed

3. **Message** - 消息
   - 包含多个 Parts (文本、文件、数据等)
   - 支持角色区分 (user/agent)

### A2A vs MCP

| 特性 | A2A | MCP |
|------|-----|-----|
| 目的 | Agent 之间通信 | Agent 访问外部工具/数据 |
| 通信方向 | Agent ↔ Agent | Agent → 工具/数据源 |
| 复杂度 | 支持复杂任务流 | 简单的请求/响应 |
| 状态管理 | 有状态 (Task 生命周期) | 无状态 |

## 项目结构

```
day-14/
├── README.md
├── remote_agent/          # 远程 Agent (A2A 服务端)
│   ├── __init__.py
│   └── agent.py          # 提供专业翻译服务的 Agent
├── host_agent/           # 主机 Agent (A2A 客户端)
│   ├── __init__.py
│   └── agent.py          # 调用远程 Agent 的主 Agent
└── run_demo.py           # 演示脚本
```

## 前提条件

API Key 已在项目根目录 `.env` 文件中配置，代码会自动加载。

## 运行示例 (请按顺序操作)

### 第一步：启动服务端 (Terminal 1)

```bash
cd day-14
uv run python -m remote_agent.agent
```

> 也可以使用 `python3 -m remote_agent.agent`

看到以下输出表示服务端启动成功：
```
============================================================
Day 14: A2A Remote Agent - 翻译服务
============================================================
Agent 信息:
  名称: translator
A2A 服务端点:
  URL: http://localhost:8001
============================================================
INFO:     Uvicorn running on http://localhost:8001
```

### 第二步：运行客户端 (Terminal 2)

**新开一个终端**，运行：

```bash
cd day-14
uv run python -m host_agent.agent
```

> 也可以使用 `python3 -m host_agent.agent`

客户端会连接服务端，发送翻译请求，你会看到翻译结果。

### 运行效果

![A2A 运行效果](https://fisherai-1312281807.cos.ap-guangzhou.myqcloud.com/202512161543243.png)

左侧是服务端 (Remote Agent)，右侧是客户端 (Host Agent) 的运行输出。

### 验证服务

在任意终端执行：
```bash
curl http://localhost:8001/.well-known/agent-card.json
```

### 关闭服务

在服务端终端按 `Ctrl+C` 即可关闭。

## 代码详解

### Remote Agent (服务端) - 关键代码

```python
from google.adk.agents import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

# 创建一个专业翻译 Agent
translator = LlmAgent(
    name="translator",
    description="专业多语言翻译 Agent",
    model="gemini-2.0-flash",
    instruction="你是专业翻译，精通中英日韩等语言..."
)

# 一行代码转换为 A2A 服务！
app = to_a2a(translator, host="localhost", port=8001)

# 启动服务
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8001)
```

### Host Agent (客户端) - 关键代码

```python
import httpx
from a2a.client import ClientFactory, ClientConfig
from a2a.types import Role
from a2a.client.helpers import create_text_message_object

# 创建无代理的 HTTP 客户端配置
def get_client_config():
    httpx_client = httpx.AsyncClient(
        trust_env=False,  # 禁用代理
        timeout=120.0,
    )
    return ClientConfig(httpx_client=httpx_client)

# 连接远程 Agent
client = await ClientFactory.connect(
    "http://localhost:8001",
    client_config=get_client_config()
)

# 创建消息
message = create_text_message_object(
    role=Role.user,
    content="请翻译：Hello World"
)

# 发送请求并处理响应
async for event in client.send_message(request=message):
    if isinstance(event, tuple):
        task, task_event = event[0], event[1]
        if task_event and hasattr(task_event, 'artifact'):
            for part in task_event.artifact.parts:
                if hasattr(part, 'text'):
                    print(f"翻译结果: {part.text}")
```

## 关键学习点

1. **`to_a2a()` 函数** - ADK 提供的便捷方法，将任何 Agent 转换为 A2A 服务
2. **Agent Card** - 自动从 Agent 元数据生成，描述 Agent 能力
3. **ClientFactory.connect()** - A2A SDK 提供的连接方法，自动获取 Agent Card
4. **Task 状态流** - submitted → working → completed/failed
5. **跨框架互操作** - A2A 是协议标准，不限于 ADK

## API 快速参考

### 服务端 API

| 函数 | 描述 |
|------|------|
| `to_a2a(agent, host, port)` | 将 ADK Agent 转换为 A2A 服务 |

### 客户端 API

| 函数/类 | 描述 |
|---------|------|
| `ClientFactory.connect(url)` | 连接远程 A2A Agent |
| `create_text_message_object(role, content)` | 创建文本消息 |
| `client.send_message(request)` | 发送消息并获取响应流 |

## 客户端功能演示

当前 `host_agent/agent.py` 实现了 3 种 A2A 调用方式：

### 方法 1: 直接调用 (`call_remote_agent_directly`)

最基本的 A2A 调用模式：
- 连接远程 Agent
- 发送单次请求
- 等待并获取完整响应

```python
client = await ClientFactory.connect(url, client_config=config)
message = create_text_message_object(role=Role.user, content="请翻译...")
async for event in client.send_message(request=message):
    # 处理响应
```

### 方法 2: 流式调用 (`call_remote_agent_streaming`)

适用于长文本，实时获取响应：
- 边处理边显示结果
- 可以看到任务状态变化 (submitted → working → completed)

### 方法 3: 多轮对话 (`multi_turn_conversation`)

演示连续对话场景：
- 发送多个相关问题
- 每次都创建新的请求

> **注意**: 当前 SDK 版本不支持 `context_id` 参数，多轮对话上下文需要应用层自行管理。

## 扩展方向

基于当前代码，你可以尝试以下扩展：

### 1. 添加更多远程 Agent

```python
# 创建多个专业 Agent
code_agent = await ClientFactory.connect("http://localhost:8002")  # 代码助手
math_agent = await ClientFactory.connect("http://localhost:8003")  # 数学助手

# 根据任务类型选择合适的 Agent
if "翻译" in user_request:
    agent = translator_agent
elif "代码" in user_request:
    agent = code_agent
```

### 2. Agent 编排 (Orchestration)

```python
async def translate_and_summarize(text: str):
    """先翻译再总结"""
    # 调用翻译 Agent
    translated = await call_agent(translator_url, f"翻译: {text}")
    # 调用总结 Agent
    summary = await call_agent(summarizer_url, f"总结: {translated}")
    return summary
```

### 3. 并行调用多个 Agent

```python
import asyncio

async def parallel_translate(text: str):
    """同时翻译成多种语言"""
    tasks = [
        call_remote_agent(text, "中文"),
        call_remote_agent(text, "日文"),
        call_remote_agent(text, "韩文"),
    ]
    results = await asyncio.gather(*tasks)
    return dict(zip(["中文", "日文", "韩文"], results))
```

### 4. 错误重试机制

```python
async def call_with_retry(client, message, max_retries=3):
    for attempt in range(max_retries):
        try:
            async for event in client.send_message(request=message):
                yield event
            return
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # 指数退避
```

### 5. 健康检查

```python
async def health_check(url: str) -> bool:
    """检查远程 Agent 是否可用"""
    try:
        async with httpx.AsyncClient(trust_env=False) as client:
            resp = await client.get(f"{url}/.well-known/agent-card.json")
            return resp.status_code == 200
    except:
        return False
```

### 6. 创建新的远程 Agent (服务端扩展)

在 `remote_agent/` 目录下创建新的 Agent 服务：

```python
# remote_agent/code_reviewer.py
from google.adk.agents import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

code_reviewer = LlmAgent(
    name="code_reviewer",
    description="专业代码审查 Agent - 检查代码质量、安全漏洞和最佳实践",
    model="gemini-2.0-flash",
    instruction="""你是一位资深的代码审查专家。

你的职责：
- 检查代码逻辑错误和潜在 bug
- 识别安全漏洞 (SQL注入、XSS等)
- 评估代码可读性和可维护性
- 建议性能优化方案
- 检查是否符合最佳实践

输出格式：
1. 问题概述
2. 具体问题列表 (严重程度: 高/中/低)
3. 改进建议
""",
)

app = to_a2a(agent=code_reviewer, host="localhost", port=8002, protocol="http")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8002)
```

### 7. 构建 Agent 注册中心

```python
# agent_registry.py
class AgentRegistry:
    """简单的 Agent 注册中心"""

    def __init__(self):
        self.agents = {}

    async def register(self, name: str, url: str):
        """注册一个 Agent"""
        if await self.health_check(url):
            client = await ClientFactory.connect(url, client_config=get_client_config())
            self.agents[name] = {
                "url": url,
                "client": client,
                "card": client._card,
            }
            return True
        return False

    async def health_check(self, url: str) -> bool:
        try:
            async with httpx.AsyncClient(trust_env=False) as client:
                resp = await client.get(f"{url}/.well-known/agent-card.json")
                return resp.status_code == 200
        except:
            return False

    def get(self, name: str):
        """获取已注册的 Agent"""
        return self.agents.get(name)

    def list_agents(self):
        """列出所有可用的 Agent"""
        return {
            name: {
                "url": info["url"],
                "description": info["card"].description,
            }
            for name, info in self.agents.items()
        }

# 使用示例
registry = AgentRegistry()
await registry.register("translator", "http://localhost:8001")
await registry.register("code_reviewer", "http://localhost:8002")

# 根据任务智能选择 Agent
translator = registry.get("translator")
```

### 8. 带工具的远程 Agent

```python
# remote_agent/weather_agent.py
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

def get_weather(city: str) -> str:
    """获取城市天气 (模拟)"""
    # 实际应用中可以调用真实天气 API
    weather_data = {
        "北京": "晴天，25°C",
        "上海": "多云，28°C",
        "东京": "小雨，22°C",
    }
    return weather_data.get(city, f"{city} 天气数据暂无")

weather_tool = FunctionTool(func=get_weather)

weather_agent = LlmAgent(
    name="weather_assistant",
    description="天气查询 Agent - 提供全球城市天气信息",
    model="gemini-2.0-flash",
    instruction="你是天气助手，帮助用户查询天气信息。",
    tools=[weather_tool],
)

app = to_a2a(agent=weather_agent, host="localhost", port=8003, protocol="http")
```

## 实战项目想法

### 项目 1: 多语言文档翻译系统

```
用户 → Host Agent → 翻译 Agent (中文)
                  → 翻译 Agent (日文)
                  → 翻译 Agent (韩文)
              → 汇总结果返回用户
```

### 项目 2: 代码审查流水线

```
代码提交 → 代码审查 Agent → 安全扫描 Agent → 性能分析 Agent → 生成报告
```

### 项目 3: 智能客服系统

```
用户问题 → 路由 Agent (分析问题类型)
              ├→ FAQ Agent (常见问题)
              ├→ 技术支持 Agent (技术问题)
              └→ 订单 Agent (订单相关)
```

### 项目 4: 研究助手

```
研究主题 → 搜索 Agent (收集资料)
        → 总结 Agent (提取要点)
        → 写作 Agent (生成报告)
```

## 常见问题

### Q: 服务启动但客户端连接失败？
A: 检查是否有代理设置。使用 `httpx.AsyncClient(trust_env=False)` 禁用代理。

### Q: 看到 "Missing key inputs argument" 错误？
A: 确保设置了 `GOOGLE_API_KEY` 环境变量。

### Q: Agent Card 端点是什么？
A: 标准端点是 `/.well-known/agent-card.json`（旧版本是 `/.well-known/agent.json`）。

## 扩展阅读

- [A2A Protocol Spec](https://a2a-protocol.org/)
- [ADK A2A Docs](https://google.github.io/adk-docs/a2a/)
- [Agent Starter Pack](https://github.com/GoogleCloudPlatform/agent-starter-pack)
- [Prototype to Production Whitepaper](https://www.kaggle.com/whitepaper-prototype-to-production)
