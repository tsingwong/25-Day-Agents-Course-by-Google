"""
Day 14: Remote Agent (A2A Server)

这是一个专业的翻译 Agent，通过 A2A 协议对外提供服务。
其他 Agent 可以通过 A2A 协议调用它来完成翻译任务。

运行方式:
    python -m remote_agent.agent
    或
    uvicorn remote_agent.agent:app --host localhost --port 8001
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载 .env 文件中的环境变量
from dotenv import load_dotenv
# 从项目根目录加载 .env
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(project_root, ".env"))

from google.adk.agents import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

# ============================================================
# 1. 定义远程 Agent - 专业翻译助手
# ============================================================

translator_agent = LlmAgent(
    name="translator",
    description="专业多语言翻译 Agent - 精通中、英、日、韩、法、德等多种语言的翻译服务",
    model="gemini-2.0-flash",
    instruction="""你是一位专业的多语言翻译专家。

你的能力：
- 精通中文、英文、日文、韩文、法文、德文等主流语言
- 能够准确理解原文的语境和文化背景
- 翻译时保持原文的风格和语气
- 可以处理技术文档、商务文件、文学作品等不同类型的内容

翻译原则：
1. 信：准确传达原文的意思
2. 达：翻译通顺流畅
3. 雅：保持文字的优美和得体

当用户提供文本时：
- 首先识别源语言
- 询问目标语言（如果用户没有指定）
- 提供高质量的翻译结果
- 必要时提供翻译说明或文化背景解释

示例：
用户：请把 "Hello, how are you?" 翻译成中文
回复：你好，你怎么样？/ 你好，最近好吗？（更口语化的表达）
""",
)

# ============================================================
# 2. 使用 to_a2a() 将 Agent 转换为 A2A 服务
# ============================================================

# 关键函数：to_a2a()
# 这是 ADK 提供的便捷方法，只需一行代码即可将 Agent 转换为 A2A 兼容的服务
# 它会自动：
#   - 创建 Agent Card（描述 Agent 能力的元数据）
#   - 设置 HTTP 端点
#   - 处理 A2A 协议的请求/响应转换

app = to_a2a(
    agent=translator_agent,
    host="localhost",
    port=8001,
    protocol="http"
)

# ============================================================
# 3. 启动服务
# ============================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("Day 14: A2A Remote Agent - 翻译服务")
    print("=" * 60)
    print()
    print("Agent 信息:")
    print(f"  名称: {translator_agent.name}")
    print(f"  描述: {translator_agent.description}")
    print()
    print("A2A 服务端点:")
    print("  URL: http://localhost:8001")
    print("  Agent Card: http://localhost:8001/.well-known/agent.json")
    print()
    print("提示: 在另一个终端运行 host_agent 来测试 A2A 通信")
    print("=" * 60)
    print()

    # 启动 uvicorn 服务器
    uvicorn.run(app, host="localhost", port=8001)
