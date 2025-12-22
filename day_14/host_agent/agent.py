"""
Day 14: Host Agent (A2A Client)

这是主控 Agent，它通过 A2A 协议调用远程的翻译 Agent。
演示了如何作为 A2A 客户端与远程 Agent 进行通信。

运行前确保:
    1. 设置环境变量: export GOOGLE_API_KEY="your-api-key"
    2. 远程 Agent 已经在 http://localhost:8001 运行
    3. 运行: python -m host_agent.agent
"""

import asyncio
import os
import sys
import uuid

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from a2a.client import ClientFactory, ClientConfig
from a2a.types import Role
from a2a.client.helpers import create_text_message_object

# 远程 Agent 的 URL
REMOTE_AGENT_URL = "http://localhost:8001"


def get_client_config() -> ClientConfig:
    """创建不使用代理的客户端配置"""
    # 创建 httpx 客户端，完全禁用代理以避免本地连接问题
    # trust_env=False 会忽略环境变量中的代理设置
    httpx_client = httpx.AsyncClient(
        trust_env=False,
        timeout=120.0,
    )
    return ClientConfig(httpx_client=httpx_client)


# ============================================================
# 1. A2A 客户端 - 直接调用远程 Agent
# ============================================================

async def call_remote_agent_directly(text_to_translate: str, target_language: str = "中文"):
    """
    直接使用 A2A 客户端调用远程翻译 Agent

    这是最基本的 A2A 调用方式，展示了：
    - 如何创建 A2A 客户端
    - 如何构造请求消息
    - 如何处理响应
    """
    print("\n" + "=" * 60)
    print("方法 1: 直接调用远程 Agent (A2A Client)")
    print("=" * 60)

    # 使用 ClientFactory.connect() 连接远程 Agent
    # 这会自动获取 Agent Card 并创建合适的客户端
    client = await ClientFactory.connect(REMOTE_AGENT_URL, client_config=get_client_config())

    # 获取 Agent Card 信息 (使用 _card 属性)
    print("\n📇 Agent 信息:")
    print(f"   名称: {client._card.name}")
    print(f"   描述: {client._card.description[:80]}...")
    print(f"   技能: {[skill.name for skill in (client._card.skills or [])]}")

    # 构造翻译请求消息
    request_text = f"请将以下文本翻译成{target_language}：\n{text_to_translate}"

    print(f"\n📤 发送请求: {request_text[:60]}...")

    # 创建消息对象 (注意: 参数是 content 不是 text)
    message = create_text_message_object(
        role=Role.user,
        content=request_text,
    )

    # 发送消息给远程 Agent (注意: 参数是 request 不是 message)
    result = None
    async for event in client.send_message(request=message):
        # 处理返回的事件
        # event 是 (Task, TaskEvent) 或 Message 元组
        if isinstance(event, tuple) and len(event) >= 2:
            task, task_event = event[0], event[1]
            if task_event:
                # 处理 TaskStatusUpdateEvent 或 TaskArtifactUpdateEvent
                if hasattr(task_event, 'status') and task_event.status:
                    state = task_event.status.state
                    print(f"   [状态] {state}")
                    if task_event.status.message:
                        for part in task_event.status.message.parts:
                            if hasattr(part, 'text') and part.text:
                                result = part.text
                elif hasattr(task_event, 'artifact') and task_event.artifact:
                    for part in task_event.artifact.parts:
                        if hasattr(part, 'text') and part.text:
                            result = part.text

    if result:
        print(f"\n📥 翻译结果:\n   {result}")

    return result


# ============================================================
# 2. 流式调用 - 实时获取翻译进度
# ============================================================

async def call_remote_agent_streaming(text_to_translate: str, target_language: str = "中文"):
    """
    使用流式模式调用远程 Agent

    适用于长文本翻译，可以实时看到翻译进度
    """
    print("\n" + "=" * 60)
    print("方法 2: 流式调用远程 Agent (Streaming)")
    print("=" * 60)

    client = await ClientFactory.connect(REMOTE_AGENT_URL, client_config=get_client_config())

    request_text = f"请将以下文本翻译成{target_language}，并提供详细的翻译说明：\n{text_to_translate}"

    print(f"\n📤 发送流式请求...")
    print(f"   原文: {text_to_translate[:50]}...")
    print("\n📥 实时响应:")

    message = create_text_message_object(
        role=Role.user,
        content=request_text,
    )

    collected_text = []
    async for event in client.send_message(request=message):
        if isinstance(event, tuple) and len(event) >= 2:
            task, task_event = event[0], event[1]
            if task_event:
                if hasattr(task_event, 'status') and task_event.status:
                    state = task_event.status.state
                    print(f"   [状态更新] {state}")
                    if task_event.status.message:
                        for part in task_event.status.message.parts:
                            if hasattr(part, 'text') and part.text:
                                collected_text.append(part.text)
                                print(f"   {part.text[:100]}...")
                elif hasattr(task_event, 'artifact') and task_event.artifact:
                    print("   [产出物] ", end="")
                    for part in task_event.artifact.parts:
                        if hasattr(part, 'text') and part.text:
                            collected_text.append(part.text)
                            print(part.text[:100], end="...")
                    print()

    if collected_text:
        print(f"\n   完整结果: {collected_text[-1][:200]}...")


# ============================================================
# 3. 多轮对话 - 保持上下文
# ============================================================

async def multi_turn_conversation():
    """
    演示与远程 Agent 的多轮对话

    A2A 支持通过 context_id 保持对话上下文
    """
    print("\n" + "=" * 60)
    print("方法 3: 多轮对话 (Multi-turn Conversation)")
    print("=" * 60)

    client = await ClientFactory.connect(REMOTE_AGENT_URL, client_config=get_client_config())

    context_id = str(uuid.uuid4())  # 创建会话上下文 ID

    conversations = [
        "请翻译：The quick brown fox jumps over the lazy dog.",
        "这句话有什么特别之处吗？",
        "能给我一个中文版本的类似句子吗？",
    ]

    for i, user_input in enumerate(conversations, 1):
        print(f"\n🗣️  轮次 {i}: {user_input}")

        message = create_text_message_object(
            role=Role.user,
            content=user_input,
        )

        result_text = None
        # 注意: 当前 SDK 版本不支持 context_id 参数
        # 多轮对话上下文需要通过其他方式管理
        async for event in client.send_message(request=message):
            if isinstance(event, tuple) and len(event) >= 2:
                task, task_event = event[0], event[1]
                if task_event:
                    if hasattr(task_event, 'status') and task_event.status and task_event.status.message:
                        for part in task_event.status.message.parts:
                            if hasattr(part, 'text') and part.text:
                                result_text = part.text
                    elif hasattr(task_event, 'artifact') and task_event.artifact:
                        for part in task_event.artifact.parts:
                            if hasattr(part, 'text') and part.text:
                                result_text = part.text

        if result_text:
            # 截断显示
            display_text = result_text[:300] + "..." if len(result_text) > 300 else result_text
            print(f"🤖 回复: {display_text}")


# ============================================================
# 简单测试函数
# ============================================================

async def simple_test():
    """最简单的 A2A 调用示例"""
    print("\n" + "=" * 60)
    print("简单测试: A2A 连接和调用")
    print("=" * 60)

    # 1. 连接到远程 Agent
    print("\n1️⃣  连接远程 Agent...")
    client = await ClientFactory.connect(REMOTE_AGENT_URL, client_config=get_client_config())
    print(f"   ✅ 连接成功! Agent: {client._card.name}")

    # 2. 发送简单请求
    print("\n2️⃣  发送翻译请求...")
    message = create_text_message_object(
        role=Role.user,
        content="请翻译：Hello World"
    )

    print("   等待响应...")
    async for event in client.send_message(request=message):
        if isinstance(event, tuple) and len(event) >= 2:
            task, task_event = event[0], event[1]
            if task_event:
                if hasattr(task_event, 'artifact') and task_event.artifact:
                    for part in task_event.artifact.parts:
                        if hasattr(part, 'text') and part.text:
                            print(f"\n3️⃣  收到翻译结果: {part.text}")


# ============================================================
# 主程序
# ============================================================

async def main():
    print("=" * 60)
    print("Day 14: A2A Host Agent - 调用远程翻译服务")
    print("=" * 60)
    print()
    print(f"远程 Agent URL: {REMOTE_AGENT_URL}")
    print("确保远程 Agent 已运行: python -m remote_agent.agent")
    print()

    try:
        # 首先进行简单测试
        await simple_test()

        # 方法 1: 直接调用
        await call_remote_agent_directly(
            "Hello, World! Welcome to the Agent2Agent protocol.",
            "中文"
        )

        # 再测试一个中译英
        await call_remote_agent_directly(
            "人工智能正在改变我们的生活方式。",
            "英文"
        )

        # 方法 2: 流式调用
        await call_remote_agent_streaming(
            "Artificial Intelligence (AI) is transforming industries worldwide. "
            "From healthcare to finance, AI systems are automating tasks.",
            "中文"
        )

        # 方法 3: 多轮对话
        await multi_turn_conversation()

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        print("\n请确保:")
        print("1. 远程 Agent 正在运行 (python -m remote_agent.agent)")
        print("2. 端口 8001 没有被占用")
        print("3. GOOGLE_API_KEY 环境变量已设置")

    print("\n" + "=" * 60)
    print("演示结束")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
