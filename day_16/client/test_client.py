"""
Day 16: A2A Client - 测试 LangGraph Agent

这是 A2A 客户端，用于测试 LangGraph Agent 服务。

运行前确保:
    1. LangGraph Agent 已在 http://localhost:8016 运行
    2. 运行: python -m client.test_client
"""

import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from a2a.client import ClientFactory, ClientConfig
from a2a.types import Role
from a2a.client.helpers import create_text_message_object

# LangGraph Agent 的 URL
LANGGRAPH_AGENT_URL = "http://localhost:8016"


def get_client_config() -> ClientConfig:
    """创建不使用代理的客户端配置"""
    httpx_client = httpx.AsyncClient(
        trust_env=False,
        timeout=120.0,
    )
    return ClientConfig(httpx_client=httpx_client)


# ============================================================
# 测试函数
# ============================================================

async def test_langgraph_agent():
    """测试 LangGraph Agent 的 A2A 服务"""
    print("\n" + "=" * 60)
    print("测试 LangGraph + A2A Agent")
    print("=" * 60)

    try:
        # 1. 连接到 LangGraph Agent
        print("\n1️⃣  连接 LangGraph Agent...")
        client = await ClientFactory.connect(
            LANGGRAPH_AGENT_URL,
            client_config=get_client_config()
        )
        print(f"   ✅ 连接成功!")
        print(f"   Agent 名称: {client._card.name}")
        print(f"   Agent 描述: {client._card.description[:60]}...")

        # 显示技能
        if client._card.skills:
            print("   技能列表:")
            for skill in client._card.skills:
                print(f"     - {skill.name}: {skill.description}")

        # 2. 测试问答功能
        test_questions = [
            "什么是 LangGraph？它和 LangChain 有什么关系？",
            "请帮我分析：为什么 AI Agent 需要使用图结构来组织工作流？",
            "A2A 协议的主要优势是什么？",
        ]

        for i, question in enumerate(test_questions, 1):
            print(f"\n{'=' * 60}")
            print(f"问题 {i}: {question}")
            print("=" * 60)

            # 创建消息
            message = create_text_message_object(
                role=Role.user,
                content=question,
            )

            # 发送请求并等待响应
            print("\n⏳ 等待 Agent 响应...")
            result_text = None

            async for event in client.send_message(request=message):
                if isinstance(event, tuple) and len(event) >= 1:
                    task = event[0]

                    # 从 Task 的 artifacts 中提取响应
                    # artifacts[].parts[].root.text 是响应的位置
                    if task and hasattr(task, 'artifacts') and task.artifacts:
                        for artifact in task.artifacts:
                            if hasattr(artifact, 'parts'):
                                for part in artifact.parts:
                                    # Part 对象有 root 属性，包含 TextPart
                                    if hasattr(part, 'root') and part.root:
                                        if hasattr(part.root, 'text') and part.root.text:
                                            result_text = part.root.text
                                    # 兼容直接访问 text 的情况
                                    elif hasattr(part, 'text') and part.text:
                                        result_text = part.text

            if result_text:
                print(f"\n🤖 Agent 回答:")
                print("-" * 40)
                # 格式化输出，每行最多 60 个字符
                lines = result_text.split('\n')
                for line in lines:
                    if len(line) > 80:
                        # 长行分割
                        words = line.split()
                        current_line = ""
                        for word in words:
                            if len(current_line) + len(word) + 1 <= 80:
                                current_line += (" " if current_line else "") + word
                            else:
                                if current_line:
                                    print(f"   {current_line}")
                                current_line = word
                        if current_line:
                            print(f"   {current_line}")
                    else:
                        print(f"   {line}")
                print("-" * 40)
            else:
                print("   ⚠️ 未收到有效响应")

            # 短暂等待，避免请求过快
            await asyncio.sleep(1)

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        print("\n请确保:")
        print("1. LangGraph Agent 正在运行 (python -m langgraph_agent.agent)")
        print("2. 端口 8016 没有被占用")
        print("3. GOOGLE_API_KEY 环境变量已设置")


async def check_agent_health():
    """检查 Agent 健康状态"""
    print("\n检查 Agent 健康状态...")
    try:
        async with httpx.AsyncClient(trust_env=False) as client:
            # 检查 Agent Card
            resp = await client.get(f"{LANGGRAPH_AGENT_URL}/.well-known/agent.json")
            if resp.status_code == 200:
                print("✅ Agent 服务正常运行")
                agent_card = resp.json()
                print(f"   名称: {agent_card.get('name', 'Unknown')}")
                print(f"   版本: {agent_card.get('version', 'Unknown')}")
                return True
            else:
                print(f"⚠️ Agent 响应异常: {resp.status_code}")
                return False
    except httpx.ConnectError:
        print("❌ 无法连接到 Agent 服务")
        print(f"   请确保服务正在 {LANGGRAPH_AGENT_URL} 运行")
        return False
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


# ============================================================
# 主程序
# ============================================================

async def main():
    print("=" * 60)
    print("Day 16: LangGraph + A2A 客户端测试")
    print("=" * 60)
    print()
    print(f"目标 Agent: {LANGGRAPH_AGENT_URL}")
    print()

    # 先检查健康状态
    is_healthy = await check_agent_health()

    if is_healthy:
        # 运行测试
        await test_langgraph_agent()
    else:
        print("\n无法进行测试，请先启动 Agent 服务:")
        print("  cd day-16")
        print("  uv run python -m langgraph_agent.agent")

    print("\n" + "=" * 60)
    print("测试结束")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
