# Day 9: Undo Buttons for your Agents - Session Rewind
#
# ADK 内置了"时间旅行"功能，让你可以实现：
# - 编辑消息（Edit Message）
# - 重新生成（Regenerate）
# - 撤销操作（Undo）

from google.adk import Agent
from google.adk.tools.tool_context import ToolContext
from google.genai import types


async def update_state(tool_context: ToolContext, key: str, value: str) -> dict:
    """更新状态值"""
    tool_context.state[key] = value
    return {"status": f"已更新 '{key}' 为 '{value}'"}


async def load_state(tool_context: ToolContext, key: str) -> dict:
    """读取状态值"""
    return {key: tool_context.state.get(key, "未找到")}


async def save_artifact(
    tool_context: ToolContext, filename: str, content: str
) -> dict:
    """保存文件内容"""
    artifact_bytes = content.encode("utf-8")
    artifact_part = types.Part(
        inline_data=types.Blob(mime_type="text/plain", data=artifact_bytes)
    )
    version = await tool_context.save_artifact(filename, artifact_part)
    return {"status": "成功", "filename": filename, "version": version}


async def load_artifact(tool_context: ToolContext, filename: str) -> dict:
    """读取文件内容"""
    artifact = await tool_context.load_artifact(filename)
    if not artifact:
        return {"error": f"文件 '{filename}' 未找到"}
    content = artifact.inline_data.data.decode("utf-8")
    return {"filename": filename, "content": content}


# 创建 Agent
root_agent = Agent(
    name="state_agent",
    model="gemini-2.0-flash",
    instruction="""你是一个状态和文件管理 Agent。

    你可以：
    - 更新状态值 (update_state)
    - 读取状态值 (load_state)
    - 保存文件 (save_artifact)
    - 读取文件 (load_artifact)

    根据用户的请求使用相应的工具。""",
    tools=[
        update_state,
        load_state,
        save_artifact,
        load_artifact,
    ],
)
