"""
Day 16: LangGraph + A2A Agent

这个示例展示了如何:
1. 使用 LangGraph 构建一个 ReAct 推理图
2. 将其包装为 ADK Agent
3. 通过 ADK 的 to_a2a() 对外提供 A2A 服务

运行方式:
    python -m langgraph_agent.agent
"""

import os
import sys
from typing import TypedDict, Annotated, Literal
from operator import add

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载 .env 文件中的环境变量
from dotenv import load_dotenv
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(project_root, ".env"))

# LangGraph 相关导入
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# ADK 相关导入 (用于 A2A 服务)
from google.adk.agents import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a


# ============================================================
# Part 1: LangGraph ReAct Agent 实现
# ============================================================

class AgentState(TypedDict):
    """
    LangGraph Agent 的状态定义

    这是 LangGraph 的核心概念之一：State
    状态在图的所有节点之间共享，每个节点可以读取和更新状态
    """
    # 消息历史 - 使用 Annotated 和 add 操作符实现消息追加
    messages: Annotated[list, add]
    # 思考过程记录
    thoughts: list
    # 最终答案
    final_answer: str
    # 迭代次数（防止无限循环）
    iteration: int


def get_llm():
    """获取 Google Gemini LLM 实例"""
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.7,
    )


def reasoning_node(state: AgentState) -> dict:
    """
    推理节点 - ReAct 模式中的 "Thought" 步骤

    这是 LangGraph 的核心概念之一：Node
    节点是执行具体逻辑的函数，接收状态，返回状态更新
    """
    llm = get_llm()

    system_prompt = """你是一个善于分析问题的 AI 助手。

请按照以下格式思考：
1. 分析问题的核心需求
2. 思考需要什么信息来回答
3. 决定是直接回答还是需要更多分析

如果你已经有足够信息回答问题，请在回复开头加上 [FINAL]
如果需要继续分析，请在回复开头加上 [CONTINUE]"""

    messages = state.get("messages", [])
    thoughts = state.get("thoughts", [])
    iteration = state.get("iteration", 0)

    # 构建 LLM 消息
    llm_messages = [SystemMessage(content=system_prompt)]

    for msg in messages:
        if isinstance(msg, dict):
            if msg.get("role") == "user":
                llm_messages.append(HumanMessage(content=msg.get("content", "")))
            else:
                llm_messages.append(AIMessage(content=msg.get("content", "")))
        elif isinstance(msg, (HumanMessage, AIMessage)):
            llm_messages.append(msg)

    # 添加之前的思考过程
    if thoughts:
        thought_summary = "\n".join([f"思考 {i+1}: {t}" for i, t in enumerate(thoughts)])
        llm_messages.append(SystemMessage(content=f"之前的思考：\n{thought_summary}"))

    # 调用 LLM
    response = llm.invoke(llm_messages)
    thought = response.content
    new_thoughts = thoughts + [thought]

    # 判断是否结束
    if "[FINAL]" in thought or iteration >= 2:
        return {
            "thoughts": new_thoughts,
            "iteration": iteration + 1,
        }
    else:
        return {
            "thoughts": new_thoughts,
            "iteration": iteration + 1,
        }


def answer_node(state: AgentState) -> dict:
    """
    回答节点 - 生成最终答案
    """
    llm = get_llm()

    messages = state.get("messages", [])
    thoughts = state.get("thoughts", [])

    # 提取原始问题
    original_question = ""
    for msg in messages:
        if isinstance(msg, dict) and msg.get("role") == "user":
            original_question = msg.get("content", "")
            break
        elif isinstance(msg, HumanMessage):
            original_question = msg.content
            break

    # 构建最终回答提示
    thought_summary = "\n".join([f"- {t}" for t in thoughts]) if thoughts else "（直接回答）"

    final_prompt = f"""用户问题：{original_question}

分析过程：
{thought_summary}

请基于以上分析，给出清晰、准确、有帮助的最终回答："""

    llm_messages = [
        SystemMessage(content="你是一个专业的 AI 助手，请简洁明了地回答用户问题。"),
        HumanMessage(content=final_prompt),
    ]

    response = llm.invoke(llm_messages)

    return {"final_answer": response.content}


def should_continue(state: AgentState) -> Literal["continue", "answer"]:
    """
    路由函数 - 决定下一步执行哪个节点

    这是 LangGraph 的核心概念之一：Conditional Edge
    条件边基于当前状态动态决定控制流
    """
    thoughts = state.get("thoughts", [])
    iteration = state.get("iteration", 0)

    if not thoughts:
        return "continue"

    last_thought = thoughts[-1] if thoughts else ""

    # 如果达到最大迭代次数或决定回答
    if "[FINAL]" in last_thought or iteration >= 2:
        return "answer"

    return "continue"


def create_langgraph_agent():
    """
    创建 LangGraph Agent

    展示 LangGraph 的核心构建流程：
    1. 创建 StateGraph
    2. 添加节点 (Nodes)
    3. 定义边 (Edges)，包括条件边
    4. 设置入口点
    5. 编译图
    """
    # 创建状态图
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("reasoning", reasoning_node)
    graph.add_node("answer", answer_node)

    # 设置入口点
    graph.set_entry_point("reasoning")

    # 添加条件边 - 这是 LangGraph 实现动态控制流的关键
    graph.add_conditional_edges(
        "reasoning",
        should_continue,
        {
            "continue": "reasoning",  # 继续推理
            "answer": "answer",       # 生成答案
        }
    )

    # 添加结束边
    graph.add_edge("answer", END)

    # 编译图
    return graph.compile()


def run_langgraph(user_input: str) -> str:
    """
    运行 LangGraph Agent

    这个函数可以被 ADK Agent 的工具调用
    """
    agent = create_langgraph_agent()

    # 准备输入状态
    input_state = {
        "messages": [{"role": "user", "content": user_input}],
        "thoughts": [],
        "final_answer": "",
        "iteration": 0,
    }

    # 执行图
    result = agent.invoke(input_state)

    return result.get("final_answer", "抱歉，我无法处理这个请求。")


# ============================================================
# Part 2: 使用 ADK 将 LangGraph Agent 包装为 A2A 服务
# ============================================================

# 创建 ADK Agent，内部调用 LangGraph
# 这展示了如何将 LangGraph 的复杂推理能力与 ADK 的 A2A 服务能力结合

langgraph_adk_agent = LlmAgent(
    name="langgraph_react_agent",
    description="基于 LangGraph 构建的 ReAct 推理 Agent - 能够进行多步骤推理分析，深思熟虑后给出答案",
    model="gemini-2.0-flash",
    instruction="""你是一个强大的 AI 助手，具有深度推理能力。

你的特点：
- 使用 ReAct (Reasoning + Acting) 模式进行思考
- 能够分析复杂问题，进行多步骤推理
- 在回答前会仔细思考，确保答案的准确性和有用性

当用户提问时，你会：
1. 先分析问题的核心需求
2. 思考需要什么信息或知识来回答
3. 给出清晰、准确、有帮助的答案

你擅长：
- 技术问题解答（编程、架构、AI/ML 等）
- 概念解释和对比分析
- 问题分析和解决方案建议
""",
)

# 使用 ADK 的 to_a2a() 将 Agent 转换为 A2A 服务
# 这是最简单可靠的方式，ADK 会自动处理所有 A2A 协议细节
app = to_a2a(
    agent=langgraph_adk_agent,
    host="localhost",
    port=8016,
    protocol="http"
)


# ============================================================
# Part 3: 独立的 LangGraph 演示（不使用 A2A）
# ============================================================

def demo_langgraph_only():
    """
    纯 LangGraph 演示，不涉及 A2A
    用于理解 LangGraph 的工作原理
    """
    print("\n" + "=" * 60)
    print("LangGraph ReAct Agent 演示")
    print("=" * 60)

    test_questions = [
        "什么是 LangGraph？它和 LangChain 有什么关系？",
        "解释一下 ReAct 模式是什么？",
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"\n问题 {i}: {question}")
        print("-" * 40)

        answer = run_langgraph(question)
        print(f"回答: {answer[:500]}...")
        print("-" * 40)


# ============================================================
# 主程序
# ============================================================

if __name__ == "__main__":
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="Day 16: LangGraph + A2A")
    parser.add_argument("--demo", action="store_true", help="运行纯 LangGraph 演示（不启动 A2A 服务）")
    args = parser.parse_args()

    if args.demo:
        # 纯 LangGraph 演示模式
        demo_langgraph_only()
    else:
        # A2A 服务模式
        print("=" * 60)
        print("Day 16: LangGraph + A2A")
        print("=" * 60)
        print()
        print("Agent 信息:")
        print(f"  名称: {langgraph_adk_agent.name}")
        print(f"  框架: LangGraph + ADK")
        print(f"  模式: ReAct (Reasoning + Acting)")
        print()
        print("A2A 服务端点:")
        print("  URL: http://localhost:8016")
        print("  Agent Card: http://localhost:8016/.well-known/agent.json")
        print()
        print("提示:")
        print("  - 运行客户端: python -m client.test_client")
        print("  - 纯 LangGraph 演示: python -m langgraph_agent.agent --demo")
        print("=" * 60)
        print()

        # 启动 A2A 服务
        uvicorn.run(app, host="localhost", port=8016)
