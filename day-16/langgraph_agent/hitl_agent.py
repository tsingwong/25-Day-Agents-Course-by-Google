"""
Human-in-the-Loop Agent - 生产级实现

核心功能:
1. 敏感操作前请求人类审批
2. 支持断点续跑（服务重启后可继续）
3. 审批超时自动拒绝
4. 完整的状态追踪和日志

工作流程:
┌─────────┐    ┌──────────┐    ┌─────────┐    ┌────────┐
│ Analyze │ ─► │ Classify │ ─► │ Human   │ ─► │Execute │
│ Request │    │ Risk     │    │ Review  │    │ Action │
└─────────┘    └──────────┘    └─────────┘    └────────┘
                    │               │
                    │ Low Risk      │ Rejected
                    └───────────────┴──────► [END]

使用场景:
- 敏感数据操作（删除、修改）
- 外部 API 调用（支付、发送消息）
- 需要人工确认的决策
"""

import os
import uuid
import logging
from typing import TypedDict, Annotated, Literal, Optional, Any
from operator import add
from dataclasses import dataclass
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .checkpointer import (
    get_checkpointer,
    get_task_store,
    TaskStore,
    TaskMetadata,
    CheckpointerType,
)

logger = logging.getLogger(__name__)


# ============================================================
# 风险等级定义
# ============================================================

class RiskLevel(Enum):
    """操作风险等级"""
    LOW = "low"           # 低风险：直接执行
    MEDIUM = "medium"     # 中风险：记录日志，可配置是否审批
    HIGH = "high"         # 高风险：必须人工审批
    CRITICAL = "critical" # 关键：必须人工审批 + 二次确认


@dataclass
class ActionPlan:
    """执行计划"""
    action_type: str      # 操作类型
    description: str      # 操作描述
    risk_level: RiskLevel # 风险等级
    parameters: dict      # 操作参数
    reason: str           # 执行原因


# ============================================================
# Agent State 定义
# ============================================================

class HITLState(TypedDict):
    """
    Human-in-the-Loop Agent 状态

    设计原则:
    - 完整记录执行过程
    - 支持断点续跑
    - 便于审计追溯
    """
    # 基础信息
    task_id: str
    thread_id: str

    # 消息历史
    messages: Annotated[list, add]

    # 分析结果
    analysis: str           # 问题分析
    action_plan: dict       # 执行计划（ActionPlan 序列化）
    risk_level: str         # 风险等级

    # 审批相关
    requires_approval: bool # 是否需要审批
    approval_status: str    # pending, approved, rejected, timeout
    approval_comment: str   # 审批意见
    approver: str           # 审批人

    # 执行结果
    execution_result: str   # 执行结果
    final_answer: str       # 最终回答

    # 控制
    iteration: int
    error: str              # 错误信息


# ============================================================
# LLM 配置
# ============================================================

def get_llm(temperature: float = 0.3):
    """获取 LLM 实例（低温度用于决策）"""
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=temperature,
    )


# ============================================================
# 节点实现
# ============================================================

def analyze_request_node(state: HITLState) -> dict:
    """
    分析请求节点 - 理解用户意图并生成执行计划

    这是流程的第一步，负责:
    1. 理解用户请求
    2. 生成执行计划
    3. 评估风险等级
    """
    logger.info(f"[{state.get('task_id')}] Analyzing request...")

    llm = get_llm(temperature=0.3)

    # 获取用户输入
    messages = state.get("messages", [])
    user_input = ""
    for msg in messages:
        if isinstance(msg, dict) and msg.get("role") == "user":
            user_input = msg.get("content", "")
            break
        elif isinstance(msg, HumanMessage):
            user_input = msg.content
            break

    # 分析提示词
    analysis_prompt = f"""分析以下用户请求，生成执行计划并评估风险。

用户请求: {user_input}

请按以下 JSON 格式输出（不要包含 markdown 代码块标记）:
{{
    "analysis": "对请求的理解和分析",
    "action_type": "操作类型（如：query_info, modify_data, delete_data, send_message, make_payment）",
    "description": "具体要执行的操作描述",
    "risk_level": "风险等级（low/medium/high/critical）",
    "parameters": {{}},
    "reason": "为什么要执行这个操作",
    "requires_approval": true/false
}}

风险评估标准:
- low: 只读查询，无副作用
- medium: 数据修改，可撤销
- high: 数据删除、外部 API 调用、发送消息
- critical: 涉及支付、批量操作、不可逆操作

示例:
- "查询天气" -> low, requires_approval: false
- "修改我的用户名" -> medium, requires_approval: false
- "删除我的账号" -> critical, requires_approval: true
- "给所有用户发送通知" -> critical, requires_approval: true
"""

    llm_messages = [
        SystemMessage(content="你是一个安全分析专家，负责评估操作风险并生成执行计划。"),
        HumanMessage(content=analysis_prompt),
    ]

    response = llm.invoke(llm_messages)
    response_text = response.content.strip()

    # 清理可能的 markdown 代码块
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])

    try:
        import json
        result = json.loads(response_text)

        return {
            "analysis": result.get("analysis", ""),
            "action_plan": {
                "action_type": result.get("action_type", "unknown"),
                "description": result.get("description", ""),
                "risk_level": result.get("risk_level", "medium"),
                "parameters": result.get("parameters", {}),
                "reason": result.get("reason", ""),
            },
            "risk_level": result.get("risk_level", "medium"),
            "requires_approval": result.get("requires_approval", True),
            "iteration": state.get("iteration", 0) + 1,
        }
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {e}")
        # 保守策略：解析失败时要求审批
        return {
            "analysis": response_text,
            "action_plan": {
                "action_type": "unknown",
                "description": user_input,
                "risk_level": "high",
                "parameters": {},
                "reason": "无法解析，需要人工判断",
            },
            "risk_level": "high",
            "requires_approval": True,
            "iteration": state.get("iteration", 0) + 1,
        }


def human_review_node(state: HITLState) -> dict:
    """
    人工审批节点 - 等待人工审批

    这个节点会:
    1. 将任务状态更新为 waiting_approval
    2. 图执行会在这里中断
    3. 等待外部 API 调用 approve/reject
    4. 审批后继续执行

    注意：实际的等待逻辑由外部控制，这里只负责状态更新
    """
    task_id = state.get("task_id", "")
    logger.info(f"[{task_id}] Entering human review node...")

    # 更新任务状态
    task_store = get_task_store()
    task_store.update_task(
        task_id,
        status="waiting_approval",
        current_node="human_review",
        pending_action=state.get("action_plan", {}).get("description", ""),
    )

    # 如果已经有审批结果（恢复执行时），直接返回
    if state.get("approval_status") in ["approved", "rejected", "timeout"]:
        logger.info(f"[{task_id}] Already has approval status: {state.get('approval_status')}")
        return {}

    # 标记等待审批
    return {
        "approval_status": "pending",
    }


def execute_action_node(state: HITLState) -> dict:
    """
    执行操作节点 - 执行已批准的操作

    安全检查:
    1. 再次验证审批状态
    2. 记录执行日志
    3. 执行操作并返回结果
    """
    task_id = state.get("task_id", "")
    logger.info(f"[{task_id}] Executing action...")

    # 安全检查：确保已获得批准
    approval_status = state.get("approval_status", "")
    requires_approval = state.get("requires_approval", True)

    if requires_approval and approval_status != "approved":
        error_msg = f"Cannot execute: approval_status={approval_status}"
        logger.error(f"[{task_id}] {error_msg}")
        return {
            "execution_result": "",
            "error": error_msg,
        }

    # 获取执行计划
    action_plan = state.get("action_plan", {})
    action_type = action_plan.get("action_type", "unknown")

    # 模拟执行（实际场景中这里会调用真实的服务）
    # 这里演示不同类型操作的处理
    result = _simulate_action_execution(action_type, action_plan)

    # 更新任务状态
    task_store = get_task_store()
    task_store.update_task(
        task_id,
        status="completed",
        current_node="execute_action",
    )

    logger.info(f"[{task_id}] Action executed successfully")
    return {
        "execution_result": result,
    }


def _simulate_action_execution(action_type: str, action_plan: dict) -> str:
    """模拟执行操作（演示用）"""
    description = action_plan.get("description", "")

    # 不同操作类型的模拟响应
    simulations = {
        "query_info": f"查询完成: {description}",
        "modify_data": f"数据修改成功: {description}",
        "delete_data": f"数据删除成功: {description}",
        "send_message": f"消息发送成功: {description}",
        "make_payment": f"支付操作完成: {description}",
    }

    return simulations.get(action_type, f"操作完成: {description}")


def generate_response_node(state: HITLState) -> dict:
    """
    生成响应节点 - 根据执行结果生成最终回答
    """
    task_id = state.get("task_id", "")
    logger.info(f"[{task_id}] Generating response...")

    llm = get_llm(temperature=0.5)

    # 构建上下文
    messages = state.get("messages", [])
    user_input = ""
    for msg in messages:
        if isinstance(msg, dict) and msg.get("role") == "user":
            user_input = msg.get("content", "")
            break
        elif isinstance(msg, HumanMessage):
            user_input = msg.content
            break

    analysis = state.get("analysis", "")
    action_plan = state.get("action_plan", {})
    approval_status = state.get("approval_status", "")
    approval_comment = state.get("approval_comment", "")
    execution_result = state.get("execution_result", "")
    error = state.get("error", "")

    # 根据不同情况生成响应
    if error:
        context = f"""
用户请求: {user_input}
分析结果: {analysis}
错误信息: {error}
"""
        system_msg = "用户的请求遇到了问题，请礼貌地解释情况并提供建议。"

    elif approval_status == "rejected":
        context = f"""
用户请求: {user_input}
分析结果: {analysis}
执行计划: {action_plan.get('description', '')}
审批结果: 被拒绝
审批意见: {approval_comment}
"""
        system_msg = "用户的请求被拒绝，请礼貌地解释原因并提供替代方案。"

    elif approval_status == "timeout":
        context = f"""
用户请求: {user_input}
分析结果: {analysis}
执行计划: {action_plan.get('description', '')}
审批结果: 超时未审批
"""
        system_msg = "用户的请求因等待审批超时而未能执行，请解释情况。"

    else:
        context = f"""
用户请求: {user_input}
分析结果: {analysis}
执行计划: {action_plan.get('description', '')}
执行结果: {execution_result}
"""
        system_msg = "请根据执行结果，给用户一个清晰、有帮助的回复。"

    llm_messages = [
        SystemMessage(content=system_msg),
        HumanMessage(content=context),
    ]

    response = llm.invoke(llm_messages)

    return {
        "final_answer": response.content,
    }


def handle_rejection_node(state: HITLState) -> dict:
    """
    处理拒绝节点 - 当操作被拒绝或超时时
    """
    task_id = state.get("task_id", "")
    logger.info(f"[{task_id}] Handling rejection...")

    task_store = get_task_store()
    task_store.update_task(
        task_id,
        status="rejected",
        current_node="handle_rejection",
    )

    return {}


# ============================================================
# 路由函数
# ============================================================

def route_after_analysis(state: HITLState) -> Literal["human_review", "execute", "respond"]:
    """
    分析后路由 - 决定是否需要人工审批

    路由逻辑:
    - 需要审批 -> human_review
    - 不需要审批 -> execute
    """
    requires_approval = state.get("requires_approval", True)
    risk_level = state.get("risk_level", "medium")

    # 强制审批的风险等级
    if risk_level in ["high", "critical"]:
        logger.info(f"[{state.get('task_id')}] High risk, requires approval")
        return "human_review"

    if requires_approval:
        logger.info(f"[{state.get('task_id')}] Approval required")
        return "human_review"

    logger.info(f"[{state.get('task_id')}] Low risk, direct execution")
    return "execute"


def route_after_review(state: HITLState) -> Literal["execute", "reject", "wait"]:
    """
    审批后路由 - 根据审批结果决定下一步

    路由逻辑:
    - approved -> execute
    - rejected/timeout -> reject
    - pending -> wait（实际上会中断）
    """
    approval_status = state.get("approval_status", "pending")

    if approval_status == "approved":
        logger.info(f"[{state.get('task_id')}] Approved, proceeding to execute")
        return "execute"
    elif approval_status in ["rejected", "timeout"]:
        logger.info(f"[{state.get('task_id')}] Rejected/timeout, handling rejection")
        return "reject"
    else:
        # pending 状态 - 图会在这里中断等待
        logger.info(f"[{state.get('task_id')}] Waiting for approval")
        return "wait"


# ============================================================
# 创建 Human-in-the-Loop Graph
# ============================================================

def create_hitl_graph(checkpointer: Optional[BaseCheckpointSaver] = None):
    """
    创建 Human-in-the-Loop Agent Graph

    图结构:
    ┌─────────┐
    │  START  │
    └────┬────┘
         │
         ▼
    ┌─────────┐
    │ Analyze │
    └────┬────┘
         │
         ▼
    ┌─────────────────┐
    │ Route: Approval │
    │    Required?    │
    └────┬───────┬────┘
         │       │
    No   │       │ Yes
         │       ▼
         │  ┌─────────┐
         │  │ Human   │◄───────┐
         │  │ Review  │        │
         │  └────┬────┘        │
         │       │             │
         │       ▼             │
         │  ┌──────────────┐   │
         │  │Route: Status │   │
         │  └──┬───────┬───┘   │
         │     │       │       │
         │ Approved  Rejected  │ Pending
         │     │       │       │ (interrupt)
         │     │       ▼       │
         │     │  ┌────────┐   │
         │     │  │ Handle │   │
         │     │  │Rejection│  │
         │     │  └────┬───┘   │
         │     │       │       │
         ▼     ▼       │       │
    ┌─────────┐        │       │
    │ Execute │        │       │
    └────┬────┘        │       │
         │             │       │
         ▼             │       │
    ┌─────────┐        │       │
    │ Respond │◄───────┘       │
    └────┬────┘                │
         │                     │
         ▼                     │
    ┌─────────┐                │
    │   END   │                │
    └─────────┘
    """
    # 使用提供的 checkpointer 或获取默认的
    if checkpointer is None:
        checkpointer = get_checkpointer()

    # 创建图
    graph = StateGraph(HITLState)

    # 添加节点
    graph.add_node("analyze", analyze_request_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("execute", execute_action_node)
    graph.add_node("handle_rejection", handle_rejection_node)
    graph.add_node("respond", generate_response_node)

    # 设置入口
    graph.set_entry_point("analyze")

    # 分析后的条件路由
    graph.add_conditional_edges(
        "analyze",
        route_after_analysis,
        {
            "human_review": "human_review",
            "execute": "execute",
            "respond": "respond",
        }
    )

    # 审批后的条件路由
    graph.add_conditional_edges(
        "human_review",
        route_after_review,
        {
            "execute": "execute",
            "reject": "handle_rejection",
            "wait": END,  # pending 时中断，等待外部更新后恢复
        }
    )

    # 执行后生成响应
    graph.add_edge("execute", "respond")

    # 拒绝后也生成响应
    graph.add_edge("handle_rejection", "respond")

    # 响应后结束
    graph.add_edge("respond", END)

    # 编译图，配置中断点和 checkpointer
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],  # 在人工审批前中断
    )


# ============================================================
# 运行入口
# ============================================================

def run_hitl_agent(
    user_input: str,
    task_id: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> dict:
    """
    运行 Human-in-the-Loop Agent

    Args:
        user_input: 用户输入
        task_id: 任务 ID（可选，默认自动生成）
        thread_id: 线程 ID（可选，默认自动生成）

    Returns:
        包含执行结果的字典
    """
    # 生成 ID
    task_id = task_id or str(uuid.uuid4())
    thread_id = thread_id or str(uuid.uuid4())

    logger.info(f"Starting HITL agent: task_id={task_id}, thread_id={thread_id}")

    # 创建任务记录
    task_store = get_task_store()
    task_store.create_task(task_id, thread_id, user_input)

    # 创建图
    agent = create_hitl_graph()

    # 准备初始状态
    initial_state = {
        "task_id": task_id,
        "thread_id": thread_id,
        "messages": [{"role": "user", "content": user_input}],
        "analysis": "",
        "action_plan": {},
        "risk_level": "",
        "requires_approval": False,
        "approval_status": "",
        "approval_comment": "",
        "approver": "",
        "execution_result": "",
        "final_answer": "",
        "iteration": 0,
        "error": "",
    }

    # 配置
    config = {"configurable": {"thread_id": thread_id}}

    # 执行图
    result = agent.invoke(initial_state, config)

    return {
        "task_id": task_id,
        "thread_id": thread_id,
        "status": task_store.get_task(task_id).status if task_store.get_task(task_id) else "unknown",
        "result": result,
    }


def resume_after_approval(
    task_id: str,
    thread_id: str,
    approved: bool,
    comment: str = "",
    approver: str = "system",
) -> dict:
    """
    审批后恢复执行

    Args:
        task_id: 任务 ID
        thread_id: 线程 ID
        approved: 是否批准
        comment: 审批意见
        approver: 审批人

    Returns:
        执行结果
    """
    logger.info(f"Resuming task {task_id} after approval: approved={approved}")

    # 更新任务状态
    task_store = get_task_store()
    approval_status = "approved" if approved else "rejected"
    task_store.update_task(
        task_id,
        status=approval_status,
        approval_status=approval_status,
    )

    # 创建图
    agent = create_hitl_graph()

    # 配置
    config = {"configurable": {"thread_id": thread_id}}

    # 更新状态并恢复执行
    # 注入审批结果
    update_state = {
        "approval_status": approval_status,
        "approval_comment": comment,
        "approver": approver,
    }

    # 使用 update_state 更新图状态
    agent.update_state(config, update_state)

    # 恢复执行（从中断点继续）
    result = agent.invoke(None, config)

    return {
        "task_id": task_id,
        "thread_id": thread_id,
        "status": task_store.get_task(task_id).status if task_store.get_task(task_id) else "unknown",
        "result": result,
    }
