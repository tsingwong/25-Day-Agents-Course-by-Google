#!/usr/bin/env python3
"""
Day 9: Undo Buttons for your Agents - Session Rewind 演示

这个示例展示了 ADK 的 Session Rewind（会话回溯）功能：
1. 创建会话并设置初始状态
2. 修改状态
3. 使用 rewind 回溯到之前的状态
4. 验证状态已恢复

这个功能可以用来实现：
- "编辑消息" 功能
- "重新生成" 功能
- 任何需要撤销的场景
"""

import asyncio

import agent
from google.adk.agents.run_config import RunConfig
from google.adk.events.event import Event
from google.adk.runners import InMemoryRunner
from google.genai import types

APP_NAME = "rewind_demo"
USER_ID = "demo_user"


async def call_agent(
    runner: InMemoryRunner, user_id: str, session_id: str, prompt: str
) -> list[Event]:
    """调用 Agent 并返回事件列表"""
    print(f"\n👤 用户: {prompt}")
    content = types.Content(
        role="user", parts=[types.Part.from_text(text=prompt)]
    )
    events = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
        run_config=RunConfig(),
    ):
        events.append(event)
        if event.content and event.author and event.author != "user":
            for part in event.content.parts:
                if part.text:
                    print(f"  🤖 Agent: {part.text}")
                elif part.function_call:
                    print(f"    🛠️ 工具调用: {part.function_call.name}")
                elif part.function_response:
                    print(f"    📦 工具响应: {part.function_response.response}")
    return events


async def main():
    """演示 Session Rewind 功能"""
    print("=" * 60)
    print("🎯 Day 9: Session Rewind (会话回溯) 功能演示")
    print("=" * 60)

    # 创建 Runner
    runner = InMemoryRunner(
        agent=agent.root_agent,
        app_name=APP_NAME,
    )

    # 创建会话
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID
    )
    print(f"\n📝 创建会话: {session.id}")

    # ===== 步骤 1: 初始化状态 =====
    print("\n" + "=" * 60)
    print("步骤 1: 初始化状态")
    print("=" * 60)
    await call_agent(runner, USER_ID, session.id, "设置状态 color 为 red")
    await call_agent(runner, USER_ID, session.id, "保存文件 note.txt 内容为 version1")

    # ===== 步骤 2: 检查当前状态 =====
    print("\n" + "=" * 60)
    print("步骤 2: 检查当前状态")
    print("=" * 60)
    await call_agent(runner, USER_ID, session.id, "查询状态 color 的值")
    await call_agent(runner, USER_ID, session.id, "读取文件 note.txt")

    # ===== 步骤 3: 修改状态 (这是我们要回溯的点) =====
    print("\n" + "=" * 60)
    print("步骤 3: 修改状态 (⚠️ 这是回溯点)")
    print("=" * 60)
    events_update = await call_agent(
        runner, USER_ID, session.id, "更新状态 color 为 blue"
    )
    rewind_invocation_id = events_update[0].invocation_id
    print(f"\n📌 记录回溯点 invocation_id: {rewind_invocation_id}")

    await call_agent(runner, USER_ID, session.id, "保存文件 note.txt 内容为 version2")

    # ===== 步骤 4: 检查修改后的状态 =====
    print("\n" + "=" * 60)
    print("步骤 4: 检查修改后的状态")
    print("=" * 60)
    await call_agent(runner, USER_ID, session.id, "查询状态 color 的值")
    await call_agent(runner, USER_ID, session.id, "读取文件 note.txt")

    # ===== 步骤 5: 执行回溯 =====
    print("\n" + "=" * 60)
    print("步骤 5: ⏪ 执行 REWIND 回溯")
    print("=" * 60)
    print(f"回溯到 invocation_id: {rewind_invocation_id} 之前...")
    await runner.rewind_async(
        user_id=USER_ID,
        session_id=session.id,
        rewind_before_invocation_id=rewind_invocation_id,
    )
    print("✅ 回溯完成！")

    # ===== 步骤 6: 验证回溯后的状态 =====
    print("\n" + "=" * 60)
    print("步骤 6: 验证回溯后的状态")
    print("=" * 60)
    await call_agent(runner, USER_ID, session.id, "查询状态 color 的值")
    await call_agent(runner, USER_ID, session.id, "读取文件 note.txt")

    # ===== 总结 =====
    print("\n" + "=" * 60)
    print("✨ 演示完成！")
    print("=" * 60)
    print("""
🔑 核心要点:
1. 使用 runner.rewind_async() 可以回溯会话状态
2. 需要指定 rewind_before_invocation_id 来确定回溯点
3. 回溯会恢复状态（state）和文件（artifacts）
4. 这个功能可以用来实现"撤销"、"编辑消息"、"重新生成"等功能

📚 文档链接:
- ADK Session Rewind: https://google.github.io/adk-docs/sessions/rewind/
- ADK Runtime Resume: https://google.github.io/adk-docs/runtime/resume/
""")


if __name__ == "__main__":
    asyncio.run(main())
