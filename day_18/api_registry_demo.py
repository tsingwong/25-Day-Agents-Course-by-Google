"""
Day 18: Cloud API Registry + ADK 演示

前置要求:
1. 配置 Google Cloud 项目
2. 启用 API Registry 和相关服务
3. 运行: gcloud auth application-default login

运行:
    python api_registry_demo.py
"""

import os

# =============================================================================
# 配置
# =============================================================================

# 从环境变量获取项目 ID，或手动设置
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")


# =============================================================================
# 示例 1: 基础用法 - 获取单个工具
# =============================================================================

def demo_basic_usage():
    """
    最简单的用法：从 Registry 获取一个工具
    """
    from google.adk import Agent
    from google.adk.tools.google_cloud import ApiRegistry

    # 1. 连接到 Cloud API Registry
    registry = ApiRegistry(project_id=PROJECT_ID)

    # 2. 获取 BigQuery 工具（管理员需要先启用）
    bq_tool = registry.get_tool("google-bigquery")

    # 3. 创建带有该工具的 Agent
    agent = Agent(
        model="gemini-3-flash-preview",
        name="data_analyst",
        instruction="你是一个数据分析师，可以查询 BigQuery 数据库。",
        tools=[bq_tool]
    )

    print("✅ Agent 已配置 BigQuery 工具")
    return agent


# =============================================================================
# 示例 2: 获取多个工具
# =============================================================================

def demo_multiple_tools():
    """
    获取多个已审批的工具
    """
    from google.adk import Agent
    from google.adk.tools.google_cloud import ApiRegistry

    registry = ApiRegistry(project_id=PROJECT_ID)

    # 获取多个工具
    tools = [
        registry.get_tool("google-bigquery"),      # 数据查询
        registry.get_tool("google-cloud-storage"), # 文件存储
    ]

    agent = Agent(
        model="gemini-3-flash-preview",
        name="cloud_assistant",
        instruction="你是云服务助手，可以查询数据和管理文件。",
        tools=tools
    )

    print("✅ Agent 已配置多个工具")
    return agent


# =============================================================================
# 示例 3: 列出所有可用工具
# =============================================================================

def demo_list_tools():
    """
    查看 Registry 中有哪些可用工具
    """
    from google.adk.tools.google_cloud import ApiRegistry

    registry = ApiRegistry(project_id=PROJECT_ID)

    # 列出所有可用工具
    available_tools = registry.list_tools()

    print("📦 可用工具列表:")
    for tool in available_tools:
        print(f"  - {tool.name}: {tool.description}")

    return available_tools


# =============================================================================
# 示例 4: 完整工作流程
# =============================================================================

async def demo_full_workflow():
    """
    完整演示：创建 Agent 并执行查询
    """
    from google.adk import Agent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.tools.google_cloud import ApiRegistry
    from google.genai.types import Content, Part

    # 1. 设置 Registry 和工具
    registry = ApiRegistry(project_id=PROJECT_ID)
    bq_tool = registry.get_tool("google-bigquery")

    # 2. 创建 Agent
    agent = Agent(
        model="gemini-3-flash-preview",
        name="data_analyst",
        instruction="""你是数据分析师。
        用户询问数据问题时，使用 BigQuery 工具查询。
        用中文简洁回答。""",
        tools=[bq_tool]
    )

    # 3. 运行对话
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="api_registry_demo",
        user_id="demo_user"
    )

    runner = Runner(
        agent=agent,
        app_name="api_registry_demo",
        session_service=session_service
    )

    # 4. 发送查询
    question = "查询公开数据集中 2023 年的数据统计"
    user_content = Content(role="user", parts=[Part(text=question)])

    print(f"📝 问题: {question}")
    print("-" * 40)

    async for event in runner.run_async(
        user_id="demo_user",
        session_id=session.id,
        new_message=user_content
    ):
        if hasattr(event, 'content') and event.content:
            if hasattr(event.content, 'parts'):
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        print(f"🤖 回答: {part.text}")


# =============================================================================
# 主程序
# =============================================================================

if __name__ == "__main__":
    print("=" * 50)
    print("Day 18: Cloud API Registry + ADK 演示")
    print("=" * 50)
    print(f"项目 ID: {PROJECT_ID}")
    print()

    # 注意：以下代码需要正确配置 Google Cloud 才能运行
    # 这里只展示代码结构，实际运行需要:
    # 1. 有效的 Google Cloud 项目
    # 2. 启用相关 API
    # 3. 配置好认证

    print("📌 示例代码已准备好")
    print("📌 请确保配置好 Google Cloud 项目后运行")
    print()
    print("启用 BigQuery MCP 服务:")
    print(f"  gcloud beta services mcp enable bigquery.googleapis.com --project={PROJECT_ID}")
    print()
    print("运行完整演示:")
    print("  取消下面的注释并运行")

    # 取消注释运行演示:
    # demo_basic_usage()
    # demo_multiple_tools()
    # demo_list_tools()
    # import asyncio
    # asyncio.run(demo_full_workflow())
